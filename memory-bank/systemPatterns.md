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

## 11. CUA Authentication and Session Management Strategy

*   **Objective**: Enable the `ComputerUseAgent` (CUA) to operate within an authenticated X.com session for designated test accounts, allowing it to perform actions that require login while maintaining security and operational simplicity.

*   **Chosen Approach**: **Manual Login with Persistent Session State (Playwright User Data Directory)**
    *   This approach uses Playwright's `launch_persistent_context` feature to maintain browser session state (cookies, local storage, session tokens) across CUA executions.
    *   Authentication is established once through manual login, then persisted for subsequent automated operations.

### Implementation Details

#### 11.1. Configuration Management
*   **Environment Variable**: `X_CUA_USER_DATA_DIR` specifies the path to the persistent browser profile directory.
*   **Configuration Setting**: `settings.x_cua_user_data_dir` in `core/config.py` manages this path.
*   **Default Behavior**: When `X_CUA_USER_DATA_DIR` is not set, CUA operates in fresh, unauthenticated browser sessions.

#### 11.2. LocalPlaywrightComputer Enhancement
*   **Constructor Parameter**: `user_data_dir_path: Optional[str]` enables persistent session support.
*   **Browser Launch Strategy**:
    *   **Persistent Context**: When `user_data_dir_path` is provided, uses `playwright.chromium.launch_persistent_context()` to maintain session state.
    *   **Fresh Browser**: When `user_data_dir_path` is `None`, uses standard `playwright.chromium.launch()` for ephemeral sessions.
*   **Session State Persistence**: All browser data (cookies, local storage, authentication tokens) automatically persists between CUA executions.

#### 11.3. Authentication Workflow

##### Initial Setup (One-Time Manual Process)
1.  **Environment Configuration**: Set `X_CUA_USER_DATA_DIR=data/cua_profile` in `.env` file.
2.  **Manual Authentication**: 
    *   Launch Playwright browser with persistent context pointing to the configured directory.
    *   Navigate to X.com and manually complete login process for designated test account.
    *   Complete any MFA, verification, or "Remember me" options.
    *   Close browser - session state is automatically saved to the user data directory.
3.  **Verification**: Subsequent CUA launches should bypass login and access authenticated features directly.

##### Operational Usage
*   **Authenticated Operations**: CUA can access user-specific pages (notifications, settings, profile management) without re-authentication.
*   **Session Persistence**: Authentication state persists across application restarts and scheduled executions.
*   **Cost Optimization**: Reduces dependency on X API authentication and associated token management overhead.

#### 11.4. Session Invalidation Detection and Handling

##### Detection Mechanisms
*   **Agent Instructions**: CUA is trained to recognize logged-out states through UI indicators.
*   **Authentication Indicators**:
    *   **Authenticated**: Access to notifications, settings, profile pages without redirects.
    *   **Unauthenticated**: Login forms, "Sign In" buttons, redirects to authentication pages.

##### Invalidation Response Protocol
1.  **Immediate Task Abort**: CUA stops current task execution upon detecting session loss.
2.  **Documentation**: Takes screenshot of login page for audit trail.
3.  **Error Reporting**: Returns structured error message: `SESSION_INVALIDATED: Browser session is no longer authenticated. Manual re-authentication required.`
4.  **No Auto-Login**: CUA explicitly **MUST NOT** attempt automatic re-authentication or credential entry.
5.  **HIL Escalation**: Session invalidation should trigger Human-in-the-Loop workflow for manual re-authentication.

#### 11.5. Security Considerations

*   **Principle of Least Privilege**: CUA browser sessions operate with minimal required permissions.
*   **Isolated Profiles**: Persistent user data directories are isolated and gitignored to prevent credential exposure.
*   **No Credential Storage**: Authentication relies on browser session tokens, not stored credentials.
*   **Access Control**: User data directories should have appropriate file system permissions restricting access.

#### 11.6. Operational Benefits

*   **Cost Efficiency**: Reduces X API authentication overhead and associated rate limiting.
*   **Feature Completeness**: Enables access to all X platform features available through browser interface.
*   **Reliability**: Persistent sessions reduce authentication failure points during automated operations.
*   **Scalability**: Multiple profiles can be maintained for different test accounts or operational scenarios.

