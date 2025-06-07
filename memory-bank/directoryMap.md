

# Repository Structure Map: X Agentic Unit (OpenAI Agents SDK Fork)

## Overview
This is a comprehensive mapping of the key directories in our forked OpenAI Agents SDK repository, customized for building the X Agentic Unit project. The structure follows a **CUA-first architecture** (Computer Use Agent) with API fallback capabilities for comprehensive X (Twitter) platform automation.

---

## 1. 📁 `core/` - Core Infrastructure & Utilities

```
core/
├── __pycache__/                    # Python bytecode cache
├── computer_env/                   # CUA Environment Management
│   ├── __pycache__/
│   ├── base.py                     # Base computer interface definitions
│   ├── local_playwright_computer.py # Primary CUA implementation with Playwright
│   └── __init__.py
├── config.py                       # Environment configuration management
├── db_manager.py                   # SQLite database operations (9.7KB)
├── oauth_manager.py                # X API OAuth 2.0 PKCE token management
└── scheduler_setup.py              # APScheduler configuration for continuous operation
```

**Key Components:**
- **`computer_env/`**: Contains the primary CUA implementation using Playwright for browser automation
- **`db_manager.py`**: Centralized database operations for agent state, OAuth tokens, task queues
- **`oauth_manager.py`**: Handles X API authentication with token refresh capabilities
- **`config.py`**: Loads environment variables and configuration settings

---

## 2. 📁 `examples/` - SDK Examples & Learning Resources

```
examples/
├── __init__.py
├── agent_patterns/                 # Advanced agent design patterns
│   ├── agents_as_tools.py
│   ├── deterministic.py
│   ├── forcing_tool_use.py
│   ├── llm_as_a_judge.py
│   ├── input_guardrails.py
│   ├── output_guardrails.py
│   ├── parallelization.py
│   ├── routing.py
│   ├── streaming_guardrails.py
│   └── README.md
├── basic/                          # Fundamental SDK usage examples
│   ├── hello_world.py
│   ├── hello_world_jupyter.py
│   ├── dynamic_system_prompt.py
│   ├── agent_lifecycle_example.py
│   ├── lifecycle_example.py
│   ├── local_image.py
│   ├── non_strict_output_type.py
│   ├── remote_image.py
│   ├── previous_response_id.py
│   ├── stream_items.py
│   ├── stream_text.py
│   ├── tools.py
│   └── media/
├── customer_service/               # Customer service agent example
│   └── main.py
├── financial_research_agent/       # Complex multi-agent system example
│   ├── agents/
│   ├── main.py
│   ├── manager.py
│   ├── printer.py
│   ├── README.md
│   └── __init__.py
├── handoffs/                       # Agent-to-agent handoff examples
│   ├── message_filter.py
│   └── message_filter_streaming.py
├── mcp/                           # Model Context Protocol examples
│   ├── filesystem_example/
│   ├── git_example/
│   └── sse_example/
├── model_providers/               # Different LLM provider integrations
├── research_bot/                  # Research agent implementation
├── tools/                         # Tool implementation examples
│   ├── computer_use.py            # CUA tool examples
│   ├── file_search.py
│   └── web_search.py
└── voice/                         # Voice interaction examples
```

**Key Learning Areas:**
- **`agent_patterns/`**: Advanced patterns for our multi-agent architecture
- **`tools/computer_use.py`**: Reference implementation for CUA integration
- **`financial_research_agent/`**: Multi-agent coordination patterns applicable to our X Agentic Unit

---

## 3. 📁 `project_agents/` - X Agentic Unit Specialized Agents

```
project_agents/
├── __pycache__/
├── __init__.py
├── computer_use_agent.py           # Primary CUA for browser automation (1.5KB)
├── content_creation_agent.py       # Content generation and curation (3.0KB)
├── orchestrator_agent.py           # Central coordination and task delegation (7.1KB)
├── scheduling_agent.py             # Task scheduling and continuous operation (3.5KB)
└── x_interaction_agent.py          # X platform interaction coordination (1.3KB)
```

**Agent Responsibilities:**
- **`orchestrator_agent.py`**: Central command center, delegates tasks to specialized agents
- **`computer_use_agent.py`**: Browser automation for X platform interactions
- **`content_creation_agent.py`**: Tweet creation, reply generation, content analysis
- **`x_interaction_agent.py`**: Coordinates between CUA and API-based interactions
- **`scheduling_agent.py`**: Manages continuous 24/7 operation and task scheduling

