import asyncio
from typing import Literal, TypedDict
from google import genai
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from app.mcp.client import search_web_via_mcp
from app.core.config import settings
from app.rag.retriever import RAGRetriever
import traceback

MODEL_ID = "gemini-3.5-flash-lite"


# Helper: Hard 10-second timeout so Google 503 retries never hang your request
async def call_gemini(prompt: str, timeout_seconds: float = 10.0) -> str | None:
    if not settings.GEMINI_API_KEY:
        return None
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
            ),
            timeout=timeout_seconds,
        )
        return (response.text or "").strip()
    except asyncio.TimeoutError:
        print(f"[WARN] Gemini call timed out after {timeout_seconds}s (Google server busy).")
        return None
    except Exception as e:
        print(f"[WARN] Gemini API error: {e}")
        return None


# 1. The Clipboard: Holds state across the entire graph
# 1. Update ResearchState to include 'sources'
class ResearchState(TypedDict):
    original_query: str
    search_query: str
    db: AsyncSession
    context: list[str]
    sources: list[str]
    retry_count: int
    is_relevant: bool
    report: str


# 2. Update Station 1 (retrieve_node) to return both context and clean source labels
async def retrieve_node(state: ResearchState) -> dict:
    query_to_use = state.get("search_query") or state["original_query"]
    print(f"--> [Station 1: Retrieve] Searching database for: '{query_to_use}'")
    docs = await RAGRetriever.search_similar(
        db=state["db"],
        query=query_to_use,
        top_k=3,
    )
    formatted_docs = [
        f"Source: {doc.title} ({doc.source})\nContent: {doc.content}"
        for doc in docs
    ]
    source_list = [f"{doc.title} ({doc.source})" for doc in docs]

    return {
        "search_query": query_to_use,
        "context": formatted_docs,
        "sources": source_list,
    }


# 3. Station 2: Fast local relevance check (0 extra API calls, 0 seconds wait)
async def grade_documents_node(state: ResearchState) -> dict:
    print("--> [Station 2: Grade] Checking retrieved documents...")
    if not state["context"]:
        return {"is_relevant": False}

    # Check if any meaningful keyword (4+ letters) from the question appears in the docs
    query_words = [
        w.lower().strip("?.,!")
        for w in state["original_query"].split()
        if len(w) >= 4
    ]
    combined_docs = " ".join(state["context"]).lower()

    has_keyword_match = any(word in combined_docs for word in query_words)
    print(f"--> [Station 2: Grade] Keyword match found: {has_keyword_match}")
    return {"is_relevant": has_keyword_match}


# 4. Station 3 (Loop): Rewrite the search query if first search missed
async def rewrite_query_node(state: ResearchState) -> dict:
    print("--> [Station 3: Rewrite] Rewriting query for better search...")
    prompt = (
        "Rewrite this engineering question into 3-5 core search keywords "
        "(e.g., 'checkout latency redis outage'). Respond with ONLY the keywords.\n\n"
        f"Question: {state['original_query']}"
    )

    rewritten = await call_gemini(prompt, timeout_seconds=8.0)
    return {
        "search_query": rewritten or state["original_query"],
        "retry_count": state.get("retry_count", 0) + 1,
    }

async def web_search_node(state: ResearchState) -> dict:

    search_query = state.get("search_query") or state["original_query"]

    print(f"--> [Station 3.5: MCP Web Search] Searching for: '{search_query}'")

    try:
        response = await search_web_via_mcp(
            query=search_query,
            max_results=6,
        )

        if not response.get("success"):
            raise RuntimeError(
                response.get("error", "Web search failed")
            )

        results = response.get("results", [])

        print(f"--> [MCP Web Search] Found {len(results)} results.")

    except Exception as e:
     print(f"[WARN] MCP web search failed: {e}")
     traceback.print_exc()
     results = []

    if not results:
        return {
            "context": state.get("context", []),
            "sources": state.get("sources", []),
        }

    web_context = "\n\n".join(
        [
            f"Title: {r.get('title', 'Web Result')}\n"
            f"URL: {r.get('url', '')}\n"
            f"Snippet: {r.get('snippet', '')}"
            for r in results
        ]
    )

    web_sources = [
        r["url"] for r in results if r.get("url")
    ]

    current_context = list(state.get("context", [])) #retrieves the previously stored context.Ex-->> context from the local_document.pdf
    current_sources = list(state.get("sources", [])) #retrieves the previously stored sources from the state.Ex->>local_document.pdf

    current_context.append(
        f"--- LIVE WEB SEARCH RESULTS ---\n{web_context}"
    )

    return {
        "context": current_context,
        "sources": current_sources + web_sources,
    }



async def synthesize_node(state: ResearchState) -> dict:
    print("--> [Station 4: Synthesize] Calling Gemini to write final report...")
    if not settings.GEMINI_API_KEY:
        return {"report": "Error: GEMINI_API_KEY is missing in your .env file."}

    if state.get("is_relevant"):
        active_context = state.get("context", [])
        active_sources = state.get("sources", [])
    else:
        active_context = [
            c for c in state.get("context", []) if "--- LIVE WEB SEARCH RESULTS ---" in c
        ]
        active_sources = [
            s for s in state.get("sources", []) if s.startswith("http")
        ]

    combined_context = "\n\n".join(active_context)
    context_block = (
        combined_context
        if combined_context
        else "No internal documents or web results matched this query."
    )

    prompt = (
        "You are IntelliOps, a senior research analyst producing structured intelligence briefings.\n"
        "Use ONLY the context provided below. Do not invent facts or numbers.\n\n"
        "Format your report cleanly in Markdown using these exact sections:\n"
        "## Executive Summary\n"
        "A direct, 2-3 sentence answer to the user's question with key figures bolded.\n\n"
        "## Key Findings\n"
        "- Bullet points breaking down specific facts, metrics, dates, or trends found in the sources.\n"
        "- Cite the source inline as [Source Name](URL) or (`filename`) right next to each claim.\n\n"
        "## Data Freshness & Gaps\n"
        "Briefly note any missing details, conflicting numbers across sources, or if real-time data could not be verified.\n\n"
        f"Context:\n{context_block}\n\n"
        f"User Question: {state['original_query']}"
    )

    report = await call_gemini(prompt, timeout_seconds=15.0)

    if report is None:
        return {
            "report": (
                "Note: Gemini API is currently experiencing high traffic (503). "
                "Here is the raw context gathered from your database and live web search:\n\n"
                f"{context_block}"
            ),
            "sources": active_sources,
        }

    return {
        "report": report,
        "sources": active_sources,
    }


def route_after_grading(state: ResearchState) -> str:
    if state.get("is_relevant") or state.get("retry_count", 0) >= 1:
        return "web_search"
    return "rewrite_query"

# 7. Wire up the Stateful Graph
builder = StateGraph(ResearchState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("grade_documents", grade_documents_node)
builder.add_node("rewrite_query", rewrite_query_node)
builder.add_node("web_search", web_search_node)      # <-- New node
builder.add_node("synthesize", synthesize_node)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "grade_documents")
builder.add_conditional_edges("grade_documents", route_after_grading)
builder.add_edge("rewrite_query", "retrieve")
builder.add_edge("web_search", "synthesize")         # <-- Web results feed into synthesize
builder.add_edge("synthesize", END)

research_graph = builder.compile()