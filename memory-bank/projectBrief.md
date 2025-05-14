# Project Brief: Autonomous X Agentic Unit

## 1. Overall Project Objectives

The "X Agentic Unit Project" aims to develop a sophisticated, autonomous agent capable of managing an X (formerly Twitter) account with a comprehensive suite of actions, mirroring human user capabilities. This Unit will be built upon a forked version of the OpenAI Agents SDK, leveraging its primitives (Agents, Tools, Handoffs, Guardrails) to create a robust, modular, and continuously operating system.

A core strategic objective is to ensure the long-term viability and cost-effectiveness of X platform interactions. This involves an initial design accommodating X API v2, but with a strong emphasis on exploring, piloting, and potentially migrating key functionalities towards Computer Use Agent (CUA) and traditional GUI automation solutions. This strategic pivot addresses the escalating costs, restrictive rate limits, and policy uncertainties associated with direct X API usage.

The project will deliver an agent exhibiting hybrid autonomy, allowing for human-in-the-loop (HIL) intervention for critical decisions and content approval, thereby balancing automation efficiency with necessary oversight and control.

## 2. Scope

### In-Scope:

*   **Core Agentic System**:
    *   Development of a multi-agent architecture (Orchestrator, Content Creation, X Interaction, Computer Use, Analysis, Profile Management, Scheduling Agents) using the forked OpenAI Agents SDK.
    *   Implementation of tools for interacting with the X platform, initially via X API v2 and progressively via CUA/GUI automation for selected features.
    *   Capabilities for a wide range of X user actions: content posting (tweets, threads, polls), replies, direct messaging (sending/receiving), engagement (likes, retweets), user interaction management (follow/unfollow, block), profile updates (text, images via CUA), and information retrieval (timelines, search, mentions).
    *   Continuous, 24/7 operation facilitated by robust task scheduling (APScheduler).
*   **Computer Use & GUI Automation**:
    *   Integration of OpenAI's "Computer Use" tool (or equivalent custom CUA mechanisms) for UI-based X interactions not well-covered or cost-prohibitive via API (e.g., certain profile image updates, navigating complex UI elements).
    *   Pilot projects and phased rollout of traditional GUI automation (e.g., using Playwright) for high-volume or cost-sensitive X interactions, including development of anti-detection strategies.
*   **Operational Robustness**:
    *   Secure credential management for X API (OAuth 2.0 PKCE) and OpenAI APIs.
    *   Persistent data storage (SQLite) for agent state, configurations, task queues, OAuth tokens, and operational logs.
    *   Comprehensive error handling, retry mechanisms, and rate limit management (for API) or interaction throttling (for GUI).
    *   Implementation of input/output guardrails for safe and policy-compliant agent behavior.
    *   Human-in-the-Loop (HIL) mechanisms for content approval and critical decisions.
*   **Development & Documentation**:
    *   Modular and maintainable Python codebase.
    *   Comprehensive project-specific Cursor rules and memory bank documentation (this initiative).
    *   Internal technical documentation for custom SDK extensions, agent designs, and operational procedures.

### Out-of-Scope (for initial delivery unless explicitly prioritized later):

*   Management of accounts on social media platforms other than X.
*   Advanced Natural Language Processing (NLP) capabilities beyond those provided by underlying OpenAI LLMs (e.g., custom sentiment analysis models will use LLMs, not be built from scratch).
*   A sophisticated, standalone graphical user interface for HIL interactions (initial HIL will rely on simpler mechanisms like database flags or CLI tools).
*   Dynamic, on-the-fly learning or self-modification of core agent instructions beyond LLM prompt adaptations.
*   Direct integration with enterprise-level analytics platforms (initial analytics will be self-contained or logged for external processing).

## 3. Key Deliverables

1.  **Functional X Agentic Unit**: A deployable system capable of autonomously managing a designated X account.
2.  **Specialized Agent Modules**: Well-defined Python modules for each specialized agent (Orchestrator, Content Creation, X Interaction, CUA, Analysis, Profile Management, Scheduling).
3.  **Interaction Toolset**: A library of reusable tools for X API v2 calls and CUA/GUI-driven X interactions.
4.  **Data Persistence Layer**: SQLite database schema and access modules for storing all necessary operational data.
5.  **Task Scheduling System**: Integrated APScheduler for managing continuous and scheduled agent tasks.
6.  **Hybrid Autonomy Framework**: Implemented HIL workflows and triggers for human oversight.
7.  **CUA/GUI Automation PoCs & Migrated Features**: Demonstrable proof-of-concepts for CUA/GUI automation on X, and selected features migrated to these methods.
8.  **Monitoring & Maintenance Plan for GUI Automation**: If GUI automation is adopted, basic monitoring scripts and a documented maintenance strategy.
9.  **Cursor AI Configuration**: This full set of project-specific rules and memory bank files.
10. **Internal Technical Documentation**: Wiki pages or documents detailing the architecture, setup, and operation of the X Agentic Unit and any SDK customizations.

## 4. Success Metrics

1.  **Functionality**: Agent successfully performs >90% of defined X user actions across content creation, engagement, DM handling, and profile management categories within 6 months of core system deployment.
2.  **Autonomy & Reliability**:
    *   Core scheduled tasks (e.g., mention checking, scheduled posts) achieve >98% successful execution rate over a 30-day period.
    *   The system demonstrates stable, continuous operation for at least 72-hour unattended periods during testing phases.
3.  **Efficiency & Cost-Effectiveness**:
    *   If X API usage is maintained for certain functions: Operate within the cost budget of a designated X API tier (e.g., Pro tier, or demonstrate significant feature capability on Basic/Free tiers through selective API use).
    *   If migrating to CUA/GUI: Demonstrate a >30% reduction in projected costs for specific X interaction workflows compared to using equivalent X API Pro/Enterprise tier pricing, within 3 months of migrating those workflows.
4.  **Hybrid Control Effectiveness**: HIL mechanism triggers correctly for 100% of predefined sensitive actions, with a straightforward process for human review and action.
5.  **Policy Compliance**: Zero account suspensions or warnings from X due to policy violations related to automation or API usage over a 6-month operational period.
6.  **Maintainability**: New X interaction tools can be developed and integrated by a developer (with AI assistance) within an average of X story points (to be defined, e.g., <3 days for a moderately complex API wrapper).
7.  **GUI Automation Viability (if pursued)**: CUA/GUI PoCs demonstrate a >70% success rate for their target tasks on the X live interface over a 1-week test period, with a documented average time-to-fix for breakages due to UI changes.