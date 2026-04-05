"""
Gemini API client — thin, retry-safe wrapper around ``google-genai``.

Design decisions
----------------
* Uses the new google-genai SDK (v1 API) which supports all current Gemini models.
* Tenacity handles transient 5xx failures with exponential back-off.
* ResourceExhausted (429) is not retried — it fails fast.
* The client is synchronous; async callers should offload to a thread pool.
"""
import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.prompt_templates import build_no_context_prompt, build_rag_prompt

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from Gemini."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float


class GeminiClient:
    """
    Wrapper around the Google GenAI SDK (v1 API).

    Parameters
    ----------
    api_key : str
        Gemini API key.
    model_name : str
        Gemini model identifier (e.g. ``"gemini-2.5-flash-preview-04-17"``).
    temperature : float
        Sampling temperature (0 = deterministic, 2 = very random).
    max_output_tokens : int
        Maximum number of tokens in the generated response.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-2.5-flash-preview-04-17",
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self._config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        logger.info("GeminiClient initialised (model=%s).", model_name)

    # ── public API ─────────────────────────────────────────────────────────────

    def generate_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: str = "",
    ) -> LLMResponse:
        """Generate a RAG-grounded legal answer."""
        if context.strip():
            prompt = build_rag_prompt(query, context, conversation_history)
        else:
            prompt = build_no_context_prompt(query, conversation_history)

        return self._call(prompt)

    # ── private helpers ────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_not_exception_type(ResourceExhausted),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call(self, prompt: str) -> LLMResponse:
        """Execute a single generation call with retry on transient errors."""
        start = time.perf_counter()

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=self._config,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        text = response.text or ""
        usage = response.usage_metadata

        prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

        logger.info(
            "Gemini response: %.0f ms | prompt=%d tok | completion=%d tok",
            elapsed_ms,
            prompt_tokens,
            completion_tokens,
        )

        return LLMResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=elapsed_ms,
        )
