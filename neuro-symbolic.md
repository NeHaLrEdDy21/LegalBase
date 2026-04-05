# Neuro-Symbolic Legal Reasoning — Deep Dive

**Document:** Technical Design Reference
**Version:** 1.0.0
**Date:** 2026-03-23
**Scope:** Symbolic rules engine, corpus seeder, lawyer-mode reasoning, and their integration with the neural RAG pipeline

---

## 1. What Is Neuro-Symbolic AI?

Classical AI systems fall into two camps:

| Paradigm | Mechanism | Strengths | Weaknesses |
|---|---|---|---|
| **Symbolic AI** | Explicit rules, logic, knowledge graphs | Deterministic, auditable, cites authority | Brittle to novel inputs, hard to scale |
| **Neural AI** | Pattern learning from data (LLMs, embeddings) | Fluent, generalises, handles ambiguity | Opaque, can hallucinate, no guaranteed rule compliance |

**Neuro-symbolic AI** combines both: the neural layer handles language understanding and retrieval; the symbolic layer enforces deterministic legal rules, catches issues the LLM might miss, and makes the reasoning auditable.

In CLRS, this means:

```
Neural:   query → embed → FAISS search → Gemini generation
Symbolic: legal_rules.json → keyword/regex evaluation → triggered rules injected into prompt + response
```

Neither layer works alone:
- Without the neural layer, you'd need a rule for every possible phrasing of every legal question.
- Without the symbolic layer, Gemini might produce fluent but legally incomplete or incorrect analysis — failing to mention that a contract is time-barred, or that an NDA breach requires a 48-hour notification obligation.

---

## 2. System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NEURO-SYMBOLIC CORE                             │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      NEURAL LAYER                                 │  │
│  │                                                                   │  │
│  │  Query ──► EmbeddingGenerator ──► FAISSVectorStore ──► Results   │  │
│  │                                        ▲                         │  │
│  │                               CorpusSeeder                       │  │
│  │                          (22 seed documents,                     │  │
│  │                           indexed at first boot)                 │  │
│  │                                                                   │  │
│  │  Results ──► ContextBuilder ──► build_rag_prompt() ──► Gemini   │  │
│  │                                         ▲                        │  │
│  │                              Triggered rules injected            │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                              LLM Response                               │
│                                    │                                    │
│  ┌─────────────────────────────────▼─────────────────────────────────┐  │
│  │                      SYMBOLIC LAYER                               │  │
│  │                                                                   │  │
│  │  RulesEngine.evaluate(query, context, llm_answer)                │  │
│  │       │                                                           │  │
│  │       ▼                                                           │  │
│  │  legal_rules.json (19 rules)                                     │  │
│  │  keyword_match | regex_match                                     │  │
│  │       │                                                           │  │
│  │       ▼                                                           │  │
│  │  list[TriggeredRule]  sorted  HIGH → MEDIUM → LOW                │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                    │
│                       parse_reasoning_steps()                           │
│                                    │                                    │
│                                    ▼                                    │
│           ChatResponse(answer, sources, triggered_rules,               │
│                        reasoning_steps)                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Pre-Seeded Legal Vector Database

### 3.1 Problem it solves

A pure RAG system is only as good as the documents uploaded to it. On a fresh deployment with no uploads, the chatbot has nothing to retrieve from — falling back entirely to Gemini's parametric knowledge, which is ungrounded and unverifiable.

### 3.2 Solution: CorpusSeeder

At application startup, `CorpusSeeder.seed_if_empty()` checks whether the FAISS index contains any vectors. If the store is empty, it:

1. Reads `legal_corpus.json` (22 curated legal principle documents)
2. Passes each document through `TextChunker` (512-token chunks, 64-token overlap)
3. Batch-embeds all chunks via `EmbeddingGenerator` (`all-MiniLM-L6-v2`, 384-dim)
4. Adds all vectors to `FAISSVectorStore` with metadata (`source: "legal_corpus"`, title, category)
5. Persists the index to disk so subsequent restarts skip seeding

This is a **one-time, idempotent operation** — if any documents have been previously indexed (either from a prior seed or from user uploads), seeding is skipped entirely.

### 3.3 Corpus contents

The 22 seed documents cover the domains most commonly encountered in legal queries:

