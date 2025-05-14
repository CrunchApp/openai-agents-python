# System Patterns: Autonomous X Agentic Unit

## 1. Core Architectural Pattern: Modular Multi-Agent System

*   **Description**: The X Agentic Unit employs a multi-agent architecture orchestrated by a central `OrchestratorAgent`. Specialized agents, each with distinct responsibilities and a limited set of tools, handle specific functions (e.g., `ContentCreationAgent`, `XInteractionAgent`, `ComputerUseAgent`, `AnalysisAgent`, `ProfileManagementAgent`, `SchedulingAgent`).
*   **Rationale**: This promotes modularity, separation of concerns, easier development and testing of individual components, and aligns with the OpenAI Agents SDK's design principles. It allows for specialized LLM prompting and toolsets per agent, enhancing efficiency and maintainability.
*   **Interaction**:
    *   The `OrchestratorAgent` breaks down high-level goals into sub-tasks and delegates them to specialized agents.
    *   Delegation primarily occurs via the OpenAI Agents SDK's `handoff` mechanism for transferring control.
    *   Alternatively, an agent can invoke another specialized agent as a `tool` if it needs a specific capability while retaining overall control of its current task.
*   **Data Flow**: High-level goals or scheduled triggers initiate workflows in the `OrchestratorAgent`. Data (e.g., content drafts, analysis results, X API responses) flows between agents as part of task delegation or handoff payloads.

## 2. Hybrid Autonomy and Human-in-the-Loop (HIL)

*   **Pattern**: Most agent tasks operate autonomously. However, predefined triggers invoke a Human-in-the-Loop (HIL) process for critical decisions, content approval, or ambiguity resolution.
*   **Mechanism**:
    1.  An agent (typically the `OrchestratorAgent` or an agent about to perform a sensitive action) identifies a HIL trigger condition.
    2.  The task is paused.
    3.  Relevant data is logged to a `human_review_queue` table in the SQLite database, flagged for human attention.
    4.  The agent awaits explicit human input (e.g., 'approved', 'rejected', 'modified' status update in the database) before proceeding or aborting the task.
    5.  A `HumanHandoffTool` or a specific state within the `OrchestratorAgent` manages this process.
*   **Rationale**: Balances automation benefits with essential human oversight, mitigating risks of undesirable autonomous actions.

## 3. X Interaction Strategy: API-First with Strategic GUI/CUA Fallback/Alternative

*   **Pattern**:
    1.  **API-First**: For X platform interactions, the system will first attempt to use the official X API v2 via tools in `tools/x_api_tools.py`. This is preferred for reliability and structured data access.
    2.  **CUA/GUI for Gaps & Cost Optimization**: For functionalities not well-supported by the available X API tier, actions with prohibitive API costs, or tasks requiring direct UI manipulation (e.g., some profile image updates), the system will utilize the `ComputerUseAgent`. This agent, in turn, uses OpenAI's "Computer Use" tool or custom Playwright scripts.
*   **Decision Logic**: The `OrchestratorAgent` will be primarily responsible for deciding which interaction method to use based on the nature of the task, pre-defined rules (e.g., "always use CUA for profile banner updates"), and potentially dynamic factors like observed API rate limit pressure (future enhancement).
*   **Rationale**: This hybrid approach aims for the robustness of API interactions where feasible, while providing flexibility and cost-control through CUA/GUI automation for specific use cases. It acknowledges the evolving and potentially restrictive nature of X API access.

## 4. Tool Implementation and Usage

*   **Pattern**: Agent capabilities are exposed as `Tools` within the OpenAI Agents SDK.
    *   Tools are Python functions, typically located in the `tools/` directory (e.g., `x_api_tools.py`, `computer_control_tools.py`, `analysis_tools.py`).
    *   Tools **MUST** have clear function signatures with type hints and comprehensive docstrings. The SDK uses these for automatic schema generation and to help the LLM understand how to use the tool.
    *   Tool arguments **SHOULD** be validated, ideally using Pydantic models if the tool input is complex, to ensure robustness.
