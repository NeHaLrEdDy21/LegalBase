# Conversational Legal Reasoning System — Technical Specification

**Version:** 2.0.0
**Date:** 2026-03-23
**Status:** Active

---

## 1. System Overview

The Conversational Legal Reasoning System (CLRS) is a production-grade **neuro-symbolic** AI chatbot designed to assist legal professionals, researchers, and laypersons in querying, understanding, and reasoning over legal matters.

The system combines:

- **Retrieval Augmented Generation (RAG)** to ground LLM responses in actual legal documents
- **Pre-seeded legal vector database** — a curated corpus of 22 legal principle documents (contracts, tort, IP, employment, property, GDPR, insolvency) embedded into FAISS at first boot, ensuring Gemini always has a legal knowledge base even before user documents are uploaded
- **Symbolic rules engine** — 19 deterministic legal rules (JSON-configurable) that cross-check every query + retrieved context + LLM answer for applicable legal principles, returning triggered rules with severity ratings and authoritative citations
- **Lawyer-mode structured output** — every response is structured as five labelled sections: Legal Issue Identified → Sources Consulted → Applicable Rules → Recommended Next Step → Legal Reasoning
- **Semantic vector search** to surface the most contextually relevant case law and principles
- **Conversational memory** to maintain multi-turn dialogue coherence
- **Google Gemini LLM** (`gemini-1.5-flash`) for legal reasoning and natural language generation
- **Explainable responses** with source citations, triggered symbolic rules, and parsed reasoning steps

The system is designed to be modular, scalable, and deployable in containerised cloud environments.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              React + TypeScript Chatbot UI                  │   │
│   │  (Chat bubbles, typing indicator, rules panel, steps panel) │   │
│   └─────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ HTTPS / REST
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY LAYER                          │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    FastAPI Application                      │   │
│   │   /api/v1/chat    /api/v1/documents    /api/v1/health       │   │
│   │   Rate Limiting | Input Validation | CORS                   │   │
│   └──────────┬─────────────────────────┬───────────────────────┘   │
└──────────────┼─────────────────────────┼───────────────────────────┘
               │                         │
               ▼                         ▼
┌──────────────────────────┐   ┌─────────────────────────────────────┐
│    RAG PIPELINE LAYER    │   │      DOCUMENT INGESTION LAYER        │
│                          │   │                                     │
│  ┌────────────────────┐  │   │  ┌──────────────────────────────┐   │
│  │ Conversation       │  │   │  │   Document Loader             │   │
│  │ Manager            │  │   │  │   (PDF, TXT, DOCX)           │   │
│  └────────┬───────────┘  │   │  └──────────────┬───────────────┘   │
│           │              │   │                 │                   │
│  ┌────────▼───────────┐  │   │  ┌──────────────▼───────────────┐   │
│  │ Query Processor    │  │   │  │   Text Chunker               │   │
│  └────────┬───────────┘  │   │  │   (512 tokens, 64 overlap)  │   │
│           │              │   │  └──────────────┬───────────────┘   │
│  ┌────────▼───────────┐  │   │                 │                   │
│  │ Retrieval Engine   │◄─┼───┼─────────────────┤                   │
│  └────────┬───────────┘  │   │  ┌──────────────▼───────────────┐   │
│           │              │   │  │   Embedding Generator        │   │
│  ┌────────▼───────────┐  │   │  │   (all-MiniLM-L6-v2, 384d)  │   │
│  │ Context Builder    │  │   │  └──────────────┬───────────────┘   │
│  └────────┬───────────┘  │   │                 │                   │
│           │              │   │  ┌──────────────▼───────────────┐   │
│  ┌────────▼───────────┐  │   │  │  FAISS Vector Store          │   │
│  │ Gemini LLM Client  │  │   │  │  (pre-seeded legal corpus)   │   │
│  └────────┬───────────┘  │   │  └──────────────────────────────┘   │
│           │              │   └─────────────────────────────────────┘
│  ┌────────▼───────────┐  │
│  │  Symbolic Rules    │  │   ┌─────────────────────────────────────┐
│  │  Engine            │  │   │      SYMBOLIC LAYER                  │
│  └────────┬───────────┘  │   │                                     │
│           │              │   │  ┌──────────────────────────────┐   │
│  ┌────────▼───────────┐  │   │  │   legal_rules.json           │   │
│  │  Reasoning Step    │  │   │  │   (19 configurable rules)    │   │
│  │  Parser            │  │   │  └──────────────────────────────┘   │
│  └────────┬───────────┘  │   │  ┌──────────────────────────────┐   │
└───────────┼──────────────┘   │  │   legal_corpus.json          │   │
            │                  │  │   (22 seed documents)        │   │
            ▼                  │  └──────────────────────────────┘   │
  ChatResponse with:           │  ┌──────────────────────────────┐   │
  - answer                     │  │   CorpusSeeder               │   │
  - sources                    │  │   (first-boot indexing)      │   │
  - triggered_rules            │  └──────────────────────────────┘   │
  - reasoning_steps            └─────────────────────────────────────┘
