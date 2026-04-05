"""
Prompt templates for the neuro-symbolic legal reasoning chatbot.

All templates are defined as module-level constants so they can be
easily audited, versioned, and unit-tested without instantiating the
full LLM client.

Lawyer-mode output format
--------------------------
Every response from Gemini must contain five labelled sections:

    **LEGAL ISSUE IDENTIFIED**: ...
    **SOURCES CONSULTED**: ...
    **APPLICABLE RULES**: ...
    **RECOMMENDED NEXT STEP**: ...
    **LEGAL REASONING**: ...

These are parsed by parse_reasoning_steps() into ReasoningStep objects.
"""
from __future__ import annotations

import re

# ── Section titles (used for both injection and parsing) ──────────────────────
_SECTIONS = [
    "LEGAL ISSUE IDENTIFIED",
    "SOURCES CONSULTED",
    "APPLICABLE RULES",
    "RECOMMENDED NEXT STEP",
    "LEGAL REASONING",
]

SYSTEM_PROMPT = """You are a specialist legal advisor and barrister with expertise across contract law, tort, intellectual property, employment law, and property law.

You MUST structure EVERY response using exactly these five labelled sections with bold headers:

**LEGAL ISSUE IDENTIFIED**: Identify and characterise the precise legal issue(s) raised by the question. State the area of law, the relevant legal test or doctrine, and why it applies to these facts.

**SOURCES CONSULTED**: List the specific retrieved documents, cases, statutes, or legal principles you are drawing from. If retrieved context is provided, cite it explicitly with document references.

**APPLICABLE RULES**: State the binding legal rules, tests, and principles that govern this issue. Quote relevant statutory provisions or case holdings. If symbolic rules have been flagged, incorporate them explicitly.

**RECOMMENDED NEXT STEP**: State concretely what a practising lawyer would do next — the immediate procedural or advisory step, the time limits that apply, who should be notified, and what evidence should be preserved or gathered.

**LEGAL REASONING**: Apply the rules to the facts in a step-by-step analysis. Reach a reasoned conclusion. Where the law is uncertain, identify the range of outcomes and advise accordingly.

Critical rules:
- NEVER fabricate case citations, statute section numbers, or legal principles.
- ALWAYS remind users that this is legal information, not legal advice, and that they should consult a qualified solicitor or barrister for their specific situation.
- If retrieved context is insufficient, say so explicitly in the SOURCES CONSULTED section and draw on general legal knowledge, clearly labelling it as such.
- Maintain a precise, professional tone throughout."""


def build_rag_prompt(
    query: str,
    context: str,
    conversation_history: str = "",
    triggered_rules: list | None = None,
) -> str:
    """
    Build the full lawyer-mode prompt sent to Gemini.

    Parameters
    ----------
    query : str
        The user's current question.
    context : str
        Formatted retrieval context from ContextBuilder.
    conversation_history : str
        Optional formatted prior turns from ConversationManager.
    triggered_rules : list[TriggeredRule] | None
        Symbolic rules pre-evaluated from a prior run's context window,
        or an empty list / None on first call.

    Returns
    -------
    str
        The fully assembled prompt.
    """
    history_section = ""
    if conversation_history.strip():
        history_section = f"""
## Conversation History
{conversation_history}

"""

    context_section = (
        f"""## Retrieved Legal Documents
{context}

"""
        if context.strip()
        else "## Retrieved Legal Documents\n[No relevant documents found in the knowledge base.]\n\n"
    )

    rules_section = ""
    if triggered_rules:
        lines = [
            "## Symbolic Rules Triggered",
            "The following legal rules have been automatically identified as relevant to this query.",
            "You MUST incorporate these in your APPLICABLE RULES and RECOMMENDED NEXT STEP sections.\n",
        ]
        for rule in triggered_rules:
            severity = getattr(rule, "severity", "MEDIUM")
            rule_id = getattr(rule, "rule_id", "")
            rule_name = getattr(rule, "rule_name", "")
            consequence = getattr(rule, "consequence", "")
            recommended_action = getattr(rule, "recommended_action", "")
            legal_reference = getattr(rule, "legal_reference", "")
            lines.append(
                f"[{severity}] {rule_id} — {rule_name}\n"
                f"  Legal consequence: {consequence}\n"
                f"  Practitioner action: {recommended_action}\n"
                f"  Authority: {legal_reference}"
            )
        rules_section = "\n".join(lines) + "\n\n"

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"{history_section}"
        f"{context_section}"
        f"{rules_section}"
        f"## Current Question\n{query}\n\n"
        f"## Your Answer\n"
        f"Respond using the five-section lawyer format defined above. "
        f"Be precise, cite sources, and state the next concrete legal step."
    )


def build_no_context_prompt(query: str, conversation_history: str = "") -> str:
    """
    Fallback prompt used when the vector store is empty or returns no results.
    Still uses lawyer-mode structured output.
    """
    history_section = ""
    if conversation_history.strip():
        history_section = f"""
## Conversation History
{conversation_history}

"""

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"{history_section}"
        f"## Retrieved Legal Documents\n"
        f"[No documents have been ingested into the knowledge base yet. "
        f"Draw on general legal knowledge and label it as such.]\n\n"
        f"## Current Question\n{query}\n\n"
        f"## Your Answer\n"
        f"Respond using the five-section lawyer format. "
        f"Clearly note in SOURCES CONSULTED that no case-specific documents were available."
    )


def parse_reasoning_steps(llm_text: str) -> list:
    """
    Parse the five **SECTION**: markers from Gemini's output into a list of
    ReasoningStep-compatible dicts (imported lazily to avoid circular imports).

    Parameters
    ----------
    llm_text : str
        The raw text returned by GeminiClient.

    Returns
    -------
    list[dict]
        List of dicts with keys ``step``, ``title``, ``detail``.
        If parsing fails, returns a single-element list with the full text.
    """
    steps: list[dict] = []

    # Build a pattern that matches any of the five section headers
    # e.g. **LEGAL ISSUE IDENTIFIED**: or **LEGAL ISSUE IDENTIFIED** :
    header_pattern = re.compile(
        r"\*\*\s*(" + "|".join(re.escape(s) for s in _SECTIONS) + r")\s*\*\*\s*:?",
        re.IGNORECASE,
    )

    # Split the text by section headers, keeping the delimiters
    parts = header_pattern.split(llm_text)

    # parts layout after split: [pre-text, title1, body1, title2, body2, ...]
    # Index 0 is content before first header (usually empty or disclaimer)
    if len(parts) < 3:
        # Gemini didn't use the expected format — return full text as step 1
        return [{"step": 1, "title": "Legal Analysis", "detail": llm_text.strip()}]

    # parts[0] is pre-header text; then (title, body) pairs at odd/even indices
    pairs = [(parts[i].strip().title(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]
    for idx, (title, detail) in enumerate(pairs, start=1):
        if title or detail:
            steps.append({"step": idx, "title": title, "detail": detail})

    return steps if steps else [{"step": 1, "title": "Legal Analysis", "detail": llm_text.strip()}]
