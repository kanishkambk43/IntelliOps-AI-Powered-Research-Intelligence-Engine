

import asyncio
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("IntelliOps Research Server")


@mcp.tool()
def greet(name: str) -> str:
    """Return a greeting to test MCP."""
    return f"Hello {name}, welcome to IntelliOps!"



@mcp.tool()
async def search_web(query: str, max_results: int = 3) -> dict:
    """Search the web and return relevant results."""

    def run_search():
         import sys 
         import os

         print(f"Python: {sys.executable}", file=sys.stderr)
         print(f"Process ID: {os.getpid()}", file=sys.stderr)
         print(f"Search query: {query!r}", file=sys.stderr)

    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


if __name__ == "__main__":
    mcp.run(transport="stdio")

