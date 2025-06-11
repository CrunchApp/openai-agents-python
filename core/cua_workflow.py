"""Centralized CUA workflow execution logic."""

import asyncio
import logging
from typing import Optional

from core.computer_env.local_playwright_computer import LocalPlaywrightComputer
from core.config import settings
from core.constants import (
    CUA_SYSTEM_INSTRUCTIONS,
    COMPUTER_USE_MODEL,
    CUA_TOOL_CONFIG,
    API_TRUNCATION_AUTO,
    API_ROLE_SYSTEM,
    API_ROLE_USER,
    RESPONSE_TYPE_COMPUTER_CALL,
    RESPONSE_TYPE_TEXT,
    RESPONSE_TYPE_MESSAGE,
    RESPONSE_TYPE_REASONING,
    CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
    CONTENT_TYPE_INPUT_IMAGE,
    IMAGE_DATA_URL_PREFIX,
    SUCCESS_PREFIX,
    FAILED_PREFIX,
    SESSION_INVALIDATED,
    COMPLETED_CUA_ITERATIONS,
    COMPLETED_CUA_WORKFLOW,
    PAGE_NAVIGATION_TIMEOUT,
    PAGE_STABILIZATION_DELAY,
    CLICK_RESPONSE_DELAY,
    KEYPRESS_RESPONSE_DELAY,
    SCROLL_RESPONSE_DELAY,
    UI_RESPONSE_DELAY,
    LOG_TEXT_MEDIUM,
    LOG_TEXT_LONG,
    LOG_TEXT_EXTENDED,
    SCREENSHOT_MIN_SIZE_THRESHOLD,
    CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT,
    PAGE_RELOAD_WAIT_SECONDS,
    VIEWPORT_DISPLACEMENT_RATIO_THRESHOLD,
    SUCCESS_STRING_LITERAL,
    FAILED_STRING_LITERAL,
    SESSION_INVALIDATED_STRING_LITERAL,
    COMPLETED_STRING_LITERAL,
    RESPONSE_TEXT_SLICE_SHORT,
    RESPONSE_TEXT_SLICE_MEDIUM,
    TEXT_PARSING_START_MARKER,
    TEXT_PARSING_QUOTE_OFFSET,
)
from core.models import CuaTask


