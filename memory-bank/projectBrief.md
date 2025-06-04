# Project Brief: Autonomous X Agentic Unit

## 1. Overall Project Objectives

The "X Agentic Unit Project" aims to develop a sophisticated, autonomous agent capable of managing an X (formerly Twitter) account with a comprehensive suite of actions, mirroring human user capabilities. This Unit will be built upon a forked version of the OpenAI Agents SDK, leveraging its primitives (Agents, Tools, Handoffs, Guardrails) to create a robust, modular, and continuously operating system.

A core strategic objective is to ensure the long-term viability and cost-effectiveness of X platform interactions through a **CUA-first approach**. This involves prioritizing Computer Use Agent (CUA) and browser automation as the primary interaction method, with X API v2 serving as a complementary fallback system. This strategic approach directly addresses the escalating costs, restrictive rate limits, and policy uncertainties associated with direct X API usage while providing complete platform feature access.

The project will deliver an agent exhibiting hybrid autonomy, allowing for human-in-the-loop (HIL) intervention for critical decisions and content approval, thereby balancing automation efficiency with necessary oversight and control.

## 2. Scope

### In-Scope:

*   **Core Agentic System**:
    *   Development of a multi-agent architecture (Orchestrator, Content Creation, X Interaction, Computer Use, Analysis, Profile Management, Scheduling Agents) using the forked OpenAI Agents SDK.
    *   **Primary CUA Implementation**: Comprehensive Computer Use Agent using Playwright for browser-based X platform automation, providing full feature access and cost optimization.
    *   **Complementary API Tools**: Implementation of tools for interacting with the X platform via X API v2 as fallback mechanisms and for specific data retrieval tasks.
    *   Capabilities for a wide range of X user actions: content posting (tweets, threads, polls), replies, direct messaging (sending/receiving), engagement (likes, retweets), user interaction management (follow/unfollow, block), profile updates (text, images via CUA), and information retrieval (timelines, search, mentions).
    *   Continuous, 24/7 operation facilitated by robust task scheduling (APScheduler) with CUA session management.
*   **Computer Use & GUI Automation**:
    *   **Primary Integration**: OpenAI's "Computer Use" tool with custom `LocalPlaywrightComputer` implementation for comprehensive X platform automation.
    *   **Browser Environment Management**: Controlled browser automation with anti-detection strategies, session persistence, and authentication management.
    *   **Screenshot Analysis**: CUA-driven screenshot capture and analysis for workflow verification and cross-agent coordination.
*   **Operational Robustness**:
    *   Secure credential management for X API (OAuth 2.0 PKCE) and OpenAI APIs, with browser session authentication via CUA.
    *   Persistent data storage (SQLite) for agent state, configurations, task queues, OAuth tokens, operational logs, and browser session data.
    *   Comprehensive error handling, retry mechanisms, and rate limit management (for API) or interaction throttling (for CUA).
    *   Implementation of input/output guardrails for safe and policy-compliant agent behavior.
    *   Human-in-the-Loop (HIL) mechanisms for content approval, CUA action verification, and critical decisions.
*   **Development & Documentation**:
    *   Modular and maintainable Python codebase with CUA-API hybrid architecture.
    *   Comprehensive project-specific Cursor rules and memory bank documentation (this initiative).
    *   Internal technical documentation for custom SDK extensions, agent designs, and operational procedures.

### Out-of-Scope (for initial delivery unless explicitly prioritized later):

*   Management of accounts on social media platforms other than X.
*   Advanced Natural Language Processing (NLP) capabilities beyond those provided by underlying OpenAI LLMs (e.g., custom sentiment analysis models will use LLMs, not be built from scratch).
*   A sophisticated, standalone graphical user interface for HIL interactions (initial HIL will rely on simpler mechanisms like database flags or CLI tools).
*   Dynamic, on-the-fly learning or self-modification of core agent instructions beyond LLM prompt adaptations.
*   Direct integration with enterprise-level analytics platforms (initial analytics will be self-contained or logged for external processing).

