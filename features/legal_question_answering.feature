# Feature: Legal Question Answering
# Covers the end-to-end conversational RAG flow from user query to grounded legal response.

Feature: Legal Question Answering
  As a legal professional or researcher
  I want to ask natural language questions about legal cases
  So that I receive accurate, cited, document-grounded answers

  Background:
    Given the vector store is initialised and contains ingested legal documents
    And the Gemini LLM service is available
    And a valid session ID exists

  # ---------------------------------------------------------------------------
  # Happy path — basic question answering
  # ---------------------------------------------------------------------------

  Scenario: User asks a direct legal question and receives a grounded answer
    Given the user has the query "What is the standard of proof in criminal cases?"
    When the user submits the query to the chat endpoint
    Then the system returns HTTP 200
    And the response contains a non-empty "answer" field
    And the response contains at least 1 source document citation
    And each source citation includes "filename" and "chunk_text"
    And the answer does not contain fabricated case names not present in the sources

  Scenario: User asks a question and the answer is grounded only in retrieved documents
    Given the vector store contains a document about "reasonable doubt standard"
    And the user submits the query "Explain the beyond reasonable doubt standard"
    When the RAG pipeline processes the query
    Then the retrieval engine returns chunks from the "reasonable doubt" document
    And the context builder includes those chunks in the LLM prompt
    And the LLM response references the retrieved content

  Scenario: User asks a follow-up question in the same session
    Given the user has previously asked "What is promissory estoppel?"
    And the system responded with an explanation citing document "contract_law_cases.pdf"
    When the user asks "Can you give me a case example of that?"
    Then the conversation manager includes the prior turn in the prompt context
    And the system returns an answer relevant to promissory estoppel
    And the session conversation turn count increments by 1

  # ---------------------------------------------------------------------------
  # Multi-turn conversation
  # ---------------------------------------------------------------------------

  Scenario: Conversation history is maintained across multiple turns
    Given a session with 3 prior conversation turns
    When the user submits a 4th query referencing the earlier discussion
    Then the LLM prompt contains the last 3 turns of conversation history
    And the response is contextually coherent with the prior turns

  Scenario: Conversation history is truncated when it exceeds the maximum turn limit
    Given a session with 52 prior conversation turns
    When the user submits a new query
    Then the conversation manager truncates history to the last 10 turns
    And the system still returns a valid response

  Scenario: Clearing a session removes all conversation history
    Given a session with 5 prior conversation turns
    When the user sends DELETE to "/api/v1/chat/session/{session_id}"
    Then the system returns HTTP 200
    And subsequent queries on the same session_id start with empty history

  # ---------------------------------------------------------------------------
  # Insufficient context handling
  # ---------------------------------------------------------------------------

  Scenario: User asks a question with no relevant documents in the vector store
    Given the vector store contains only documents about contract law
    And the user submits the query "What are the immigration rules for asylum seekers?"
    When the RAG pipeline processes the query
    Then the retrieval engine returns chunks with relevance scores below the threshold
    And the system responds with a message indicating insufficient document coverage
    And the response does not fabricate an answer from ungrounded knowledge

  Scenario: Retrieved documents have low relevance scores
    Given the retrieval engine returns 3 chunks all with similarity score below 0.3
    When the context builder evaluates the retrieved chunks
    Then the context builder flags the low confidence
    And the LLM prompt includes a low-confidence instruction
    And the response informs the user that the answer may not be fully supported

  # ---------------------------------------------------------------------------
  # Input validation
  # ---------------------------------------------------------------------------

  Scenario: User submits an empty query
    Given the user sends a POST to "/api/v1/chat" with an empty "query" field
    When the API validates the request
    Then the system returns HTTP 422
    And the response contains a validation error message for the "query" field

  Scenario: User submits a query exceeding the maximum character limit
    Given the user sends a query of 2001 characters
    When the API validates the request
    Then the system returns HTTP 422
    And the response error message references the query length constraint

  Scenario: User submits a request with a missing session_id
    Given the user sends a POST to "/api/v1/chat" without a "session_id" field
    When the API validates the request
    Then the system returns HTTP 422

  Scenario: User submits a top_k value exceeding the maximum
    Given the user sends a POST with "top_k" set to 25
    When the API validates the request
    Then the system returns HTTP 422
    And the response error message indicates top_k must be between 1 and 20
