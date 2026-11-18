import asyncio
from typing import Literal, TypedDict
from google import genai
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.retriever import RAGRetriever

MODEL_ID = "gemini-3.8-flash"


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


# 5. Station 4: Write the final cited engineering report
async def synthesize_node(state: ResearchState) -> dict:
    print("--> [Station 4: Synthesize] Calling Gemini to write final report...")
    if not settings.GEMINI_API_KEY:
        return {"report": "Error: GEMINI_API_KEY is missing in your .env file."}

    context_block = (
        "\n\n".join(state["context"])
        if state["context"]
        else "No internal company documents matched this query."
    )

    prompt = (
        "You are IntelliOps, a senior engineering research assistant.\n"
        "Answer the user's question clearly using ONLY the internal documents below.\n"
        "Always cite the document title and source file in your answer.\n\n"
        f"Internal Documents:\n{context_block}\n\n"
        f"User Question: {state['original_query']}"
    )

    report = await call_gemini(prompt, timeout_seconds=12.0)
    if report is None:
        return {
            "report": (
                "Note: Gemini API is currently experiencing high traffic (503). "
                "Here is the direct match retrieved from your pgvector database:\n\n"
                f"{context_block}"
            )
        }

    return {"report": report}


# 6. Traffic Cop: Decide whether to synthesize immediately or rewrite & retry once
def route_after_grading(state: ResearchState) -> Literal["synthesize", "rewrite_query"]:
    if state.get("is_relevant", False) or state.get("retry_count", 0) >= 1:
        return "synthesize"
    return "rewrite_query"


# 7. Wire up the Stateful Graph
builder = StateGraph(ResearchState)

builder.add_node("retrieve", retrieve_node)
builder.add_node("grade_documents", grade_documents_node)
builder.add_node("rewrite_query", rewrite_query_node)
builder.add_node("synthesize", synthesize_node)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "grade_documents")
builder.add_conditional_edges("grade_documents", route_after_grading)
builder.add_edge("rewrite_query", "retrieve")
builder.add_edge("synthesize", END)

research_graph = builder.compile()