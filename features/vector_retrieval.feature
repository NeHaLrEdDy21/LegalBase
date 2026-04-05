# Feature: Semantic Vector Retrieval
# Covers the behaviour of the retrieval engine when searching the vector store.

Feature: Semantic Vector Retrieval
  As the RAG pipeline
  I want to retrieve the most semantically relevant legal document chunks
  So that the LLM has accurate grounding for its responses

  Background:
    Given the vector store contains 50 ingested legal document chunks
    And the embedding model is loaded and ready

  # ---------------------------------------------------------------------------
  # Basic retrieval correctness
  # ---------------------------------------------------------------------------

  Scenario: Query retrieves semantically relevant chunks
    Given the vector store contains a chunk about "breach of contract remedies"
    When a query "What remedies exist for breach of contract?" is embedded and searched
    Then the top result's chunk_text is semantically related to breach of contract
    And the top result's relevance score is above 0.5

  Scenario: Retrieval returns the correct number of results
    Given the user requests top_k equals 5
    When the retrieval engine performs a similarity search
    Then exactly 5 chunks are returned
    And results are ordered by descending relevance score

  Scenario: Retrieval returns fewer results than top_k when store has fewer chunks
    Given the vector store contains only 3 chunks
    And the user requests top_k equals 5
    When the retrieval engine performs a similarity search
    Then exactly 3 chunks are returned

  Scenario: Each retrieved chunk includes required metadata fields
    When the retrieval engine returns results
    Then each result contains "chunk_id", "document_id", "filename", "chunk_text", "relevance_score"
    And "relevance_score" is a float between 0.0 and 1.0

  # ---------------------------------------------------------------------------
  # Relevance filtering
  # ---------------------------------------------------------------------------

  Scenario: Chunks below the similarity threshold are filtered out
    Given all chunks in the vector store have similarity score below 0.3 for the query
    When the retrieval engine applies the similarity threshold filter
    Then 0 chunks are returned above the threshold
    And the pipeline receives an empty retrieval result

  Scenario: Retrieval correctly ranks a highly relevant chunk above a less relevant one
    Given the vector store contains:
      | chunk_id | content                                               |
      | c-001    | "The tort of negligence requires duty of care"        |
      | c-002    | "Contract law governs commercial agreements"          |
    When the query "What is required to prove negligence?" is searched
    Then chunk "c-001" has a higher relevance score than chunk "c-002"
    And chunk "c-001" appears first in the results

  # ---------------------------------------------------------------------------
  # Edge cases
  # ---------------------------------------------------------------------------

  Scenario: Retrieval on an empty vector store returns empty results
    Given the vector store contains 0 chunks
    When a query is submitted to the retrieval engine
    Then the retrieval engine returns an empty list
    And no error is raised

  Scenario: A very long query is handled without error
    Given a query string of 1000 characters
    When the embedding generator processes the query
    Then the embedding is generated without error
    And the retrieval engine returns results normally

  Scenario: Duplicate documents do not skew retrieval results
    Given the same document "landmark_case.pdf" has been ingested twice
    When a query semantically matching that document is searched
    Then the retrieval engine returns results from both copies
    And the pipeline deduplicates results by document_id before building context
