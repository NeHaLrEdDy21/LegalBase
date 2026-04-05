import axios from "axios";
import type {
  ChatRequest,
  ChatResponse,
  IngestTextRequest,
  IngestResponse,
  DeleteDocumentResponse,
  ReadinessResponse,
  KnowledgeBaseDocument,
  Rule,
  RuleCreate,
  RuleUpdate,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

// Gemma 4 with thinking mode can take 2-3 min for complex legal reasoning.
// Set a 5-minute timeout to accommodate extended inference.
const http = axios.create({
  baseURL: BASE_URL,
  timeout: 300_000,
  headers: { "Content-Type": "application/json" },
});

// Token getter — set by App once the auth provider is ready
let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenGetter(fn: () => Promise<string | null>) {
  _getToken = fn;
}

// Attach Bearer token to every request when available
http.interceptors.request.use(async (config) => {
  if (_getToken) {
    const token = await _getToken().catch(() => null);
    if (token) config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  chat: (req: ChatRequest) =>
    http.post<ChatResponse>("/chat", req).then((r) => r.data),

  getHistory: (sessionId: string) =>
    http.get(`/chat/${sessionId}`).then((r) => r.data),

  deleteSession: (sessionId: string) =>
    http.delete(`/chat/${sessionId}`).then((r) => r.data),

  ingestText: (req: IngestTextRequest) =>
    http.post<IngestResponse>("/documents/text", req).then((r) => r.data),

  ingestFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post<IngestResponse>("/documents/file", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  deleteDocument: (documentId: string) =>
    http
      .delete<DeleteDocumentResponse>(`/documents/${documentId}`)
      .then((r) => r.data),

  readiness: () =>
    http.get<ReadinessResponse>("/health/ready").then((r) => r.data),

  // ── Knowledge Base ──────────────────────────────────────────────────────────
  listDocuments: () =>
    http.get<KnowledgeBaseDocument[]>("/documents").then((r) => r.data),

  // ── Symbolic Rules ──────────────────────────────────────────────────────────
  listRules: () =>
    http.get<Rule[]>("/rules").then((r) => r.data),

  addRule: (rule: RuleCreate) =>
    http.post<Rule>("/rules", rule).then((r) => r.data),

  updateRule: (ruleId: string, updates: RuleUpdate) =>
    http.patch<Rule>(`/rules/${ruleId}`, updates).then((r) => r.data),

  deleteRule: (ruleId: string) =>
    http.delete(`/rules/${ruleId}`),
};