```

---

## 3. Component Descriptions

### 3.1 Frontend (React + TypeScript)

| Component | Responsibility |
|---|---|
| `ChatInterface` | Root container managing chat state and API calls |
| `MessageList` | Renders conversation history with role-based styling |
| `MessageBubble` | Individual message with source citation display |
| `InputBar` | User text input with submit and keyboard handling |
| `TypingIndicator` | Animated indicator while awaiting LLM response |
| `SourcePanel` | Expandable panel showing retrieved legal document citations |
| `RulesPanel` | Displays triggered symbolic rules with severity badges (HIGH/MEDIUM/LOW) |
| `ReasoningStepsPanel` | Shows the five-step lawyer reasoning chain as expandable cards |
| `apiService` | Axios-based HTTP client for backend communication |

### 3.2 Backend — API Layer

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app initialisation, middleware, lifespan events |
| `api/v1/chat.py` | Chat endpoint: receives query, returns LLM response with rules + steps |
| `api/v1/documents.py` | Document ingestion endpoint (text, file, delete) |
| `api/v1/health.py` | Liveness and readiness probes |
| `middleware/rate_limiter.py` | Token-bucket rate limiting per IP |

### 3.3 RAG Pipeline

| Module | Responsibility |
|---|---|
| `rag/pipeline.py` | Orchestrates the full neuro-symbolic flow: retrieve → augment → generate → evaluate rules → parse steps |
| `rag/query_processor.py` | Cleans, validates, and appends legal domain hint to queries |
| `rag/context_builder.py` | Formats retrieved chunks into LLM prompt context (token-budget aware) |
| `rag/conversation_manager.py` | Manages session-based conversation history with TTL eviction |
| `rag/retrieval_engine.py` | Embeds query, searches FAISS, returns ranked SearchResult list |

### 3.4 Symbolic Layer

| Module | Responsibility |
|---|---|
| `symbolic/rules_engine.py` | Loads `legal_rules.json`, evaluates keyword/regex rules against query+context+answer |
| `symbolic/legal_rules.json` | 19 configurable legal rules (contracts, NDA, tort, IP, employment, property, statutes) |
| `symbolic/corpus_seeder.py` | Indexes `legal_corpus.json` into FAISS at startup if the store is empty |
| `symbolic/legal_corpus.json` | 22 curated legal principle documents used as the base knowledge layer |

### 3.5 Vector Store

| Module | Responsibility |
|---|---|
| `vector_store/faiss_store.py` | FAISS IndexFlatIP with L2-normalisation (cosine similarity), thread-safe, persistent |
| `vector_store/base.py` | Abstract base interface for store implementations |

### 3.6 Embedding & Document Processing

| Module | Responsibility |
|---|---|
| `document_processing/loader.py` | Loads PDF (pdfplumber), DOCX (python-docx), TXT files |
| `document_processing/chunker.py` | Sentence-level sliding window, tiktoken-aware, 512-token chunks with 64-token overlap |
| `embedding/generator.py` | Dense vectors via Sentence Transformers (`all-MiniLM-L6-v2`, 384-dim), L2-normalised |

### 3.7 LLM Integration

| Module | Responsibility |
|---|---|
| `services/gemini_client.py` | Gemini API wrapper with tenacity retry (3 attempts, exponential backoff) |
| `services/prompt_templates.py` | Lawyer-mode system prompt, RAG prompt builder (injects triggered rules), `parse_reasoning_steps()` |

---

## 4. Data Flow

### 4.1 First-Boot Corpus Seeding

```
Application Startup
    │
    ▼
