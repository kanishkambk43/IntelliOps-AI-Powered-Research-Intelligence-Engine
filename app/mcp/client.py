
import sys
import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def search_web_via_mcp(query: str, max_results: int = 6) -> dict:

    project_root = Path(__file__).resolve().parents[2]
    server_path = project_root / "app" / "mcp" / "server.py"

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        cwd=str(project_root),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            result = await session.call_tool(
                "search_web",
                arguments={
                    "query": query,
                    "max_results": max_results,
                },
            )

            if result.isError:
                raise RuntimeError(
                    f"MCP web search failed: {result.content}"
                )

            if result.structuredContent is not None:
                data = result.structuredContent

                if "success" in data:
                    return data

                raw_results = data.get("results", data.get("result", []))
            else:
                raw_results = []

                for block in result.content:
                    if block.type == "text":
                        parsed = json.loads(block.text)

                        if isinstance(parsed, dict):
                            if "success" in parsed:
                                return parsed
                            raw_results.append(parsed)

                        elif isinstance(parsed, list):
                            raw_results.extend(parsed)

            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", item.get("href", "")),
                    "snippet": item.get("snippet", item.get("body", "")),
                }
                for item in raw_results
            ]

            return {
                "success": True,
                "results": results,
            }