| Category | Document | Key principles |
|---|---|---|
| **Contract** | Consideration | Currie v Misa, past consideration, promissory estoppel |
| **Contract** | Offer & Acceptance | Invitation to treat, postal rule, revocation |
| **Contract** | Certainty of Terms | Scammell v Ouston, agreement to agree |
| **Contract** | Breach & Remedies | Hadley v Baxendale, mitigation, specific performance |
| **Contract** | Force Majeure | Davis Contractors, frustration, Law Reform Act 1943 |
| **Contract** | Liquidated Damages | Cavendish v Makdessi, penalty clause test |
| **NDA** | Essential Elements | Coco v Clark, quality of confidence, notification |
| **NDA** | Injunctive Relief | American Cyanamid, springboard, ex parte applications |
| **Tort** | Negligence | Caparo three-part test, Bolam, contributory negligence |
| **Tort** | Vicarious Liability | Lister v Hesley Hall, close connection test |
| **IP** | Copyright | CDPA 1988, originality, substantial part, fair dealing |
| **IP** | Trade Marks | TMA 1994, s.10 infringement, passing off, Reckitt |
| **IP** | Patents | PA 1977, inventive step, doctrine of equivalents, Actavis |
| **Employment** | Unfair Dismissal | ERA 1996 s.98, ACAS Code, 2-year qualifying period |
| **Employment** | Discrimination | EA 2010, protected characteristics, Vento bands |
| **Employment** | Notice & Wrongful Dismissal | ERA 1996 s.86, garden leave, PILON, constructive dismissal |
| **Property** | Sale of Land | LP(MP)A 1989 s.2, exchange, SDLT, registration |
| **Property** | Leasehold | Street v Mountford, LTA 1954, LTA 1985 s.11 |
| **General** | Limitation Periods | Limitation Act 1980: contract (6yr), tort (6yr), PI (3yr) |
| **General** | UK GDPR | Article 5 principles, lawful bases, 72-hour breach notification |
| **General** | Directors' Duties | CA 2006 ss.171–177, wrongful trading, Sequana |
| **General** | Dispute Resolution | CPR, ADR, Halsey, arbitration, mediation, Tomlin Order |
| **General** | Insolvency | IA 1986, administration, CVA, wrongful trading, CDDA 1986 |

### 3.4 Why this matters for retrieval quality

When a user asks "Is my NDA enforceable?", the retrieval engine searches the entire FAISS index — including the seeded corpus. The top-k results will include the NDA seed documents (covering Coco v Clark, injunctive relief, notification obligations) even before the user has uploaded a single document. This gives Gemini factually grounded context on every query, not just queries about uploaded files.

User-uploaded documents augment the corpus rather than replacing it. A user who uploads their specific NDA will get retrieval results from both their document and the seeded NDA principles — the combination of specific facts and general law.

---

## 4. The Symbolic Rules Engine

### 4.1 Architecture

```
legal_rules.json
      │
      ▼
 RulesEngine.__init__()
      │  reads JSON, constructs list[RuleDefinition] (frozen dataclasses)
      │  raises FileNotFoundError if rules file missing
      ▼
 RulesEngine.evaluate(query, context, llm_answer)
      │
      ├── combined_lower = (query + context + llm_answer).lower()
      │
      ├── for each RuleDefinition:
      │     if condition == "keyword_match":
      │       matched_kws = [kw for kw in trigger_keywords if kw in combined_lower]
      │       if matched_kws → fire TriggeredRule
      │     elif condition == "regex_match":
      │       if re.search(pattern, combined_original, IGNORECASE) → fire TriggeredRule
      │
      └── sort by severity: HIGH(0) → MEDIUM(1) → LOW(2)
          return list[TriggeredRule]
```

### 4.2 Why evaluate against all three inputs?

The engine evaluates `query + context + llm_answer` together, not just the query. This is deliberate:

| Input surface | Why it matters |
|---|---|
| **query** | Catches issues the user explicitly mentioned — "my NDA was breached" immediately fires `NDA_001` |
| **context** | Catches issues present in retrieved documents even if the user didn't use legal terminology — retrieved text mentioning "consideration" fires `CONTRACT_001` |
| **llm_answer** | Catches issues Gemini raised in its own analysis — if Gemini mentions "limitation period" in its answer, `STATUTE_001` fires even if neither the query nor the context contained that phrase |

This three-surface evaluation means rules fire based on the **full legal picture** assembled for the response, not just the raw user input.

### 4.3 Rule types

#### `keyword_match`
Fires if **any** trigger keyword appears (case-insensitive) in the combined text. Used for clear-cut legal concepts with well-known terminology.

