# OpenAI Agents SDK Fork: Critical Bug Resolution & Custom Logic Onboarding

## Overview

This document provides a comprehensive overview of the custom logic and modifications in our `src/agents/` fork of the OpenAI Agents SDK. Our implementation includes critical bug fixes, runtime detection improvements, and a complete Computer Use Agent (CUA) architecture that differs significantly from the upstream SDK.

## Critical Bug Resolution & SDK Fork Management

### 1. Async/Await Fix in `_run_impl.py`

**Location**: `src/agents/_run_impl.py` - `ComputerAction._get_screenshot_sync()` method (lines 867-914)

**Problem Resolved**: The upstream OpenAI Agents SDK had a critical issue where Computer actions were called but their results (which could be coroutines) were not being properly awaited, leading to potential runtime errors and inconsistent behavior.

**Solution Implemented**:
```python
# Before (upstream):
computer.click(action.x, action.y, action.button)

# After (our fix):
result = computer.click(action.x, action.y, action.button)
if asyncio.iscoroutine(result):
    await result
```

**Key Changes**:
- Added runtime detection for coroutines using `asyncio.iscoroutine(result)`
- Implemented proper awaiting of async computer operations
- Applied the fix to ALL computer actions: click, double_click, drag, keypress, move, screenshot, scroll, type, wait
- Enhanced the final screenshot capture with the same pattern

### 2. Runtime Detection in `_get_screenshot_sync`

**Enhancement**: The `_get_screenshot_sync` method now includes intelligent runtime detection that:
- Checks if computer method calls return coroutines
- Dynamically awaits them when necessary
- Provides compatibility between sync and async Computer implementations
- Ensures reliable operation regardless of the underlying Computer interface

**Technical Details**:
```python
async def _get_screenshot_sync(cls, computer: Computer, tool_call: ResponseComputerToolCall) -> str:
    # Execute the action with runtime coroutine detection
    result = computer.action_method(...)
    if asyncio.iscoroutine(result):
        await result
    
    # Handle screenshot with same pattern
    screenshot_result = computer.screenshot()
    if asyncio.iscoroutine(screenshot_result):
        return await screenshot_result
    return screenshot_result
```

### 3. Project Structure Fix

**Configuration**: Our project is configured to use the forked SDK via editable install:
```bash
pip install -e .
```

This ensures that any changes made to the `src/agents/` directory are immediately reflected in the runtime without requiring reinstallation.

## Computer Use Agent (CUA) Architecture

### 1. Custom Computer Environment Implementation

**Location**: `core/computer_env/`

Our fork includes a complete CUA implementation that's not present in the upstream SDK:

#### Base Interface (`core/computer_env/base.py`)
- **Computer**: Synchronous computer interface
- **AsyncComputer**: Asynchronous computer interface 
- **Environment**: Literal type for environment detection (`"mac" | "windows" | "ubuntu" | "browser"`)
- **Button**: Literal type for mouse buttons (`"left" | "right" | "wheel" | "back" | "forward"`)

#### Playwright Implementation (`core/computer_env/local_playwright_computer.py`)
**Key Features**:
- **Browser Automation**: Full Playwright integration for X.com interaction
- **Async Context Manager**: Proper resource management with `__aenter__` and `__aexit__`
- **Custom Key Mapping**: Maps CUA keys to Playwright keys (`_CUA_KEY_TO_PLAYWRIGHT_KEY`)
- **Screenshot Capture**: Base64-encoded PNG screenshots
- **Mouse Operations**: Click, double-click, drag, move with pixel-perfect precision
- **Keyboard Operations**: Type text and key combinations
- **Viewport Management**: Fixed 1024x768 dimensions for consistency

### 2. Computer Use Agent (`project_agents/computer_use_agent.py`)

**Model**: Uses OpenAI's `computer-use-preview` model specifically designed for computer control tasks
**Instructions**: Specialized for X platform interactions with step-by-step planning
**Tools**: Integrates with our custom `ComputerTool(computer=self.computer)`

### 3. Application Integration (`main.py`)

**CUA-First Approach**: The application has been refactored to prioritize CUA over traditional API calls:

```python
async with LocalPlaywrightComputer() as computer:
    cua_agent = ComputerUseAgent(computer=computer)
    result = await Runner.run(
        cua_agent,
        input="Navigate to x.com and take a screenshot of the main page."
    )
```

## Additional Key Customizations

### 1. Multi-Agent Architecture

**Specialized Agents** (all in `project_agents/`):
- **OrchestratorAgent** (7.1KB): Central coordination and task delegation
- **ComputerUseAgent** (1.5KB): Primary CUA for browser automation  
- **ContentCreationAgent** (3.0KB): Content generation and curation
- **XInteractionAgent** (1.3KB): X platform interaction coordination
- **SchedulingAgent** (3.5KB): Task scheduling and continuous operation

