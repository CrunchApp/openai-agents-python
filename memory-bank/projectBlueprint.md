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
    2.  **LLMs**: OpenAI models (GPT-4o, GPT-4, computer-use-preview) for reasoning and decision-making.
    3.  **X API v2**: Complementary interface for X platform interaction (fallback/data retrieval).
    4.  **OpenAI "Computer Use" Tool / Custom CUA**: Primary interaction method via Responses API with custom Playwright implementation.
    5.  **Persistent Storage**: SQLite database (`data/agent_data.db`) for state, configurations, task queues, OAuth tokens, logs.
    6.  **Task Scheduler**: APScheduler for continuous operation and scheduled tasks.
*   **Agent Specialization**:
    1.  **Orchestrator Agent (Manager Agent)**: Central coordinator; breaks down goals, delegates tasks, manages workflow.
    2.  **Content Creation Agent**: Drafts tweets, threads, replies.
    3.  **X Interaction Agent**: Executes X platform actions via X API tools.
    4.  **Computer Use Agent (CUA)**: Primary agent using OpenAI "Computer Use" tool with custom Playwright scripts for UI interactions on X.
    5.  **Analysis Agent**: Analyzes engagement, monitors mentions, identifies trends.
    6.  **Profile Management Agent**: Handles X profile updates (via API or CUA).
    7.  **Scheduling Agent**: Manages and triggers tasks via APScheduler, interfacing with Orchestrator.
    8.  **Human Handoff Agent/Mechanism**: Facilitates HIL for review/approval.
*   **Workflow Conceptualization**:
    *   Orchestrator initiates workflows based on scheduled events or triggers.
    *   Tasks delegated to specialized agents (e.g., Content Creation -> (HIL) -> Computer Use Agent).
    *   OpenAI Agents SDK `handoffs` feature for inter-agent control transfer. Agents can also be used as `tools` by other agents.
    *   Built-in agent loop handles tool calls, results, and iteration.

## 3. Technology Stack Summary (Reference `techContext.md` for versions)

*   **Core Framework**: OpenAI Agents SDK (Forked), Python 3.9.x.
*   **API Interactions**:
    *   OpenAI API (for LLMs, CUA tool).
    *   X API v2 (Client: Tweepy; or `requests` + `requests-oauthlib`) - Fallback/complement to CUA.
*   **Computer Use Implementation**:
    *   OpenAI Computer Use Tool with computer-use-preview model.
    *   Execution Environment: Browser controlled by Playwright within controlled environment.
    *   Custom `LocalPlaywrightComputer` implementation for async compatibility.
*   **Data Persistence**: SQLite (built-in `sqlite3` module).
*   **Task Scheduling**: APScheduler.
*   **Environment & Dependency Management**: `venv`, `pip`, `requirements.txt`, `python-dotenv`.
*   **Development Environment**: Cursor IDE.

## 4. Current Project Directory Structure (IMPLEMENTED)

The following directory structure reflects the **actual current implementation**. The AI **MUST** use these paths when referencing existing files and follow this structure for new files.

```
OPENAI-AGENTS-PYTHON-1/ (repository root)
├── core/                           # Core infrastructure & utilities
│   ├── computer_env/               # CUA environment management
│   │   ├── base.py                 # Base computer interface definitions  
│   │   ├── local_playwright_computer.py # Primary CUA implementation with Playwright
│   │   └── __init__.py
│   ├── config.py                   # Environment configuration management
│   ├── db_manager.py               # SQLite database operations (9.7KB)
│   ├── oauth_manager.py            # X API OAuth 2.0 PKCE token management
│   └── scheduler_setup.py          # APScheduler configuration for continuous operation
├── project_agents/                 # Specialized agent implementations
│   ├── orchestrator_agent.py       # Central coordination and task delegation (7.1KB)
│   ├── computer_use_agent.py       # Primary CUA for browser automation (1.5KB)
│   ├── content_creation_agent.py   # Content generation and curation (3.0KB)
│   ├── x_interaction_agent.py      # X platform interaction coordination (1.3KB)
│   ├── scheduling_agent.py         # Task scheduling and continuous operation (3.5KB)
│   └── __init__.py
├── tools/                          # Agent tool implementations
│   ├── x_api_tools.py              # X API v2 integration tools (5.0KB)
│   ├── human_handoff_tool.py       # HIL workflow implementation (2.2KB)
│   └── __init__.py
├── scripts/                        # Operational & maintenance scripts
│   ├── initialize_db.py            # Database schema initialization (638B)
│   ├── manual_approve_reply.py     # HIL approval workflow (2.3KB)
│   └── temp_set_initial_tokens.py  # OAuth token setup utility (1.5KB)
├── src/                            # OpenAI Agents SDK core implementation
│   └── agents/                     # Main SDK implementation
│       ├── computer.py             # Computer use interface (2.6KB)
│       ├── models/                 # LLM provider implementations
│       │   ├── openai_responses.py # OpenAI Responses API integration (14KB)
│       │   └── [other model providers]
│       ├── [extensive SDK modules] # 40+ core SDK files
│       └── __init__.py
├── examples/                       # SDK examples & learning resources
│   ├── basic/                      # Fundamental SDK usage examples
│   ├── agent_patterns/             # Advanced agent design patterns
│   ├── tools/                      # Tool implementation examples
│   │   └── computer_use.py         # CUA tool examples (5.3KB)
│   ├── financial_research_agent/   # Complex multi-agent system example
│   └── [other example directories]
├── tests/                          # Comprehensive test suite
│   ├── core/                       # Core infrastructure tests
│   │   ├── test_config.py          # Configuration tests
│   │   ├── test_db_manager.py      # Database operation tests (4.9KB)
│   │   └── test_oauth_manager.py   # OAuth flow tests (8.7KB)
│   ├── agents/                     # Project agent tests
│   │   ├── test_orchestrator_agent.py # Core orchestration tests (14KB)
│   │   └── test_scheduling_agent.py # Scheduling logic tests (5.6KB)
│   ├── tools/                      # Tool implementation tests
│   │   ├── test_x_api_tools.py     # X API tool tests (9.0KB)
│   │   └── test_human_handoff_tool.py
│   ├── [50+ SDK integration tests] # Extensive SDK test suite
│   ├── conftest.py                 # PyTest configuration
│   └── __init__.py
├── data/                           # Persistent data (gitignored except .gitkeep)
│   └── agent_data.db               # SQLite database file (when created)
├── memory-bank/                    # Project documentation & context
│   ├── projectBrief.md             # High-level overview and goals
│   ├── productContext.md           # User needs and business context  
│   ├── systemPatterns.md           # Architectural decisions and patterns
│   ├── techContext.md              # Technical stack and dependencies
│   ├── progress.md                 # Change tracking and milestones
│   └── projectBlueprint.md         # This file - roadmap and structure
├── .cursor/                        # Cursor IDE configuration
│   └── rules/                      # Development rules and guidelines
├── main.py                         # Main application entry point (1.6KB)
├── requirements.txt                # Project dependencies (301B)
├── pyproject.toml                  # Project metadata, Ruff configuration (3.6KB)
├── .env                            # Environment variables (gitignored)
├── .gitignore                      # Git ignore patterns
├── README.md                       # Project documentation (6.7KB)
└── [other config files]            # Makefile, LICENSE, etc.
```

