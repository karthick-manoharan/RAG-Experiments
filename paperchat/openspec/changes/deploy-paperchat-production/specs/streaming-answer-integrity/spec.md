# Spec Delta

## Purpose

Ensure deployed chat success represents an actual streamed answer while retaining the established SSE contract, source references, and cancellation lifecycle.

## ADDED Requirements

### Requirement: Answer text required for model success
A model stream producing no non-whitespace answer text SHALL terminate with a safe SSE error and no done. Non-answer chunks SHALL NOT establish success. Text deltas SHALL continue streaming as received without buffering the complete answer.

#### Scenario: Empty provider response
- **WHEN** retrieval finds sources but the provider yields no text, only metadata, or whitespace-only text
- **THEN** sources arrives first and a terminal safe error reports an empty answer without done

#### Scenario: Incremental valid answer
- **WHEN** the model yields multiple answer text deltas
- **THEN** sources precedes ordered incremental token events and exactly one done terminates successful generation

### Requirement: Compatible errors and cleanup
The sources, token, done, and error JSON payloads and framing SHALL remain compatible. Provider failure or timeout SHALL end with safe error and no done; disconnect SHALL cancel generation and close owned resources. Empty retrieval SHALL retain its deterministic insufficient-context answer.

#### Scenario: Provider fails after partial text
- **WHEN** an upstream exception occurs after sources or tokens
- **THEN** the client receives a safe terminal error, keeps partial text incomplete, and receives no raw provider exception

#### Scenario: Client cancels
- **WHEN** the browser aborts a pending stream
- **THEN** the server stops awaiting generation and closes request-owned clients and iterators

#### Scenario: No passages
- **WHEN** retrieval returns no passages
- **THEN** empty sources, the existing fallback token, and done are returned without invoking generation
