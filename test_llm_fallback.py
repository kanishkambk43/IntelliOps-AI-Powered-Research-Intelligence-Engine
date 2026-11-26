
import asyncio
import time

from unittest.mock import AsyncMock, patch
from app.services.llm_service import generate_with_fallback


async def main():

    start = time.perf_counter()

    with patch(
        "app.services.llm_service.call_gemini",
        new_callable=AsyncMock,
        return_value=None
    ):

        result = await generate_with_fallback(
            "Explain the difference between Python and C++."
        )

    if result:
        print("\nFallback successful!\n")
        print(result)
    else:
        print("\nAll providers failed.")

    print(
        f"\nExecution time: "
        f"{time.perf_counter() - start:.2f}s"
    )


if __name__ == "__main__":
    asyncio.run(main())
