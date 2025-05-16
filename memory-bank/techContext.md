# Technical Context: Autonomous X Agentic Unit

## 1. Core Technology Stack

*   **Primary Programming Language**: Python
    *   **Version**: 3.9.x (Ensure all generated Python code is compatible with this version).
*   **Core AI Framework**: Forked OpenAI Agents SDK
    *   **Baseline Version**: (To be determined based on the initial cloned version, e.g., OpenAI Agents SDK v0.5.0). This project will introduce custom modifications and extensions to this base. Cursor must prioritize project-specific implementations found within our codebase over generic knowledge of the public OpenAI Agents SDK.
*   **LLM Interaction**: OpenAI API
    *   **Models (for the Agentic Unit itself)**: Our strategy will employ a hybrid approach, leveraging different OpenAI models based on task requirements, aligning with OpenAI's guidance for agentic systems:
            *   **OrchestratorAgent & AnalysisAgent (Primary Reasoning/Planning)**: Will primarily use reasoning models like **`o4-mini`** or **`o3`** (if available and suitable via the Responses API) due to their strengths in long-term planning and complex decision-making.
            *   **ContentCreationAgent (Content Generation)**: Will use capable text generation models like **`GPT-4.1`** or **`GPT-4o`** (via the Responses API) for high-quality text generation (tweets, replies).
            *   **ComputerUseAgent (UI Task Planning)**: For planning multi-step UI automation sequences, will leverage reasoning models like **`o4-mini`** or **`o3`**. The underlying OpenAI `computer_use_preview` tool itself (accessed via the Responses API or Agents SDK) will utilize its own integrated vision model.
            *   **Task Execution Agents (minor LLM calls)**: May use faster, cost-effective models available through the Responses API if the task is well-defined.
            *   The choice of model for a specific agent or task can be configured.
        *   **Preferred API for Agent LLM Calls**: For direct interactions with OpenAI LLMs from within our agent logic (e.g., for content generation, decision making not handled by the SDK's agent loop itself), we **MUST** use the **OpenAI Responses API** (`client.responses.create(...)`) with the modern `openai` library (v1.x.x or newer). This aligns with OpenAI's recommended approach for building agentic applications and provides access to built-in tools and a stateful, event-driven architecture. We will **AVOID** using the `client.chat.completions.create(...)` API for new agent logic.
    *   **Computer Use Tool**: OpenAI's `computer_use_preview` tool (likely accessed via the Responses API or as a hosted tool within the Agents SDK framework, which itself uses the Responses API).
*   **Operating System Considerations**: The primary development and deployment target is Linux-based environments (e.g., Ubuntu LTS). CUA operations involving direct computer control will be designed with this in mind, though browser automation aspects (via Playwright) aim for cross-platform compatibility where feasible.

## 2. Key Libraries & Dependencies

*   **X API Interaction**:
    *   `tweepy`: Version 4.10.x or later (for X API v2 interactions).
    *   `requests`: Latest stable version (Primary library for direct X API v2 calls, especially user-context write actions. Also for other general HTTP interactions).
    *   `requests-oauthlib`: Latest stable version (for managing X API OAuth 2.0 PKCE flows and token refresh).
*   **Computer Use & GUI Automation**:
    *   `Playwright`: Latest stable Python version (for browser automation tasks as part of CUA or traditional GUI automation).
    *   (The OpenAI Agents SDK itself may bring in dependencies for its `ComputerTool` or `AsyncComputer`.)
*   **Data Persistence**:
    *   `sqlite3`: Python's built-in module. No external ORM like SQLAlchemy is planned for the initial core system to maintain simplicity, but direct, secure SQL construction is paramount.
*   **Task Scheduling**:
    *   `APScheduler`: Version 3.9.x or later.
*   **Environment & Configuration Management**:
    *   `python-dotenv`: Latest stable version (for loading `.env` files).
    *   `pydantic`: Version 1.10.x or V2.x (as per project choice, see below). Used for `BaseSettings` in `core/config.py` and potentially for tool argument/API model validation.
*   **Code Quality & Formatting**:
    *   `Ruff`: Latest stable version (for linting and formatting, replacing Black, Flake8, isort). Project configuration will be in `pyproject.toml`.
*   **Testing**:
    *   `pytest`: Latest stable version (for all unit and integration tests).
    *   `pytest-cov`: For test coverage reporting.
    *   `pytest-mock`: For mocking dependencies in tests.
*   **Serialization/Validation (for Agent Tools & API models, if any)**:
    *   `Pydantic`: Current project usage in `core/config.py` uses `from pydantic import BaseSettings`. We will standardize on Pydantic **V2.x** for all new Pydantic usage (e.g., for tool arguments, API request/response models if any are built). This implies `core/config.py` should eventually be updated to use `from pydantic_settings import BaseSettings` to align with Pydantic V2 best practices for settings management. For now, new Pydantic models should use V2 features. `pip install "pydantic>=2.0.0"` and `pip install "pydantic-settings>=2.0.0"`.
*   **Security (Cryptography for token encryption)**:
    *   `cryptography`: Latest stable version (if implementing database-level encryption for OAuth tokens).

*(Note to AI: Specific versions will be formally pinned in `requirements.txt`. When generating code involving these libraries, adhere to the typical usage patterns and APIs for these versions. If a library offers multiple ways to achieve a task, prefer the most modern, idiomatic, and secure approach compatible with the specified versions.)*

## 3. Build, Dependency, and Environment Management

*   **Dependency Management**: `pip` with `requirements.txt` files. For development, a `requirements-dev.txt` may include testing and linting tools.
    *   We may explore `uv` as a faster alternative to `pip` later, but initial guidance should assume `pip`.
*   **Virtual Environments**: `venv` (Python's built-in module) is mandatory for local development.
*   **Containerization (for CUA & Deployment)**: Docker will be used for:
    *   Creating controlled, reproducible environments for CUA execution (e.g., a container with a browser and Playwright).
    *   Packaging the application for deployment.
    *   AI should be able to generate `Dockerfile` snippets if requested, based on project needs.

## 4. CI/CD Pipeline (Conceptual)

*   **Version Control**: Git, hosted on GitHub (or similar platform).
*   **Automation Server**: GitHub Actions (or similar, e.g., Jenkins, GitLab CI).
*   **Pipeline Stages**:
    1.  Linting and Formatting (Ruff).
    2.  Unit & Integration Tests (PyTest).
    3.  Code Coverage Check.
    4.  Build Docker Image.
    5.  (Future) Deployment to staging/production environments.

## 5. Environment-Specific Configurations

*   All sensitive configurations (API keys, secrets, database paths if not default) **MUST** be managed via environment variables.
*   The `core/config.py` module will be responsible for loading these variables using `python-dotenv` for local development and directly from the environment in deployed settings.
*   Distinct configurations may exist for `development`, `testing`, `staging`, and `production` environments. The AI should assume that environment-specific API endpoints or behaviors will be handled through these loaded configurations, not hardcoded.

## 6. Integration with External Services

*   **X (Twitter)**: Primary interaction via X API v2 and GUI/CUA.
*   **OpenAI**: For LLM access (GPT models) and Computer Use tool.
*   **Logging/Monitoring (Future Consideration)**: While not in the initial scope, we may integrate with services like Logfire, Sentry, or AgentOps. Generated code should use Python's standard `logging` module, which can be configured to pipe to such services later.

## 7. API Keys and Sensitive Credentials

*   **Storage**: NEVER hardcode API keys or secrets in the source code.
*   **Local Development**: Store in a `.env` file at the project root (this file **MUST BE** in `.gitignore`).
*   **Deployment**: Store as environment variables injected into the runtime environment (e.g., Docker environment variables, secrets management service).
*   **X OAuth Tokens**: Stored encrypted in the SQLite database (`x_oauth_tokens` table), with the encryption key itself managed as a secure environment variable.