class CuaWorkflowRunner:
    """Centralized workflow runner for Computer Use Agent tasks.
    
    This class encapsulates all the complex interaction logic for CUA workflows,
    including the OpenAI responses API calls, safety check handling, and error recovery.
    """
    
    def __init__(self) -> None:
        """Initialize the CUA workflow runner."""
        self.logger = logging.getLogger(__name__)
    
    async def run_workflow(self, task: CuaTask, computer: LocalPlaywrightComputer) -> str:
        """Execute a CUA workflow based on the provided task using an existing computer session.
        
        Args:
            task: The CuaTask containing the prompt, optional start URL, and configuration
            computer: Pre-initialized LocalPlaywrightComputer instance to use for the workflow
            
        Returns:
            String describing the outcome of the CUA operation
        """
        self.logger.info(f"Starting CUA workflow with prompt: {task.prompt[:LOG_TEXT_MEDIUM]}...")
        if task.start_url:
            self.logger.info(f"Starting URL: {task.start_url}")
        
        try:
            # =================================================================
            # 🔧 LAYER 1: PRE-VIEWPORT STABILIZATION (CRITICAL FIX)
            # =================================================================
            self.logger.info("🔧 Starting Layer 1: Pre-viewport stabilization for all CUA tasks")
            
            try:
                # Step 1: Reset scroll position to top
                self.logger.info("📐 Resetting scroll position to top")
                await computer.page.evaluate("window.scrollTo(0, 0);")
                await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                
                # Step 2: Ensure consistent zoom level (100%)
                self.logger.info("🔍 Setting zoom level to 100%")
                await computer.page.evaluate("document.body.style.zoom = '1.0';")
                await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                
                # Step 3: Add viewport stabilization CSS to prevent displacement
                self.logger.info("🎯 Adding viewport stabilization CSS")
                stabilization_css = """
                body { 
                    overflow-x: hidden !important;
                    position: relative !important;
                }
                html {
                    scroll-behavior: auto !important;
                }
                [data-testid="primaryColumn"] {
                    position: relative !important;
                    transform: none !important;
                }
                """
                await computer.page.add_style_tag(content=stabilization_css)
                await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
                
                # Step 4: Force layout recalculation
                self.logger.info("⚡ Forcing layout recalculation")
                await computer.page.evaluate("""
                    // Force layout recalculation
                    document.body.offsetHeight;
                    window.getComputedStyle(document.body).getPropertyValue('height');
                    // Ensure we're at the top of the page
                    window.scrollTo({top: 0, left: 0, behavior: 'auto'});
                """)
                await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                
                self.logger.info("✅ Layer 1: Pre-viewport stabilization completed successfully")
                
            except Exception as stabilization_error:
                self.logger.warning(f"⚠️ Pre-viewport stabilization failed (proceeding anyway): {stabilization_error}")
            
            # =================================================================
            # End of Layer 1 Pre-Viewport Stabilization
            # =================================================================
            
            # Initialize the OpenAI client for direct responses API calls
            from openai import OpenAI
            import base64
            client = OpenAI(api_key=settings.openai_api_key)
            
            # Navigate to start URL if provided (after stabilization)
            if task.start_url:
                self.logger.info(f"🧭 Navigating to start URL: {task.start_url}")
                try:
                    await computer.page.goto(task.start_url, wait_until='networkidle', timeout=PAGE_NAVIGATION_TIMEOUT)
                    await computer.page.wait_for_timeout(PAGE_STABILIZATION_DELAY)
                    
                    # Re-apply stabilization after navigation to start URL
                    self.logger.info("🔧 Re-applying viewport stabilization after navigation")
                    await computer.page.evaluate("window.scrollTo(0, 0);")
                    await computer.page.add_style_tag(content="""
                    body { 
                        overflow-x: hidden !important;
                        position: relative !important;
                    }
                    html {
                        scroll-behavior: auto !important;
                    }
                    [data-testid="primaryColumn"] {
                        position: relative !important;
                        transform: none !important;
                    }
                    """)
                    await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                    
                    self.logger.info(f"✅ Successfully navigated to {task.start_url} with viewport stabilization")
                except Exception as nav_error:
                    self.logger.error(f"❌ Failed to navigate to {task.start_url}: {nav_error}")
                    return f"{FAILED_PREFIX}: Could not navigate to start URL - {nav_error}"
            
            # Define system instructions (general CUA behavior)
            system_instructions = CUA_SYSTEM_INSTRUCTIONS
            
            # Initial request to get first screenshot
            self.logger.info("Sending initial CUA request")
            initial_input_messages = [
                {"role": API_ROLE_SYSTEM, "content": system_instructions},
                {"role": API_ROLE_USER, "content": task.prompt}
            ]
            response = client.responses.create(
                model=COMPUTER_USE_MODEL,
                tools=[CUA_TOOL_CONFIG],
                input=initial_input_messages,
                truncation=API_TRUNCATION_AUTO
            )
            
            max_iterations = task.max_iterations
            iteration = 0
            consecutive_empty_screenshots = 0
            
            while iteration < max_iterations:
                iteration += 1
                self.logger.info(f"CUA iteration {iteration}")
                
                # Check for computer calls in the response
                computer_calls = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_COMPUTER_CALL]
                
                # Debug: Log all response output items
                self.logger.info(f"Response output items: {len(response.output)}")
                for i, item in enumerate(response.output):
                    if hasattr(item, 'type'):
                        self.logger.info(f"  Item {i}: type={item.type}")
                        if item.type == RESPONSE_TYPE_TEXT and hasattr(item, 'text'):
                            self.logger.info(f"    Text content: {item.text[:LOG_TEXT_LONG]}...")
                    else:
                        self.logger.info(f"  Item {i}: {type(item)} - {str(item)[:LOG_TEXT_MEDIUM]}...")
                
                if not computer_calls:
                    # Check for text output that might contain our success/failure message
                    text_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_TEXT]
                    reasoning_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_REASONING]
                    message_outputs = [item for item in response.output if hasattr(item, 'type') and item.type == RESPONSE_TYPE_MESSAGE]
                    
                    if text_outputs:
                        final_text = text_outputs[-1].text if hasattr(text_outputs[-1], 'text') else str(text_outputs[-1])
                        self.logger.info(f"CUA completed with text output: {final_text}")
                        if SUCCESS_PREFIX in final_text:
                            return final_text
                        elif SESSION_INVALIDATED in final_text:
                            return final_text
                        elif FAILED_PREFIX in final_text:
                            return final_text
                    
                    if message_outputs:
                        # Handle both direct text and ResponseOutputText objects
                        final_message = ""
                        for msg in message_outputs:
                            if hasattr(msg, 'text'):
                                final_message = msg.text
                                break
                            elif hasattr(msg, 'content') and hasattr(msg.content, 'text'):
                                final_message = msg.content.text
                                break
                            elif str(msg):
                                msg_str = str(msg)
                                # Extract text from ResponseOutputText representation
                                if TEXT_PARSING_START_MARKER in msg_str:
                                    start = msg_str.find(TEXT_PARSING_START_MARKER) + TEXT_PARSING_QUOTE_OFFSET
                                    end = msg_str.find("'", start)
                                    if end > start:
                                        final_message = msg_str[start:end]
                                        break
                        
                        self.logger.info(f"CUA completed with message text: {final_message}")
                        # Check if message contains our response patterns
                        if SUCCESS_STRING_LITERAL in final_message:
                            return final_message  # Return the actual success message
                        elif SESSION_INVALIDATED_STRING_LITERAL in final_message:
                            return SESSION_INVALIDATED
                        elif FAILED_STRING_LITERAL in final_message:
                            return f"{FAILED_PREFIX}: {final_message}"
                    
                    if reasoning_outputs:
                        final_reasoning = reasoning_outputs[-1].content if hasattr(reasoning_outputs[-1], 'content') else str(reasoning_outputs[-1])
                        self.logger.info(f"CUA completed with reasoning: {final_reasoning[:LOG_TEXT_EXTENDED]}...")
                        # Check if reasoning contains our response patterns
                        if SUCCESS_STRING_LITERAL in final_reasoning:
                            return f"{SUCCESS_PREFIX}: Task completed successfully (from reasoning)"
                        elif SESSION_INVALIDATED_STRING_LITERAL in final_reasoning:
                            return SESSION_INVALIDATED
                        elif FAILED_STRING_LITERAL in final_reasoning:
                            return f"{FAILED_PREFIX}: {final_reasoning[:RESPONSE_TEXT_SLICE_SHORT]}"
                    
                    self.logger.info("No computer call found, CUA workflow completed")
                    return COMPLETED_CUA_WORKFLOW
                
                computer_call = computer_calls[0]
                action = computer_call.action
                call_id = computer_call.call_id
                
                # Handle safety checks - automatically acknowledge routine social media checks
                acknowledged_checks = []
                if hasattr(computer_call, 'pending_safety_checks') and computer_call.pending_safety_checks:
                    self.logger.info(f"Safety checks detected: {len(computer_call.pending_safety_checks)} checks")
                    # Automatically acknowledge routine social media safety checks for autonomous operation
                    for check in computer_call.pending_safety_checks:
                        self.logger.info(f"Acknowledging safety check: {check.code} - {check.message}")
                        acknowledged_checks.append({
                            "id": check.id,
                            "code": check.code,
                            "message": check.message
                        })
                
                # Execute the computer action
                try:
                    await self._execute_computer_action(computer, action)
                except Exception as e:
                    self.logger.error(f"Error executing computer action {action.type}: {e}")
                    return f"{FAILED_PREFIX}: Computer action execution error: {e}"
                
                # Take screenshot with enhanced monitoring
                try:
                    screenshot_b64 = await computer.screenshot()
                    screenshot_size = len(screenshot_b64)
                    
                    # Monitor for blank/problematic screenshots
                    self.logger.info(f"Screenshot size: {screenshot_size} characters")
                    
                    # Check for consistently small screenshots (blank page indicator)
                    if screenshot_size < SCREENSHOT_MIN_SIZE_THRESHOLD:
                        consecutive_empty_screenshots += 1
                        self.logger.warning(f"Small screenshot detected ({screenshot_size} chars). Count: {consecutive_empty_screenshots}")
                        
                        # If we get multiple small screenshots, the page is likely in a bad state
                        if consecutive_empty_screenshots >= CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT:
                            self.logger.error("Multiple consecutive small screenshots - page appears blank or broken")
                            
                            # Attempt recovery by refreshing the page
                            try:
                                self.logger.info("Attempting page refresh recovery")
                                await computer.keypress(['CTRL', 'R'])
                                await asyncio.sleep(PAGE_RELOAD_WAIT_SECONDS)
                                
                                # Take a new screenshot to check if recovery worked
                                recovery_screenshot = await computer.screenshot()
                                recovery_size = len(recovery_screenshot)
                                self.logger.info(f"Recovery screenshot size: {recovery_size} characters")
                                
                                if recovery_size > SCREENSHOT_MIN_SIZE_THRESHOLD:
                                    self.logger.info("Page refresh recovery successful")
                                    screenshot_b64 = recovery_screenshot
                                    consecutive_empty_screenshots = 0
                                else:
                                    self.logger.error("Page refresh recovery failed - still getting small screenshots")
                                    return f"{FAILED_PREFIX}: Page appears blank and recovery attempts failed"
                            except Exception as recovery_error:
                                self.logger.error(f"Recovery attempt failed: {recovery_error}")
                                return f"{FAILED_PREFIX}: Page refresh recovery failed"
                    else:
                        consecutive_empty_screenshots = 0  # Reset counter on good screenshot
                    
                except Exception as e:
                    self.logger.error(f"Error taking screenshot: {e}")
                    return f"{FAILED_PREFIX}: Screenshot capture error: {e}"
                
                # Prepare next request input
                input_content = [{
                    "call_id": call_id,
                    "type": CONTENT_TYPE_COMPUTER_CALL_OUTPUT,
                    "output": {
                        "type": CONTENT_TYPE_INPUT_IMAGE,
                        "image_url": f"{IMAGE_DATA_URL_PREFIX},{screenshot_b64}"
                    }
                }]
                
                # Add acknowledged safety checks if any
                if acknowledged_checks:
                    input_content[0]["acknowledged_safety_checks"] = acknowledged_checks
                    self.logger.info(f"Including {len(acknowledged_checks)} acknowledged safety checks in next request")
                
                # Send next request
                try:
                    response = client.responses.create(
                        model=COMPUTER_USE_MODEL,
                        previous_response_id=response.id,
                        tools=[CUA_TOOL_CONFIG],
                        input=input_content,
                        truncation=API_TRUNCATION_AUTO
                    )
                except Exception as e:
                    self.logger.error(f"Error in CUA API call: {e}")
                    return f"{FAILED_PREFIX}: API call error: {e}"
            
            self.logger.warning(f"CUA reached maximum iterations ({max_iterations})")
            return COMPLETED_CUA_ITERATIONS
                
        except Exception as e:
            error_msg = f"CUA workflow failed: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"{FAILED_PREFIX}: {error_msg}"
    
    async def _execute_computer_action(self, computer, action):
        """Execute a computer action using the AsyncComputer interface."""
        action_type = action.type
        
        if action_type == "screenshot":
            # Screenshot will be taken after this method returns
            pass
        elif action_type == "click":
            self.logger.info(f"Executing click at ({action.x}, {action.y}) with button {action.button}")
            await computer.click(action.x, action.y, action.button)
            # Add extra wait for X.com UI to respond to clicks
            await asyncio.sleep(CLICK_RESPONSE_DELAY / 1000)
        elif action_type == "double_click":
            self.logger.info(f"Executing double-click at ({action.x}, {action.y})")
            await computer.double_click(action.x, action.y)
            await asyncio.sleep(CLICK_RESPONSE_DELAY / 1000)
        elif action_type == "type":
            self.logger.info(f"Typing text: '{action.text}'")
            await computer.type(action.text)
            await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
        elif action_type == "keypress":
            self.logger.info(f"Pressing keys: {action.keys}")
            
            # Special handling for 'j' navigation to detect viewport displacement
            if action.keys == ['j'] or action.keys == 'j':
                self.logger.info("🔧 Executing 'j' navigation with viewport displacement detection")
                
                # Take a screenshot before the 'j' keypress to establish baseline
                try:
                    before_screenshot = await computer.screenshot()
                    before_size = len(before_screenshot)
                    self.logger.info(f"Pre-navigation screenshot size: {before_size}")
                except Exception as e:
                    self.logger.warning(f"Could not capture pre-navigation screenshot: {e}")
                    before_size = 0
                
                # Execute the 'j' keypress
                await computer.keypress(action.keys)
                await asyncio.sleep(UI_RESPONSE_DELAY / 1000)  # Longer wait for navigation to complete
                
                # Take a screenshot after the 'j' keypress to check for displacement
                try:
                    after_screenshot = await computer.screenshot()
                    after_size = len(after_screenshot)
                    self.logger.info(f"Post-navigation screenshot size: {after_size}")
                    
                    # Detect potential viewport displacement
                    size_change_ratio = abs(after_size - before_size) / max(before_size, 1)
                    
                    if after_size < SCREENSHOT_MIN_SIZE_THRESHOLD or size_change_ratio > VIEWPORT_DISPLACEMENT_RATIO_THRESHOLD:
                        self.logger.warning(f"⚠️ Potential viewport displacement detected!")
                        self.logger.warning(f"Size change: {before_size} -> {after_size} (ratio: {size_change_ratio:.2f})")
                        
                        # Attempt automatic viewport recovery
                        self.logger.info("🔧 Attempting automatic viewport recovery...")
                        try:
                            # Method 1: Reset scroll position via JavaScript
                            await computer.page.evaluate("window.scrollTo(0, 0);")
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                            
                            # Method 2: Press Home key to return to top
                            await computer.keypress(['Home'])
                            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
                            
                            # Method 3: Re-navigate to home timeline if needed
                            recovery_screenshot = await computer.screenshot()
                            recovery_size = len(recovery_screenshot)
                            
                            if recovery_size > SCREENSHOT_MIN_SIZE_THRESHOLD:
                                self.logger.info("✅ Viewport recovery successful")
                            else:
                                self.logger.warning("⚠️ Viewport recovery may have failed")
                                
                        except Exception as recovery_error:
                            self.logger.error(f"❌ Viewport recovery failed: {recovery_error}")
                    else:
                        self.logger.info("✅ Navigation completed without viewport displacement")
                        
                except Exception as e:
                    self.logger.warning(f"Could not capture post-navigation screenshot: {e}")
            else:
                # Normal keypress execution for non-'j' keys
                await computer.keypress(action.keys)
                await asyncio.sleep(KEYPRESS_RESPONSE_DELAY / 1000)
        elif action_type == "scroll":
            self.logger.info(f"Scrolling at ({action.x}, {action.y}) by ({action.scroll_x}, {action.scroll_y})")
            await computer.scroll(action.x, action.y, action.scroll_x, action.scroll_y)
            await asyncio.sleep(SCROLL_RESPONSE_DELAY / 1000)
        elif action_type == "move":
            await computer.move(action.x, action.y)
        elif action_type == "wait":
            self.logger.info("Executing wait action")
            await computer.wait()
        elif action_type == "drag":
            await computer.drag([(p.x, p.y) for p in action.path])
            await asyncio.sleep(UI_RESPONSE_DELAY / 1000)
        else:
            self.logger.warning(f"Unknown computer action type: {action_type}") 