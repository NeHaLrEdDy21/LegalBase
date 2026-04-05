"""
RAG pipeline — the single entry point for end-to-end question answering.

Orchestrates:
  1. Query processing
  2. Retrieval (vector search against FAISS, pre-seeded with legal corpus)
  3. Context assembly
  4. Symbolic rules evaluation (neuro-symbolic cross-check)
  5. LLM generation (Gemini, lawyer-mode structured output)
  6. Reasoning step parsing
  7. Conversation history management

Usage
-----
    pipeline = RAGPipeline(settings)
    response = pipeline.chat(session_id, user_message)
"""
import logging
import time
from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.document_processing.chunker import TextChunker
from app.document_processing.loader import DocumentLoader
from app.embedding.generator import EmbeddingGenerator, get_embedding_generator
from app.models.chat import (
    ChatResponse,
    ReasoningStep,
    SourceDocument,
    TriggeredRuleModel,
)
from app.models.document import DocumentMetadata
from app.rag.context_builder import ContextBuilder
from app.rag.conversation_manager import ConversationManager
from app.rag.query_processor import QueryProcessor
from app.rag.retrieval_engine import RetrievalEngine
from app.services.gemini_client import GeminiClient, LLMResponse
from app.services.nim_client import NIMClient
from app.services.prompt_templates import build_rag_prompt, parse_reasoning_steps
from app.symbolic.corpus_seeder import CorpusSeeder
from app.symbolic.rules_engine import RulesEngine, TriggeredRule
from app.vector_store.base import SearchResult
from app.vector_store.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Neuro-symbolic RAG pipeline with conversation memory.

    Combines neural retrieval (FAISS + Sentence-Transformers + Gemini) with
    a symbolic rules engine that cross-checks every response against a
    catalogue of legal rules before returning to the client.

    Designed as a singleton (see :func:`get_rag_pipeline`) to avoid
    reloading the embedding model on every request.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # ── Embedding & vector store ───────────────────────────────────────────
        self._embedding_generator: EmbeddingGenerator = get_embedding_generator(
            settings.embedding_model
        )
        self._vector_store = FAISSVectorStore(dimension=settings.embedding_dimension)

        # Try to load persisted index if it exists
        self._vector_store.load(str(settings.vector_store_path))

        # ── RAG sub-components ─────────────────────────────────────────────────
        self._query_processor = QueryProcessor()
        self._context_builder = ContextBuilder()
        self._retrieval_engine = RetrievalEngine(
            vector_store=self._vector_store,
            embedding_generator=self._embedding_generator,
            query_processor=self._query_processor,
            top_k=settings.vector_store_top_k,
        )
        self._conversation_manager = ConversationManager(
            max_turns=settings.max_conversation_turns
        )

        # ── Document processing ────────────────────────────────────────────────
        self._loader = DocumentLoader()
        self._chunker = TextChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        # ── LLM — Gemini or NVIDIA NIM (cloud-hosted or self-hosted) ─────────
        if settings.llm_provider.lower() == "nim":
            from app.services.nim_client import HOSTED_BASE_URL
            # Use the NGC key for the hosted endpoint; self-hosted doesn't need one
            nim_api_key = (
                settings.ngc_api_key
                if settings.nim_base_url == HOSTED_BASE_URL
                else "not-used"
            )
            self._llm: GeminiClient | NIMClient = NIMClient(
                base_url=settings.nim_base_url,
                model=settings.nim_model,
                api_key=nim_api_key,
                temperature=settings.nim_temperature,
                max_tokens=settings.nim_max_tokens,
                enable_thinking=settings.nim_enable_thinking,
            )
            mode = "cloud-hosted" if settings.nim_base_url == HOSTED_BASE_URL else "self-hosted"
            logger.info(
                "LLM provider: NVIDIA NIM %s (%s @ %s)",
                mode, settings.nim_model, settings.nim_base_url,
            )
        else:
            self._llm = GeminiClient(
                api_key=settings.gemini_api_key,
                model_name=settings.gemini_model,
                temperature=settings.gemini_temperature,
                max_output_tokens=settings.gemini_max_output_tokens,
            )
            logger.info("LLM provider: Google Gemini (%s)", settings.gemini_model)

        # ── Symbolic rules engine ──────────────────────────────────────────────
        self._rules_engine = RulesEngine(settings.rules_path)
        logger.info(
            "RulesEngine loaded with %d rules.", self._rules_engine.rule_count()
        )

        # ── Corpus seeder — populate FAISS on first boot ───────────────────────
        seeder = CorpusSeeder(settings.corpus_path)
        # Pass the vector_store_path so the seeder knows where to persist
        self._vector_store._save_dir = str(settings.vector_store_path)  # type: ignore[attr-defined]
        seeded = seeder.seed_if_empty(
            vector_store=self._vector_store,
            embedding_generator=self._embedding_generator,
            chunker=self._chunker,
        )
        if seeded:
            logger.info("CorpusSeeder: added %d chunks on first boot.", seeded)

        logger.info(
            "RAGPipeline initialised. Vector store: %d chunks.",
            self._vector_store.count(),
        )

    # ── public API ─────────────────────────────────────────────────────────────

    def chat(self, session_id: str | None, user_message: str) -> ChatResponse:
        """
        Process a user message and return a lawyer-mode ChatResponse.

        Flow
        ----
        1. Session management
        2. Retrieval from FAISS (pre-seeded legal corpus + user documents)
        3. Context assembly
        4. Conversation history formatting
        5. LLM generation (Gemini, lawyer-mode structured prompt)
        6. Symbolic rules evaluation (cross-check query + context + LLM answer)
        7. Reasoning step parsing
        8. Persist assistant turn
        9. Build and return ChatResponse with triggered_rules + reasoning_steps

        Parameters
        ----------
        session_id : str | None
            Existing session ID, or ``None`` to start a new session.
        user_message : str
            The raw user question.
        """
        start = time.perf_counter()

        # 1. Session management
        sid = self._conversation_manager.get_or_create_session(session_id)
        self._conversation_manager.add_user_message(sid, user_message)

        # 2. Retrieval
        results: list[SearchResult] = self._retrieval_engine.retrieve(user_message)

        # 3. Context assembly
        context = self._context_builder.build(results)

        # 4. Conversation history
        history = self._conversation_manager.format_history_for_prompt(sid)

        # 5. LLM generation — pass empty rules list on first call;
        #    rules are evaluated post-generation and included next turn
        llm_response = self._llm.generate_rag_response(
            query=user_message,
            context=context,
            conversation_history=history,
        )

        # 6. Symbolic rules evaluation against the full text surface
        triggered: list[TriggeredRule] = self._rules_engine.evaluate(
            query=user_message,
            context=context,
            llm_answer=llm_response.text,
        )

        # 7. Parse structured reasoning steps from the LLM output
        raw_steps = parse_reasoning_steps(llm_response.text)
        reasoning_steps = [
            ReasoningStep(
                step=s["step"],
                title=s["title"],
                detail=s["detail"],
            )
            for s in raw_steps
        ]

        # 8. Persist assistant turn
        assistant_msg = self._conversation_manager.add_assistant_message(
            sid, llm_response.text
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        # 9. Build API response
        sources: list[SourceDocument] = []
        for r in results:
            preview: str = r.content[:300]
            sources.append(
                SourceDocument(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    content=preview,
                    relevance_score=r.score,
                    metadata=r.metadata,
                    # Convenience fields — extracted so the frontend doesn't need to dig into metadata.
                    # Corpus docs use "title"; user-uploaded docs use "filename"; fall back to doc ID.
                    filename=(
                        r.metadata.get("filename")
                        or r.metadata.get("title")
                        or r.document_id
                    ),
                    excerpt=preview,
                )
            )

        triggered_rule_models = [
            TriggeredRuleModel(
                rule_id=r.rule_id,
                rule_name=r.rule_name,
                consequence=r.consequence,
                recommended_action=r.recommended_action,
                severity=r.severity,
                legal_reference=r.legal_reference,
                explanation=r.explanation,
            )
            for r in triggered
        ]

        if triggered:
            logger.info(
                "chat(): %d symbolic rule(s) triggered for query '%s...'",
                len(triggered),
                user_message[:60],
            )

        return ChatResponse(
            session_id=sid,
            message_id=assistant_msg.message_id,
            answer=llm_response.text,
            sources=sources,
            tokens_used=llm_response.total_tokens,
            processing_time_ms=elapsed_ms,
            triggered_rules=triggered_rule_models,
            reasoning_steps=reasoning_steps,
        )

    def ingest_text(self, text: str, filename: str = "manual_input.txt") -> DocumentMetadata:
        """
        Ingest raw text directly (no file I/O required).
        Returns the document metadata including total chunks.
        """
        raw_text, metadata = self._loader.load_text(text, filename)
        return self._ingest_raw(raw_text, metadata)

    def ingest_file(self, file_path: str) -> DocumentMetadata:
        """Load a file from disk, chunk it, embed it, and index it."""
        raw_text, metadata = self._loader.load(file_path)
        return self._ingest_raw(raw_text, metadata)

    def delete_document(self, document_id: str) -> int:
        """Remove all chunks for a document from the vector store."""
        removed = self._vector_store.delete(document_id)
        self._vector_store.save(str(self.settings.vector_store_path))
        return removed

    def vector_store_count(self) -> int:
        return self._vector_store.count()

    # ── private helpers ────────────────────────────────────────────────────────

    def _ingest_raw(self, raw_text: str, metadata: DocumentMetadata) -> DocumentMetadata:
        chunks = self._chunker.chunk(raw_text, metadata.document_id)
        if not chunks:
            logger.warning("Document '%s' produced no chunks.", metadata.filename)
            return metadata

        texts = [c.content for c in chunks]
        embeddings = self._embedding_generator.embed_texts(texts)

        self._vector_store.add(
            chunk_ids=[c.chunk_id for c in chunks],
            document_ids=[c.document_id for c in chunks],
            contents=texts,
            embeddings=embeddings,
            metadatas=[
                {"filename": metadata.filename, "chunk_index": c.chunk_index}
                for c in chunks
            ],
        )

        self._vector_store.save(str(self.settings.vector_store_path))

        updated = metadata.model_copy(update={"total_chunks": len(chunks)})
        logger.info(
            "Ingested document '%s' → %d chunks.", metadata.filename, len(chunks)
        )
        return updated


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RAGPipeline:
    """Return the application-wide RAGPipeline singleton."""
    return RAGPipeline(settings=get_settings())