#### 11.7. Maintenance Procedures

*   **Session Refresh**: Manual re-authentication required when persistent session expires or is invalidated.
*   **Profile Management**: Regular cleanup of user data directories to manage disk space.
*   **Security Audits**: Periodic review of session persistence configurations and access controls.
*   **Backup Procedures**: Critical authentication profiles should have backup/restore procedures for operational continuity.

### Integration with Multi-Agent Architecture

*   **Orchestrator Coordination**: `OrchestratorAgent` determines when to use authenticated vs. unauthenticated CUA sessions based on task requirements.
*   **Fallback Strategy**: API-based tools serve as fallback when CUA authentication sessions are unavailable.
*   **HIL Integration**: Session invalidation events automatically trigger human review queue entries for re-authentication.
*   **Cross-Agent State**: Authentication status can be shared across agents to inform task delegation decisions.

*   **Rationale**: This authentication strategy balances automation efficiency with security requirements, providing sustainable access to authenticated X platform features while maintaining operational robustness and security compliance.

## 12. Keyboard-First Interaction Strategy for CUA

*   **Core Principle**: The `ComputerUseAgent` prioritizes keyboard shortcuts over mouse interactions when automating X.com to maximize reliability, speed, and resilience to UI changes.

*   **Strategic Implementation**: 
    *   **Primary Method**: Keyboard shortcuts are attempted first for all interactions where X.com provides native keyboard support.
    *   **Fallback Method**: Mouse clicks are used only when no keyboard equivalent exists or when keyboard shortcuts fail.
    *   **Comprehensive Coverage**: All 50+ official X.com keyboard shortcuts are integrated into CUA instructions.

### 12.1. Keyboard Shortcut Categories

#### Navigation Shortcuts
*   **Timeline Navigation**: `j` (next post), `k` (previous post), `Space` (page down), `.` (load new posts)
*   **Page Navigation**: `g+h` (home), `g+n` (notifications), `g+p` (profile), `g+e` (explore)
*   **Feature Access**: `g+m` (messages), `g+s` (settings), `g+b` (bookmarks), `g+l` (likes)

#### Action Shortcuts  
*   **Content Actions**: `l` (like), `r` (reply), `t` (repost), `s` (share), `b` (bookmark)
*   **Account Actions**: `u` (mute), `x` (block), `Enter` (open details)
*   **Utility Actions**: `/` (search), `?` (help), `i` (messages dock)

#### Posting Shortcuts
*   **Compose**: `n` (new post)
*   **Publishing**: `Ctrl+Shift+Enter` (post tweet), `Ctrl+Enter` (send post)

#### Media Controls
*   **Video**: `k`/`Space` (play/pause), `m` (mute), `o` (expand photo)
*   **Audio Dock**: `a+d` (go to dock), `a+Space` (play/pause), `a+m` (mute/unmute)

### 12.2. Implementation in LocalPlaywrightComputer

*   **Enhanced Keypress Method**: Upgraded `keypress()` function with intelligent handling for:
    *   **Single Character Keys**: Direct processing for all X.com letter shortcuts
    *   **Sequential Combinations**: Support for `g+` navigation and `a+` audio shortcuts
    *   **Special Keys**: Mapping for Space, Enter, arrows, and punctuation
    *   **Complex Combinations**: Proper timing for Ctrl/Cmd combinations

*   **Timing Optimization**: Appropriate delays between key sequences to ensure reliable execution
*   **Robust Error Handling**: Fallback mechanisms when keyboard shortcuts encounter issues

### 12.3. Agent Instruction Integration

*   **Priority Guidelines**: Clear instructions in `ComputerUseAgent` to attempt keyboard shortcuts before mouse interactions
*   **Workflow Examples**: Detailed step-by-step processes for common tasks using keyboard-first approach
*   **Decision Logic**: Explicit criteria for when to fallback to mouse interactions

### 12.4. Operational Benefits

*   **Reliability**: Keyboard shortcuts are less affected by UI layout changes and dynamic content loading
*   **Speed**: Keyboard actions execute faster than mouse movements and clicks
*   **Consistency**: Native keyboard shortcuts provide predictable behavior across X.com sessions
*   **Detection Resistance**: Keyboard interactions appear more natural and reduce automation detection risk

