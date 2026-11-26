
import asyncio
import logging

from google import genai
from google.genai import types, errors
from groq import AsyncGroq

from app.core.config import settings

logger = logging.getLogger(__name__)


# 1. Primary LLM: Gemini
async def call_gemini(
    prompt: str,
    timeout_seconds: float = 10.0,
    max_attempts: int = 2
) -> str | None:

    if not settings.GEMINI_API_KEY:
        logger.warning("Gemini API key is missing.")
        return None

    for attempt in range(max_attempts):

        try:
            client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(
                        attempts=1
                    )
                )
            )

            async with client.aio as async_client:

                response = await asyncio.wait_for(
                    async_client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=prompt
                    ),
                    timeout=timeout_seconds
                )

            content = (response.text or "").strip()

            if content:
                return content

            logger.warning("Gemini returned an empty response.")

        except asyncio.TimeoutError:

            logger.warning(
                "Gemini attempt %s timed out.",
                attempt + 1
            )

        except errors.APIError as e:

            logger.warning(
                "Gemini attempt %s failed: %s",
                attempt + 1,
                e
            )

            if e.code not in (408, 429, 500, 502, 503, 504):
                return None

        except Exception as e:

            logger.warning("Gemini error: %s", e)
            return None

        if attempt < max_attempts - 1:

            delay = 2 ** attempt

            logger.warning(
                "Retrying Gemini after %s seconds.",
                delay
            )

            await asyncio.sleep(delay)

    return None


# 2. Secondary LLM: Groq
async def call_groq(
    prompt: str,
    timeout_seconds: float = 15.0
) -> str | None:

    if not settings.GROQ_API_KEY:
        logger.warning("Groq API key is missing.")
        return None

    try:

        async with AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=timeout_seconds,
            max_retries=0
        ) as client:

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.2,
                    max_completion_tokens=4096
                ),
                timeout=timeout_seconds
            )

            content = response.choices[0].message.content

            if content and content.strip():
                return content.strip()

            logger.warning("Groq returned an empty response.")
            return None

    except asyncio.TimeoutError:

        logger.warning("Groq request timed out.")
        return None

    except Exception as e:

        logger.warning("Groq API error: %s", e)
        return None


# 3. Automatic LLM Fallback Manager
async def generate_with_fallback(
    prompt: str,
    timeout_seconds: float = 10.0,
    max_attempts: int = 2,
    fallback_timeout: float = 15.0
) -> str | None:

    print("--> [LLM Service] Calling Gemini...")

    result = await call_gemini(
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts
    )

    if result:
        print("--> [LLM Service] Gemini succeeded.")
        return result

    print("--> [LLM Service] Gemini failed. Switching to Groq...")

    result = await call_groq(
        prompt=prompt,
        timeout_seconds=fallback_timeout
    )

    if result:
        print("--> [LLM Service] Groq succeeded.")
        return result

    logger.error("All LLM providers failed.")

    return None
