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
  Requires ≥64 GB VRAM to host Gemma 4 31B.

Gemma 4 features
────────────────
  * enable_thinking = True  → passes chat_template_kwargs to activate the
    model's extended chain-of-thought reasoning (thinking tokens are stripped
    from the visible response before returning to the caller).
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
        NIM model identifier, e.g. ``"google/gemma-4-31b-it"``.
    api_key : str
        NGC Personal API key for the hosted endpoint.
        Pass ``"not-used"`` for local self-hosted NIM (no auth required).
    temperature : float
        Sampling temperature. NIM docs recommend 1.0 for Gemma 4.
    max_tokens : int
        Maximum tokens in the completion (up to 32 768 for Gemma 4).
    enable_thinking : bool
        Pass ``chat_template_kwargs={"enable_thinking": True}`` to activate
        Gemma 4's extended chain-of-thought reasoning. Thinking tokens are
        automatically stripped from the visible answer.
    """

    def __init__(
        self,
        base_url: str = HOSTED_BASE_URL,
        model: str = "google/gemma-4-31b-it",
        api_key: str = "not-used",
        temperature: float = 1.0,
        max_tokens: int = 16384,
        enable_thinking: bool = True,
    ) -> None:
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
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
        Gemma 4 thinking tokens (enclosed in <think>...</think>) are stripped
        from the returned text — they're captured but not shown to the user.
        """
        start = time.perf_counter()

        # Build extra kwargs for Gemma 4 thinking mode
        extra_body: dict = {}
        if self.enable_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": True}

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            extra_body=extra_body if extra_body else None,
        )

        # Aggregate streamed chunks
        full_text = ""
        prompt_tokens = 0
        completion_tokens = 0

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
            # Capture usage if the provider sends it in the final chunk
            if hasattr(chunk, "usage") and chunk.usage:
                prompt_tokens     = chunk.usage.prompt_tokens     or 0
                completion_tokens = chunk.usage.completion_tokens or 0

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Strip Gemma 4 thinking tokens from the visible answer
        visible_text = _strip_thinking_tokens(full_text)

        logger.info(
            "NIM response: %.0f ms | ~%d chars (thinking stripped=%s)",
            elapsed_ms, len(visible_text), self.enable_thinking,
        )

        return LLMResponse(
            text=visible_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=elapsed_ms,
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _strip_thinking_tokens(text: str) -> str:
    """
    Remove Gemma 4 thinking blocks from the response text.

    Gemma 4 wraps its internal reasoning in ``<think>...</think>`` tags.
    These are useful for debugging but should not be shown to end users
    in the chat interface.
    """
    import re
    # Remove <think>...</think> blocks (possibly multiline)
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()