```json
{
  "id": "CONTRACT_001",
  "name": "Missing Consideration",
  "trigger_keywords": ["consideration", "gratuitous", "no payment", "without payment", "gift promise"],
  "condition": "keyword_match",
  "consequence": "A contract without consideration is void ab initio under common law.",
  "recommended_action": "Advise client to establish adequate consideration or restructure the agreement as a deed.",
  "severity": "HIGH",
  "legal_reference": "Currie v Misa [1875] LR 10 Ex 153"
}
```

#### `regex_match`
Fires if a regular expression matches the combined text. Used for rules where the trigger is a pattern rather than a fixed keyword — e.g. "six year" / "6-year" / "6 year" all refer to the same limitation period concept.

```json
{
  "id": "STATUTE_001",
  "name": "Limitation Period — General Contract",
  "condition": "regex_match",
  "pattern": "limitation|time.?bar|statute of limitation|6.?year|six.?year",
  "consequence": "A simple contract claim becomes time-barred six years from breach.",
  "severity": "HIGH",
  "legal_reference": "Limitation Act 1980 s.5"
}
```

### 4.4 Severity levels

| Level | Meaning | Examples |
|---|---|---|
| **HIGH** | Fundamental legal issue; missing it could be negligent advice | Missing consideration, NDA breach 48-hr obligation, unfair dismissal qualifying period, limitation period |
| **MEDIUM** | Important issue that may affect outcome | Restraint of trade, occupiers' liability classification, defamation seriousness threshold, adverse possession |
| **LOW** | Informational; worth noting but not typically action-critical | Residual knowledge NDA clause |

Results are always sorted `HIGH → MEDIUM → LOW` so the most critical issues surface first.

### 4.5 Adding new rules

Rules are **data, not code** — add a new rule by appending a JSON object to `legal_rules.json`. No Python changes required. Call `RulesEngine.reload()` to hot-reload without restart.

Example: adding a data protection rule:

```json
{
  "id": "GDPR_001",
  "name": "Data Breach — 72-Hour Notification",
  "trigger_keywords": ["data breach", "personal data", "ico", "notification", "gdpr", "data protection"],
  "condition": "keyword_match",
  "pattern": "",
  "consequence": "A personal data breach likely to risk individuals' rights must be reported to the ICO within 72 hours of discovery.",
  "recommended_action": "Assess risk to data subjects; notify ICO within 72 hours; notify affected individuals if high risk; document the breach.",
  "severity": "HIGH",
  "legal_reference": "UK GDPR Article 33; Data Protection Act 2018"
}
```

---

## 5. Lawyer-Mode Structured Reasoning

### 5.1 The problem with unstructured LLM responses

An unconstrained LLM might respond to a legal query with a fluent but:
- **Unactionable** answer ("It depends on the circumstances...")
- **Incomplete** answer (mentioning the rule but not the recommended next step)
- **Unverifiable** answer (no citations, no indication of what sources were used)
- **Passive** answer (describing the law without saying what the lawyer would *do*)

### 5.2 The five-section output format

The system prompt enforces a mandatory five-section structure on every Gemini response:

```
**LEGAL ISSUE IDENTIFIED**:
  What legal issue is raised. The area of law, the applicable test or doctrine,
  and why it applies to these specific facts.

**SOURCES CONSULTED**:
  The specific retrieved documents, seed corpus entries, cases, or statutes
  the response draws from. Makes the answer verifiable.

**APPLICABLE RULES**:
  The binding legal rules and tests. Statute sections quoted verbatim.
  Symbolic rules flagged by the engine are explicitly incorporated here.

**RECOMMENDED NEXT STEP**:
  The immediate concrete action a practising lawyer would take.
  Specific: who to contact, what time limits apply, what evidence to preserve.

**LEGAL REASONING**:
  Step-by-step application of rules to facts.
  Reaches a conclusion. Identifies range of outcomes where law is uncertain.
```

This format transforms the chatbot from a legal encyclopedia into a **legal reasoning assistant** — one that not only knows the law but tells you what to do about it.

### 5.3 Why symbolic rules are injected *before* generation

The system runs two passes of symbolic reasoning:

**Pass 1 (pre-generation):** On follow-up turns where prior triggered rules exist, they are injected into the prompt under `## Symbolic Rules Triggered`. Gemini receives the rules as explicit instructions — "you MUST incorporate these in your APPLICABLE RULES and RECOMMENDED NEXT STEP sections." This means Gemini's generated text reflects the symbolic rules.

**Pass 2 (post-generation):** After Gemini responds, `RulesEngine.evaluate()` runs again against the full combined surface (query + context + llm_answer). This catches any rules that are relevant but were not pre-injected — for instance, because the retrieved context mentioned a legal concept that only became apparent after retrieval.