## 3. Key Deliverables

1.  **Functional X Agentic Unit**: A deployable system capable of autonomously managing a designated X account via CUA-first automation.
2.  **Specialized Agent Modules**: Well-defined Python modules for each specialized agent (Orchestrator, Content Creation, X Interaction, CUA, Analysis, Profile Management, Scheduling).
3.  **CUA Infrastructure**: Complete Computer Use Agent implementation with `LocalPlaywrightComputer`, browser session management, and screenshot analysis capabilities.
4.  **Hybrid Interaction Toolset**: A library of CUA tools for browser automation and complementary X API v2 tools for fallback scenarios.
5.  **Data Persistence Layer**: SQLite database schema and access modules for storing all necessary operational data including browser session management.
6.  **Task Scheduling System**: Integrated APScheduler for managing continuous and scheduled agent tasks with CUA operation timing considerations.
7.  **Hybrid Autonomy Framework**: Implemented HIL workflows and triggers for human oversight of both CUA and API operations.
8.  **CUA Operations & Maintenance Plan**: Comprehensive monitoring scripts, anti-detection strategies, and maintenance procedures for sustained browser automation.
9.  **Cursor AI Configuration**: This full set of project-specific rules and memory bank files.
10. **Internal Technical Documentation**: Wiki pages or documents detailing the architecture, setup, and operation of the X Agentic Unit and any SDK customizations.

## 4. Success Metrics

1.  **Functionality**: Agent successfully performs >90% of defined X user actions across content creation, engagement, DM handling, and profile management categories via CUA within 6 months of core system deployment.
2.  **Autonomy & Reliability**:
    *   Core scheduled tasks (e.g., CUA-based mention checking, scheduled posts) achieve >98% successful execution rate over a 30-day period.
    *   The system demonstrates stable, continuous operation for at least 72-hour unattended periods during testing phases.
    *   CUA operations achieve >85% success rate for primary X platform interactions.
3.  **Efficiency & Cost-Effectiveness**:
    *   **CUA Cost Optimization**: Demonstrate >50% reduction in projected costs for X interaction workflows compared to using equivalent X API Pro/Enterprise tier pricing within 3 months of CUA deployment.
    *   **Operational Efficiency**: CUA-based workflows complete core X interactions within acceptable time frames (e.g., posting within 30 seconds, navigation within 15 seconds).
4.  **Hybrid Control Effectiveness**: HIL mechanism triggers correctly for 100% of predefined sensitive actions, with streamlined approval processes for both CUA and API operations.
5.  **Policy Compliance**: Zero account suspensions or warnings from X due to policy violations related to automation, CUA detection, or API usage over a 6-month operational period.
6.  **Maintainability**: New CUA interaction patterns and API tools can be developed and integrated by a developer (with AI assistance) within an average of 3 days for moderately complex interactions.
7.  **CUA Operational Viability**: CUA operations demonstrate >80% success rate for target tasks on the X live interface over a 2-week operational period, with documented maintenance procedures for UI change adaptation.

## 5. Strategic Rationale for CUA-First Approach

The prioritization of Computer Use Agent implementation addresses critical challenges in X platform automation:

*   **Cost Sustainability**: Browser automation eliminates API usage costs for routine interactions while maintaining full platform access.
*   **Feature Completeness**: CUA provides access to all X platform features, including those not available through API endpoints.
*   **Future-Proofing**: Reduces dependency on X API policy changes and pricing modifications that could impact long-term viability.
*   **Operational Resilience**: Provides alternative interaction pathways when API access is restricted or unavailable.
*   **Enhanced Capabilities**: Enables advanced interactions like visual content analysis, complex UI navigation, and real-time platform adaptation.

This CUA-first strategy, combined with strategic API fallback capabilities, ensures robust, cost-effective, and comprehensive X platform automation for sustainable long-term operation.