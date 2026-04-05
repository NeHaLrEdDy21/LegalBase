# Feature: RAG Pipeline Orchestration
# Covers the retrieve-augment-generate pipeline behaviour end to end.

Feature: RAG Pipeline Orchestration
  As the system
  I want to orchestrate retrieval, context building, and LLM generation
  So that answers are always grounded, cited, and coherent

  Background:
    Given the RAG pipeline is initialised with a FAISS vector store
    And the Gemini LLM client is available (mocked in unit tests)

  # ---------------------------------------------------------------------------
  # Context building
  # ---------------------------------------------------------------------------

  Scenario: Context builder formats retrieved chunks correctly
    Given the retrieval engine returns 3 chunks with filenames and page numbers
    When the context builder formats the chunks
    Then the output contains a labelled section for each chunk
    And each section includes the filename and chunk text
    And the total formatted context does not exceed 4096 tokens

  Scenario: Context builder truncates when retrieved chunks exceed token budget
    Given the retrieval engine returns 5 chunks each containing 1200 tokens
    When the context builder applies the token budget of 4096
    Then only chunks that fit within the budget are included
    And the highest scoring chunks are prioritised over lower scoring ones

  Scenario: Context builder handles empty retrieval gracefully
    Given the retrieval engine returns 0 chunks
    When the context builder formats an empty chunk list
    Then the context string contains a no-documents-found notice
    And the pipeline continues without raising an exception

  # ---------------------------------------------------------------------------
  # Prompt construction
  # ---------------------------------------------------------------------------

  Scenario: LLM prompt contains system instruction, context, history, and query
    Given context chunks have been built
    And there are 2 prior conversation turns in the session
    And the user query is "What constitutes fair use in copyright law?"
    When the Gemini client constructs the prompt
    Then the prompt contains the system legal assistant instruction
    And the prompt contains the formatted context section
    And the prompt contains the 2 prior conversation turns
    And the prompt contains the user query

  Scenario: System prompt instructs the LLM not to fabricate citations
    When the Gemini client constructs any prompt
    Then the system instruction explicitly states "Do not fabricate case names or citations"

  # ---------------------------------------------------------------------------
  # End-to-end pipeline
  # ---------------------------------------------------------------------------

  Scenario: Full RAG pipeline returns a grounded answer
    Given a legal query "What is the duty of care in tort law?"
    And the vector store contains relevant chunks about "duty of care"
    When the full RAG pipeline is executed
    Then the pipeline returns an "answer" string
    And the pipeline returns a non-empty "sources" list
    And the answer is not empty

  Scenario: RAG pipeline records processing time
    When the full RAG pipeline executes
    Then the response includes a "processing_time_ms" field
    And "processing_time_ms" is a positive float

  # ---------------------------------------------------------------------------
  # Failure resilience
  # ---------------------------------------------------------------------------

  Scenario: Gemini API returns an error — pipeline returns a graceful error response
    Given the Gemini API client raises a ServiceUnavailableError
    When the RAG pipeline calls the LLM
    Then the pipeline catches the exception
    And the API returns HTTP 503
    And the response body contains an "error" field with a user-friendly message

  Scenario: Gemini API times out — pipeline applies retry with backoff
    Given the Gemini API client times out on the first two calls
    And succeeds on the third call
    When the RAG pipeline calls the LLM
    Then the client retries up to 3 times with exponential backoff
    And the pipeline ultimately returns a successful response

  Scenario: Embedding generator fails during query processing
    Given the embedding generator raises a RuntimeError for the query
    When the RAG pipeline processes the query
    Then the pipeline catches the exception
    And the API returns HTTP 500 with a structured error response