*   **Key Directory Explanations**:
    *   `project_agents/`: **Specialized agent implementations** - Each file defines a specialized agent with its instructions and tools.
    *   `tools/`: **Agent tool implementations** - Python functions that agents use (X API wrappers, HIL tools).
    *   `core/`: **Core infrastructure** - Configuration, database, OAuth, scheduling, and CUA environment.
    *   `core/computer_env/`: **CUA implementation** - Browser automation with Playwright and OpenAI computer use integration.
    *   `src/agents/`: **OpenAI Agents SDK core** - The forked SDK implementation with our customizations.
    *   `examples/`: **SDK learning resources** - Reference implementations and patterns from the base SDK.
    *   `scripts/`: **Operational utilities** - Database setup, token management, HIL approval workflows.
    *   `tests/`: **Comprehensive testing** - Unit and integration tests mirroring the project structure.
    *   `memory-bank/`: **Project documentation** - Memory bank files for context and guidelines.
    *   `data/`: **Runtime data** - SQLite database and logs (gitignored).

*   **Future Planned Additions**:
    *   `workflows/`: Higher-level scripts defining complex multi-agent sequences (when needed).
    *   `frontend/`: Simple UI for HIL/monitoring (if developed later).
    *   `logs/`: Detailed logging infrastructure (alternative to data/ logging).

## 5. Phased Development Roadmap Summary

### Phase 1: Foundation and Core Posting Agent (MVP) ✅ **COMPLETED**
*   **Goal**: Basic project structure, X API auth, post simple text tweet.
*   **Key Tasks**: Env setup, X API credential & OAuth 2.0 PKCE flow, core modules (`config.py`, `db_manager.py`, `oauth_manager.py`), basic `OrchestratorAgent` & `XInteractionAgent`, `post_text_tweet` tool, basic logging.
*   **Status**: ✅ **COMPLETED** - All MVP functionality implemented and tested.

### Phase 2: CUA Development & Integration ✅ **COMPLETED** 
*   **Goal**: Integrate OpenAI "Computer Use" tool with custom Playwright implementation; establish multi-agent architecture.
*   **Key Tasks**: CUA environment setup (`core/computer_env/`), `ComputerUseAgent` implementation, `LocalPlaywrightComputer` with async compatibility, complete agent suite, comprehensive testing.
*   **Status**: ✅ **COMPLETED** - Full CUA-first architecture implemented and operational.

### Phase 3: Production Deployment & Optimization 🔄 **IN PROGRESS**
*   **Goal**: Deploy system for continuous operation with monitoring, optimization, and robustness.
*   **Key Tasks**: 
    *   End-to-end workflow validation
    *   Performance optimization for CUA operations
    *   Anti-detection strategies for browser automation
    *   Containerization with Docker
    *   Production monitoring and alerting
    *   Advanced error handling and recovery
*   **Status**: 🔄 **IN PROGRESS** - System integration and validation phase.

### Phase 4: Advanced Features & Scaling (Future)
*   **Goal**: Advanced capabilities, multi-account management, enterprise features.
*   **Key Tasks**: 
    *   Advanced screenshot analysis and computer vision
    *   Machine learning-enhanced content generation  
    *   Multi-session CUA management
    *   Advanced sentiment analysis and engagement optimization
    *   Enterprise integration capabilities

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

## 7. Implementation Status Summary

*   **✅ Completed**: Core infrastructure, all specialized agents, tool suite, CUA implementation, comprehensive testing, operational scripts
*   **🔄 In Progress**: System integration testing, performance optimization, production deployment preparation
*   **⏳ Planned**: Advanced monitoring, containerization, workflow automation, advanced CUA capabilities

*(Note to AI: This blueprint now accurately reflects the current repository structure and implementation status. Use the `project_agents/` directory for agent files, reference the existing `core/computer_env/` for CUA implementations, and follow the documented directory structure for any new files. The system has successfully completed Phase 2 and is ready for Phase 3 production optimization.)*