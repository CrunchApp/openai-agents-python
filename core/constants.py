"""Constants for the X Agentic Unit project.

This file contains constants extracted from project_agents/orchestrator_agent.py to make the code more maintainable.

Extracted constants include:
- CUA (Computer Use Agent) configuration settings
- Timing and delay constants for UI interactions
- Screenshot analysis thresholds for error detection
- Response pattern constants for consistent messaging
- X.com keyboard shortcuts for browser automation
- Tool configurations for OpenAI API calls
- URL patterns and endpoints
- Unicode handling settings and emoji mappings

These constants help ensure consistency across the codebase and make configuration changes easier.
"""

from typing import Dict, List

# =============================================================================
# CUA (Computer Use Agent) Configuration Constants
# =============================================================================

# Display settings for CUA browser environment
CUA_DISPLAY_WIDTH = 1024
CUA_DISPLAY_HEIGHT = 768
CUA_ENVIRONMENT = "browser"

# CUA iteration limits for different workflows
CUA_MAX_ITERATIONS_DEFAULT = 30
CUA_MAX_ITERATIONS_REPLY = 25
CUA_MAX_ITERATIONS_LIKE = 20
CUA_MAX_ITERATIONS_ROBUST_TIMELINE = 40

# Screenshot analysis thresholds
SCREENSHOT_MIN_SIZE_THRESHOLD = 50000  # Bytes - below this indicates blank/problematic page
CONSECUTIVE_EMPTY_SCREENSHOT_LIMIT = 3

# Timing constants (milliseconds)
PAGE_NAVIGATION_TIMEOUT = 15000
PAGE_STABILIZATION_DELAY = 3000
UI_RESPONSE_DELAY = 2000
FOCUS_TRANSITION_DELAY = 1000
CLICK_RESPONSE_DELAY = 500
KEYPRESS_RESPONSE_DELAY = 300
SCROLL_RESPONSE_DELAY = 300
MOVE_RESPONSE_DELAY = 200

# Unicode handling
UNICODE_THRESHOLD = 127  # Characters above this are considered Unicode

# Logging text length limits
LOG_TEXT_SHORT = 50
LOG_TEXT_MEDIUM = 100
LOG_TEXT_LONG = 200
LOG_TEXT_EXTENDED = 300

# =============================================================================
# Model Configuration Constants
# =============================================================================

# OpenAI models
COMPUTER_USE_MODEL = "computer-use-preview"
ORCHESTRATOR_MODEL = "o4-mini"

# =============================================================================
# Response Pattern Constants
# =============================================================================

# Standard response prefixes
SUCCESS_PREFIX = "SUCCESS"
FAILED_PREFIX = "FAILED"
SESSION_INVALIDATED = "SESSION_INVALIDATED"
COMPLETED_PREFIX = "COMPLETED"

# CUA response format templates
CUA_RESPONSE_FORMATS = {
    "tweet_posted": "SUCCESS: Tweet posted successfully",
    "tweet_posted_emoji_escaped": "SUCCESS: Posted but emojis showed as escaped text",
    "reply_posted": "SUCCESS: Reply posted successfully", 
    "tweet_liked": "SUCCESS: Tweet liked successfully",
    "session_invalid": "SESSION_INVALIDATED",
    "navigation_failed": "FAILED: Could not navigate to {target}",
    "blank_timeline": "FAILED: Timeline appears blank or unresponsive",
    "extraction_failed": "FAILED: Could not extract tweet text",
    "max_iterations": "COMPLETED: CUA reached maximum iterations",
}

# =============================================================================
# X.com Keyboard Shortcuts
# =============================================================================

# Navigation shortcuts
X_SHORTCUT_HELP = "?"
X_SHORTCUT_NEXT_POST = "j"
X_SHORTCUT_PREV_POST = "k"
X_SHORTCUT_PAGE_DOWN = "Space"
X_SHORTCUT_LOAD_NEW = "."
X_SHORTCUT_HOME = ["g", "h"]
X_SHORTCUT_NOTIFICATIONS = ["g", "n"]
X_SHORTCUT_PROFILE = ["g", "p"]

# Action shortcuts
X_SHORTCUT_COMPOSE = "n"
X_SHORTCUT_SEND_POST = ["Ctrl", "Shift", "Enter"]
X_SHORTCUT_LIKE = "l"
X_SHORTCUT_REPLY = "r"
X_SHORTCUT_ENTER = "Enter"

# Media shortcuts
X_MEDIA_SHORTCUTS = {
    "pause_play": "k",
    "pause_play_alt": "Space",
    "mute_video": "m",
    "audio_dock": ["a", "d"],
    "audio_play_pause": ["a", "Space"],
    "audio_mute": ["a", "m"],
}

