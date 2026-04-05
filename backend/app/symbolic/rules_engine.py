"""
RulesEngine — symbolic layer that cross-checks the query, retrieved context,
and LLM answer against a JSON rule catalogue.

Evaluation logic
----------------
For each rule:
  condition == "keyword_match":
      Fire if ANY trigger_keyword appears in the combined text (case-insensitive).
  condition == "regex_match":
      Fire if re.search(rule.pattern, combined_text, re.IGNORECASE) matches.

"Combined text" = query + " " + context + " " + llm_answer

Returns list[TriggeredRule] sorted HIGH → MEDIUM → LOW.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SEVERITY_ORDER: dict[str, int] = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@dataclass(frozen=True)
class RuleDefinition:
    """Internal representation of one rule loaded from JSON."""

    id: str
    name: str
    trigger_keywords: list[str]
    condition: str          # "keyword_match" | "regex_match"
    pattern: str
    consequence: str
    recommended_action: str
    severity: str           # "HIGH" | "MEDIUM" | "LOW"
    legal_reference: str


@dataclass(frozen=True)
class TriggeredRule:
    """A rule that fired during evaluation — returned to the caller and API."""

    rule_id: str
    rule_name: str
    consequence: str
    recommended_action: str
    severity: str
    legal_reference: str
    matched_keywords: list[str]  # empty for regex_match rules
    explanation: str             # human-readable sentence for the reasoning step


class RulesEngine:
    """
    Loads legal rules from a JSON file and evaluates them against
    the assembled context of a RAG response.

    Parameters
    ----------
    rules_path : str | Path
        Absolute or relative path to ``legal_rules.json``.

    Public methods
    --------------
    evaluate(query, context, llm_answer) -> list[TriggeredRule]
    reload() -> None
    rule_count() -> int
    """

    def __init__(self, rules_path: str | Path) -> None:
        self._rules_path = Path(rules_path)
        self._rules: list[RuleDefinition] = []
        self._load()

    # ── public API ─────────────────────────────────────────────────────────────

    def evaluate(
        self,
        query: str,
        context: str,
        llm_answer: str,
    ) -> list[TriggeredRule]:
        """
        Cross-check (query + context + llm_answer) against all loaded rules.

        Returns
        -------
        list[TriggeredRule]
            Ordered HIGH → MEDIUM → LOW; empty list if no rules fire.
        """
        combined_lower = (query + " " + context + " " + llm_answer).lower()
        combined_original = query + " " + context + " " + llm_answer

        triggered: list[TriggeredRule] = []

        for rule in self._rules:
            if rule.condition == "keyword_match":
                matched = [
                    kw for kw in rule.trigger_keywords
                    if kw.lower() in combined_lower
                ]
                if matched:
                    triggered.append(
                        TriggeredRule(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            consequence=rule.consequence,
                            recommended_action=rule.recommended_action,
                            severity=rule.severity,
                            legal_reference=rule.legal_reference,
                            matched_keywords=matched,
                            explanation=(
                                f"Rule {rule.id} ({rule.name}) triggered on "
                                f"keywords: {', '.join(matched)}. "
                                f"{rule.consequence}"
                            ),
                        )
                    )

            elif rule.condition == "regex_match":
                if rule.pattern and re.search(
                    rule.pattern, combined_original, re.IGNORECASE
                ):
                    triggered.append(
                        TriggeredRule(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            consequence=rule.consequence,
                            recommended_action=rule.recommended_action,
                            severity=rule.severity,
                            legal_reference=rule.legal_reference,
                            matched_keywords=[],
                            explanation=(
                                f"Rule {rule.id} ({rule.name}) triggered by "
                                f"pattern match. {rule.consequence}"
                            ),
                        )
                    )

            else:
                logger.warning(
                    "Unknown condition '%s' in rule '%s'; skipping.",
                    rule.condition,
                    rule.id,
                )

        triggered.sort(key=lambda r: _SEVERITY_ORDER.get(r.severity, 3))

        logger.info(
            "Rules evaluation: %d/%d rules triggered.",
            len(triggered),
            len(self._rules),
        )
        return triggered

    def reload(self) -> None:
        """Re-read the rules JSON from disk (useful for dev hot-reload)."""
        self._rules.clear()
        self._load()
        logger.info("RulesEngine reloaded %d rules from '%s'.", len(self._rules), self._rules_path)

    def rule_count(self) -> int:
        return len(self._rules)

    def list_rules(self) -> list[dict[str, Any]]:
        """Return all rules as plain dicts (safe to serialise)."""
        return [self._rule_to_dict(r) for r in self._rules]

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        for r in self._rules:
            if r.id == rule_id:
                return self._rule_to_dict(r)
        return None

    def add_rule(self, data: dict[str, Any]) -> dict[str, Any]:
        """Add a new rule and persist to JSON. Raises ValueError on duplicate id."""
        if any(r.id == data["id"] for r in self._rules):
            raise ValueError(f"Rule with id '{data['id']}' already exists.")
        rule = RuleDefinition(
            id=data["id"],
            name=data["name"],
            trigger_keywords=data.get("trigger_keywords", []),
            condition=data.get("condition", "keyword_match"),
            pattern=data.get("pattern", ""),
            consequence=data["consequence"],
            recommended_action=data["recommended_action"],
            severity=data.get("severity", "MEDIUM"),
            legal_reference=data.get("legal_reference", ""),
        )
        self._rules.append(rule)
        self._save()
        logger.info("RulesEngine: added rule '%s'.", rule.id)
        return self._rule_to_dict(rule)

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update fields on an existing rule and persist. Raises KeyError if not found."""
        idx = next((i for i, r in enumerate(self._rules) if r.id == rule_id), None)
        if idx is None:
            raise KeyError(f"Rule '{rule_id}' not found.")
        old = self._rule_to_dict(self._rules[idx])
        old.update(updates)
        old["id"] = rule_id  # id is immutable
        updated = RuleDefinition(
            id=rule_id,
            name=old["name"],
            trigger_keywords=old.get("trigger_keywords", []),
            condition=old.get("condition", "keyword_match"),
            pattern=old.get("pattern", ""),
            consequence=old["consequence"],
            recommended_action=old["recommended_action"],
            severity=old.get("severity", "MEDIUM"),
            legal_reference=old.get("legal_reference", ""),
        )
        self._rules[idx] = updated
        self._save()
        logger.info("RulesEngine: updated rule '%s'.", rule_id)
        return self._rule_to_dict(updated)

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by id. Returns True if deleted, False if not found."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        if len(self._rules) == before:
            return False
        self._save()
        try:
            from app.db.supabase_client import get_supabase
            db = get_supabase()
            if db:
                db.table("rules").delete().eq("id", rule_id).execute()
        except Exception as exc:
            logger.warning("RulesEngine: Supabase delete failed: %s", exc)
        logger.info("RulesEngine: deleted rule '%s'.", rule_id)
        return True

    # ── private helpers ────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Persist rules to JSON file (always) and Supabase (when available)."""
        data = [self._rule_to_dict(r) for r in self._rules]
        self._rules_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.debug("RulesEngine: persisted %d rules to '%s'.", len(data), self._rules_path)
        self._sync_to_supabase(data)

    def _sync_to_supabase(self, data: list[dict]) -> None:
        """Push the full rules list to Supabase (upsert)."""
        try:
            from app.db.supabase_client import get_supabase
            db = get_supabase()
            if not db:
                return
            rows = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "trigger_keywords": r["trigger_keywords"],
                    "condition": r["condition"],
                    "pattern": r.get("pattern", ""),
                    "consequence": r["consequence"],
                    "recommended_action": r["recommended_action"],
                    "severity": r["severity"],
                    "legal_reference": r.get("legal_reference", ""),
                }
                for r in data
            ]
            db.table("rules").upsert(rows).execute()
            logger.debug("RulesEngine: synced %d rules to Supabase.", len(rows))
        except Exception as exc:
            logger.warning("RulesEngine: Supabase sync failed: %s", exc)

    @staticmethod
    def _rule_to_dict(r: RuleDefinition) -> dict[str, Any]:
        return {
            "id": r.id,
            "name": r.name,
            "trigger_keywords": list(r.trigger_keywords),
            "condition": r.condition,
            "pattern": r.pattern,
            "consequence": r.consequence,
            "recommended_action": r.recommended_action,
            "severity": r.severity,
            "legal_reference": r.legal_reference,
        }

    def _load(self) -> None:
        if not self._rules_path.exists():
            raise FileNotFoundError(
                f"Legal rules file not found: {self._rules_path}"
            )
        raw: list[dict[str, Any]] = json.loads(
            self._rules_path.read_text(encoding="utf-8")
        )
        for entry in raw:
            self._rules.append(
                RuleDefinition(
                    id=entry["id"],
                    name=entry["name"],
                    trigger_keywords=entry.get("trigger_keywords", []),
                    condition=entry.get("condition", "keyword_match"),
                    pattern=entry.get("pattern", ""),
                    consequence=entry["consequence"],
                    recommended_action=entry["recommended_action"],
                    severity=entry.get("severity", "MEDIUM"),
                    legal_reference=entry.get("legal_reference", ""),
                )
            )
        logger.info(
            "RulesEngine loaded %d rules from '%s'.",
            len(self._rules),
            self._rules_path,
        )
