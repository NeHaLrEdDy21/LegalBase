# Feature: Legal Document Ingestion
# Covers uploading, parsing, chunking, embedding, and storing legal case documents.

Feature: Legal Document Ingestion
  As a system administrator or legal data curator
  I want to upload legal case documents into the system
  So that the chatbot can retrieve and reason over them

  Background:
    Given the vector store is initialised and empty
    And the embedding service is available

  # ---------------------------------------------------------------------------
  # Happy path — successful ingestion
  # ---------------------------------------------------------------------------

  Scenario: Successfully ingesting a PDF legal document
    Given a valid PDF file "case_law_tort.pdf" of size 2MB
    When the user uploads the file to "POST /api/v1/documents/ingest"
    Then the system returns HTTP 200
    And the response contains "ingested_count" equal to 1
    And the response contains a non-empty "document_ids" list
    And the document appears in "GET /api/v1/documents"
    And the vector store index contains embeddings for the document's chunks

  Scenario: Successfully ingesting a plain text legal document
    Given a valid TXT file "statute_2024.txt" of size 500KB
    When the user uploads the file to "POST /api/v1/documents/ingest"
    Then the system returns HTTP 200
    And the response "ingested_count" is 1
    And the document is retrievable via semantic search

  Scenario: Successfully ingesting multiple documents in one request
    Given 3 valid PDF files: "case_a.pdf", "case_b.pdf", "case_c.pdf"
    When the user uploads all 3 files in a single multipart request
    Then the system returns HTTP 200
    And "ingested_count" equals 3
    And all 3 document IDs appear in the response

  Scenario: Document is split into correct number of chunks
    Given a TXT file containing exactly 5000 words
    When the document is ingested
    Then the text chunker produces chunks of at most 512 tokens each
    And consecutive chunks overlap by approximately 64 tokens
    And all chunks together cover the full document text without gaps

  Scenario: Each chunk receives an embedding vector
    Given a document that produces 10 chunks after splitting
    When the embedding generator processes all chunks
    Then each chunk is assigned exactly one embedding vector
    And all embedding vectors have dimension 384
    And no embedding vector is the zero vector

  Scenario: Document metadata is stored with each chunk
    Given a PDF file "supreme_court_2023.pdf" uploaded with metadata '{"year": 2023, "court": "Supreme Court"}'
    When the document is ingested
    Then each chunk's stored metadata includes "filename", "document_id", "chunk_index", and "ingested_at"

  # ---------------------------------------------------------------------------
  # Partial failure handling
  # ---------------------------------------------------------------------------

  Scenario: One file fails in a multi-file upload batch
    Given 3 files where "valid_1.pdf" and "valid_2.pdf" are valid and "corrupt.pdf" is corrupted
    When the user uploads all 3 files
    Then the system returns HTTP 200
    And "ingested_count" equals 2
    And "failed_count" equals 1
    And the "errors" list contains an error message referencing "corrupt.pdf"

  # ---------------------------------------------------------------------------
  # Document deletion
  # ---------------------------------------------------------------------------

  Scenario: Successfully deleting an ingested document
    Given a document with id "doc-123" exists in the vector store
    When the user sends DELETE to "/api/v1/documents/doc-123"
    Then the system returns HTTP 200
    And the document "doc-123" no longer appears in "GET /api/v1/documents"
    And no chunks from "doc-123" appear in subsequent similarity searches

  Scenario: Deleting a non-existent document returns 404
    Given no document with id "doc-999" exists in the vector store
    When the user sends DELETE to "/api/v1/documents/doc-999"
    Then the system returns HTTP 404

  # ---------------------------------------------------------------------------
  # Input validation and security
  # ---------------------------------------------------------------------------

  Scenario: Uploading an unsupported file type is rejected
    Given a file "spreadsheet.xlsx" of type application/vnd.ms-excel
    When the user uploads the file to the ingest endpoint
    Then the system returns HTTP 400
    And the response error message states the file type is not supported

  Scenario: Uploading a file exceeding the size limit is rejected
    Given a PDF file of size 60MB
    When the user uploads the file to the ingest endpoint
    Then the system returns HTTP 413
    And the response error message references the maximum upload size

  Scenario: Uploading a file with no content is rejected
    Given an empty file "empty.txt" with 0 bytes
    When the user uploads the file to the ingest endpoint
    Then the system returns HTTP 400
    And the response error indicates the file contains no extractable text

  Scenario: Uploading a file with a path traversal filename is rejected
    Given a file with name "../../etc/passwd"
    When the user uploads the file to the ingest endpoint
    Then the system returns HTTP 400
    And the filename is sanitised or rejected