*   **Invocation**: Agents invoke tools based on their instructions and the current task. The SDK handles the tool call, result processing, and iteration.
*   **Error Handling within Tools**: Tools are responsible for handling their own specific errors (e.g., X API errors, CUA execution failures). They should catch exceptions, log them appropriately, and return a structured error response or raise a custom, catchable exception that the calling agent can understand and handle. Avoid letting raw exceptions from underlying libraries (like Tweepy or Playwright) propagate unhandled out of a tool.

## 5. Persistent State Management

*   **Pattern**: Agent state that needs to persist across runs or between tasks (e.g., last processed mention ID, OAuth tokens, ongoing task status) is stored in the SQLite database (`data/agent_data.db`).
*   **Access**: All database interactions are encapsulated within the `core/db_manager.py` module. Agents **DO NOT** interact with the database directly but call functions provided by `db_manager.py`.
*   **Schema**: The database schema is defined and managed as described in `DB Rules` (and will be in `.cursor/rules/db.mdc`). Key tables include `agent_state`, `task_queue`, `x_oauth_tokens`, `human_review_queue`.
*   **Rationale**: Ensures data integrity, enables recovery from interruptions, and supports long-running, continuous agent operation.

## 6. Task Scheduling and Continuous Operation

*   **Pattern**: The `SchedulingAgent`, using `APScheduler`, manages all scheduled tasks.
*   **Mechanism**:
    *   `core/scheduler_setup.py` initializes APScheduler and defines job configurations (interval, cron, date-based).
    *   Scheduled jobs typically trigger methods on the `OrchestratorAgent` to initiate specific workflows (e.g., "check for new mentions," "post scheduled content").
*   **Persistence**: APScheduler jobs can be configured to persist (e.g., using an SQLAlchemyJobStore with the SQLite DB) to survive application restarts, though simpler in-memory scheduling is the default for initial phases.
*   **Rationale**: Enables continuous, autonomous operation and proactive task execution without constant manual triggering.

## 7. Configuration Management

*   **Pattern**: Application configuration, especially sensitive data like API keys, is managed via environment variables.
*   **Loading**:
    *   For local development, a `.env` file (in `.gitignore`) is loaded by `core/config.py` using `python-dotenv`.
    *   In deployed environments, environment variables are injected directly.
*   **Access**: Agents and modules access configuration values through functions or attributes provided by `core/config.py`. No hardcoded configuration values in agent logic.
*   **Rationale**: Promotes security and flexibility across different deployment environments.

## 8. Security Patterns for CUA

*   **Sandboxed Execution**: CUA browser actions executed via Playwright **SHOULD** run within a controlled browser context, potentially sandboxed (e.g., within a Docker container with limited permissions).
*   **Validated Inputs**: Prompts and parameters passed to the CUA model or Playwright scripts for execution **MUST** be validated or sanitized, especially if derived from external inputs, to prevent injection-style attacks.
*   **Restricted Capabilities**: The `ComputerUseAgent` and its tools will operate under the principle of least privilege. Actions like file system access or command execution will be restricted to designated safe directories or use wrappers that enforce strict policies.
*   **Guardrails**: Specific input/output guardrails (defined in the Agents SDK) will be applied to CUA operations to prevent unintended or malicious actions.
*   **Rationale**: Mitigates the inherent risks associated with an agent performing direct computer/UI interactions.

## 9. Error Handling and Retry Idioms

*   **External Calls**: All external calls (X API, OpenAI API, CUA actions) **MUST** be wrapped in `try-except` blocks.
*   **Specific Exceptions**: Catch specific exceptions rather than generic `Exception`. Define custom project exceptions where appropriate (e.g., in `core/exceptions.py`) for better error discrimination.
*   **Retry Logic**: For transient errors (e.g., network issues, temporary API unavailability), implement a retry mechanism with exponential backoff and a maximum number of retries. A utility function for this (e.g., in `core/utils.py`) should be used consistently.
*   **Logging**: All significant errors, including retry attempts, **MUST** be logged comprehensively with contextual information.
*   **Fallback/HIL Escalation**: If errors persist after retries, the system should define fallback behaviors: pausing the workflow, deferring the task, or escalating to HIL.
*   **Rationale**: Enhances system robustness and resilience to common operational issues.