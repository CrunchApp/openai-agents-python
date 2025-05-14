# Project Blueprint & Roadmap: Autonomous X Agentic Unit

## 1. Introduction & Guiding Principles

*   **Objective**: Construct an Agentic Unit using a forked OpenAI Agents SDK to autonomously manage an X (formerly Twitter) account, incorporating "Computer Use" (CUA) capabilities. The agent will operate continuously with a hybrid autonomy model (human-in-the-loop for critical tasks).
*   **Development Approach**: LLM-assisted coding via Cursor, emphasizing modularity and clear task definition.
*   **Guiding Principles**:
    *   **Modularity and Specialization**: Distinct agents for specific tasks (content creation, X interaction, analysis, CUA, etc.).
    *   **Hybrid Autonomy**: Balance automation with human oversight.
    *   **Security First**: Secure credential handling, least privilege.
    *   **Scalability and Maintainability**: Architecture supports future growth.
    *   **Observability and Debugging**: Comprehensive logging and tracing.
    *   **Adherence to X Platform Policies**: All actions must comply.
    *   **LLM-Assisted Development Focus**: Small, well-defined coding units.

## 2. Architectural Overview

*   **Core Design**: Multi-agent architecture orchestrated by a central agent, leveraging specialized agents.
*   **Core Components**:
    1.  **OpenAI Agents SDK (Forked)**: Foundational framework (Agents, Tools, Handoffs, Guardrails).
    2.  **LLMs**: OpenAI models (GPT-4o, GPT-4) for reasoning and decision-making.
    3.  **X API v2**: Primary interface for X platform interaction (initially).
    4.  **OpenAI "Computer Use" Tool / Custom CUA**: For UI-based actions via Responses API or hosted tool, potentially supplemented by custom Playwright scripts.
    5.  **Persistent Storage**: SQLite database (`data/agent_data.db`) for state, configurations, task queues, OAuth tokens, logs.
    6.  **Task Scheduler**: APScheduler for continuous operation and scheduled tasks.
*   **Agent Specialization**:
    1.  **Orchestrator Agent (Manager Agent)**: Central coordinator; breaks down goals, delegates tasks, manages workflow.
    2.  **Content Creation Agent**: Drafts tweets, threads, replies.
    3.  **X Interaction Agent**: Executes X platform actions via X API tools.
    4.  **Computer Use Agent (CUA)**: Uses OpenAI "Computer Use" tool or custom Playwright scripts for UI interactions on X.
    5.  **Analysis Agent**: Analyzes engagement, monitors mentions, identifies trends.
    6.  **Profile Management Agent**: Handles X profile updates (via API or CUA).
    7.  **Scheduling Agent**: Manages and triggers tasks via APScheduler, interfacing with Orchestrator.
    8.  **Human Handoff Agent/Mechanism**: Facilitates HIL for review/approval.
*   **Workflow Conceptualization**:
    *   Orchestrator initiates workflows based on scheduled events or triggers.
    *   Tasks delegated to specialized agents (e.g., Content Creation -> (HIL) -> X Interaction).
    *   OpenAI Agents SDK `handoffs` feature for inter-agent control transfer. Agents can also be used as `tools` by other agents.
    *   Built-in agent loop handles tool calls, results, and iteration.

## 3. Technology Stack Summary (Reference `techContext.md` for versions)

*   **Core Framework**: OpenAI Agents SDK (Forked), Python 3.9.x.
*   **API Interactions**:
    *   OpenAI API (for LLMs, CUA tool).
    *   X API v2 (Client: Tweepy; or `requests` + `requests-oauthlib`).
*   **Computer Use Implementation**:
    *   OpenAI Computer Use Tool.
    *   Execution Environment: Browser controlled by Playwright (or similar) within a controlled environment (e.g., Docker).
*   **Data Persistence**: SQLite (built-in `sqlite3` module).
*   **Task Scheduling**: APScheduler.
*   **Environment & Dependency Management**: `venv`, `pip`, `requirements.txt`, `python-dotenv`.
*   **Development Environment**: Cursor IDE.

## 4. Project Directory Structure (MANDATORY)

The following directory structure **MUST** be adhered to. The AI **MUST** place new files in the correct directories and reference existing files using these paths.

