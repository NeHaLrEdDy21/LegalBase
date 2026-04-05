"""
Symbolic rules management API.

GET    /rules            — list all rules
POST   /rules            — add a new rule
PATCH  /rules/{rule_id}  — update rule fields
DELETE /rules/{rule_id}  — delete a rule
POST   /rules/reload     — hot-reload from disk (discards unsaved changes)
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

from app.rag.pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["Rules"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    id: str
    name: str
    trigger_keywords: list[str] = []
    condition: str = "keyword_match"
    pattern: str = ""
    consequence: str
    recommended_action: str
    severity: str = "MEDIUM"
    legal_reference: str = ""

    @field_validator("condition")
    @classmethod
    def valid_condition(cls, v: str) -> str:
        if v not in ("keyword_match", "regex_match"):
            raise ValueError("condition must be 'keyword_match' or 'regex_match'")
        return v

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v: str) -> str:
        if v.upper() not in ("HIGH", "MEDIUM", "LOW"):
            raise ValueError("severity must be HIGH, MEDIUM, or LOW")
        return v.upper()


class RuleUpdate(BaseModel):
    name: str | None = None
    trigger_keywords: list[str] | None = None
    condition: str | None = None
    pattern: str | None = None
    consequence: str | None = None
    recommended_action: str | None = None
    severity: str | None = None
    legal_reference: str | None = None

    @field_validator("condition")
    @classmethod
    def valid_condition(cls, v: str | None) -> str | None:
        if v is not None and v not in ("keyword_match", "regex_match"):
            raise ValueError("condition must be 'keyword_match' or 'regex_match'")
        return v

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v: str | None) -> str | None:
        if v is not None and v.upper() not in ("HIGH", "MEDIUM", "LOW"):
            raise ValueError("severity must be HIGH, MEDIUM, or LOW")
        return v.upper() if v else v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", summary="List all symbolic rules")
async def list_rules() -> list[dict[str, Any]]:
    pipeline = get_rag_pipeline()
    return pipeline._rules_engine.list_rules()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Add a new symbolic rule")
async def add_rule(body: RuleCreate) -> dict[str, Any]:
    pipeline = get_rag_pipeline()
    try:
        return pipeline._rules_engine.add_rule(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.patch("/{rule_id}", summary="Update fields on an existing rule")
async def update_rule(rule_id: str, body: RuleUpdate) -> dict[str, Any]:
    pipeline = get_rag_pipeline()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        return pipeline._rules_engine.update_rule(rule_id, updates)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a rule")
async def delete_rule(rule_id: str) -> None:
    pipeline = get_rag_pipeline()
    deleted = pipeline._rules_engine.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found.",
        )


@router.post("/reload", summary="Hot-reload rules from disk")
async def reload_rules() -> dict[str, Any]:
    pipeline = get_rag_pipeline()
    pipeline._rules_engine.reload()
    return {"rules_loaded": pipeline._rules_engine.rule_count()}
