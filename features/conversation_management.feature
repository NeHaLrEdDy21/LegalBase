# Feature: Conversation Session Management
# Covers session lifecycle, history storage, truncation, and isolation.

Feature: Conversation Session Management
  As a user
  I want my conversation history to be maintained within a session
  So that follow-up questions are answered coherently

  Background:
    Given the conversation manager is initialised

  # ---------------------------------------------------------------------------
  # Session creation and retrieval
  # ---------------------------------------------------------------------------

  Scenario: A new session is created on first query
    Given no session exists for session_id "session-abc-123"
    When a query is submitted with session_id "session-abc-123"
    Then the conversation manager creates a new session
    And the session contains exactly 1 turn after the query completes

  Scenario: An existing session accumulates turns correctly
    Given a session "session-xyz" with 2 existing turns
    When a new query is submitted on "session-xyz"
    Then the session contains 3 turns
    And the new turn is appended at the end

  Scenario: Each turn stores both user query and assistant response
    Given a completed query-response exchange on "session-001"
    When the session history for "session-001" is inspected
    Then the latest turn contains "role: user" with the submitted query
    And the latest turn contains "role: assistant" with the response answer

  # ---------------------------------------------------------------------------
  # History truncation
  # ---------------------------------------------------------------------------

  Scenario: Session history is truncated to the last 10 turns for prompt construction
    Given a session with 15 stored turns
    When the conversation manager prepares history for the LLM prompt
    Then only the last 10 turns are included in the prompt context
    And all 15 turns remain stored in the session (no deletion)

  # ---------------------------------------------------------------------------
  # Session expiry
  # ---------------------------------------------------------------------------

  Scenario: An inactive session expires after the configured TTL
    Given a session "session-old" last active 3601 seconds ago
    And SESSION_TTL_SECONDS is configured to 3600
    When the conversation manager checks the session
    Then the session is considered expired
    And a subsequent query on "session-old" starts a fresh session

  # ---------------------------------------------------------------------------
  # Session isolation
  # ---------------------------------------------------------------------------

  Scenario: Two concurrent sessions do not share history
    Given session "session-A" has asked about "contract law"
    And session "session-B" has asked about "criminal procedure"
    When session "session-A" submits a follow-up question
    Then the prompt context for "session-A" contains only "session-A" history
    And no content from "session-B" is present in the prompt

  # ---------------------------------------------------------------------------
  # Session deletion
  # ---------------------------------------------------------------------------

  Scenario: Deleting a session clears all its history
    Given session "session-del" has 7 turns
    When DELETE is sent to "/api/v1/chat/session/session-del"
    Then the session "session-del" is removed from the store
    And the next query on "session-del" starts with 0 turns

  Scenario: Deleting a non-existent session returns 404
    Given no session exists for "session-ghost"
    When DELETE is sent to "/api/v1/chat/session/session-ghost"
    Then the system returns HTTP 404