# =============================================================================
# CUA System Instructions Template
# =============================================================================

CUA_SYSTEM_INSTRUCTIONS = """You are an AI assistant that can control a computer browser to perform tasks on web pages, specifically for interacting with the X (Twitter) platform. Describe your plan step-by-step. Then, use the provided computer tool to execute actions like clicking, typing, scrolling, and taking screenshots to achieve the user's goal. Analyze screenshots to determine next steps.

🎯 CRITICAL: URL NAVIGATION STRATEGY
To navigate to a specific URL:
1. **Click on the browser's address bar** (usually at the top of the page)
2. **Select all existing text** in the address bar (Ctrl+A or triple-click)
3. **Type the complete URL** you want to navigate to
4. **Press Enter** to navigate to the URL
5. **Wait for the page to load** before taking further actions
Example: To go to https://x.com/username/status/123, click address bar, type the URL, press Enter
DO NOT use any 'navigate' action - it doesn't exist. Use click, type, and keypress actions!

🎯 CRITICAL: KEYBOARD-FIRST INTERACTION STRATEGY
ALWAYS prioritize keyboard shortcuts over mouse clicks when interacting with X.com. Keyboard shortcuts are more reliable, faster, and less prone to UI changes. Only use mouse clicks when absolutely necessary (e.g., no keyboard equivalent exists).

📋 X.COM KEYBOARD SHORTCUTS (USE THESE FIRST):

🧭 NAVIGATION SHORTCUTS:
• '?' - Show keyboard shortcuts help
• 'j' - Next post (move down timeline)
• 'k' - Previous post (move up timeline)
• 'Space' - Page down / Scroll down
• '.' - Load new posts at top
• 'g + h' - Go to Home timeline
• 'g + e' - Go to Explore page
• 'g + n' - Go to Notifications
• 'g + r' - Go to Mentions
• 'g + p' - Go to Profile
• 'g + f' - Go to Drafts
• 'g + t' - Go to Scheduled posts
• 'g + l' - Go to Likes
• 'g + i' - Go to Lists
• 'g + m' - Go to Direct Messages
• 'g + g' - Go to Grok
• 'g + s' - Go to Settings
• 'g + b' - Go to Bookmarks
• 'g + u' - Go to user profile (when available)
• 'g + d' - Go to Display settings

⚡ ACTION SHORTCUTS:
• 'n' - Create new post (compose tweet)
• 'Ctrl + Enter' OR 'Cmd + Enter' - Send post
• 'Ctrl + Shift + Enter' OR 'Cmd + Shift + Enter' - Send post (alternative)
• 'l' - Like selected post
• 'r' - Reply to selected post
• 't' - Repost selected post
• 's' - Share selected post
• 'b' - Bookmark selected post
• 'u' - Mute account
• 'x' - Block account
• 'Enter' - Open post details
• 'o' - Expand photo in selected post
• 'i' - Open/Close Messages dock
• '/' - Search (focus search box)

🎬 MEDIA SHORTCUTS:
• 'k' - Pause/Play selected Video
• 'Space' - Pause/Play selected Video (alternative)
• 'm' - Mute selected Video
• 'a + d' - Go to Audio Dock
• 'a + Space' - Play/Pause Audio Dock
• 'a + m' - Mute/Unmute Audio Dock

🎯 KEYBOARD-FIRST WORKFLOW EXAMPLES:

📝 POSTING A TWEET:
1. Press 'n' to open compose area (don't click the compose button)
2. Type your tweet text directly
3. Use 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post
4. Avoid clicking the 'Post' button unless keyboard shortcut fails

👀 BROWSING TIMELINE:
1. Use 'j' and 'k' to navigate between posts (don't scroll with mouse)
2. Use 'l' to like posts (don't click heart icon)
3. Use 'r' to reply (don't click reply icon)
4. Use 't' to repost (don't click repost icon)

🔍 NAVIGATION:
1. Use 'g + h' for Home (don't click Home button)
2. Use 'g + n' for Notifications (don't click Notifications)
3. Use 'g + p' for Profile (don't click Profile)
4. Use '/' for Search (don't click search box)

⚠️ WHEN TO USE MOUSE CLICKS:
Only resort to mouse clicks when:
• No keyboard shortcut exists for the specific action
• You need to interact with dynamic content (embedded media, links within posts)
• Keyboard shortcuts are confirmed to be non-functional
• Dealing with modal dialogs or popups without keyboard alternatives

🔧 IMPLEMENTATION STRATEGY:
1. **Take Screenshot**: Always start by capturing current state
2. **Identify Task**: Determine what needs to be accomplished
3. **Choose Keyboard First**: Look for applicable keyboard shortcuts from the list above
4. **Execute Keyboard Action**: Use keypress() function with appropriate keys
5. **Verify Success**: Take another screenshot to confirm action worked
6. **Fallback to Mouse**: Only if keyboard approach fails, use click() as backup
7. **Document Approach**: Clearly state which method you used and why

COOKIE CONSENT HANDLING:
When encountering cookie consent banners on x.com or twitter.com, you MUST handle them autonomously to ensure operational continuity. Follow this priority order:
1. If options like 'Refuse non-essential cookies', 'Reject all', 'Decline', or similar privacy-focused options are present, you MUST choose that option.
2. If only 'Accept all cookies', 'Accept', 'Agree', or similar acceptance options are available, you may choose that to proceed with the task.
3. Do NOT ask for confirmation when handling standard cookie consent banners - this is a routine operational requirement for accessing the platform.
4. After dismissing the cookie banner, continue with your original task.

SESSION AUTHENTICATION DETECTION:
You may be operating with either an authenticated or unauthenticated browser session:
1. **Authenticated Session**: If you can access user-specific pages (notifications, settings, profile pages) without being redirected to login, you are in an authenticated session.
2. **Unauthenticated Session**: If you encounter login forms, 'Sign In' buttons, or are redirected to login pages when trying to access authenticated features, the session is invalid.
3. **Session Invalidation Handling**: If you detect a logged-out state during task execution:
   - IMMEDIATELY abort the current task
   - Take a screenshot of the login page for documentation
   - Report in your response: 'SESSION_INVALIDATED: Browser session is no longer authenticated. Manual re-authentication required.'
   - DO NOT attempt to log in or enter credentials
   - DO NOT continue with the original task

Always prioritize user privacy and platform compliance while maintaining task execution flow. Remember: KEYBOARD SHORTCUTS FIRST, mouse clicks only as a last resort!"""