RAGPipeline.__init__()
    │
    ▼
Load persisted FAISS index (if exists)
    │
    ▼
CorpusSeeder.seed_if_empty()
    │  if vector store count == 0:
    │    read legal_corpus.json (22 documents)
    │    chunk each document (TextChunker)
    │    embed all chunks (EmbeddingGenerator, batch)
    │    add to FAISSVectorStore
    │    save index to disk
    ▼
Vector store is guaranteed non-empty on first query
```

### 4.2 Document Ingestion Flow

```
File Upload (PDF/TXT/DOCX) or Raw Text
    │
    ▼
Document Loader  →  raw text + DocumentMetadata
    │
    ▼
Text Chunker  →  list[DocumentChunk] (512 tokens, 64 overlap)
    │
    ▼
Embedding Generator  →  (n, 384) float32 ndarray, L2-normalised
    │
    ▼
FAISSVectorStore.add()  →  indexed in-memory + persisted to disk
```

### 4.3 Neuro-Symbolic Chat Flow

```
User Query  (POST /api/v1/chat)
    │
    ▼
Input Validation (Pydantic ChatRequest)
    │
    ▼
ConversationManager  →  create/get session, append user message
    │
    ▼
QueryProcessor.process()  →  clean + validate + append legal hint
    │
    ▼
RetrievalEngine.retrieve()
    │  embed query (384-dim) → FAISS top-k search
    │  returns list[SearchResult] with cosine scores
    │  (searches pre-seeded corpus + any user-uploaded docs)
    ▼
ContextBuilder.build()  →  filter by score ≥ 0.30, pack within 3000 token budget
    │
    ▼
build_rag_prompt(query, context, history)
    │  lawyer-mode system prompt
    │  structured output: 5 mandatory sections
    ▼
GeminiClient.generate_rag_response()  →  LLMResponse (text, tokens, latency)
    │
    ▼
RulesEngine.evaluate(query, context, llm_answer)
    │  keyword_match and regex_match rules
    │  returns list[TriggeredRule] sorted HIGH→MEDIUM→LOW
    ▼
parse_reasoning_steps(llm_answer)
    │  parses **SECTION**: markers → list[ReasoningStep]
    ▼
ConversationManager  →  append assistant message
    │
    ▼
ChatResponse(answer, sources, triggered_rules, reasoning_steps)
    │
    ▼
