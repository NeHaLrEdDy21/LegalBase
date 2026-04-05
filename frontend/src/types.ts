export interface SourceDocument {
  document_id: string;
  filename: string;
  relevance_score: number;
  excerpt: string;
}

export interface TriggeredRule {
  rule_id: string;
  rule_name: string;
  consequence: string;
  recommended_action: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  legal_reference: string;
  explanation: string;
}

export interface ReasoningStep {
  step: number;
  title: string;
  detail: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDocument[];
  triggered_rules?: TriggeredRule[];
  reasoning_steps?: ReasoningStep[];
  timestamp: Date;
  tokens_used?: number;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  answer: string;
  sources: SourceDocument[];
  tokens_used: number;
  processing_time_ms: number;
  triggered_rules: TriggeredRule[];
  reasoning_steps: ReasoningStep[];
}

export interface IngestTextRequest {
  text: string;
  filename?: string;
}

export interface IngestResponse {
  document_id: string;
  filename: string;
  document_type: string;
  file_size_bytes: number;
  total_chunks: number;
  message: string;
}

export interface DeleteDocumentResponse {
  document_id: string;
  chunks_removed: number;
  message: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  python_version: string;
  platform: string;
}

export interface ReadinessResponse {
  status: string;
  vector_store_chunks: number;
}

// ── Knowledge Base ─────────────────────────────────────────────────────────────

export interface KnowledgeBaseDocument {
  document_id: string;
  filename: string;
  chunk_count: number;
  extra: Record<string, unknown>;
}

// ── Symbolic Rules ─────────────────────────────────────────────────────────────

export interface Rule {
  id: string;
  name: string;
  trigger_keywords: string[];
  condition: "keyword_match" | "regex_match";
  pattern: string;
  consequence: string;
  recommended_action: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  legal_reference: string;
}

export type RuleCreate = Omit<Rule, never>;  // all fields required on create
export type RuleUpdate = Partial<Omit<Rule, "id">>;  // all optional on update
