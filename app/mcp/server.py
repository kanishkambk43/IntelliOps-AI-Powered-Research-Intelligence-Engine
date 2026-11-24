import sys
import asyncio
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("IntelliOps Research Server")


@mcp.tool()
def greet(name: str) -> str:
    """Return a greeting to test MCP."""
    return f"Hello {name}, welcome to IntelliOps!"




@mcp.tool()
async def search_web(query: str, max_results: int = 6) -> dict:

    def run_search():
        with DDGS() as ddgs:
            return list(
                ddgs.text(query, max_results=max_results)
            )

    max_attempts = 3
    last_error = ""

    for attempt in range(max_attempts):

        try:
            results = await asyncio.to_thread(run_search)

            if results:
                return {
                    "success": True,
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                        for r in results
                    ],
                }

            last_error = "No results found"

        except Exception as e:
            last_error = str(e)

        print(
            f"[MCP] Attempt {attempt + 1} failed: {last_error}",
            file=sys.stderr,
        )

        if attempt < max_attempts - 1: #Exponential backoff
            await asyncio.sleep(2 ** attempt)

    return {
        "success": False,
        "error": last_error,
        "results": [],
    }



if __name__ == "__main__":
    mcp.run(transport="stdio")