The result: **rules are both injected into the LLM's reasoning AND verified against its output**. The LLM cannot silently ignore a critical legal rule that the symbolic engine has flagged.

### 5.4 Parsing reasoning steps

`parse_reasoning_steps(llm_text)` uses a regex to split on the five `**SECTION**:` headers, producing a `list[ReasoningStep]`:

```python
[
  ReasoningStep(step=1, title="Legal Issue Identified", detail="..."),
  ReasoningStep(step=2, title="Sources Consulted",      detail="..."),
  ReasoningStep(step=3, title="Applicable Rules",       detail="..."),
  ReasoningStep(step=4, title="Recommended Next Step",  detail="..."),
  ReasoningStep(step=5, title="Legal Reasoning",        detail="..."),
]
```

These appear in `ChatResponse.reasoning_steps` — the frontend can render them as expandable cards rather than raw markdown, giving users a structured, navigable legal opinion.

---

## 6. End-to-End Example

**User query:** *"My employee signed an NDA but has been sharing our trade secrets with a competitor. What can I do?"*

### Step 1: Neural retrieval

The query is embedded (384-dim) and searched against FAISS. Top-k results include:
- `CORPUS_NDA_ELEMENTS` (score: 0.82) — NDA essential elements, Coco v Clark
- `CORPUS_NDA_INJUNCTIVE_RELIEF` (score: 0.79) — American Cyanamid, springboard injunctions
- `CORPUS_IP_TRADEMARK` (score: 0.41) — trade mark passing off (lower relevance, filtered by context builder if token budget exceeded)

### Step 2: Context assembly

ContextBuilder formats the top results into a 3000-token context block:

```
[Source 1 | Doc: CORPUS_NDA_ELEMENTS | Relevance: 0.82]
A valid non-disclosure agreement must clearly identify... Coco v AN Clark...
three requirements: quality of confidence, imparted in circumstances importing
obligation, unauthorised use causing detriment...

[Source 2 | Doc: CORPUS_NDA_INJUNCTIVE_RELIEF | Relevance: 0.79]
An injunction is the primary remedy... American Cyanamid balance of convenience
test... springboard injunctions neutralise competitive advantage... courts may
grant ex parte within 24–48 hours of discovered breach...
```

### Step 3: LLM generation (lawyer-mode)

Gemini receives the lawyer-mode system prompt + context + query. It generates:

```
**LEGAL ISSUE IDENTIFIED**:
The core issue is breach of confidence / breach of contract arising from an
employee's disclosure of trade secrets in violation of a non-disclosure agreement.
This engages both the equitable doctrine of breach of confidence (Coco v AN Clark
(Engineers) Ltd [1969] RPC 41) and contractual NDA obligations.

**SOURCES CONSULTED**:
- CORPUS_NDA_ELEMENTS: NDA essential elements, three-part Coco v Clark test
- CORPUS_NDA_INJUNCTIVE_RELIEF: Injunctive relief framework, American Cyanamid

**APPLICABLE RULES**:
Under Coco v AN Clark, three elements must be satisfied: (1) the information
has the necessary quality of confidence; (2) it was imparted in circumstances
importing an obligation of confidence; (3) there was unauthorised use causing
detriment. Trade secrets shared with a competitor clearly satisfy all three.
The NDA contractual obligation reinforces this equitable duty.

**RECOMMENDED NEXT STEP**:
Instruct solicitors immediately to apply for an emergency without-notice
(ex parte) injunction within 24–48 hours to prevent further disclosure.
Simultaneously: (1) preserve all evidence of disclosure (emails, messages,
meeting records); (2) identify the competitor and scope of information shared;
(3) issue a written cease-and-desist to the employee and competitor;
(4) review the NDA for any notification obligations to business partners.

**LEGAL REASONING**:
The employee's ongoing disclosure to a competitor satisfies the Coco v Clark
test. Damages are likely inadequate because the competitive harm of ongoing
disclosure is irreversible — each day of further disclosure compounds the
injury. Under American Cyanamid: (1) serious question to be tried — yes,
clear NDA breach; (2) damages inadequate — yes, irreversible competitive harm;
(3) balance of convenience favours injunction — harm to claimant from refusal
outweighs harm to defendant from grant. A springboard injunction may be
appropriate to neutralise the competitive advantage already gained.
```

### Step 4: Symbolic rules evaluation

