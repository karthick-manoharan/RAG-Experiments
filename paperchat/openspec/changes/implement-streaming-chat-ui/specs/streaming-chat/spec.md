# Spec Delta

## Purpose

Enable readers to ask independent questions about “Attention Is All You Need” in a responsive browser interface, follow answers as they arrive, and inspect retrieved source references.

## ADDED Requirements

### Requirement: Responsive accessible chat interface
The interface SHALL display the paper title, short description, example questions, message history, labelled composer, and send control in a usable mobile and desktop layout with semantic HTML and keyboard access.

#### Scenario: Empty session
- **WHEN** a reader opens the page without messages
- **THEN** the title, description, and useful example questions are visible and an example can populate the composer

#### Scenario: Keyboard composition
- **WHEN** a reader uses Enter in the composer outside IME composition
- **THEN** a valid question is submitted, while Shift+Enter inserts a newline and IME composition does not submit

#### Scenario: Focus and accessibility
- **WHEN** a request completes, fails, or is cancelled
- **THEN** the composer remains keyboard accessible, status changes are announced accessibly, and streaming updates do not steal focus

### Requirement: Independent question submission
The browser SHALL POST JSON containing only the current question to `/api/v1/chat/stream`, retain exchanges in session-local UI state, reject blank or over-4000-character input before trimming, and prevent concurrent submissions.

#### Scenario: Multiple exchanges
- **WHEN** a reader asks a second question after the first request ends
- **THEN** both exchanges remain visible and the second request contains no earlier messages

#### Scenario: Active or invalid submission
- **WHEN** a request is active or the proposed input is blank or longer than 4000 characters
- **THEN** no additional request is sent and the UI conveys the relevant active or validation state

### Requirement: Compatible incremental stream consumption
The client SHALL consume the existing sources, token, done, and error JSON SSE events correctly across arbitrary byte boundaries, and display each token without waiting for completion. Only done SHALL establish successful completion.

#### Scenario: Split and coalesced events
- **WHEN** network chunks split UTF-8 characters, field lines, or frame delimiters, or contain multiple frames
- **THEN** complete events are processed exactly once in order and token text is appended without corruption

#### Scenario: Request lifecycle
- **WHEN** submission begins, answer text arrives, and done arrives
- **THEN** the assistant progresses through loading, generating, and completed states

#### Scenario: Broken response
- **WHEN** a recognized event contains invalid JSON or payload shape, or the response ends before done or error
- **THEN** the exchange becomes failed with a useful message and any partial answer remains visibly incomplete

### Requirement: Actual source references
The interface SHALL display compact references beneath the associated assistant response using the sources event's actual id, source, page, and snippet metadata. It SHALL preserve null provenance and SHALL NOT fabricate citations, page numbers, or document URLs.

#### Scenario: Known and missing provenance
- **WHEN** sources include a one-based page and filename for one record and null provenance for another
- **THEN** the known values are shown unchanged and the other record uses its supplied ID or an unknown-source label without a guessed page

#### Scenario: No retrieved sources
- **WHEN** sources is an empty array
- **THEN** no invented source references accompany the streamed answer

### Requirement: Cancellation and failure recovery
Readers SHALL be able to cancel an active request, see failed requests without losing history, and retry the original failed question. Cancelled and failed partial answers SHALL remain distinguishable from completed answers.

#### Scenario: Cancellation during loading or generation
- **WHEN** a reader cancels while awaiting headers or consuming tokens
- **THEN** the active request is aborted, the exchange becomes cancelled, late updates are ignored, and a new question can be submitted

#### Scenario: HTTP or SSE failure
- **WHEN** a request returns an HTTP error, network failure, or terminal SSE error
- **THEN** a user-friendly error appears, the exchange becomes failed, and retry resubmits only that exchange's original question

#### Scenario: Cancellation after a terminal result
- **WHEN** completion or failure has already been accepted
- **THEN** a late cancellation does not overwrite that terminal result

### Requirement: Scroll-aware streaming
The interface SHALL follow new answer content while the reader is near the bottom and SHALL stop automatic following when the reader scrolls upward.

#### Scenario: Reading previous messages
- **WHEN** the reader scrolls upward during generation
- **THEN** arriving tokens do not move the reader away from previous messages and returning to the bottom resumes following

### Requirement: Public endpoint configuration and restricted cross-origin access
The frontend SHALL use NEXT_PUBLIC_API_BASE_URL with a default of http://localhost:8000. The backend SHALL permit the local frontend origin http://localhost:3000 for chat POST requests, including preflight and error responses, without allowing arbitrary origins. Browser configuration SHALL contain no service credentials.

#### Scenario: Default local connection
- **WHEN** the local frontend submits a question with no public base URL configured
- **THEN** the request targets http://localhost:8000/api/v1/chat/stream and CORS permits the local origin

#### Scenario: Disallowed origin
- **WHEN** an unrelated origin attempts cross-origin access
- **THEN** the backend does not grant that origin cross-origin permission

#### Scenario: Configured API
- **WHEN** NEXT_PUBLIC_API_BASE_URL identifies another API location
- **THEN** the client uses that base URL without requiring provider credentials or a frontend API proxy
