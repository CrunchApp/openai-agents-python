# Technical Context: Autonomous X Agentic Unit

## 1. Core Technology Stack

*   **Primary Programming Language**: Python
    *   **Version**: 3.9.x (Ensure all generated Python code is compatible with this version).
*   **Core AI Framework**: Forked OpenAI Agents SDK
    *   **Baseline Version**: (To be determined based on the initial cloned version, e.g., OpenAI Agents SDK v0.5.0). This project will introduce custom modifications and extensions to this base. Cursor must prioritize project-specific implementations found within our codebase over generic knowledge of the public OpenAI Agents SDK.
*   **LLM Interaction**: OpenAI API
    *   **Models (for the Agentic Unit itself)**: Our strategy will employ a hybrid approach, leveraging different OpenAI models based on task requirements, aligning with OpenAI's guidance for agentic systems:
            *   **ComputerUseAgent (Primary CUA Operations)**: Will use **`computer-use-preview`** model specifically designed for computer control tasks via the Responses API, providing visual understanding and action planning capabilities for browser automation.
            *   **OrchestratorAgent & AnalysisAgent (Primary Reasoning/Planning)**: Will primarily use reasoning models like **`o4-mini`** or **`o3`** (if available and suitable via the Responses API) due to their strengths in long-term planning and complex decision-making.
            *   **ContentCreationAgent (Content Generation)**: Will use capable text generation models like **`GPT-4.1`** or **`GPT-4o`** (via the Responses API) for high-quality text generation (tweets, replies).
            *   **Task Execution Agents (minor LLM calls)**: May use faster, cost-effective models available through the Responses API if the task is well-defined.
            *   The choice of model for a specific agent or task can be configured.
        *   **Preferred API for Agent LLM Calls**: For direct interactions with OpenAI LLMs from within our agent logic (e.g., for content generation, decision making not handled by the SDK's agent loop itself), we **MUST** use the **OpenAI Responses API** (`client.responses.create(...)`) with the modern `openai` library (v1.x.x or newer). This aligns with OpenAI's recommended approach for building agentic applications and provides access to built-in tools and a stateful, event-driven architecture. We will **AVOID** using the `client.chat.completions.create(...)` API for new agent logic.
    *   **Computer Use Tool**: OpenAI's `computer-use-preview` model integrated through the Agents SDK `ComputerTool`, interfacing with our custom `AsyncComputer` implementations.
*   **Operating System Considerations**: The primary development and deployment target is Linux-based environments (e.g., Ubuntu LTS). CUA operations involving direct computer control will be designed with this in mind, though browser automation aspects (via Playwright) aim for cross-platform compatibility where feasible.

## 2. Key Libraries & Dependencies

*   **Computer Use & GUI Automation (PRIMARY)**:
    *   **`Playwright`**: Latest stable Python version (**CRITICAL DEPENDENCY** - Primary library for browser automation tasks as part of CUA operations). Core component of our `LocalPlaywrightComputer` implementation.
    *   **Implementation Status**: **✅ COMPLETE** - `core/computer_env/local_playwright_computer.py` (5.4KB) fully implemented
    *   (The OpenAI Agents SDK itself may bring in dependencies for its `ComputerTool` or `AsyncComputer`.)
*   **X API Interaction (COMPLEMENTARY/FALLBACK)**:
    *   `tweepy`: Version 4.10.x or later (for X API v2 interactions as fallback).
    *   `requests`: Latest stable version (Primary library for direct X API v2 calls when needed, especially user-context write actions. Also for other general HTTP interactions).
    *   `requests-oauthlib`: Latest stable version (for managing X API OAuth 2.0 PKCE flows and token refresh).
    *   **Implementation Status**: **✅ COMPLETE** - `tools/x_api_tools.py` (5.0KB) and `core/oauth_manager.py` (7.0KB) fully implemented
*   **Data Persistence**:
    *   `sqlite3`: Python's built-in module. No external ORM like SQLAlchemy is planned for the initial core system to maintain simplicity, but direct, secure SQL construction is paramount.
    *   **Note**: Recent implementation uses `SQLAlchemy~=2.0.0` for APScheduler job persistence, maintaining hybrid approach.
    *   **Implementation Status**: **✅ COMPLETE** - `core/db_manager.py` (9.7KB) fully implemented with SQLite operations
*   **Task Scheduling**:
    *   `APScheduler`: Version 3.9.x or later with `SQLAlchemyJobStore` for persistent scheduling.
    *   **Implementation Status**: **✅ COMPLETE** - `core/scheduler_setup.py` (1012B) and `project_agents/scheduling_agent.py` (3.5KB) implemented
*   **Environment & Configuration Management**:
    *   `python-dotenv`: Latest stable version (for loading `.env` files).
    *   `pydantic`: Version 2.x (Updated to V2 for new implementations). Used for `BaseSettings` in `core/config.py` and potentially for tool argument/API model validation.
    *   **Implementation Status**: **✅ COMPLETE** - `core/config.py` (2.3KB) implemented with Pydantic
*   **Code Quality & Formatting**:
    *   `Ruff`: Latest stable version (for linting and formatting, replacing Black, Flake8, isort). Project configuration will be in `pyproject.toml`.
    *   **Implementation Status**: **✅ COMPLETE** - `pyproject.toml` (3.6KB) configured with Ruff settings
*   **Testing**:
    *   `pytest`: Latest stable version (for all unit and integration tests).
    *   `pytest-cov`: For test coverage reporting.
    *   `pytest-mock`: For mocking dependencies in tests.
    *   `pytest-asyncio`: For testing async CUA operations.
    *   **Implementation Status**: **✅ COMPLETE** - Comprehensive test suite with 50+ test files:
        *   `tests/core/` - Core infrastructure tests
        *   `tests/agents/` - Agent behavior tests  
        *   `tests/tools/` - Tool implementation tests
        *   SDK integration tests throughout `tests/` directory
*   **Serialization/Validation (for Agent Tools & API models, if any)**:
    *   `Pydantic`: Current project usage in `core/config.py` uses `from pydantic import BaseSettings`. We will standardize on Pydantic **V2.x** for all new Pydantic usage (e.g., for tool arguments, API request/response models if any are built). This implies `core/config.py` should eventually be updated to use `from pydantic_settings import BaseSettings` to align with Pydantic V2 best practices for settings management. For now, new Pydantic models should use V2 features. `pip install "pydantic>=2.0.0"` and `pip install "pydantic-settings>=2.0.0"`.
*   **Security (Cryptography for token encryption)**:
    *   `cryptography`: Latest stable version (if implementing database-level encryption for OAuth tokens).
    *   **Implementation Status**: **✅ COMPLETE** - OAuth token encryption implemented in `core/oauth_manager.py`

*(Note to AI: Specific versions will be formally pinned in `requirements.txt`. When generating code involving these libraries, adhere to the typical usage patterns and APIs for these versions. If a library offers multiple ways to achieve a task, prefer the most modern, idiomatic, and secure approach compatible with the specified versions. Playwright integration is now a PRIMARY dependency, not optional.)*

## 3. Build, Dependency, and Environment Management

*   **Dependency Management**: `pip` with `requirements.txt` files. For development, a `requirements-dev.txt` may include testing and linting tools.
    *   We may explore `uv` as a faster alternative to `pip` later, but initial guidance should assume `pip`.
*   **Virtual Environments**: `venv` (Python's built-in module) is mandatory for local development.
*   **Containerization (for CUA & Deployment)**: Docker will be used for:
    *   Creating controlled, reproducible environments for CUA execution (e.g., a container with a browser and Playwright) - **NOW PRIORITY**.
    *   Packaging the application for deployment.
    *   AI should be able to generate `Dockerfile` snippets if requested, based on project needs.

## 4. CI/CD Pipeline (Conceptual)

*   **Version Control**: Git, hosted on GitHub (or similar platform).
*   **Automation Server**: GitHub Actions (or similar, e.g., Jenkins, GitLab CI).
*   **Pipeline Stages**:
    1.  Linting and Formatting (Ruff).
    2.  Unit & Integration Tests (PyTest).
    3.  **CUA Integration Tests**: Playwright-based tests for browser automation workflows.
    4.  Code Coverage Check.
    5.  Build Docker Image with Playwright dependencies.
    6.  (Future) Deployment to staging/production environments.

## 5. Environment-Specific Configurations

*   All sensitive configurations (API keys, secrets, database paths if not default) **MUST** be managed via environment variables.
*   The `core/config.py` module will be responsible for loading these variables using `python-dotenv` for local development and directly from the environment in deployed settings.
*   **CUA-Specific Configuration**: Browser automation settings (viewport size, user agent, headless mode, automation detection countermeasures) are configured through environment variables and the `LocalPlaywrightComputer` implementation.
*   Distinct configurations may exist for `development`, `testing`, `staging`, and `production` environments. The AI should assume that environment-specific API endpoints or behaviors will be handled through these loaded configurations, not hardcoded.

## 6. Integration with External Services

*   **X (Twitter)**: **Primary interaction via CUA/browser automation**, with secondary interaction via X API v2 for fallback scenarios.
*   **OpenAI**: For LLM access (GPT models, computer-use-preview for CUA) and Computer Use tool functionality.
*   **Browser Infrastructure**: Playwright-managed browser instances for CUA operations, including session management and anti-detection measures.
*   **Logging/Monitoring (Future Consideration)**: While not in the initial scope, we may integrate with services like Logfire, Sentry, or AgentOps. Generated code should use Python's standard `logging` module, which can be configured to pipe to such services later.

## 7. API Keys and Sensitive Credentials

*   **Storage**: NEVER hardcode API keys or secrets in the source code.
*   **Local Development**: Store in a `.env` file at the project root (this file **MUST BE** in `.gitignore`).
*   **Deployment**: Store as environment variables injected into the runtime environment (e.g., Docker environment variables, secrets management service).
*   **X OAuth Tokens**: Stored encrypted in the SQLite database (`x_oauth_tokens` table), with the encryption key itself managed as a secure environment variable.
*   **Browser Session Management**: CUA authentication handled through browser session cookies and localStorage, managed securely within browser profiles.

## 8. CUA-Specific Technical Requirements

*   **Browser Engine**: Chromium-based browsers via Playwright for consistent automation behavior.
*   **Viewport Management**: Standardized viewport dimensions (e.g., 1024x768) for consistent screenshot analysis and interaction targeting.
*   **Session Persistence**: Browser profiles and session data managed for authentication state maintenance across CUA operations.
*   **Anti-Detection**: Implementation of human-like interaction patterns, timing delays, and browser fingerprint management to avoid platform detection.
*   **Screenshot Handling**: Base64-encoded screenshot capture and analysis capabilities for workflow verification and cross-agent coordination.
*   **Error Recovery**: Browser crash recovery, session restoration, and fallback mechanisms for maintaining operational continuity.

## 9. Implementation Status Summary

*   **Repository Structure**: **✅ COMPLETE** - All planned directories and files implemented:
    *   `core/` - Complete infrastructure (4 modules, computer_env package)
    *   `project_agents/` - All 5 specialized agents implemented
    *   `tools/` - Complete tool suite (X API + HIL tools)
    *   `scripts/` - Operational utilities for database and OAuth management  
    *   `tests/` - Comprehensive test suite with 50+ test files
    *   `src/agents/` - Forked OpenAI Agents SDK with custom modifications
*   **Core Functionality**: **✅ OPERATIONAL** - All major components tested and working:
    *   CUA browser automation with Playwright
    *   Multi-agent coordination and handoffs
    *   X API integration with OAuth token management
    *   Database persistence and task scheduling
    *   Human-in-the-loop workflows
*   **Development Infrastructure**: **✅ COMPLETE** - Full development environment:
    *   Build configuration (`pyproject.toml`, `requirements.txt`)
    *   Testing framework with comprehensive coverage
    *   Code quality tools (Ruff) properly configured
    *   Documentation and memory bank system
*   **Next Phase**: System integration testing and production deployment preparation

*(Note to AI: This technical context now reflects the CUA-first strategic approach, with Playwright as a primary dependency and computer use operations as the core interaction method, while maintaining API tools as complementary fallback systems. All major technical components are implemented and operational.)*