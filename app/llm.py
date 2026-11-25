
import os
import time
import logging

from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Check your .env file."
    )

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.5-flash-lite"


def generate_answer(question: str, context: str) -> str:
    """Generate an answer grounded in retrieved document passages."""

    prompt = f"""
You are an assistant for an enterprise knowledge base.

Answer the user's question using only the document passages below.
If the passages do not contain enough information, say you don't
have enough information in the provided documents.
Do not invent policies or facts.

Document passages:
{context}

User question:
{question}

Provide a clear, concise answer.
"""

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            answer = response.text

            if not answer:
                raise RuntimeError("Gemini returned an empty answer.")

            return answer.strip()

        except errors.ServerError as exc:
            status_code = exc.code

            # Retry only temporary server-side errors.
            if status_code not in {500, 502, 503, 504}:
                raise

            if attempt == max_attempts - 1:
                logger.exception(
                    "Gemini failed after all retry attempts."
                )
                raise

            wait_seconds = 2 ** (attempt + 1)

            logger.warning(
                "Gemini returned %s. Retrying in %s seconds "
                "(attempt %s of %s).",
                status_code,
                wait_seconds,
                attempt + 1,
                max_attempts,
            )

            time.sleep(wait_seconds)
