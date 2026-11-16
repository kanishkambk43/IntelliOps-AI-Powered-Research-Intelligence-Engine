from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.rag.retriever import RAGRetriever


# 1. The Clipboard: Holds all information as it moves from step to step
class ResearchState(TypedDict):
    query: str
    db: AsyncSession
    context: list[str]
    report: str


# 2. Station 1: Search the pgvector database for matching documents
async def retrieve_node(state: ResearchState) -> dict:
    docs = await RAGRetriever.search_similar(
        db=state["db"],
        query=state["query"],
        top_k=3,
    )
    formatted_docs = [
        f"Source: {doc.title} ({doc.source})\nContent: {doc.content}"
        for doc in docs
    ]
    return {"context": formatted_docs}


# 3. Station 2: Use Gemini to read the documents and write the final report
# 3. Station 1 & 2 remain the same, update synthesize_node:
async def synthesize_node(state: ResearchState) -> dict:
    if not settings.GEMINI_API_KEY:
        return {
            "report": "Error: GEMINI_API_KEY is missing in your .env file."
        }

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
    )

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
        f"User Question: {state['query']}"
    )

    response = await llm.ainvoke(prompt)
    
    # Cleanly extract text whether Gemini returns a string or a list of blocks
    content = response.content
    if isinstance(content, list):
        ai_report = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    else:
        ai_report = str(content)

    return {"report": ai_report}


# 4. Connect the stations into a pipeline: START -> retrieve -> synthesize -> END
builder = StateGraph(ResearchState)
builder.add_node("retrieve", retrieve_node)
builder.add_node("synthesize", synthesize_node)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "synthesize")
builder.add_edge("synthesize", END)

research_graph = builder.compile()