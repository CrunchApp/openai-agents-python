### **The Plan: Refactoring CUA Interactions with Agent Handoffs**

This initiative will be executed in three phases to ensure a smooth transition and maintain system stability.

---

#### **Phase 1: Establish the CUA Handoff Framework**

The first step is to create the foundational components for a proper agent handoff, as recommended by the SDK documentation on handoffs.

1. Create a CuaTask Data Model: We need a structured way to pass tasks to the ComputerUseAgent. I will define a Pydantic model named CuaTask in a new file, core/models.py. This model will serve as the contract for our handoff, ensuring data is clear and validated. It will contain fields like prompt, start\_url, and max\_iterations.  
1. Refactor ComputerUseAgent: The existing ComputerUseAgent will be repurposed. Instead of being a self-contained entity with hardcoded instructions, it will become a specialized agent that accepts CuaTask objects. Its primary role will be to receive the handoff from the Orchestrator and initiate the CUA workflow.  
1. Introduce the Handoff Tool in OrchestratorAgent:  
* I will modify OrchestratorAgent to instantiate the ComputerUseAgent.  
* Using the SDK's handoff() function, I will create a new tool for the Orchestrator, named execute\_cua\_task.  
* This tool will be configured with input\_type=CuaTask, making the handoff explicit and structured. This single tool will replace the dozen or so CUA-related methods currently polluting the Orchestrator.

---

#### **Phase 2: Centralize the CUA Interaction Logic**

The complex while loop that manages the CUA conversation (sending prompts, handling actions, taking screenshots) is duplicated across many methods. This violates the DRY principle and makes maintenance difficult. We will centralize this logic.

1. Create CuaWorkflowRunner: I will create a new class, CuaWorkflowRunner, in core/cua\_workflow.py. This class will contain a single method, run\_workflow(task: CuaTask), which will encapsulate the entire CUA interaction loop that is currently repeated in OrchestratorAgent. This includes initializing LocalPlaywrightComputer, managing the conversation with the OpenAI responses API, and handling safety checks.  
1. Integrate with ComputerUseAgent: The refactored ComputerUseAgent will become much simpler. When it receives a CuaTask via handoff, it will delegate the entire execution to an instance of CuaWorkflowRunner. This aligns with the Single Responsibility Principle, where the ComputerUseAgent is the designated entry point for computer use tasks, and the CuaWorkflowRunner is the engine that executes them.

---

#### **Phase 3: Streamline the OrchestratorAgent**

With the framework in place, the final phase is to clean up the OrchestratorAgent and have it use the new, robust mechanism.

1. Deprecate Old Methods: All the public and private CUA methods in OrchestratorAgent (e.g., post\_tweet\_via\_cua, like\_tweet\_via\_cua, get\_home\_timeline\_tweets\_via\_cua, \_internal\_like\_via\_cua\_with\_params) will be removed.  
1. Update High-Level Workflows: The remaining strategic methods, like \_enhanced\_like\_tweet\_with\_memory, will be updated. Instead of calling internal CUA logic, they will now:  
* Generate the appropriate CUA prompt using the existing functions in core/cua\_instructions.py.  
* Construct a CuaTask object with the prompt and other parameters.  
* Call the new execute\_cua\_task tool to hand off the task to the ComputerUseAgent.  
1. Code Cleanup: I will remove the large number of now-unused imports from core.constants and other modules within project\_agents/orchestrator\_agent.py, resulting in a much cleaner and more focused agent definition.