`RulesEngine.evaluate()` runs on `query + context + llm_answer`:

- "nda" ✓ → **NDA_001** fires (HIGH) — *"Breach of an NDA triggers an immediate obligation to notify legal counsel and assess injunctive relief within 48 hours."*
- "non-disclosure" ✓ → NDA_001 (already triggered)
- "confidentiality breach" ✓ → NDA_001 (already triggered)
- "breach of confidence" ✓ → NDA_001 (already triggered)

Result: `[TriggeredRule(rule_id="NDA_001", severity="HIGH", ...)]`

### Step 5: ChatResponse assembly

```json
{
  "session_id": "3f8a1b2c-...",
  "message_id": "9d4e7f1a-...",
  "answer": "**LEGAL ISSUE IDENTIFIED**:\n...",
  "sources": [
    { "document_id": "CORPUS_NDA_ELEMENTS", "relevance_score": 0.82, ... },
    { "document_id": "CORPUS_NDA_INJUNCTIVE_RELIEF", "relevance_score": 0.79, ... }
  ],
  "triggered_rules": [
    {
      "rule_id": "NDA_001",
      "rule_name": "NDA Breach — Notification Obligation",
      "consequence": "Breach of an NDA triggers an immediate obligation to notify legal counsel...",
      "recommended_action": "Notify legal counsel immediately; preserve evidence; apply for emergency injunction within 48 hours.",
      "severity": "HIGH",
      "legal_reference": "Coco v AN Clark (Engineers) Ltd [1969] RPC 41",
      "explanation": "Rule NDA_001 triggered on keywords: nda, non-disclosure, breach of confidence..."
    }
  ],
  "reasoning_steps": [
    { "step": 1, "title": "Legal Issue Identified", "detail": "The core issue is breach of confidence..." },
    { "step": 2, "title": "Sources Consulted", "detail": "- CORPUS_NDA_ELEMENTS..." },
    { "step": 3, "title": "Applicable Rules", "detail": "Under Coco v AN Clark..." },
    { "step": 4, "title": "Recommended Next Step", "detail": "Instruct solicitors immediately..." },
    { "step": 5, "title": "Legal Reasoning", "detail": "The employee's ongoing disclosure..." }
  ],
  "tokens_used": 1847,
  "processing_time_ms": 2341.5
}
```

---

## 7. Design Decisions and Trade-offs

### 7.1 Why evaluate rules post-generation rather than pre-generation only?

Pre-generation injection requires knowing which rules to inject before seeing the LLM output. On the very first turn, we have no LLM output yet, so we inject nothing. On subsequent turns, we could inject rules based on the prior turn's LLM output — but this introduces a one-turn lag.

Post-generation evaluation solves both problems: it always runs on the complete text surface (query + context + llm_answer), catching rules that only become apparent from Gemini's own analysis. The two-pass design (inject when available, always post-evaluate) gives maximum coverage.

### 7.2 Why keyword/regex rather than embedding-based rule matching?

Symbolic rules are **deterministic** by design. If a rule should fire when the word "consideration" is present, it must fire every time without exception — this is the guarantee that makes the system auditable and legally reliable. Embedding-based matching introduces probabilistic threshold decisions that could cause a HIGH-severity rule to silently fail to trigger on a slight rephrasing.

The trade-off is brittleness to terminology variation — but this is mitigated by:
1. Each rule carries multiple synonymous keywords (e.g. NDA_001 has 6 trigger keywords)
2. Regex rules handle pattern variation (STATUTE_001 matches "6-year", "six year", "6 year", etc.)
3. The neural layer handles the semantic understanding; the symbolic layer handles the rule enforcement

### 7.3 Why 22 seed documents rather than a larger corpus?

The seed corpus is intentionally curated rather than bulk-imported. Each document was written to:
- Cover the most commonly litigated legal areas
- Be dense with authoritative citations (cases, statute sections)
- Be short enough to chunk into a small number of high-quality embeddings
- Not overlap excessively with other documents in the corpus

A larger corpus of lower-quality documents would degrade retrieval precision — irrelevant chunks would compete with the truly relevant ones in top-k results, diluting the context assembled for Gemini.

### 7.4 Why not use a knowledge graph for symbolic reasoning?

Knowledge graphs (RDF, OWL, Prolog) offer richer symbolic reasoning — transitivity, inheritance, inference chains. However, they require:
- A formal ontology of legal concepts
- Expert manual annotation of every document
- A query engine (SPARQL, Datalog) integrated into the pipeline

