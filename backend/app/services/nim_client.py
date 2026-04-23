"""
NVIDIA NIM client — OpenAI-compatible wrapper for NIM endpoints.

Supports two modes selected automatically from the base_url:

  HOSTED (default)
  ────────────────
  base_url = "https://integrate.api.nvidia.com/v1"
  Requires an NGC Personal API key (set NGC_API_KEY in backend/.env).
  No GPU needed — inference runs on NVIDIA's cloud.

  SELF-HOSTED
  ───────────
  base_url = "http://localhost:8001/v1"
  api_key  = "not-used"   (no auth on local NIM)

DeepSeek v3.2 features
──────────────────────
  * enable_thinking = True  → passes chat_template_kwargs={"thinking": True} to
    activate the model's extended chain-of-thought reasoning.
  * Thinking tokens arrive via the ``reasoning_content`` field on each delta
    chunk — captured for logging but not included in the visible response.
  * Streams internally and aggregates — avoids proxy/gateway timeouts on long
    legal reasoning responses without requiring SSE on the FastAPI side.
"""
import logging
import time

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.gemini_client import LLMResponse  # reuse the same dataclass
from app.services.prompt_templates import build_no_context_prompt, build_rag_prompt

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

HOSTED_BASE_URL      = "https://integrate.api.nvidia.com/v1"
SELF_HOSTED_BASE_URL = "http://localhost:8001/v1"

_SYSTEM_PROMPT = (
    "You are LegalMind, an expert AI legal research assistant. "
    "You reason carefully over retrieved legal sources, apply relevant legal principles, "
    "and always structure your answers clearly for legal professionals."
)


class NIMClient:
    """
    Thin wrapper around NVIDIA NIM's OpenAI-compatible Chat Completions endpoint.

    Parameters
    ----------
    base_url : str
        NIM endpoint. Defaults to the NVIDIA-hosted cloud API.
        Set to ``"http://localhost:8001/v1"`` when running self-hosted NIM.
    model : str
        NIM model identifier, e.g. ``"deepseek-ai/deepseek-v3.2"``.
    api_key : str
        NGC Personal API key for the hosted endpoint.
        Pass ``"not-used"`` for local self-hosted NIM (no auth required).
    temperature : float
        Sampling temperature.
    top_p : float
        Nucleus sampling probability.
    max_tokens : int
        Maximum tokens in the completion.
    enable_thinking : bool
        Pass ``chat_template_kwargs={"thinking": True}`` to activate
        DeepSeek's extended chain-of-thought reasoning. Thinking tokens
        arrive via the ``reasoning_content`` delta field and are not
        included in the visible response.
    """

    def __init__(
        self,
        base_url: str = HOSTED_BASE_URL,
        model: str = "deepseek-ai/deepseek-v3.2",
        api_key: str = "not-used",
        temperature: float = 1.0,
        top_p: float = 0.95,
        max_tokens: int = 8192,
        enable_thinking: bool = True,
    ) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking

        mode = "cloud-hosted" if base_url == HOSTED_BASE_URL else "self-hosted"
        logger.info(
            "NIMClient initialised (%s, model=%s, endpoint=%s, thinking=%s).",
            mode, model, base_url, enable_thinking,
        )

    # ── public API (mirrors GeminiClient) ─────────────────────────────────────

    def generate_rag_response(
        self,
        query: str,
        context: str,
        conversation_history: str = "",
    ) -> LLMResponse:
        """Generate a RAG-grounded legal answer via NIM."""
        if context.strip():
            user_content = build_rag_prompt(query, context, conversation_history)
        else:
            user_content = build_no_context_prompt(query, conversation_history)

        return self._call(user_content)

    # ── private helpers ────────────────────────────────────────────────────────

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _call(self, user_content: str) -> LLMResponse:
        """
        Stream the completion from NIM and aggregate into a single LLMResponse.

        Streaming internally avoids proxy/gateway timeouts on long responses.
        DeepSeek thinking tokens arrive in the ``reasoning_content`` field of
        each delta chunk — captured for logging but not included in the
        visible response (only ``content`` is returned to the caller).
        """
        start = time.perf_counter()

        # Build extra kwargs for DeepSeek thinking mode
        extra_body: dict = {}
        if self.enable_thinking:
            extra_body["chat_template_kwargs"] = {"thinking": True}

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            stream=True,
            extra_body=extra_body if extra_body else None,
        )

        # Aggregate streamed chunks
        full_text = ""
        thinking_text = ""
        prompt_tokens = 0
        completion_tokens = 0

        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            # DeepSeek reasoning arrives in reasoning_content (separate from content)
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                thinking_text += reasoning
            if delta.content is not None:
                full_text += delta.content
            # Capture usage if the provider sends it in the final chunk
            if hasattr(chunk, "usage") and chunk.usage:
                prompt_tokens     = chunk.usage.prompt_tokens     or 0
                completion_tokens = chunk.usage.completion_tokens or 0

        elapsed_ms = (time.perf_counter() - start) * 1000

        if thinking_text:
            logger.debug("DeepSeek thinking: %d chars", len(thinking_text))
        logger.info(
            "NIM response: %.0f ms | ~%d chars (thinking=%s)",
            elapsed_ms, len(full_text), self.enable_thinking,
        )

        return LLMResponse(
            text=full_text.strip(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=elapsed_ms,
        )

