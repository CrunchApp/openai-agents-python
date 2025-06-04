# System Patterns: Autonomous X Agentic Unit

## 1. Core Architectural Pattern: Modular Multi-Agent System

*   **Description**: The X Agentic Unit employs a multi-agent architecture orchestrated by a central `OrchestratorAgent`. Specialized agents, each with distinct responsibilities and a limited set of tools, handle specific functions (e.g., `ContentCreationAgent`, `XInteractionAgent`, `ComputerUseAgent`, `AnalysisAgent`, `ProfileManagementAgent`, `SchedulingAgent`).
*   **Implementation Status**: **✅ COMPLETE** - All agents implemented in `project_agents/`:
    *   `orchestrator_agent.py` (7.1KB) - Central coordination and task delegation
    *   `computer_use_agent.py` (1.5KB) - Primary CUA for browser automation
    *   `content_creation_agent.py` (3.0KB) - Content generation and curation  
    *   `x_interaction_agent.py` (1.3KB) - X platform interaction coordination
    *   `scheduling_agent.py` (3.5KB) - Task scheduling and continuous operation
*   **Rationale**: This promotes modularity, separation of concerns, easier development and testing of individual components, and aligns with the OpenAI Agents SDK's design principles. It allows for specialized LLM prompting and toolsets per agent, enhancing efficiency and maintainability.
*   **Interaction**:
    *   The `OrchestratorAgent` breaks down high-level goals into sub-tasks and delegates them to specialized agents.
    *   Delegation primarily occurs via the OpenAI Agents SDK's `handoff` mechanism for transferring control (implemented in `src/agents/handoffs.py`).
    *   Alternatively, an agent can invoke another specialized agent as a `tool` if it needs a specific capability while retaining overall control of its current task.
    *   **CUA Integration**: The `ComputerUseAgent` operates as a specialized execution agent for browser-based X platform interactions, coordinated by the `OrchestratorAgent` and working alongside other agents.
*   **Data Flow**: High-level goals or scheduled triggers initiate workflows in the `OrchestratorAgent`. Data (e.g., content drafts, analysis results, X API responses, screenshots) flows between agents as part of task delegation or handoff payloads.

## 2. Hybrid Autonomy and Human-in-the-Loop (HIL)

*   **Pattern**: Most agent tasks operate autonomously. However, predefined triggers invoke a Human-in-the-Loop (HIL) process for critical decisions, content approval, or ambiguity resolution.
*   **Mechanism**:
    1.  An agent (typically the `OrchestratorAgent` or an agent about to perform a sensitive action) identifies a HIL trigger condition.
    2.  The task is paused.
    3.  Relevant data is logged to a `human_review_queue` table in the SQLite database, flagged for human attention.
    4.  The agent awaits explicit human input (e.g., 'approved', 'rejected', 'modified' status update in the database) before proceeding or aborting the task.
    5.  A `HumanHandoffTool` or a specific state within the `OrchestratorAgent` manages this process.
*   **CUA HIL Integration**: CUA operations can trigger HIL for screenshot verification, suspicious platform behavior detection, or before executing high-impact actions (e.g., posting controversial content).
*   **Rationale**: Balances automation benefits with essential human oversight, mitigating risks of undesirable autonomous actions, especially critical for browser automation where detection risks exist.

## 3. X Interaction Strategy: CUA-First with API Fallback/Complement

*   **Pattern**:
    1.  **CUA-First Approach**: For X platform interactions, the system will primarily utilize the `ComputerUseAgent` with `LocalPlaywrightComputer` for browser-based automation. This addresses X API cost concerns and provides full platform feature access.
    2.  **API Fallback/Complement**: X API v2 tools in `tools/x_api_tools.py` serve as fallback mechanisms when CUA operations fail, or as complementary tools for specific data retrieval tasks where API calls are more efficient.
    3.  **Hybrid Decision Logic**: The `OrchestratorAgent` determines interaction method based on:
        *   Task complexity and platform feature requirements
        *   Performance and reliability considerations 
        *   Cost optimization strategies
        *   Current browser session state and authentication status