*   **Rationale**: This keyboard-first strategy leverages X.com's native accessibility features to create more robust, efficient, and maintainable browser automation while reducing dependency on fragile mouse-based interactions.

## 13. OrchestratorAgent Direct Response Management Pattern

*   **Pattern Description**: For complex CUA operations requiring fine-grained control, the `OrchestratorAgent` uses direct `client.responses.create()` calls instead of delegating through `Runner.run(cua_agent, ...)`.

*   **Implementation Context**: Specifically applied to CUA tweet posting workflows where precise iteration control, safety check handling, and multi-step coordination are essential.

### 13.1. Technical Implementation

#### Direct Response API Usage
*   **Primary Method**: `client.responses.create()` with iterative processing of response items
*   **Model Configuration**: Uses `computer-use-preview` model with appropriate context windows
*   **Safety Integration**: Handles OpenAI safety checks and acknowledgments within the orchestration loop

#### Iteration Management
*   **Custom Loop Control**: Manual iteration counting and termination logic
*   **Response Processing**: Direct handling of different response item types (reasoning, computer_call, message)
*   **Context Building**: Progressive context accumulation across iterations for complex multi-step workflows

### 13.2. Advantages Over Standard Agent Delegation

#### Fine-Grained Control
*   **Iteration Limits**: Custom termination criteria based on workflow requirements rather than generic agent limits
*   **Safety Handling**: Direct processing of safety checks without interrupting the workflow
*   **Response Analysis**: Immediate access to all response components (reasoning, actions, results)

#### Complex Workflow Support
*   **Multi-Step Coordination**: Ability to inject orchestrator logic between CUA iterations
*   **State Management**: Direct control over workflow state and decision points
*   **Error Recovery**: Custom error handling and retry logic specific to CUA operations

#### Performance Optimization
*   **Reduced Overhead**: Eliminates agent delegation overhead for time-sensitive operations
*   **Direct Integration**: Immediate access to CUA responses without additional processing layers
*   **Streamlined Execution**: Optimized flow for high-frequency CUA interactions

### 13.3. Implementation Examples

#### CUA Tweet Posting Workflow
```python
# Direct response management for CUA tweet posting
response = await client.responses.create(
    model="computer-use-preview",
    messages=context_messages,
    max_tokens=2048
)

# Process response items directly
for item in response.output:
    if item.type == "computer_call":
        # Execute CUA action immediately
        result = await computer_tool.execute(item.content)
        # Add result to context for next iteration
    elif item.type == "reasoning":
        # Log reasoning for debugging
    # Continue iteration logic...
```

#### Safety Check Integration
*   **Acknowledgment Handling**: Direct processing of safety warnings without workflow interruption
*   **Context Preservation**: Maintains full conversation context across safety check interactions
*   **Workflow Continuity**: Seamless resumption after safety check resolution

### 13.4. When to Use This Pattern

#### Appropriate Scenarios
*   **Complex CUA Workflows**: Multi-step browser automation requiring precise control
*   **Time-Sensitive Operations**: Real-time interactions where delegation overhead is problematic
*   **Safety-Critical Tasks**: Operations requiring custom safety check handling
*   **Integration Points**: Workflows requiring tight coordination between CUA and other agent operations

#### Alternative Approaches
*   **Standard Delegation**: Use `Runner.run(agent, ...)` for simple, self-contained tasks
*   **Agent Handoffs**: Use SDK handoff mechanisms for clear task boundaries
*   **Tool Invocation**: Use agent tools for discrete, stateless operations

### 13.5. Best Practices

*   **Context Management**: Careful handling of message context to prevent token limit issues
*   **Error Handling**: Robust exception handling around direct response calls
*   **Logging**: Comprehensive logging of iterations, decisions, and outcomes
*   **Documentation**: Clear documentation of custom workflows and their rationale

*   **Rationale**: This pattern provides the precise control needed for complex CUA operations while maintaining the benefits of the OpenAI Agents SDK architecture. It enables sophisticated workflow orchestration without sacrificing reliability or performance.