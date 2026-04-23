"""
Legal Document Generator endpoint.

POST /generate-doc  — generate a standard legal document from template + AI
"""
import logging
from functools import partial
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate-doc", tags=["Document Generator"])

DocumentType = Literal[
    "nda",
    "rent_agreement",
    "employment_agreement",
    "legal_notice",
    "affidavit",
    "power_of_attorney",
    "sale_agreement",
    "loan_agreement",
    "partnership_deed",
    "demand_notice",
]


class GenerateDocRequest(BaseModel):
    document_type: DocumentType = Field(..., description="Type of legal document to generate")
    party_a: str = Field(..., min_length=2, max_length=200, description="First party name/details")
    party_b: str = Field(..., min_length=2, max_length=200, description="Second party name/details")
    key_terms: dict = Field(default_factory=dict, description="Key terms for the document")
    jurisdiction: str = Field(default="India", description="Governing jurisdiction (state/India)")
    additional_context: str = Field(default="", max_length=2000,
                                     description="Additional context or special clauses to include")


class GenerateDocResponse(BaseModel):
    document_type: str
    title: str
    content: str
    applicable_laws: list[str]
    notes: str


_SYSTEM = (
    "You are LegalMind, an expert Indian legal document drafter with 20+ years of experience. "
    "You draft legally sound documents compliant with Indian law."
)

_DOC_CONFIGS = {
    "nda": {
        "title": "Non-Disclosure Agreement (NDA)",
        "laws": ["Indian Contract Act 1872", "Information Technology Act 2000", "Trade Secrets (Common Law)"],
    },
    "rent_agreement": {
        "title": "Rent/Lease Agreement",
        "laws": ["Transfer of Property Act 1882 (S.105-111)", "Indian Contract Act 1872",
                 "State Rent Control Acts", "Registration Act 1908"],
    },
    "employment_agreement": {
        "title": "Employment Agreement",
        "laws": ["Indian Contract Act 1872", "Industrial Disputes Act 1947",
                 "Payment of Wages Act 1936", "Shops and Establishments Act (State)"],
    },
    "legal_notice": {
        "title": "Legal Notice",
        "laws": ["Code of Civil Procedure 1908", "Indian Contract Act 1872", "Limitation Act 1963"],
    },
    "affidavit": {
        "title": "Affidavit",
        "laws": ["Indian Evidence Act 1872 (S.1-3)", "Oaths Act 1969", "Code of Civil Procedure 1908"],
    },
    "power_of_attorney": {
        "title": "Power of Attorney",
        "laws": ["Powers of Attorney Act 1882", "Indian Contract Act 1872 (S.182-238)",
                 "Registration Act 1908"],
    },
    "sale_agreement": {
        "title": "Agreement to Sell / Sale Agreement",
        "laws": ["Transfer of Property Act 1882 (S.54)", "Indian Contract Act 1872",
                 "Registration Act 1908", "Stamp Act 1899"],
    },
    "loan_agreement": {
        "title": "Loan Agreement / Promissory Note",
        "laws": ["Indian Contract Act 1872", "Negotiable Instruments Act 1881",
                 "SARFAESI Act 2002", "Banking Regulation Act 1949"],
    },
    "partnership_deed": {
        "title": "Partnership Deed",
        "laws": ["Indian Partnership Act 1932", "Indian Contract Act 1872",
                 "Income Tax Act 1961 (S.184)"],
    },
    "demand_notice": {
        "title": "Demand Notice",
        "laws": ["Indian Contract Act 1872 (S.73)", "Limitation Act 1963",
                 "Code of Civil Procedure 1908 (Order XXI)"],
    },
}

_PROMPT = """\
Draft a professional, legally sound {doc_title} under Indian law.

PARTIES:
- Party A: {party_a}
- Party B: {party_b}

KEY TERMS:
{key_terms}

JURISDICTION: {jurisdiction}

ADDITIONAL CONTEXT:
{additional_context}

APPLICABLE LAWS: {laws}

Requirements:
1. Use proper legal language and standard Indian legal document format
2. Include all standard clauses for this document type
3. Include date placeholder as [DATE] and signature blocks
4. Reference specific sections of applicable Indian laws where relevant
5. Include a dispute resolution clause (prefer arbitration under Arbitration and Conciliation Act 1996)
6. Include governing law clause specifying Indian jurisdiction
7. Mark blanks that need to be filled as [SPECIFY: description]

Draft the complete document now:
"""


def _do_generate(req: GenerateDocRequest) -> GenerateDocResponse:
    from app.config.settings import get_settings
    from openai import OpenAI
    settings = get_settings()

    config = _DOC_CONFIGS.get(req.document_type, {
        "title": req.document_type.replace("_", " ").title(),
        "laws": ["Indian Contract Act 1872"],
    })
    title = config["title"]
    laws = config["laws"]

    key_terms_str = "\n".join(f"- {k}: {v}" for k, v in req.key_terms.items()) or "- (standard terms apply)"

    prompt = _PROMPT.format(
        doc_title=title,
        party_a=req.party_a,
        party_b=req.party_b,
        key_terms=key_terms_str,
        jurisdiction=req.jurisdiction,
        additional_context=req.additional_context or "None specified",
        laws=", ".join(laws),
    )

    client = OpenAI(base_url=settings.nim_base_url, api_key=settings.ngc_api_key or "not-used")

    content = client.chat.completions.create(
        model=settings.nim_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=3000,
        temperature=0.15,
        stream=False,
    ).choices[0].message.content or ""

    notes = (
        "IMPORTANT: This document is AI-generated for informational purposes only. "
        "It should be reviewed and customized by a qualified Indian lawyer before execution. "
        "Ensure proper stamping and registration as required under the Registration Act 1908 "
        "and applicable Stamp Act."
    )

    return GenerateDocResponse(
        document_type=title,
        title=title,
        content=content,
        applicable_laws=laws,
        notes=notes,
    )


@router.post(
    "",
    response_model=GenerateDocResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a standard Indian legal document using AI",
)
async def generate_document(request: GenerateDocRequest) -> GenerateDocResponse:
    """
    Generate NDA, rent agreement, employment contract, legal notice, affidavit,
    power of attorney, sale agreement, loan agreement, partnership deed, or demand notice.

    The generated document references applicable Indian laws and includes
    standard clauses. Always review with a qualified lawyer before use.
    """
    try:
        result = await run_in_threadpool(partial(_do_generate, request))
    except Exception as exc:
        logger.exception("Document generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document generation failed. Please try again.",
        )
    return result