---

## 4. 📁 `scripts/` - Operational & Maintenance Scripts

```
scripts/
├── __pycache__/
├── initialize_db.py                # Database schema initialization (638B)
├── manual_approve_reply.py         # HIL approval workflow (2.3KB)
└── temp_set_initial_tokens.py      # OAuth token setup utility (1.5KB)
```

**Script Functions:**
- **`initialize_db.py`**: Sets up SQLite database schema for agent operations
- **`manual_approve_reply.py`**: Human-in-the-loop content approval mechanism
- **`temp_set_initial_tokens.py`**: Initial X API OAuth token configuration

---

## 5. 📁 `src/` - OpenAI Agents SDK Core Implementation

```
src/
└── agents/                         # Main SDK implementation
    ├── __pycache__/
    ├── __init__.py                 # SDK public API (7.0KB)
    ├── _config.py                  # Internal configuration
    ├── _debug.py                   # Debug utilities
    ├── _run_impl.py                # Core agent execution logic (34KB)
    ├── agent.py                    # Base agent class (11KB)
    ├── agent_output.py             # Agent response handling
    ├── computer.py                 # Computer use interface (2.6KB)
    ├── exceptions.py               # SDK exception definitions
    ├── function_schema.py          # Tool function schema generation (13KB)
    ├── guardrail.py                # Input/output guardrails (9.4KB)
    ├── handoffs.py                 # Agent handoff mechanisms (9.1KB)
    ├── items.py                    # Message and item processing
    ├── lifecycle.py                # Agent lifecycle management
    ├── logger.py                   # Logging utilities
    ├── model_settings.py           # LLM model configuration
    ├── py.typed                    # Type checking marker
    ├── result.py                   # Result processing and validation
    ├── run.py                      # Main agent runner (40KB)
    ├── run_context.py              # Execution context management
    ├── strict_schema.py            # Schema validation
    ├── stream_events.py            # Streaming event handling
    ├── tool.py                     # Tool definition and execution (12KB)
    ├── usage.py                    # Usage tracking
    ├── version.py                  # Version information
    ├── extensions/                 # SDK extensions
    ├── mcp/                        # Model Context Protocol
    ├── models/                     # LLM provider implementations
    │   ├── __pycache__/
    │   ├── __init__.py
    │   ├── _openai_shared.py
    │   ├── chatcmpl_converter.py   # Chat completion conversion (18KB)
    │   ├── chatcmpl_helpers.py
    │   ├── chatcmpl_stream_handler.py
    │   ├── fake_id.py
    │   ├── interface.py            # Model provider interface
    │   ├── multi_provider.py       # Multiple LLM provider support
    │   ├── openai_chatcompletions.py
    │   ├── openai_provider.py
    │   └── openai_responses.py     # OpenAI Responses API integration (14KB)
    ├── tracing/                    # Agent execution tracing
    ├── util/                       # Utility functions
    └── voice/                      # Voice interaction support
```

**Critical SDK Components:**
- **`computer.py`**: Computer use interface for CUA operations
- **`models/openai_responses.py`**: Responses API integration for advanced agent capabilities
- **`guardrail.py`**: Input/output validation for safe operation
- **`handoffs.py`**: Agent-to-agent task delegation mechanisms

---

## 6. 📁 `tests/` - Comprehensive Test Suite