*   **CUA Implementation Details**:
    *   **Browser Environment**: `LocalPlaywrightComputer` provides controlled browser automation with Playwright
    *   **Authentication Management**: CUA maintains browser session authentication, reducing API token usage
    *   **Screenshot Analysis**: CUA captures and analyzes page state to verify action success and inform next steps
    *   **Anti-Detection**: CUA employs human-like interaction patterns to comply with X platform policies
*   **Rationale**: This CUA-first approach maximizes feature access while minimizing API costs, providing sustainable long-term automation. API tools provide reliability fallback and specialized data access when needed.
    *   **Proven `requests` Usage**: Experience in Phase 1 demonstrated that direct `requests` calls, with explicitly constructed `Authorization: Bearer <token>` headers, were successful for user-context tweet posting where initial attempts with `tweepy.Client(bearer_token=...)` faced "Unsupported Authentication" issues. This establishes `requests` as a reliable fallback method for direct X API v2 calls when precise header control is needed.

## 4. Tool Implementation and Usage

*   **Pattern**: Agent capabilities are exposed as `Tools` within the OpenAI Agents SDK.
    *   Tools are Python functions, typically located in the `tools/` directory (e.g., `x_api_tools.py`, `computer_control_tools.py`, `analysis_tools.py`).
    *   **CUA Tools**: The `ComputerUseAgent` uses the OpenAI `ComputerTool` which interfaces with `AsyncComputer` implementations like `LocalPlaywrightComputer`.
    *   Tools **MUST** have clear function signatures with type hints and comprehensive docstrings. The SDK uses these for automatic schema generation and to help the LLM understand how to use the tool.
    *   Tool arguments **SHOULD** be validated, ideally using Pydantic models if the tool input is complex, to ensure robustness.
*   **Invocation**: Agents invoke tools based on their instructions and the current task. The SDK handles the tool call, result processing, and iteration.
*   **Error Handling within Tools**: Tools are responsible for handling their own specific errors (e.g., X API errors, CUA execution failures, browser navigation failures). They should catch exceptions, log them appropriately, and return a structured error response or raise a custom, catchable exception that the calling agent can understand and handle. Avoid letting raw exceptions from underlying libraries (like Tweepy or Playwright) propagate unhandled out of a tool.

## 5. Persistent State Management

*   **Pattern**: Agent state that needs to persist across runs or between tasks (e.g., last processed mention ID, OAuth tokens, ongoing task status, browser session data) is stored in the SQLite database (`data/agent_data.db`).
*   **Access**: All database interactions are encapsulated within the `core/db_manager.py` module. Agents **DO NOT** interact with the database directly but call functions provided by `db_manager.py`.
*   **Schema**: The database schema is defined and managed as described in `DB Rules` (and will be in `.cursor/rules/db.mdc`). Key tables include `agent_state`, `task_queue`, `x_oauth_tokens`, `human_review_queue`.
*   **CUA State Management**: Browser session state, authentication cookies, and CUA execution context are managed through the `AsyncComputer` context manager pattern and persistent browser profiles when needed.
*   **Rationale**: Ensures data integrity, enables recovery from interruptions, and supports long-running, continuous agent operation with both API and browser-based interactions.

## 6. Task Scheduling and Continuous Operation

*   **Pattern**: The `SchedulingAgent`, using `APScheduler`, manages all scheduled tasks.
*   **Mechanism**:
    *   `core/scheduler_setup.py` initializes APScheduler with persistent job storage using `SQLAlchemyJobStore`.
    *   Scheduled jobs typically trigger methods on the `OrchestratorAgent` to initiate specific workflows (e.g., "check for new mentions via CUA," "post scheduled content via CUA").
    *   **CUA Scheduling Considerations**: CUA operations require longer execution windows and browser session management across scheduled tasks.
