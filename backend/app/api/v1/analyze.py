"""
Document Analysis endpoint — smart contract / legal document analyzer.

POST /analyze   — analyze text for clauses, risks, obligations
"""
import logging
from functools import partial

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=20, max_length=50_000,
                      description="Legal text to analyze (contract, notice, judgment, clause…)")
    document_type: str = Field(
        default="auto",
        description="Hint the document type: 'contract', 'judgment', 'notice', 'statute', 'auto'",
    )


class AnalyzeResponse(BaseModel):
    summary: str
    document_type: str
    key_clauses: list[str]
    obligations: list[str]
    risk_flags: list[str]
    missing_clauses: list[str]
    applicable_laws: list[str]
    jurisdiction_notes: str
    raw_analysis: str


_SYSTEM = (
    "You are LegalMind, an expert AI legal analyst specializing in Indian law. "
    "You perform structured analysis of legal documents with precision."
)

_PROMPT = """\
You are an expert Indian legal analyst. Analyze the following legal text and provide a structured analysis.

DOCUMENT TYPE HINT: {doc_type}

--- LEGAL TEXT ---
{text}
--- END TEXT ---

Provide your analysis in the following EXACT format (use these exact section headers):

DOCUMENT TYPE:
[State the type of legal document: Contract, Agreement, Court Order, Statute, Legal Notice, etc.]

SUMMARY:
[2-3 sentence summary of what this document is about and its legal purpose]

KEY CLAUSES:
- [Clause 1: brief description]
- [Clause 2: brief description]
[List all significant legal clauses found]

OBLIGATIONS:
- [Party name / role]: [obligation]
[List all obligations imposed on each party]

RISK FLAGS:
- [Risk 1: description and why it is a risk]
[List any unfair, ambiguous, illegal, or problematic clauses]

MISSING CLAUSES:
- [Missing clause that should typically be present]
[List any standard clauses that are absent but should be present]

APPLICABLE LAWS:
- [Law/Section/Article that applies to this document]
[List relevant Indian laws, IPC sections, constitutional articles, etc.]

JURISDICTION NOTES:
[Notes about Indian jurisdiction, applicable courts, governing law, any conflict of laws issues]
"""


def _parse_section(text: str, header: str) -> list[str]:
    """Extract bullet points from a named section."""
    lines = text.splitlines()
    in_section = False
    items = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith(header.upper() + ":"):
            in_section = True
            continue
        if in_section:
            if stripped and stripped[0].isupper() and stripped.endswith(":") and len(stripped) < 40:
                break  # next section header
            if stripped.startswith("-"):
                items.append(stripped.lstrip("- ").strip())
    return items


def _parse_single(text: str, header: str) -> str:
    """Extract single-paragraph section content."""
    lines = text.splitlines()
    in_section = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith(header.upper() + ":"):
            in_section = True
            remainder = stripped[len(header) + 1:].strip()
            if remainder:
                result.append(remainder)
            continue
        if in_section:
            if stripped and stripped.endswith(":") and len(stripped) < 40 and stripped[0].isupper():
                break
            if stripped:
                result.append(stripped)
    return " ".join(result)


def _do_analyze(text: str, document_type: str) -> AnalyzeResponse:
    prompt = _PROMPT.format(doc_type=document_type, text=text[:8000])

    from app.config.settings import get_settings
    from openai import OpenAI
    settings = get_settings()

    client = OpenAI(base_url=settings.nim_base_url, api_key=settings.ngc_api_key or "not-used")

    raw = client.chat.completions.create(
        model=settings.nim_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2048,
        temperature=0.1,
        stream=False,
    ).choices[0].message.content or ""

    doc_type = _parse_single(raw, "DOCUMENT TYPE") or document_type
    summary = _parse_single(raw, "SUMMARY")
    key_clauses = _parse_section(raw, "KEY CLAUSES")
    obligations = _parse_section(raw, "OBLIGATIONS")
    risk_flags = _parse_section(raw, "RISK FLAGS")
    missing_clauses = _parse_section(raw, "MISSING CLAUSES")
    applicable_laws = _parse_section(raw, "APPLICABLE LAWS")
    jurisdiction_notes = _parse_single(raw, "JURISDICTION NOTES")

    return AnalyzeResponse(
        summary=summary or "Analysis complete.",
        document_type=doc_type,
        key_clauses=key_clauses,
        obligations=obligations,
        risk_flags=risk_flags,
        missing_clauses=missing_clauses,
        applicable_laws=applicable_laws,
        jurisdiction_notes=jurisdiction_notes or "",
        raw_analysis=raw,
    )


@router.post(
    "",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a legal document for clauses, risks, and applicable Indian law",
)
async def analyze_document(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Submit legal text (contract, court order, notice, statute excerpt) and receive
    structured analysis: key clauses, obligations, risk flags, missing clauses,
    and applicable Indian laws.
    """
    try:
        result = await run_in_threadpool(
            partial(_do_analyze, request.text, request.document_type)
        )
    except Exception as exc:
        logger.exception("Document analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again.",
        )
    return result