# =============================================================================
# Emoji Mapping for CUA Unicode Handling
# =============================================================================

EMOJI_MAPPINGS = {
    '🚀': '[rocket emoji]',
    '✅': '[checkmark emoji]', 
    '❌': '[X emoji]',
    '🎯': '[target emoji]',
    '🔧': '[wrench emoji]',
    '📋': '[clipboard emoji]',
    '🎬': '[movie camera emoji]',
    '⚡': '[lightning emoji]',
    '🧭': '[compass emoji]',
    '💡': '[light bulb emoji]',
    '🔥': '[fire emoji]',
    '👍': '[thumbs up emoji]',
    '👎': '[thumbs down emoji]',
    '💯': '[hundred points emoji]',
    '🤔': '[thinking face emoji]',
    '😊': '[smiling face emoji]',
    '😎': '[cool face emoji]',
    '🙌': '[raised hands emoji]',
    '💪': '[flexed biceps emoji]',
    '🎉': '[party popper emoji]',
}

# =============================================================================
# CUA Tool Configuration
# =============================================================================

CUA_TOOL_CONFIG = {
    "type": "computer_use_preview",
    "display_width": CUA_DISPLAY_WIDTH,
    "display_height": CUA_DISPLAY_HEIGHT,
    "environment": CUA_ENVIRONMENT,
}

# =============================================================================
# Common Error Recovery Instructions
# =============================================================================

CUA_RESET_INSTRUCTIONS = """🔄 RESET INSTRUCTION:
If you get stuck, confused, or in an unexpected UI state at ANY step:
1. Press 'ESC' key to close any modals or cancel current actions
2. Wait 1 second for UI to stabilize
3. Take a screenshot to see current state
4. Start over from the appropriate step"""

CUA_ERROR_RECOVERY = """🚨 ERROR RECOVERY:
- If stuck in compose area: Press ESC to close, start over
- If wrong page loads: Press ESC, then use 'g+h' to go to home
- If shortcuts don't work: Use mouse clicks as backup
- If emojis appear as escaped text: Report this in your response"""

# =============================================================================
# URL Patterns and Endpoints
# =============================================================================

X_HOME_URL = "https://x.com/home"
X_BASE_URL = "https://x.com"

# Regular expression pattern for extracting tweet IDs from URLs
TWEET_URL_PATTERN = r'/status/(\d+)'

# =============================================================================
# Text Processing Constants
# =============================================================================

# String parsing constants
TEXT_PARSING_START_MARKER = "text='"
TEXT_PARSING_QUOTE_OFFSET = 6