*   **Persistence**: APScheduler jobs persist using `SQLAlchemyJobStore` with the SQLite database to survive application restarts and maintain scheduling integrity.
*   **Rationale**: Enables continuous, autonomous operation and proactive task execution without constant manual triggering, while accommodating the different timing requirements of CUA vs API operations.

## 7. Configuration Management

*   **Pattern**: Application configuration, especially sensitive data like API keys, is managed via environment variables.
*   **Loading**:
    *   For local development, a `.env` file (in `.gitignore`) is loaded by `core/config.py` using `python-dotenv`.
    *   In deployed environments, environment variables are injected directly.
*   **Access**: Agents and modules access configuration values through functions or attributes provided by `core/config.py`. No hardcoded configuration values in agent logic.
*   **CUA Configuration**: Browser automation settings (viewport size, user agent, automation flags) are configured through environment variables and the `LocalPlaywrightComputer` implementation.
*   **Rationale**: Promotes security and flexibility across different deployment environments, including containerized CUA execution environments.

## 8. Security Patterns for CUA

*   **Sandboxed Execution**: CUA browser actions executed via Playwright **SHOULD** run within a controlled browser context, potentially sandboxed (e.g., within a Docker container with limited permissions).
*   **Validated Inputs**: Prompts and parameters passed to the CUA model or Playwright scripts for execution **MUST** be validated or sanitized, especially if derived from external inputs, to prevent injection-style attacks.
*   **Restricted Capabilities**: The `ComputerUseAgent` and its tools will operate under the principle of least privilege. Actions like file system access or command execution will be restricted to designated safe directories or use wrappers that enforce strict policies.
*   **Guardrails**: Specific input/output guardrails (defined in the Agents SDK) will be applied to CUA operations to prevent unintended or malicious actions.
*   **Browser Security**: CUA uses browser automation in controlled environments with disabled JavaScript execution where appropriate, restricted file access, and isolated browsing profiles.
*   **Rationale**: Mitigates the inherent risks associated with an agent performing direct computer/UI interactions while maintaining operational effectiveness.

## 9. Error Handling and Retry Idioms

*   **External Calls**: All external calls (X API, OpenAI API, CUA actions, browser operations) **MUST** be wrapped in `try-except` blocks.
*   **Specific Exceptions**: Catch specific exceptions rather than generic `Exception`. Define custom project exceptions where appropriate (e.g., in `core/exceptions.py`) for better error discrimination.
*   **Retry Logic**: For transient errors (e.g., network issues, temporary API unavailability, browser navigation failures), implement a retry mechanism with exponential backoff and a maximum number of retries. A utility function for this (e.g., in `core/utils.py`) should be used consistently.
*   **CUA-Specific Error Handling**: Browser automation failures may require different retry strategies (e.g., browser restart, session refresh) compared to API failures.
*   **Logging**: All significant errors, including retry attempts, **MUST** be logged comprehensively with contextual information.
*   **Fallback/HIL Escalation**: If errors persist after retries, the system should define fallback behaviors: switching from CUA to API calls, pausing the workflow, deferring the task, or escalating to HIL.
*   **Rationale**: Enhances system robustness and resilience to common operational issues in both API and browser automation contexts.

## 10. CUA-Agent Coordination Patterns

*   **Screenshot-Driven Workflows**: CUA captures screenshots that are analyzed by other agents (e.g., `AnalysisAgent` for engagement metrics, `ContentCreationAgent` for context-aware replies).
*   **Action Delegation**: Other agents can request specific CUA actions (e.g., "post this content," "navigate to user profile") through the `OrchestratorAgent`.
*   **State Synchronization**: CUA maintains awareness of overall agent system state and can provide browser-based verification of API actions or system state.
*   **Hybrid Operations**: Complex workflows may combine CUA actions (e.g., screenshot capture) with API calls (e.g., data retrieval) and content generation (e.g., LLM analysis) in coordinated sequences.
*   **Rationale**: Maximizes the strengths of each agent type while providing comprehensive X platform automation capabilities.