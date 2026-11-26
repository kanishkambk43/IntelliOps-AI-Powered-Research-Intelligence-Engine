import asyncio
import time

from app.services.llm_service import call_groq


async def main():
    start = time.perf_counter()

    result = await call_groq(
        "Explain the difference between LangChain and LangGraph."
    )

    if result:
        print(result)
    else:
        print("Groq failed to generate a response.")

    print(f"\nExecution time: {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())