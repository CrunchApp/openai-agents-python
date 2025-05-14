# Rule Hierarchy: Autonomous X Agentic Unit

## 1. Purpose

This document defines the order of precedence for applying project-specific rules (.mdc files within the `.cursor/` directory structure) when the Cursor AI agent is assisting with development. It also outlines guiding principles for resolving ambiguities or conflicts between rules. The AI **MUST** consult this hierarchy when multiple rules seem applicable or contradictory.

## 2. Order of Precedence (Highest to Lowest)

1.  **Security First (CUA & API Security Rules)**:
    *   Any rule within `cua.mdc` or `api.mdc` explicitly addressing security vulnerabilities, safe data handling, authentication, authorization, or prevention of malicious actions (e.g., input sanitization, restricted file access for CUA, secure API key management) takes **ABSOLUTE PRECEDENCE** over any other conflicting rule.
    *   *Rationale*: Ensuring the security and integrity of the system, user data, and X account access is paramount and non-negotiable.

2.  **Project-Specific Implementation Rules (for Forked SDK Components)**:
    *   Rules within `cua.mdc`, `db.mdc`, `api.mdc`, or other files that define how to use or extend **project-specific modifications or custom classes within our forked OpenAI Agents SDK** (e.g., custom `AsyncComputer` extensions, specific handoff mechanisms, unique tool structures) take precedence over general SDK knowledge or more generic coding standards if there's a direct conflict regarding the implementation of these custom components.
    *   *Rationale*: The project's specific way of implementing or extending the forked SDK is the source of truth.

3.  **Contextual / Nested Rules (Auto Attached)**:
    *   Rules located in nested `.cursor/rules/` subdirectories (e.g., `agents/.cursor/rules/agent_definition.mdc`, `tools/gui/.cursor/rules/playwright_best_practices.mdc`) that are `Auto Attached` based on file paths, take precedence over more general rules (like `general.mdc` or `api.mdc`) for the specific files or modules they cover, unless the conflicting general rule is explicitly higher in this hierarchy (e.g., a security rule).
    *   *Rationale*: Contextual rules provide more specific guidance for particular areas of the codebase.

4.  **Specialized Domain Rules (API, DB, CUA Functional Rules)**:
    *   Functional and structural rules defined in `api.mdc` (for API design), `db.mdc` (for database schema and querying), and `cua.mdc` (for CUA operational logic, excluding top-priority security rules) take precedence over general coding standards when guiding the specific implementation within those domains.
    *   *Rationale*: These domains have specific best practices and project conventions that are more targeted than general style guides.

5.  **General Project-Wide Rules (`general.mdc`)**:
    *   Core coding standards, style guides (PEP 8, naming conventions), AI interaction guidelines, testing requirements, and general best practices defined in `general.mdc` apply broadly across the project. They are superseded by higher-priority rules in specific contexts.
    *   *Rationale*: Provides a consistent baseline for all code.

6.  **Agent Requested Rules (AI's Discretion)**:
    *   Rules designated as `Agent Requested` are applied based on the AI's understanding of their relevance (guided by their description). Their effective precedence is determined by the context in which the AI chooses to apply them, but they should not override explicit `Always` or `Auto Attached` rules that are higher in this hierarchy.
    *   *Rationale*: Allows for complex, situational guidance without cluttering every prompt.

7.  **Manual Rules (@ruleName in chat)**:
    *   Rules explicitly invoked by a developer in a chat prompt using `@ruleName` are intended for specific, ad-hoc guidance or to temporarily override default behavior for that particular interaction. They should be used judiciously and do not alter this established hierarchy for general AI operation.
    *   *Rationale*: Provides flexibility for specific scenarios or experimentation.

## 3. Guiding Principles for Conflict Resolution & Ambiguity

When rules appear to conflict and the Order of Precedence above does not provide an immediate, clear resolution, or if a rule is ambiguous, apply the following guiding principles:

1.  **Prioritize Project Values**:
    *   **Security First**: If ambiguity exists, choose the interpretation that maximizes security and minimizes risk.
    *   **Simplicity and Readability**: Prefer solutions that are simpler to understand, implement, and maintain, even if slightly less performant (unless performance is explicitly a critical requirement for the specific task).
    *   **Robustness and Reliability**: Favor approaches that enhance system stability and fault tolerance.
    *   **Adherence to X Platform Policies**: Ensure interpretations do not lead to violations of X Developer Agreement and Policy.
    (These values will also be reflected in `general.mdc`).

2.  **Favor Specificity**: A more specific rule generally overrides a more general one if they are at the same effective hierarchical level after considering context.

3.  **Least Harm Principle**: If an action prescribed by a rule seems potentially harmful or could lead to unintended negative consequences (e.g., data loss, security vulnerability not explicitly covered by a higher-priority rule), err on the side of caution. The AI should flag this concern and ask for human developer clarification.

## 4. Escalation for Unresolved Conflicts

*   If, after applying the Order of Precedence and Guiding Principles, a rule conflict remains genuinely irresolvable or a rule's application in a specific context is dangerously ambiguous, the Cursor AI agent **MUST**:
    1.  State the identified conflict or ambiguity clearly to the human developer.
    2.  Reference the specific rules involved (e.g., "Rule X in `general.mdc` suggests A, while Rule Y in `api.mdc` suggests B for this API response structure.").
    3.  Explicitly ask the developer for clarification on which approach to take or how to interpret the rule in the current context.
    4.  **DO NOT** proceed with an arbitrary choice if significant conflict or safety concerns exist.

*(Note to AI: This hierarchy is critical for consistent and predictable behavior. When in doubt, refer back to these principles or escalate to the developer.)*