HTTP 200  →  Frontend
```

---

## 5. API Endpoints

### Base URL: `/api/v1`

---

#### `POST /chat`

Submits a user query and receives a neuro-symbolic lawyer-mode response.

**Request Body:**
```json
{
  "session_id": "string | null",
  "message": "string (min 1, max 4096 chars)"
}
```

**Response:**
```json
{
  "session_id": "string (UUID)",
  "message_id": "string (UUID)",
  "answer": "string (five-section lawyer-mode text)",
  "sources": [
    {
      "chunk_id": "string",
      "document_id": "string",
      "content": "string (truncated to 300 chars)",
      "relevance_score": "float [0.0, 1.0]",
      "metadata": {}
    }
  ],
  "tokens_used": "integer",
  "processing_time_ms": "float",
  "triggered_rules": [
    {
      "rule_id": "string",
      "rule_name": "string",
      "consequence": "string",
      "recommended_action": "string",
      "severity": "HIGH | MEDIUM | LOW",
      "legal_reference": "string",
      "explanation": "string"
    }
  ],
  "reasoning_steps": [
    {
      "step": "integer (1–5)",
      "title": "string",
      "detail": "string"
    }
  ]
}
```

**Status Codes:**
- `200` — Success
- `422` — Empty query or query exceeds 4096 characters
- `429` — Rate limit exceeded
- `500` — Internal server error

---

#### `GET /chat/{session_id}`

Returns the full conversation history for a session.

**Response:** `ConversationHistory` with `session_id`, `messages[]`, `created_at`, `updated_at`

**Status Codes:** `200` | `404`

---

#### `DELETE /chat/{session_id}`

Clears a conversation session. Returns `204 No Content`.

**Status Codes:** `204` | `404`

---

#### `POST /documents/text`

Ingests raw text directly into the vector store.

**Request Body:**
```json
{
  "text": "string",
  "filename": "string (default: manual_input.txt)"
}
```

**Response:** `IngestResponse` — `document_id`, `filename`, `total_chunks`, `message`
**Status:** `201 Created`

---

#### `POST /documents/file`

Ingests a file (PDF, DOCX, TXT) via multipart upload. Max 20 MB.

**Response:** `IngestResponse`
**Status:** `201` | `400` (load error) | `413` (file too large) | `415` (unsupported type)

---

#### `DELETE /documents/{document_id}`

Removes a document and all its chunks from the vector store.

**Response:** `{ "document_id": "...", "chunks_removed": N, "message": "..." }`
**Status:** `200` | `404`

---

#### `GET /health`

Liveness probe. Always returns `200`.

**Response:** `{ "status": "healthy", "timestamp": "ISO 8601" }`

---

#### `GET /health/ready`

Readiness probe. Returns `200` when vector store is loaded.

**Response:** `{ "status": "ready", "vector_store_chunks": N, "timestamp": "ISO 8601" }`
**Status:** `200` | `503`

---

## 6. Vector Database Design

### Index Structure

**Primary Index:** FAISS `IndexFlatIP` (Inner Product on L2-normalised vectors = cosine similarity)
**Dimension:** 384 (all-MiniLM-L6-v2)
**Thread safety:** `threading.Lock` on all read/write operations
**Persistence:** `faiss.index` + `metadata.pkl` written to `data/vector_store/`

### Pre-Seeded Legal Corpus (22 documents)

| Category | Documents |
|---|---|
| Contract | Consideration, Offer & Acceptance, Certainty, Breach & Remedies, Force Majeure, Liquidated Damages |
| NDA | Essential Elements, Injunctive Relief |
| Tort | Negligence (Caparo), Vicarious Liability |
| IP | Copyright, Trade Marks, Patents |
| Employment | Unfair Dismissal, Discrimination (EA 2010), Notice & Wrongful Dismissal |
| Property | Sale of Land, Leasehold |
| General | Limitation Periods, UK GDPR, Directors' Duties, Dispute Resolution, Insolvency |

### Chunking Parameters

| Parameter | Value | Justification |
|---|---|---|
| `chunk_size` | 512 tokens | Balances context and retrieval precision |
| `chunk_overlap` | 64 tokens | Prevents context boundary loss |
| `tokeniser` | tiktoken `cl100k_base` | Consistent with Gemini token counting |
| `splitter` | Sentence-level sliding window | Respects sentence boundaries |

### Retrieval Parameters

| Parameter | Default | Configurable |
|---|---|---|
| `top_k` | 5 | Yes (1–20 via settings) |
| `min_relevance_score` | 0.30 | Yes |
| `max_context_tokens` | 3000 | Yes |

---

## 7. Symbolic Rules Engine

### Rule Schema

Each rule in `legal_rules.json` follows this schema:

```json
{
  "id": "CONTRACT_001",
  "name": "Missing Consideration",
  "trigger_keywords": ["consideration", "gratuitous"],
  "condition": "keyword_match",
  "pattern": "",
  "consequence": "A contract without consideration is void ab initio.",
  "recommended_action": "Establish adequate consideration or restructure as a deed.",
  "severity": "HIGH",
  "legal_reference": "Currie v Misa [1875] LR 10 Ex 153"
}
```

### Rule Coverage (19 rules)

| Category | Rules | IDs |
|---|---|---|
| Contract | 4 | CONTRACT_001–004 |
| NDA | 2 | NDA_001–002 |
| Tort | 3 | TORT_001–003 |
| IP | 3 | IP_001–003 |
| Employment | 3 | EMPLOYMENT_001–003 |
| Property | 2 | PROPERTY_001–002 |
| Statutes | 2 | STATUTE_001–002 |

### Evaluation Logic

```
combined_text = query + context + llm_answer