# Image data URL constants
IMAGE_DATA_URL_PREFIX = "data:image/png;base64"

# Viewport displacement detection
VIEWPORT_DISPLACEMENT_RATIO_THRESHOLD = 0.3

# Page reload timing
PAGE_RELOAD_WAIT_SECONDS = 3

# Default tweet counts
DEFAULT_TIMELINE_TWEET_COUNT = 3

# =============================================================================
# Logging Constants  
# =============================================================================

# Logging text slicing limits (extended)
LOG_TEXT_ULTRA_SHORT = 20
LOG_TEXT_ULTRA_LONG = 500

# =============================================================================
# API Response Type Constants
# =============================================================================

# OpenAI API response output types
RESPONSE_TYPE_COMPUTER_CALL = "computer_call"
RESPONSE_TYPE_TEXT = "text"
RESPONSE_TYPE_MESSAGE = "message"
RESPONSE_TYPE_REASONING = "reasoning"

# OpenAI API input parameters
API_TRUNCATION_AUTO = "auto"
API_ROLE_SYSTEM = "system"
API_ROLE_USER = "user"

# API response content types
CONTENT_TYPE_COMPUTER_CALL_OUTPUT = "computer_call_output"
CONTENT_TYPE_INPUT_IMAGE = "input_image"

# Safety check response fields
SAFETY_CHECK_ID = "id"
SAFETY_CHECK_CODE = "code"
SAFETY_CHECK_MESSAGE = "message"

# =============================================================================
# Response Message Templates
# =============================================================================

# Common response prefixes (extended from basic ones)
SUCCESS_MESSAGE_TWEET_POSTED = "SUCCESS: Tweet posted successfully (from reasoning)"
SUCCESS_MESSAGE_REPLY_POSTED = "SUCCESS: Reply posted successfully (from reasoning)"
SUCCESS_MESSAGE_TWEET_LIKED = "SUCCESS: Tweet liked successfully (from reasoning)"
SUCCESS_MESSAGE_TWEETS_EXTRACTED = "SUCCESS: Tweets extracted successfully (from reasoning)"

# Completion messages
COMPLETED_CUA_WORKFLOW = "COMPLETED: CUA workflow finished"
COMPLETED_CUA_TWEET_REPLY_WORKFLOW = "COMPLETED: CUA tweet reply workflow finished"
COMPLETED_CUA_TWEET_LIKING_WORKFLOW = "COMPLETED: CUA tweet liking workflow finished"
COMPLETED_CUA_ITERATIONS = "COMPLETED: CUA reached maximum iterations"

# Numeric constants for text slicing in responses
RESPONSE_TEXT_SLICE_SHORT = 200
RESPONSE_TEXT_SLICE_MEDIUM = 300

# =============================================================================
# Additional Response Constants for Remaining Hardcoded Values
# =============================================================================

# String literal constants for message checking
SUCCESS_STRING_LITERAL = "SUCCESS"
FAILED_STRING_LITERAL = "FAILED"
SESSION_INVALIDATED_STRING_LITERAL = "SESSION_INVALIDATED"
COMPLETED_STRING_LITERAL = "COMPLETED"

# Additional completion messages
COMPLETED_CUA_WORKFLOW_TEXT = "COMPLETED: CUA workflow finished"
SUCCESS_REPLY_POSTED_FROM_REASONING = "SUCCESS: Reply posted successfully (from reasoning)"
COMPLETED_CUA_TIMELINE_WORKFLOW = "COMPLETED: CUA timeline workflow finished"
SUCCESS_TWEET_LIKED_FROM_REASONING = "SUCCESS: Tweet liked successfully (from reasoning)"

# Additional workflow completion messages
COMPLETED_CUA_TWEET_LIKING_WORKFLOW_TEXT = "COMPLETED: CUA tweet liking workflow finished"

# Additional response messages for specific workflows
COMPLETED_CUA_LATEST_TWEET_READING = "COMPLETED: CUA latest tweet reading workflow finished"
SUCCESS_MESSAGE_TWEET_TEXT_EXTRACTED = "SUCCESS: Tweet text extracted successfully (from reasoning)"

# Hardcoded response format strings that should use constants
RESPONSE_SUCCESS_PATTERNS = ["SUCCESS", "COMPLETED"]
RESPONSE_FAILURE_PATTERNS = ["FAILED", "SESSION_INVALIDATED"]

# Text parsing constants for message extraction
TEXT_PARSING_QUOTE_START = "text='"
TEXT_PARSING_QUOTE_END = "'" 