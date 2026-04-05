# Feature: Chatbot UI Behaviour
# Covers the React frontend chat interface from a user perspective.

Feature: Chatbot UI — Message Submission and Display
  As a user
  I want to interact with a chat interface
  So that I can ask legal questions and read grounded responses

  Scenario: User types a message and submits with the Enter key
    Given the chat input bar is focused and empty
    When the user types "What is habeas corpus?" and presses Enter
    Then the user message appears immediately in the message list
    And a typing indicator is displayed
    And the input bar is cleared and disabled during the request

  Scenario: User submits a message with the Send button
    Given the user has typed "Explain res judicata" in the input bar
    When the user clicks the Send button
    Then the message is submitted to the API
    And the user message appears in the message list

  Scenario: Shift+Enter inserts a newline instead of submitting
    Given the input bar contains "First line"
    When the user presses Shift+Enter
    Then a newline is inserted into the input
    And no API request is made

  Scenario: Assistant response appears after the typing indicator
    Given a user message has been submitted
    When the API returns a response
    Then the typing indicator disappears
    And the assistant message bubble appears in the message list
    And the message is left-aligned with the assistant avatar

  Scenario: Source citations are displayed below the assistant response
    Given the API response includes 3 source citations
    When the assistant message is rendered
    Then a collapsible sources section appears below the message
    And expanding it shows 3 citation entries with filename and excerpt

  Scenario: User messages are right-aligned and assistant messages are left-aligned
    Given the chat contains a user message followed by an assistant message
    Then the user message bubble is right-aligned
    And the assistant message bubble is left-aligned

  Scenario: Message list auto-scrolls to the latest message
    Given the message list contains 20 messages requiring scroll
    When a new message is added
    Then the view automatically scrolls to the bottom

# ---------------------------------------------------------------------------

Feature: Chatbot UI — Error Handling
  As a user
  I want to see clear error messages when something goes wrong
  So that I understand what happened and can retry

  Scenario: API returns a 500 error — user sees an inline error message
    Given the API returns HTTP 500 for a chat request
    When the response is received by the frontend
    Then the typing indicator disappears
    And an error message is displayed in the chat
    And a Retry button is shown

  Scenario: API returns a 429 rate limit error — user sees a rate limit message
    Given the API returns HTTP 429
    When the response is received by the frontend
    Then the error message informs the user they have sent too many requests
    And the input bar remains disabled for the retry-after duration

  Scenario: Network request fails (offline) — user sees a connectivity error
    Given the user's network connection is unavailable
    When the user submits a message
    Then the frontend displays a network connectivity error
    And the unsent message remains in the input bar

  Scenario: Empty input submission is prevented
    Given the input bar contains only whitespace
    When the user presses Enter or clicks Send
    Then no API request is made
    And the input bar shows a validation hint

# ---------------------------------------------------------------------------

Feature: Chatbot UI — Session Behaviour
  As a user
  I want my session to persist within a browser tab
  So that my conversation context is maintained during my session

  Scenario: Session ID is generated on first page load
    Given the user opens the chatbot for the first time
    When the page loads
    Then a new UUID session_id is generated
    And it is stored in sessionStorage

  Scenario: Session ID persists across messages within the same tab
    Given a session_id "sess-001" is stored in sessionStorage
    When the user sends 3 messages
    Then all 3 API requests include session_id "sess-001"

  Scenario: Refreshing the page starts a new session
    Given a session_id "sess-001" is stored in sessionStorage
    When the user refreshes the browser tab
    Then sessionStorage is cleared
    And a new session_id is generated on next page load

  Scenario: New browser tab starts an independent session
    Given session "sess-tab-1" is active in tab 1
    When the user opens a new browser tab with the chatbot
    Then a new independent session_id is generated for tab 2
    And the two tabs do not share conversation history
