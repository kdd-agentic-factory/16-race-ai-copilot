# Specification: Initial Implementation - 16 Race AI Copilot

## Executive Summary
This specification defines the initial implementation of the AI Copilot, transitioning from a mock-based prototype to a production-ready local agentic system. The architecture centers on a FastAPI backend integrating Ollama for reasoning, a RAG/CAG pipeline for grounding, and a "Crew Chief" governance layer to ensure safety in critical race operations. It introduces five specialized domains (Chat, Orchestration, Knowledge, Governance, and Assistants) to handle everything from tire degradation analysis to circuit-specific parts design, all while maintaining a strict local-first execution policy.

---

## 1. Chat Interface & LLM Integration

### Purpose
Enable real-time, streaming chat interactions between the user and a local LLM (Ollama).

### Requirements

#### Requirement: Ollama Integration
The system MUST integrate with Ollama via its API for local LLM execution.

#### Scenario: Basic Chat
- GIVEN a user query
- WHEN sent to the backend
- THEN the system returns a streamed response from Ollama

#### Requirement: Streaming Responses
The system SHALL support streaming responses to reduce perceived latency.

#### Scenario: Real-time Feedback
- GIVEN a long-form response generation
- WHEN the response starts
- THEN the user sees tokens appearing in real-time rather than waiting for the full block

#### Requirement: Session Context
The system MUST maintain session history for contextual follow-up questions.

#### Scenario: Contextual Follow-up
- GIVEN a previous conversation about "tire pressure"
- WHEN the user asks "what about the rear ones?"
- THEN the system understands "tire pressure" is the implicit topic

---

## 2. Orchestration & Planning

### Purpose
Determine user intent and plan the necessary tool calls to fulfill requests.

### Requirements

#### Requirement: Intent Classification
The system MUST classify the user intent (e.g., Telemetry, Setup, Parts) before executing actions.

#### Scenario: Intent Detection
- GIVEN "Show me the tire temps"
- WHEN processed by the orchestrator
- THEN the system classifies intent as `Telemetry`

#### Requirement: Tool Planning
The system SHALL generate a tool-execution plan based on the classified intent.

#### Scenario: Plan Generation
- GIVEN a `Telemetry` intent
- WHEN planning the response
- THEN the system plans a call to the Telemetry service with the specific sensor parameters

#### Requirement: Error Handling & Re-planning
The system MUST handle tool failures by attempting a re-plan or notifying the user.

#### Scenario: Tool Failure Recovery
- GIVEN a failed API call to a telemetry sensor
- WHEN the error is caught
- THEN the system attempts to retrieve cached data or informs the user of the sensor failure

---

## 3. Knowledge & Grounding (RAG/CAG)

### Purpose
Ensure AI responses are grounded in race-specific data and documentation to prevent hallucinations.

### Requirements

#### Requirement: Context Retrieval
The system MUST retrieve relevant context from the vector store (RAG) or cache (CAG) before generating a response.

#### Scenario: Evidence-based Query
- GIVEN a query about "Circuit X's optimal wing angle"
- WHEN processed
- THEN the system retrieves the Circuit X spec and incorporates it into the answer

#### Requirement: Source Attribution
The system SHALL cite the source of the evidence used in the response.

#### Scenario: Citation Display
- GIVEN a grounded response
- WHEN presented to the user
- THEN the system includes a reference to the specific technical document used

#### Requirement: Hallucination Control
The system MUST flag responses that cannot be grounded in existing evidence.

#### Scenario: Ungrounded Response
- GIVEN a query about a non-existent car part
- WHEN the system finds no evidence
- THEN the system responds "I cannot find evidence for this part in the documentation"

---

## 4. Governance & Control (Crew Chief)

### Purpose
Prevent unauthorized or dangerous changes to car setup/strategy via a human-in-the-loop approval process.

### Requirements

#### Requirement: Critical Action Interception
The system MUST intercept "critical" actions (e.g., changing suspension settings) and route them to the Crew Chief for approval.

#### Scenario: Critical Action Trigger
- GIVEN a request to "Increase front wing by 2 degrees"
- WHEN processed
- THEN the system marks the action as `PENDING_APPROVAL`

#### Requirement: Approval UI State
The system SHALL display a clear "Approval Pending" state in the UI.

#### Scenario: User Notification
- GIVEN a pending action
- WHEN the Crew Chief opens the dashboard
- THEN they see a highlighted request for approval with the proposed change

#### Requirement: Execution Guardrail
The system MUST only execute the action after a positive approval signal from the authorized user.

#### Scenario: Approved Execution
- GIVEN a `PENDING_APPROVAL` action
- WHEN the Crew Chief clicks "Approve"
- THEN the system executes the setup change in the simulation/car

---

## 5. Specialized Assistants

### Purpose
Provide domain-specific capabilities for Telemetry, Setup, Parts, and Simulation.

### Requirements

#### Requirement: Telemetry Analysis
The Telemetry Assistant MUST be able to query and summarize real-time sensor data.

#### Scenario: Tire Degradation Query
- GIVEN a request for "tire wear trend"
- WHEN processed
- THEN the system analyzes telemetry and returns the degradation rate per lap

#### Requirement: Setup Optimization
The Setup Assistant SHALL suggest setup changes based on driver feedback and telemetry.

#### Scenario: Setup Change Request
- GIVEN "car is understeering in turn 4"
- WHEN processed
- THEN the system suggests a specific front spring change and routes it for approval

#### Requirement: Parts Specification
The Parts Assistant MUST provide specifications and compatibility for car components.

#### Scenario: Circuit Specific Parts
- GIVEN "best brake duct for Monaco"
- WHEN processed
- THEN the system retrieves the Monaco-specific brake part specs

#### Requirement: Simulation Interface
The Simulation Assistant SHALL trigger and interpret results from race simulations.

#### Scenario: Sim Run Analysis
- GIVEN a request to "sim lap 5 with current fuel"
- WHEN processed
- THEN the system triggers the sim and returns the predicted lap time

---

## Non-Functional Requirements

| ID | Requirement | Strength | Target |
|----|-------------|-----------|--------|
| NFR-1 | Local-first Execution | MUST | 100% local LLM/Data processing |
| NFR-2 | Streaming Latency | SHOULD | First token < 500ms |
| NFR-3 | Groundedness Score | MUST | > 0.8 for factual claims |
| NFR-4 | Availability | SHOULD | 99.9% during race weekend |