For each rule:
  if condition == "keyword_match":
    fire if ANY trigger_keyword ∈ combined_text.lower()
  if condition == "regex_match":
    fire if re.search(pattern, combined_text, IGNORECASE) matches

Sort fired rules: HIGH → MEDIUM → LOW
Return list[TriggeredRule] with explanation, recommended_action, legal_reference
```

---

## 8. Lawyer-Mode Prompt Architecture

Every response from Gemini is structured using five mandatory sections:

```
**LEGAL ISSUE IDENTIFIED**: Characterise the legal issue, area of law, relevant test.

**SOURCES CONSULTED**: List retrieved documents, cases, statutes drawn upon.

**APPLICABLE RULES**: State the binding legal rules, tests, and principles.
  (Symbolic rules flagged by the rules engine are injected here.)

**RECOMMENDED NEXT STEP**: Concrete practitioner action — what to do next,
  time limits, who to notify, evidence to preserve.

**LEGAL REASONING**: Step-by-step application of rules to facts; reasoned conclusion.
```

### Symbolic Rule Injection

Triggered rules are injected into the prompt under a `## Symbolic Rules Triggered` section **before** Gemini generates its response, so the LLM reasons *with* the rules — not just around them:

```
## Symbolic Rules Triggered
[HIGH] CONTRACT_001 — Missing Consideration
  Legal consequence: A contract without consideration is void ab initio.
  Practitioner action: Advise client to establish adequate consideration...
  Authority: Currie v Misa [1875] LR 10 Ex 153
```

### Context Window Management

- Maximum context chunks: 5 (configurable via `vector_store_top_k`)
- Maximum conversation history turns: 20 (configurable)
- Token budget for context: 3000 tokens
- Truncation strategy: oldest turns removed first; chunks filtered by score, then greedily packed

---

## 9. Chatbot UI Behaviour

### Chat Interface Features

- **Message bubbles:** user messages right-aligned, assistant messages left-aligned
- **Typing indicator:** animated three-dot animation while awaiting response
- **Source panel:** collapsible panel below each assistant message showing retrieved chunks with relevance scores
- **Symbolic rules panel:** expandable section per response showing triggered rules with HIGH/MEDIUM/LOW severity badges and legal citations
- **Reasoning steps panel:** the five lawyer-mode sections rendered as expandable step cards
- **Error states:** inline error messages with retry option
- **Session persistence:** `session_id` stored in `sessionStorage`
- **Keyboard shortcuts:** Enter to submit, Shift+Enter for newline
- **Responsive layout:** desktop and tablet

### UI State Machine

```
IDLE
 │ user types
 ▼
INPUT_READY
 │ user submits
 ▼
LOADING (typing indicator shown)
 │ response received
 ▼
RESPONSE_DISPLAYED (answer + rules + reasoning steps rendered)
 │ user types next message
 ▼
INPUT_READY ...
 │ error occurs
 ▼
ERROR_STATE (retry button shown)
```

---

## 10. Scalability Considerations

| Concern | Strategy |
|---|---|
| High chat concurrency | FastAPI async endpoints; GeminiClient is sync but called from async handler |
| Large document corpora | FAISS IVF index for million-scale vectors (swap IndexFlatIP → IndexIVFFlat) |
| Session state | Migrate ConversationManager from in-memory dict to Redis for horizontal scaling |
| Embedding throughput | Batch embedding (default batch_size=64); GPU-accelerated Sentence Transformers |
| API rate limits | Gemini API quota managed with tenacity retry (3 attempts, exponential backoff 2–30s) |
| Symbolic rules scale | RulesEngine is O(n×m) — n rules, m keywords; scales to hundreds of rules without issue |
| Document ingestion load | Background task queue (Celery + Redis) for async ingestion at scale |