For a v1 neuro-symbolic system, keyword/regex rules offer 80% of the benefit at 2% of the complexity. The `RulesEngine` is designed to be **swappable** — the `evaluate()` interface is stable, so a graph-based engine could replace it without touching the pipeline.

---

## 8. Extending the Symbolic Layer

### 8.1 Adding a new legal domain (e.g. competition law)

1. Add seed documents to `legal_corpus.json`:
```json
{
  "id": "CORPUS_COMPETITION_DOMINANCE",
  "title": "Abuse of Dominant Position",
  "category": "competition",
  "text": "Article 102 TFEU prohibits any abuse by one or more undertakings of a dominant position... market share above 40% creates a presumption of dominance..."
}
```

2. Add rules to `legal_rules.json`:
```json
{
  "id": "COMPETITION_001",
  "name": "Abuse of Dominant Position",
  "trigger_keywords": ["dominant position", "market share", "article 102", "competition law", "anti-competitive"],
  "condition": "keyword_match",
  "consequence": "Abuse of a dominant position is prohibited under Article 102 TFEU / Chapter II CA 1998.",
  "recommended_action": "Assess market definition and dominance threshold; notify CMA if merger control may apply; preserve internal documents.",
  "severity": "HIGH",
  "legal_reference": "Article 102 TFEU; Competition Act 1998 Chapter II"
}
```

3. No Python changes required. Restart (or call `rules_engine.reload()`) to activate.

### 8.2 Jurisdiction-aware rules (future)

Rules could be extended with a `jurisdiction` field:

```json
{
  "id": "CONTRACT_001_US",
  "jurisdiction": "US",
  "trigger_keywords": ["ucc", "uniform commercial code", "article 2"],
  ...
}
```

The `RulesEngine.evaluate()` signature could accept a `jurisdiction` parameter to filter:
```python
def evaluate(self, query, context, llm_answer, jurisdiction="UK") -> list[TriggeredRule]:
    rules = [r for r in self._rules if r.jurisdiction in (jurisdiction, "ALL")]
    ...
```

### 8.3 Confidence scoring for rules (future)

Currently a rule either fires or it does not. A future enhancement could weight matched keywords by their specificity — "consideration" is highly specific to contract law; "breach" appears across many domains. A weighted scoring system could produce a `confidence: float` on each `TriggeredRule`, allowing the frontend to distinguish "definite match" from "probable match".

---

## 9. Audit Trail and Explainability

Every `ChatResponse` returned by the API is fully auditable:

| Field | What it explains |
|---|---|
| `sources[].document_id` | Which document the answer draws from |
| `sources[].relevance_score` | How semantically similar the chunk was to the query |
| `sources[].content` | The actual text retrieved (first 300 chars) |
| `triggered_rules[].rule_id` | Which symbolic rule fired |
| `triggered_rules[].matched_keywords` | Exactly which words triggered it |
| `triggered_rules[].legal_reference` | The authoritative legal citation |
| `triggered_rules[].explanation` | Human-readable sentence explaining the trigger |
| `reasoning_steps[].title` | Which of the five sections this step represents |
| `reasoning_steps[].detail` | The full text of that reasoning section |
| `tokens_used` | Total token consumption for cost tracking |
| `processing_time_ms` | End-to-end latency for performance monitoring |

A legal professional reviewing the output can trace every claim in the answer back to:
- A retrieved document (via `sources`)
- A deterministic rule (via `triggered_rules`)
- A step in the structured reasoning (via `reasoning_steps`)

This is the core explainability guarantee of the neuro-symbolic design. A purely neural system can only say "here is my answer." This system can say "here is my answer, here is what I retrieved, here is which rules fired, and here is how I reasoned from those to this conclusion."

---

## 10. Summary

| Capability | How it's achieved |
|---|---|
| Always has legal knowledge to retrieve | 22-document seed corpus embedded at first boot |
| Never misses a critical legal rule | 19 symbolic rules evaluated against full text surface |
| Gives actionable lawyer-style advice | Five-section mandatory output format enforced via system prompt |
| Rules integrated into LLM reasoning | Triggered rules injected into prompt before generation |
| Fully auditable output | Every source, rule, and reasoning step returned in ChatResponse |
| Extensible without code changes | Add rules and corpus documents via JSON only |
| Deterministic rule enforcement | keyword_match and regex_match — no probabilistic thresholds |
| Handles novel queries gracefully | Neural layer (Gemini) handles anything the rules don't cover |

---

*End of Neuro-Symbolic Technical Design Reference v1.0.0*