x_agentic_unit/
├── agents/ # Specialized agent definitions
│ ├── init.py
│ ├── orchestrator_agent.py
│ ├── content_creation_agent.py
│ ├── x_interaction_agent.py
│ ├── computer_use_agent.py
│ ├── analysis_agent.py
│ ├── profile_management_agent.py
│ └── scheduling_agent.py # Manages APScheduler job definitions and triggers
├── tools/ # Agent tools (X API wrappers, CUA functions, custom logic)
│ ├── init.py
│ ├── x_api_tools.py # Functions for X API v2 calls (using Tweepy/requests)
│ ├── computer_control_tools.py # Wrappers for OpenAI CUA actions & custom Playwright scripts
│ ├── analysis_tools.py # Tools for data analysis, sentiment, etc.
│ └── human_handoff_tool.py # Tool to trigger/manage HIL process
├── workflows/ # Definitions of complex, multi-step agentic flows (Python scripts/modules orchestrating agent sequences)
│ ├── init.py
│ ├── post_generation_workflow.py
│ └── engagement_response_workflow.py
├── core/ # Core system components, utilities, and base classes
│ ├── init.py
│ ├── config.py # Configuration loading (API keys from .env)
│ ├── db_manager.py # SQLite database interaction logic (CRUD operations, schema setup)
│ ├── scheduler_setup.py # APScheduler instance setup and core job store configuration
│ ├── oauth_manager.py # X API OAuth 2.0 token acquisition, storage, and refresh logic
│ └── exceptions.py # Custom project-specific exception classes
│ └── utils.py # Common utility functions (e.g., retry decorators, date formatters)
├── data/ # Persistent data (e.g., SQLite DB, logs). THIS DIRECTORY IS IN .gitignore (except for maybe an empty .gitkeep file).
│ └── agent_data.db # SQLite database file
│ └── app.log # Main application log file
├── logs/ # Alternative/additional directory for more detailed or separated log files if needed (also in .gitignore).
├── tests/ # Unit and integration tests
│ ├── init.py
│ ├── agents/ # Tests for agent logic
│ ├── tools/ # Tests for tools
│ ├── core/ # Tests for core components
│ └── test_x_api_tools.py # Example test file
├── frontend/ # (If a simple UI for HIL/monitoring is developed later)
│ ├── src/
│ └── ...
├── .cursor/ # Cursor-specific configuration
│ ├── memory/ # Memory bank files (projectBrief.md, productContext.md, etc.)
│ └── rules/ # Rule files (.mdc)
├── .env # Environment variables (API keys, secrets) - DO NOT COMMIT (in .gitignore)
├── .gitignore # Specifies intentionally untracked files that Git should ignore
├── main.py # Main application entry point (initializes system, starts Orchestrator/Scheduler)
├── requirements.txt # Project dependencies
├── requirements-dev.txt # Development dependencies (e.g., pytest, ruff)
├── pyproject.toml # Project metadata, Ruff configuration
└── README.md # Project documentation (high-level overview, setup instructions)

*   **Explanation of Key Folders**:
    *   `agents/`: Each `.py` file defines a specialized agent, its instructions, and the tools it uses.
    *   `tools/`: Contains Python functions that agents use as tools (e.g., `x_api_tools.py` for X API wrappers, `computer_control_tools.py` for CUA).
    *   `workflows/`: Higher-level scripts/modules defining sequences of agent interactions for complex tasks.
    *   `core/`: Foundational modules (config, DB interaction, OAuth, custom exceptions, utilities).
    *   `data/`: For runtime data like the SQLite DB and logs (should be gitignored).
    *   `tests/`: All test code, mirroring the project structure.

## 5. Phased Development Roadmap Summary

### Phase 1: Foundation and Core Posting Agent (MVP)
*   **Goal**: Basic project structure, X API auth, post simple text tweet.
*   **Key Tasks**: Env setup, X API credential & OAuth 2.0 PKCE flow, core modules (`config.py`, `db_manager.py`, `oauth_manager.py`), basic `OrchestratorAgent` & `XInteractionAgent`, `post_text_tweet` tool, basic logging.

### Phase 2: Expanding Interactions (Replies, DMs, Basic Analysis & Scheduling)
*   **Goal**: Read timeline, reply to mentions (with HIL), send/receive DMs, basic scheduled checks.
*   **Key Tasks**: New X API tools (mentions, DMs, timeline), `ContentCreationAgent`, SQLite schema expansion, APScheduler integration (`SchedulingAgent`, `core/scheduler_setup.py`), `HumanHandoffTool`.

### Phase 3: Integrating "Computer Use" and Advanced Content (Media, Polls)
*   **Goal**: Integrate OpenAI "Computer Use" tool / custom Playwright for UI automation; post tweets with media/polls.
*   **Key Tasks**: CUA environment setup, `ComputerUseAgent` & `computer_control_tools.py` (Playwright wrappers, OpenAI CUA tool integration), X API media upload tool, poll creation tool.
*   **Strategic Focus**: Begin PoCs for shifting some X interactions from API to CUA/GUI.

### Phase 4: Full Hybrid Control, Profile Management, and Robustness
*   **Goal**: Comprehensive profile management (API/CUA), advanced analysis, refined HIL, robust error/rate limit handling, full guardrails.
*   **Key Tasks**: `ProfileManagementAgent` (profile text & image updates via CUA), advanced analysis tools, refined HIL triggers, proactive rate limit management, comprehensive guardrails.
*   **Strategic Focus**: Evaluate CUA/GUI PoCs and begin migrating selected workflows if successful and cost-effective.

### Iterative Tasks (Throughout all phases):
*   Unit, Integration, and Workflow Testing.
*   Continuous Monitoring & Logging.
*   Prompt Engineering for LLMs (agent instructions, tool descriptions).
*   Utilize OpenAI Agents SDK tracing for debugging.
*   Refine Cursor rules and memory bank based on performance.

## 6. Mapping X User Actions to Agent Tasks (High-Level)

The agent aims to cover "All activities available to me as a user." This includes:
*   **Content**: Posting (tweets, threads, polls), replies, quotes, DMs.
*   **Engagement**: Likes, retweets, bookmarks.
*   **User Management**: Follow/unfollow, block, mute.
*   **Profile Management**: Name, bio, location, website, profile picture, banner (profile/banner images are strong candidates for CUA).
*   **Information Retrieval**: Timelines, mentions, search, notifications, lists.
*   **List Management**: Create, delete, update lists, manage members.

*(Note to AI: This blueprint provides the structural and strategic framework for the project. Refer to it for understanding agent roles, workflow concepts, directory structure for new files, and the overall development trajectory. Specific technical details are in `techContext.md` and behavioral guidelines in other rule/memory files.)*