```
tests/
├── __pycache__/
├── __init__.py
├── conftest.py                     # PyTest configuration
├── fake_model.py                   # Mock model for testing
├── testing_processor.py           # Test processing utilities
├── README.md                       # Testing documentation
├── agents/                         # Project agent tests
│   ├── __pycache__/
│   ├── __init__.py
│   ├── test_agents.py              # General agent tests
│   ├── test_content_creation_agent.py
│   ├── test_orchestrator_agent.py  # Core orchestration tests (14KB)
│   └── test_scheduling_agent.py    # Scheduling logic tests (5.6KB)
├── core/                          # Core infrastructure tests
│   ├── __pycache__/
│   ├── __init__.py
│   ├── test_config.py              # Configuration tests
│   ├── test_db_manager.py          # Database operation tests (4.9KB)
│   └── test_oauth_manager.py       # OAuth flow tests (8.7KB)
├── tools/                         # Tool implementation tests
│   ├── __pycache__/
│   ├── __init__.py
│   ├── test_human_handoff_tool.py
│   └── test_x_api_tools.py         # X API tool tests (9.0KB)
├── [SDK Tests]                    # Extensive SDK test suite
│   ├── test_agent_config.py
│   ├── test_agent_runner.py       # Core runner tests (23KB)
│   ├── test_computer_action.py    # CUA action tests (12KB)
│   ├── test_function_schema.py    # Tool schema tests (15KB)
│   ├── test_guardrails.py         # Guardrail validation tests
│   ├── test_handoff_tool.py       # Handoff mechanism tests
│   └── [40+ additional test files]
└── [Additional Test Directories]
    ├── fastapi/                   # FastAPI integration tests
    ├── mcp/                       # MCP protocol tests
    ├── models/                    # LLM provider tests
    ├── tracing/                   # Execution tracing tests
    ├── voice/                     # Voice interaction tests
    └── tools/                     # General tool tests
```

**Test Coverage:**
- **Project-specific tests**: Agent behavior, database operations, X API integration
- **SDK tests**: Comprehensive coverage of all SDK functionality
- **CUA tests**: Computer use action validation and browser automation testing

---

## 7. 📁 `memory-bank/` - Project Documentation & Context

```
memory-bank/
├── activeContext.md               # Current development state and active tasks
├── directoryMap.md               # This file - repository structure mapping
├── productContext.md             # User needs and business context
├── progress.md                   # Historical milestones and completed work
├── projectBlueprint.md           # Updated roadmap and implementation structure
├── projectBrief.md               # High-level overview, goals, and scope
├── ruleHierarchy.md              # Memory bank rule precedence and organization
├── systemPatterns.md             # Architectural patterns and design decisions
└── techContext.md                # Technical stack, dependencies, and environment
```

**Memory Bank Functions:**
- **`activeContext.md`**: Current sprint status, active debugging efforts, and immediate tasks
- **`progress.md`**: Historical record of completed phases, milestones, and achievements
- **`systemPatterns.md`**: Architectural decisions, CUA patterns, and multi-agent coordination
- **`techContext.md`**: Technology stack, dependencies, and implementation requirements
- **`projectBrief.md`**: High-level project goals, scope, and strategic objectives
- **`productContext.md`**: Business context, user needs, and product rationale

---

## 8. 📁 `tools/` - Agent Tool Implementations

```
tools/
├── __pycache__/
├── __init__.py                     # Tool exports
├── human_handoff_tool.py           # HIL workflow implementation (2.2KB)
└── x_api_tools.py                  # X API v2 integration tools (5.0KB)
```

**Tool Functions:**
- **`x_api_tools.py`**: X API v2 tools for fallback scenarios and data retrieval
- **`human_handoff_tool.py`**: Human-in-the-loop approval and intervention mechanisms

---

## 9. Architecture Summary

This repository structure supports our **CUA-first architecture** with the following key design patterns:

### 🎯 **Multi-Agent Coordination**
- `project_agents/` contains specialized agents working in concert
- `src/agents/handoffs.py` enables seamless agent-to-agent task delegation

### 🖥️ **Computer Use Agent (CUA) Primary**
- `core/computer_env/` provides the foundation for browser automation
- `examples/tools/computer_use.py` offers reference implementations
- `tests/test_computer_action.py` ensures CUA reliability

### 🔄 **Hybrid Interaction Strategy**
- `tools/x_api_tools.py` provides API fallback capabilities
- CUA handles primary X platform interactions via browser automation
- API tools serve as complementary data retrieval and fallback mechanisms

### 🛡️ **Robust Operation**
- `core/db_manager.py` and `core/oauth_manager.py` handle persistent state and authentication
- `tests/` directory ensures comprehensive coverage with 50+ test files
- `scripts/` provide operational utilities for maintenance and setup

### 🔧 **Development & Testing**
- `examples/` directory provides learning resources and implementation patterns
- Extensive test suite covers both project-specific and SDK functionality
- Memory bank documentation ensures consistent development practices

This structure aligns perfectly with our strategic goal of building a sophisticated, autonomous X Agentic Unit that prioritizes cost-effective browser automation while maintaining robust API fallback capabilities for comprehensive X platform management.