---

## 11. Security Considerations

| Risk | Mitigation |
|---|---|
| Prompt injection | Input sanitisation; system prompt isolation; QueryProcessor rejects oversized inputs |
| API key exposure | Environment variables only; `.env` excluded from VCS; `.env.example` documented |
| Rate abuse / DoS | Token-bucket rate limiter per IP (60 req/min default, configurable) |
| Malicious file upload | File type validation (extension + MIME); 20 MB size limit; temp file cleanup |
| XSS via LLM output | Frontend sanitises rendered markdown (react-markdown with remark-gfm) |
| CORS misconfiguration | Strict allowlist of origins via settings |
| Data leakage in logs | No user query content logged at INFO level |
| Dependency vulnerabilities | `pip audit` + `npm audit` in CI pipeline |

---

## 12. Testing Strategy

### Test Pyramid

```
         ┌───────┐
         │  E2E  │  Playwright — chat flow end-to-end
         └───┬───┘
       ┌─────┴─────┐
       │Integration│  pytest — API endpoints, RAG pipeline, vector store
       └─────┬─────┘
     ┌───────┴───────┐
     │  Unit Tests   │  pytest — chunker, embedder, retriever, rules engine, prompt builder
     └───────────────┘
```

### Test Coverage Targets

| Layer | Target Coverage |
|---|---|
| document ingestion | 90% |
| chunker | 95% |
| embedding generator | 85% |
| vector store | 90% |
| retrieval engine | 90% |
| RAG pipeline | 85% |
| symbolic rules engine | 90% |
| corpus seeder | 80% |
| chat API | 90% |
| conversation manager | 90% |

---

## 13. Deployment Plan

### Environment Configuration

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | required |
| `GEMINI_MODEL` | Gemini model name | `gemini-1.5-flash` |
| `GEMINI_TEMPERATURE` | LLM temperature | `0.2` |
| `VECTOR_STORE_PATH` | Persistent FAISS index directory | `data/vector_store` |
| `EMBEDDING_MODEL` | Sentence Transformer model ID | `all-MiniLM-L6-v2` |
| `RULES_PATH` | Path to `legal_rules.json` | `app/symbolic/legal_rules.json` |
| `CORPUS_PATH` | Path to `legal_corpus.json` | `app/symbolic/legal_corpus.json` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_REQUESTS` | Requests per window per IP | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window | `60` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000","http://localhost:5173"]` |

### Docker Compose Topology

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./data:/app/data"]
    env_file: .env

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    depends_on: [backend]
```

### Deployment Stages

1. **Local development** — `uvicorn app.main:app --reload` + `npm run dev`, Docker Compose optional
2. **CI pipeline** — GitHub Actions: lint → test → build → `pip audit` / `npm audit`
3. **Staging** — containerised deployment, smoke tests against `/api/v1/health/ready`
4. **Production** — cloud container service (GCP Cloud Run / AWS ECS), HTTPS, secrets manager

### Health Check Strategy

- `GET /api/v1/health` — liveness (always `200`)
- `GET /api/v1/health/ready` — readiness (`vector_store_chunks > 0` required)
- Docker `HEALTHCHECK` directive pointing to liveness endpoint

---

## 14. Implementation Status

| Step | Description | Status |
|---|---|---|
| 1 | Technical Specification (this document) | Complete |
| 2 | BDD Scenarios (Gherkin feature files) | Complete |
| 3 | TDD Test Suite (unit + integration) | Complete |
| 4 | Backend Implementation (FastAPI + RAG + Symbolic) | Complete |
| 5 | Frontend UI (React + TypeScript) | In Progress |
| 6 | Devil's Advocate Review | Pending |
| 7 | Production Hardening | Pending |

---

*End of Specification v2.0.0*