### 2. Core Infrastructure Extensions

**Database Management** (`core/db_manager.py`):
- SQLite operations with enhanced human review functionality
- Tables: `x_oauth_tokens`, `task_queue`, `agent_state`, `human_review_queue`

**OAuth Management** (`core/oauth_manager.py`):
- Fernet encryption/decryption for X API tokens
- PKCE OAuth 2.0 flow implementation

**Configuration** (`core/config.py`):
- Pydantic-based settings management
- Environment-specific configurations

### 3. Tool Suite

**X API Integration** (`tools/x_api_tools.py`):
- Direct `requests` implementation (bypasses Tweepy issues)
- Fallback mechanism for CUA operations
- Custom `XApiError` handling

**Human-in-the-Loop** (`tools/human_handoff_tool.py`):
- HIL workflow implementation for critical decisions
- Integration with CUA operations

### 4. Operational Scripts

**Management Utilities** (`scripts/`):
- `initialize_db.py`: Database schema setup
- `manual_approve_reply.py`: HIL approval workflow
- `temp_set_initial_tokens.py`: OAuth token configuration

### 5. Comprehensive Testing

**SDK Integration Tests**: 50+ test files covering all functionality
**CUA-Specific Testing**: `test_computer_action.py` for browser automation validation
**Project-Specific Tests**: `tests/core/`, `tests/agents/`, `tests/tools/`

## SDK Dispatch Logic

### Runtime Detection Pattern

Our fork implements a consistent pattern for handling both sync and async Computer implementations:

```python
# Pattern used throughout the codebase
result = computer.method(...)
if asyncio.iscoroutine(result):
    await result
```

This allows seamless integration between:
- Traditional sync Computer implementations (upstream compatibility)
- Our custom async Computer implementations (CUA functionality)

### Computer Tool Integration

**Location**: `src/agents/computer.py`
**Enhancement**: Our fork ensures that the `ComputerTool` properly integrates with both sync and async Computer interfaces through the runtime detection logic.

## Dependencies & Environment

### Key Dependencies Added
- **Playwright**: Browser automation engine for CUA
- **Fernet**: Encryption for sensitive data
- **APScheduler**: Task scheduling
- **Pydantic**: Configuration management

### Environment Variables
Our fork relies on extensive environment configuration for:
- X API credentials and OAuth settings
- Database configuration
- Logging levels
- CUA browser settings

## Known Differences from Upstream

### 1. Model Support
- **Added**: `computer-use-preview` model support for CUA
- **Enhanced**: Model settings with truncation strategies

### 2. Computer Interface
- **Upstream**: Basic Computer interface with limited implementation
- **Our Fork**: Complete Computer/AsyncComputer abstraction with Playwright implementation

### 3. Agent Architecture
- **Upstream**: Single-agent focused
- **Our Fork**: Multi-agent architecture with specialized roles

### 4. Error Handling
- **Enhanced**: Custom exceptions and comprehensive error recovery
- **Added**: CUA-specific error handling and browser session management

### 5. Testing Framework
- **Expanded**: Extensive test coverage for CUA operations
- **Added**: Integration tests for multi-agent workflows

## Development Guidelines

### 1. Maintaining the Fork
- Always test changes against both sync and async Computer implementations
- Ensure runtime detection patterns are preserved
- Validate CUA operations with comprehensive integration tests

### 2. Upstream Synchronization
- Be cautious when merging upstream changes to `src/agents/_run_impl.py`
- Our async/await fixes must be preserved
- Runtime detection logic is critical and must not be lost

### 3. Testing Requirements
- All CUA functionality must be tested with `LocalPlaywrightComputer`
- Integration tests should cover multi-agent workflows
- Performance tests for browser automation timing

## Troubleshooting Common Issues

### 1. Coroutine Not Awaited Errors
- Check that runtime detection is properly implemented
- Ensure `asyncio.iscoroutine()` checks are in place
- Validate that async Computer methods are properly defined

### 2. Browser Session Issues
- Verify Playwright installation and browser dependencies
- Check viewport settings and session persistence
- Monitor anti-detection strategies

### 3. Agent Coordination Issues
- Review orchestrator logic and task delegation
- Check database state management
- Validate HIL workflow integration

## Conclusion

This fork represents a significant enhancement over the upstream OpenAI Agents SDK, with critical bug fixes, a complete CUA architecture, and a production-ready multi-agent system. Understanding these customizations is essential for maintaining and extending the system while preserving its unique capabilities and reliability.

For questions or clarifications about specific implementations, refer to the memory bank documentation in the `memory-bank/` directory or consult the comprehensive test suite in `tests/`. 