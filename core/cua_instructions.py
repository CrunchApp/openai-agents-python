"""CUA (Computer Use Agent) system instructions and templates for X.com interactions.

This file contains reusable CUA instruction templates extracted from project_agents/orchestrator_agent.py.

The system instructions provide comprehensive guidance for browser automation on X.com including:
- URL navigation strategies
- Keyboard-first interaction patterns  
- X.com keyboard shortcuts reference
- Cookie consent and session handling
- Error recovery procedures

Template functions generate task-specific prompts for common CUA workflows:
- Tweet posting
- Tweet replies
- Tweet liking  
- Timeline reading

These templates help ensure consistent CUA behavior across different use cases.
"""

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
# Common CUA Instruction Templates
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

CUA_UNICODE_HANDLING_INSTRUCTIONS = """⚠️ IMPORTANT UNICODE HANDLING:
The content contains emojis that must be typed as Unicode characters.
Type the EXACT text provided, including all emoji characters.
If you see escaped sequences like \\\\ud83d\\\\ude80, you are typing incorrectly."""

# =============================================================================
# CUA Response Format Templates
# =============================================================================

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
    "composer_failed": "FAILED: Could not open reply composer",
    "focus_failed": "FAILED: Could not focus text input",
    "send_failed": "FAILED: Could not send reply",
    "like_failed": "FAILED: Could not like tweet",
}

# =============================================================================
# Task-Specific CUA Prompt Templates
# =============================================================================

def get_tweet_posting_prompt(tweet_text: str) -> str:
    """Generate CUA prompt for posting a tweet."""
    return f"""POST THIS TWEET EXACTLY: "{tweet_text}"

{CUA_UNICODE_HANDLING_INSTRUCTIONS}

{CUA_RESET_INSTRUCTIONS}

🎯 STEP-BY-STEP APPROACH:

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to understand your current page context.

STEP 2 - NAVIGATE TO COMPOSE:
Use the keyboard shortcut 'n' to open the compose area. This is faster than clicking.

STEP 3 - TYPE THE TWEET:
Type the EXACT text provided above. Include all emojis as Unicode characters.

STEP 4 - SEND TWEET:
Use keyboard shortcut 'Ctrl+Shift+Enter' (Windows) or 'Cmd+Shift+Enter' (Mac) to post.

STEP 5 - VERIFY SUCCESS:
After posting, take a screenshot to confirm the tweet was posted successfully.

{CUA_ERROR_RECOVERY}

RESPONSE FORMAT:
- Start your response with 'SUCCESS:' if the tweet was posted successfully
- Start with 'FAILED:' if any step failed
- Include 'SESSION_INVALIDATED' if login is required"""

def get_latest_tweet_reading_prompt() -> str:
    """Generate CUA prompt for reading the latest tweet from own profile."""
    return """Your task is to retrieve the full text content of the most recent tweet posted on your own X.com profile page. You are already logged in. Prioritize keyboard shortcuts. Follow these steps meticulously:

STEP 1 - INITIAL SCREENSHOT:
Take a screenshot to understand your current page context.

STEP 2 - NAVIGATE TO YOUR PROFILE:
Use the X.com keyboard shortcut to go to your profile: Press 'g' first, then immediately press 'p'. IMPORTANT: This is a two-key sequence (g then p) that should be executed quickly in succession, not as separate individual keystrokes with long pauses. You can use keypress(['g', 'p']) to execute this sequence.
Take a screenshot to confirm you are on your profile page. It should show your username, bio, and a list of your tweets.

STEP 3 - IDENTIFY LATEST TWEET:
Your tweets should be listed in reverse chronological order, with the latest one at the top. Focus on the first distinct tweet element in the main feed/timeline area of your profile.
Take a screenshot highlighting or focusing on what you identify as the latest tweet's main text area.

STEP 4 - EXTRACT TWEET TEXT:
Carefully extract ALL the visible text content from this latest tweet. Ensure you capture the full text, including any hashtags or links if they are part of the tweet's body. Be precise.
Do NOT extract timestamps, like/reply/repost counts, or author names unless they are part of the tweet's main text itself.

STEP 5 - FINAL RESPONSE:
Based on your actions and observations, your final response MUST be in one of these formats:
   - 'SUCCESS: Extracted latest tweet text: "[The full extracted text of the tweet]"'
   - 'FAILED: Could not navigate to profile page. Current page appears to be [describe page or state reason].'
   - 'FAILED: Profile page loaded, but no tweets were found.'
   - 'FAILED: Found latest tweet, but could not reliably extract its text content. [Optionally, describe the issue, e.g., text was an image, or UI was too complex].'
   - 'SESSION_INVALIDATED' (if you encounter a login screen at any point).

IMPORTANT GUIDELINES:
- Prioritize keyboard actions. Use 'j'/'k' if needed to focus on the first tweet after profile navigation, but usually, the latest is immediately visible.
- If cookie banners appear, dismiss them first as per your general instructions.
- Take screenshots between major steps to help you (and for debugging).
- Do NOT ask for confirmation; proceed autonomously.
- For the g+p navigation shortcut, ensure you execute it as a quick sequence: keypress(['g', 'p'])."""

def get_robust_timeline_reading_prompt(num_tweets: int) -> str:
    """Generate CUA prompt for robust timeline reading with individual page navigation."""
    return f"""Your task is to read the text content of the top {num_tweets} tweets from your home timeline using a robust individual page navigation strategy.

This enhanced approach navigates to each tweet's individual page to capture complete content, eliminating viewport displacement issues.

🔧 ROBUST INDIVIDUAL PAGE NAVIGATION STRATEGY:

STEP 1 - VERIFY HOME TIMELINE:
You should already be on the home timeline with tweets visible.
Take a screenshot to confirm you can see the timeline with multiple tweets.

STEP 2 - NAVIGATE THROUGH TWEETS INDIVIDUALLY:
For each tweet from 1 to {num_tweets}:
   1. Use 'j' to navigate to/focus on the target tweet
   2. Press 'Enter' to open the tweet's individual page
   3. Wait for the page to load and stabilize (2-3 seconds)
   4. Extract the complete tweet text from the dedicated page
   5. Press 'g' then 'h' to return to home timeline
   6. Continue to next tweet

STEP 3 - EXTRACT COMPLETE CONTENT:
On each individual tweet page:
- Capture the full main tweet text
- Include hashtags, mentions, and emojis
- Ignore: author names, timestamps, interaction counts, replies

STEP 4 - COMPILE RESULTS:
Create a JSON array with the extracted tweet texts

RESPONSE FORMATS:
- 'SUCCESS: ["tweet1 text", "tweet2 text", ...]' (if all tweets extracted)
- 'FAILED: Could not navigate to home timeline'
- 'FAILED: Could not navigate to individual tweet pages'
- 'SESSION_INVALIDATED' (if login required)

NAVIGATION PATTERN EXAMPLE for 3 tweets:
1. j → Enter → [extract] → g+h → j → j → Enter → [extract] → g+h → j → j → j → Enter → [extract]

This individual page strategy provides more reliable content extraction."""

def get_tweet_reply_prompt(tweet_url: str, reply_text: str) -> str:
    """Generate CUA prompt for replying to a tweet."""
    return f"""You are on the page of the specific tweet you need to reply to: {tweet_url}

Your task is to post a reply with EXACTLY this text: "{reply_text}"

{CUA_UNICODE_HANDLING_INSTRUCTIONS}

{CUA_RESET_INSTRUCTIONS}

🎯 STRUCTURED APPROACH:

STEP 1 - VERIFY TWEET PAGE:
Confirm you are on the correct tweet page and can see the original tweet
The tweet should be prominently displayed with reply options visible below

STEP 2 - OPEN REPLY COMPOSER:
Press 'r' (lowercase) to open the reply composer
EXPECTED: A reply composition area should appear, usually below the tweet
IF NOTHING HAPPENS: Press ESC, wait 1 second, try 'r' again
IF STILL FAILS: Look for reply icon (speech bubble) and click it

STEP 3 - FOCUS TEXT INPUT:
The reply text input should be automatically focused after pressing 'r'

STEP 4 - TYPE REPLY TEXT:
Type the exact reply text: {reply_text}
⚠️ CRITICAL: Type slowly to ensure emojis render correctly
VERIFY: Emojis should appear as symbols, not escaped sequences

STEP 5 - SEND REPLY:
Press 'Ctrl+Enter' (Windows) or 'Cmd+Enter' (Mac) to send
EXPECTED: Reply should be posted and appear in the conversation thread
IF SHORTCUT FAILS: Look for blue 'Reply' button and click it

STEP 6 - VERIFY SUCCESS:
Wait 3 seconds for the page to update
Look for your reply in the conversation thread below the original tweet
Your reply should appear with your username and the text you typed

RESPONSE FORMATS:
- 'SUCCESS: Reply posted successfully' (if reply appears in thread)
- 'SUCCESS: Posted but emojis showed as escaped text' (if posting worked but emojis wrong)
- 'FAILED: Could not open reply composer' (if 'r' shortcut and click both fail)
- 'FAILED: Could not focus text input' (if text area won't accept input)
- 'FAILED: Could not send reply' (if both keyboard shortcut and button fail)
- 'SESSION_INVALIDATED' (if you encounter login screen)"""

def get_tweet_like_prompt(tweet_url: str) -> str:
    """Generate CUA prompt for liking a tweet."""
    return f"""You are controlling a browser on X.com and you are already on the specific tweet page: {tweet_url}

Your task is to LIKE this tweet. You are already logged in and on the correct page.

Follow these steps EXACTLY:

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to see the current page state and confirm you're on the tweet page.

STEP 2 - LIKE THE TWEET:
Use the 'l' (lowercase L) keyboard shortcut to like the tweet.
This is X.com's standard keyboard shortcut for liking and is much more reliable than clicking.
The shortcut works on the main tweet when you're on a tweet's individual page.

STEP 3 - VERIFY SUCCESS:
Wait 1-2 seconds for the UI to update.
Take a screenshot to verify the like action worked.
Look for visual confirmation that the like icon changed state (filled red heart icon).

STEP 4 - RESPOND WITH RESULT:
Based on your actions, respond with one of:
- 'SUCCESS: Tweet liked successfully' (if the heart icon shows as liked/filled)
- 'FAILED: Could not like tweet - [specific reason]' (if like action failed)
- 'SESSION_INVALIDATED' (if you encounter a login screen)

FALLBACK OPTION (only if keyboard shortcut fails):
If the 'l' keyboard shortcut doesn't work, look for the heart/like icon and click it directly.
The heart icon is usually located below the tweet text, in the row of action buttons.

IMPORTANT NOTES:
- If you see a cookie consent banner, dismiss it first before liking
- The 'l' shortcut should work immediately without clicking anywhere first
- If you see a login page, respond with 'SESSION_INVALIDATED' immediately
- Take screenshots between major steps to track progress"""

def get_tweet_repost_prompt(tweet_url: str) -> str:
    """Generate CUA prompt for reposting a tweet."""
    return f"""You are on the page of the specific tweet you need to repost: {tweet_url}

Your task is to perform a standard repost (not a 'Quote Post').

Follow this two-step keyboard and mouse workflow:

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to see the current page state and confirm you're on the tweet page.

STEP 2 - OPEN REPOST DIALOG:
Press 't' to open the repost dialog menu. This is the keyboard shortcut.
Wait 1-2 seconds for the dialog to appear.

STEP 3 - CONFIRM REPOST:
After the dialog appears, take a screenshot. The dialog will have two options: 'Repost' and 'Quote'.
Press the ArrowDown key to select 'Repost' and then press the enter key to confirm.
DO NOT click 'Quote' - we want a standard repost.

STEP 4 - VERIFY SUCCESS:
Take a final screenshot. Look for a confirmation message like 'Your post was sent' or see if the repost icon on the original tweet changes color (e.g., to green).

RESPONSE FORMATS:
- 'SUCCESS: Tweet at {tweet_url} was successfully reposted.'
- 'FAILED: Could not repost tweet. [Reason, e.g., repost dialog did not appear, confirmation button not found].'
- 'SESSION_INVALIDATED' (if you see a login screen).

FALLBACK OPTION (only if keyboard shortcut fails):
If the 't' keyboard shortcut doesn't work, look for the repost/retweet icon (usually two curved arrows) and click it directly.
The repost icon is usually located below the tweet text, in the row of action buttons.

IMPORTANT NOTES:
- If you see a cookie consent banner, dismiss it first before reposting
- The 't' shortcut should work immediately without clicking anywhere first
- If you see a login page, respond with 'SESSION_INVALIDATED' immediately
- Take screenshots between major steps to track progress
- Ensure you click 'Repost' not 'Quote' when the dialog appears"""

def get_user_follow_prompt(profile_url: str) -> str:
    """Generate CUA prompt for following a user."""
    return f"""You are on the X.com profile page of a user you need to follow. Your task is to click the 'Follow' button.

Follow this workflow:

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to see the current page state and confirm you're on the user's profile page.

STEP 2 - LOCATE FOLLOW BUTTON:
Visually scan the profile page, typically near the top right area, for a button with the text 'Follow'. 
It is usually a prominent button, often with a colored background (blue or black).
The Follow button is commonly located next to or near the user's profile information (name, bio, etc.).

STEP 3 - CLICK FOLLOW:
Execute a mouse click directly on the 'Follow' button you identified.
This action requires a precise click on the button.

STEP 4 - VERIFY SUCCESS:
Wait 1-2 seconds for the UI to update.
Take a final screenshot. The button you just clicked should now have changed its text to 'Following'.
Visually confirm this change - the button should show 'Following' instead of 'Follow'.

RESPONSE FORMATS:
- 'SUCCESS: Successfully followed user at {profile_url}.'
- 'FAILED: Could not follow user. [Reason, e.g., Follow button not found, button text did not change to Following].'
- 'SESSION_INVALIDATED' (if you see a login screen).

ALTERNATIVE SCENARIOS:
- If the button already shows 'Following', respond with 'SUCCESS: User is already being followed.'
- If you see 'Blocked' or similar restrictive states, respond with 'FAILED: Cannot follow user due to account restrictions.'
- If the profile appears to be private and requires approval, the button might change to 'Requested' - this is also a success.

IMPORTANT NOTES:
- If you see a cookie consent banner, dismiss it first before attempting to follow
- The Follow button is typically prominent and easy to locate on profile pages
- If you see a login page, respond with 'SESSION_INVALIDATED' immediately
- Take screenshots between major steps to track progress
- Be precise with your click to ensure you hit the Follow button accurately"""

def get_search_x_prompt(query: str, num_results: int) -> str:
    """Generate CUA prompt for searching X.com for a topic."""
    return f"""Your task is to search X.com for the query '{query}' and extract the text of the top {num_results} search results.

Follow this keyboard-first workflow:

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to see the current page state.

STEP 2 - FOCUS SEARCH BAR:
Press the '/' key to move focus directly to the search bar.
This is X.com's keyboard shortcut to focus the search input field.
Wait 1 second for the focus to activate.

STEP 3 - EXECUTE SEARCH:
Type the query '{query}' into the search bar.
Then press 'Enter' to execute the search.
Wait 2-3 seconds for the search results page to load.

STEP 4 - VERIFY SEARCH RESULTS:
Take a screenshot to confirm you see a list of tweets related to your search.
You should be on a search results page showing tweets that match your query.
The page should show multiple tweet results in a timeline-like format.

STEP 5 - EXTRACT RESULTS:
Similar to reading a timeline, identify the first tweet in the search results and extract its text.
Focus on the main tweet content, ignoring usernames, timestamps, and interaction counts.
Then, press 'j' to move to the next result and extract its text.
Repeat this until you have {num_results} tweets.

Navigation pattern:
- Start with the first visible search result
- Press 'j' to move to each subsequent result
- Extract only the main text content of each tweet
- Continue until you have {num_results} tweet texts

STEP 6 - COMPILE RESULTS:
Create a JSON array with the extracted tweet texts from the search results.

FINAL RESPONSE FORMAT:
Your final response MUST be a JSON string representing a list of the tweet texts you extracted. Example for 2 results:
SUCCESS: ["Text of first search result tweet...", "Text of second search result tweet..."]

If you fail, respond with 'FAILED: [Reason]' or 'SESSION_INVALIDATED'.

IMPORTANT NOTES:
- Use keyboard navigation ('/' for search, 'j' for next result) whenever possible
- Focus only on extracting the main tweet text content
- Ignore usernames, timestamps, like counts, reply counts, etc.
- If you see a cookie consent banner, dismiss it first
- If you encounter a login screen, respond with 'SESSION_INVALIDATED'
- Take screenshots between major steps to track progress
- If search returns no results, respond with 'FAILED: No search results found for query'"""

def get_timeline_reading_prompt(num_tweets: int) -> str:
    """Generate CUA prompt for reading timeline tweets."""
    return f"""Your task is to read the text content of the top {num_tweets} tweets from your home timeline. You are already logged in and the viewport has been pre-stabilized.

🔧 CRITICAL: VIEWPORT STABILITY PROTOCOL
The browser viewport has been pre-stabilized to prevent displacement during navigation.
If you notice the page content shifting outside the visible area during 'j' navigation:
1. IMMEDIATELY press 'Home' key to return to top of page
2. Wait 1 second for page to stabilize  
3. Press 'g+h' to re-navigate to home timeline
4. Resume navigation from the first tweet

{CUA_RESET_INSTRUCTIONS}

⚠️ CRITICAL: SCREENSHOT HANDLING
- DO NOT press Alt+PrintScreen or any manual screenshot keys
- Screenshots are automatically taken by the system
- DO NOT attempt to take screenshots manually
- If you need to see the current state, just describe what you observe

🎯 STEP-BY-STEP APPROACH:

STEP 1 - VERIFY HOME TIMELINE:
You should already be on the home timeline due to pre-navigation
Look for the main timeline feed with tweets visible
If not on home timeline, press 'g+h' to navigate there

STEP 2 - ENSURE TOP POSITION:
Press 'Home' key to ensure you're at the top of the timeline
This prevents any scroll displacement issues
Wait 1 second for page to stabilize

STEP 3 - FOCUS ON FIRST TWEET:
The first tweet should be visible at the top of the timeline
Press 'j' once to focus on the first tweet
VERIFY: Look for visual indication that a tweet is selected/focused
IF VIEWPORT SHIFTS: Execute viewport recovery protocol above

STEP 4 - READ TWEETS SEQUENTIALLY:
For each tweet from 1 to {num_tweets}:
   1. Read and note the text content of the currently focused tweet
   2. Ignore usernames, timestamps, interaction counts
   3. Focus ONLY on the main tweet text content
   4. If this is not the last tweet, press 'j' to move to next tweet
   5. CRITICAL: After pressing 'j', check if content is still visible
   6. If viewport shifted/content disappeared, execute recovery:
      - Press 'Home' key to return to top
      - Press 'g+h' to re-navigate to home timeline
      - Use 'j' key {num_tweets-1} times to return to current position
   7. Wait 1 second for the focus to move and stabilize
   8. Repeat until you have {num_tweets} tweet texts

STEP 5 - COMPILE RESULTS:
Create a JSON array with the extracted tweet texts
Include: Main tweet text, hashtags, mentions, emojis
Exclude: Author names, timestamps, interaction counts

RESPONSE FORMATS:
- 'SUCCESS: ["tweet1 text", "tweet2 text", "tweet3 text"]' (if all tweets extracted)
- 'FAILED: Could not navigate to home timeline' (if navigation failed)
- 'FAILED: Timeline appears blank or unresponsive' (if no content loads)
- 'FAILED: Could not extract tweet text' (if text extraction failed)
- 'SESSION_INVALIDATED' (if you encounter a login screen)"""

def get_consolidated_timeline_reading_prompt(num_tweets: int) -> str:
    """Generate CUA prompt for consolidated timeline reading with viewport fixes and individual page navigation."""
    return f"""Your task is to read the text content of the top {num_tweets} tweets from your home timeline using a consolidated approach that combines viewport stabilization with robust individual page navigation.

🔧 CRITICAL: CONSOLIDATED VIEWPORT & NAVIGATION STRATEGY
This method combines the proven viewport stabilization fixes with robust individual page navigation to eliminate all displacement issues while providing reliable content extraction.

The browser viewport has been pre-stabilized and you are starting from a stable home timeline position.

{CUA_RESET_INSTRUCTIONS}

⚠️ CRITICAL: SCREENSHOT HANDLING
- DO NOT press Alt+PrintScreen or any manual screenshot keys
- Screenshots are automatically taken by the system
- DO NOT attempt to take screenshots manually
- If you need to see the current state, just describe what you observe

🎯 CONSOLIDATED STEP-BY-STEP APPROACH:

STEP 1 - VERIFY STABILIZED HOME TIMELINE:
You should already be on a pre-stabilized home timeline with tweets visible.
The viewport has been stabilized to prevent displacement during navigation.
Take a moment to confirm you can see the timeline with multiple tweets.

STEP 2 - ENSURE OPTIMAL STARTING POSITION:
Press 'Home' key to ensure you're at the very top of the timeline
This leverages the viewport stabilization and prevents scroll issues
Wait 1 second for page to fully stabilize

STEP 3 - CONSOLIDATED INDIVIDUAL PAGE NAVIGATION:
For each tweet from 1 to {num_tweets}:
   🧭 NAVIGATION SEQUENCE:
   1. Use 'j' to navigate to/focus on the target tweet
   2. VIEWPORT CHECK: If content shifts or becomes unavailable:
      - Press 'Home' key to return to top
      - Press 'g+h' to re-navigate to home timeline
      - Use 'j' key to return to current position
   3. Press 'Enter' to open the tweet's individual page
   4. Wait 2-3 seconds for the individual page to load and stabilize
   5. Extract the complete tweet text from the dedicated page
   6. Press 'g' then 'h' in sequence to return to home timeline
   7. Wait 1 second for timeline to reload and stabilize
   8. Continue to next tweet

STEP 4 - ENHANCED CONTENT EXTRACTION:
On each individual tweet page:
- Capture the full main tweet text content
- Include hashtags, mentions, and emoji characters
- Focus on the primary tweet text (ignore author names, timestamps, interaction counts)
- Ignore replies and quoted tweets unless they're part of the main content

STEP 5 - COMPILE CONSOLIDATED RESULTS:
Create a JSON array with all extracted tweet texts
Format: ["tweet1 text here", "tweet2 text here", "tweet3 text here"]

🔧 VIEWPORT RECOVERY PROTOCOL:
If at any point you notice content displacement or blank pages:
1. IMMEDIATELY press 'Home' key to return to page top
2. Wait 1 second for stabilization
3. Press 'g+h' to re-navigate to home timeline
4. Resume from current tweet position using 'j' navigation

NAVIGATION PATTERN EXAMPLE for 3 tweets:
Starting position → j → Enter → [extract on individual page] → g+h → j → j → Enter → [extract] → g+h → j → j → j → Enter → [extract]

RESPONSE FORMATS:
- 'SUCCESS: ["tweet1 text", "tweet2 text", "tweet3 text"]' (if all tweets extracted successfully)
- 'FAILED: Could not navigate to home timeline' (if initial navigation failed)
- 'FAILED: Could not navigate to individual tweet pages' (if Enter navigation failed)
- 'FAILED: Viewport displacement could not be recovered' (if stabilization failed)
- 'SESSION_INVALIDATED' (if login screen encountered)

This consolidated approach provides maximum reliability by combining viewport stabilization with individual page navigation for the most robust content extraction possible."""

def get_search_and_like_tweet_prompt(search_query: str, max_iterations: int = 20) -> str:
    """Generate comprehensive CUA prompt for searching and liking tweets.
    
    This function creates detailed, step-by-step instructions for the CUA to:
    1. Search for tweets using a specific query
    2. Evaluate search results for quality
    3. Select an appropriate tweet to like
    4. Execute the like action
    
    Args:
        search_query: The search query to use (e.g., '#AI', 'machine learning')
        max_iterations: Maximum iterations for the CUA workflow
        
    Returns:
        Detailed step-by-step prompt for CUA execution
    """
    return f"""🎯 TASK: SEARCH FOR AND LIKE A HIGH-QUALITY TWEET

Your mission: Search X.com for tweets containing '{search_query}', evaluate the results, select one high-quality tweet, and like it.

{CUA_RESET_INSTRUCTIONS}

📋 DETAILED STEP-BY-STEP WORKFLOW:

PHASE 1: SEARCH EXECUTION
--------------------------

STEP 1 - TAKE INITIAL SCREENSHOT:
Take a screenshot to see your current page state on X.com.

STEP 2 - INITIATE SEARCH:
Press '/' (forward slash) to focus the search box.
Wait 1 second for the search bar to be focused.

STEP 3 - EXECUTE SEARCH:
Type EXACTLY: {search_query}
Press 'Enter' to execute the search.
Wait 2-3 seconds for search results to load.

STEP 4 - VERIFY SEARCH RESULTS:
Take a screenshot to confirm you see search results.
You should see a list of tweets related to '{search_query}'.

PHASE 2: TWEET EVALUATION & SELECTION
-------------------------------------

STEP 5 - EVALUATE FIRST TWEET:
Look at the first search result tweet. Consider these quality factors:
- Is it from a legitimate account (has profile picture, reasonable follower count)?
- Does the tweet content make sense and relate to {search_query}?
- Is it recent (posted within last few days/weeks)?
- Does it have some engagement (likes, retweets) indicating it's not spam?
- Is the content insightful, informative, or adds value to the conversation?

STEP 6 - DECISION POINT:
If the first tweet meets quality criteria: PROCEED TO LIKE IT (Go to Step 7)
If the first tweet is low quality: Use 'j' to move to next tweet and re-evaluate

Quality red flags to avoid:
- Accounts with no profile picture or suspicious usernames
- Tweets with excessive hashtags or promotional content
- Very old tweets (older than 1 month)
- Tweets with zero engagement
- Spam-like or nonsensical content

STEP 7 - SELECT TWEET TO LIKE:
Once you've identified a suitable tweet, click on it to open the individual tweet page.
This is important - you need to be on the specific tweet's page to like it effectively.
Wait 2 seconds for the page to load.

PHASE 3: LIKE EXECUTION
-----------------------

STEP 8 - EXECUTE LIKE ACTION:
Press 'l' (lowercase L) to like the tweet.
This is X.com's keyboard shortcut for liking.
Wait 2 seconds for the UI to update.

STEP 9 - VERIFY LIKE SUCCESS:
Take a final screenshot to confirm the like worked.
Look for visual confirmation:
- Heart icon should be filled/colored (usually red)
- Like count should have increased by 1
- The heart icon should appear "active" or "selected"

STEP 10 - REPORT RESULT:
Based on your actions, respond with:
- 'SUCCESS: Found and liked tweet about {search_query} - [brief description of tweet content]'
- 'FAILED: Could not find suitable tweet for {search_query} - [reason]'
- 'SESSION_INVALIDATED' if you encounter login screens

🚨 ERROR HANDLING & FALLBACKS:

Search Issues:
- If search returns no results: Try a simpler version of the query
- If search page won't load: Press 'g+h' to go home, then try search again

Tweet Selection Issues:
- If first 3-5 tweets are all low quality: Report this in your response
- If you can't determine tweet quality: Choose the most recent one with some engagement

Like Action Issues:
- If 'l' keyboard shortcut doesn't work: Click the heart icon directly
- If heart icon is already filled: The tweet is already liked, try the next one
- If like seems to fail: Take screenshot and report what you observe

Session Issues:
- If you see any login prompts: Immediately respond with 'SESSION_INVALIDATED'
- If pages won't load properly: Try refreshing with 'F5' then continue

IMPORTANT REMINDERS:
- Use keyboard shortcuts whenever possible ('/', 'j', 'l')
- Take screenshots at key decision points to track progress
- Focus on quality over speed - better to like one good tweet than like spam
- If you encounter cookie consent, dismiss it and continue
- Maximum iterations: {max_iterations} - use them wisely

FINAL RESPONSE FORMAT:
Provide a clear success/failure message with details about what you accomplished."""

def get_structured_cua_task_prompt(
    main_objective: str,
    steps: list,
    success_criteria: str,
    fallback_actions: list = None,
    max_iterations: int = 30
) -> str:
    """Generate a structured, step-by-step CUA prompt for complex tasks.
    
    This function creates comprehensive prompts that guide the CUA through
    multi-step workflows with clear objectives, detailed steps, and fallback options.
    
    Args:
        main_objective: Clear statement of what needs to be accomplished
        steps: List of detailed step descriptions
        success_criteria: How to determine if the task was successful
        fallback_actions: Optional list of fallback actions for common issues
        max_iterations: Maximum iterations for the CUA workflow
        
    Returns:
        Structured prompt with clear phases, steps, and error handling
    """
    fallback_section = ""
    if fallback_actions:
        fallback_list = "\n".join([f"- {action}" for action in fallback_actions])
        fallback_section = f"""
🚨 FALLBACK ACTIONS:
{fallback_list}
"""
    
    steps_section = ""
    for i, step in enumerate(steps, 1):
        steps_section += f"STEP {i}: {step}\n\n"
    
    return f"""🎯 MAIN OBJECTIVE: {main_objective}

{CUA_RESET_INSTRUCTIONS}

📋 DETAILED WORKFLOW:

{steps_section}🎯 SUCCESS CRITERIA:
{success_criteria}

Take a final screenshot to verify completion and respond with:
- 'SUCCESS: [brief description of what was accomplished]'
- 'FAILED: [specific reason for failure]'  
- 'SESSION_INVALIDATED' if you encounter login screens

{fallback_section}
IMPORTANT REMINDERS:
- Use keyboard shortcuts whenever possible for better reliability
- Take screenshots at key decision points to track progress
- If you encounter cookie consent banners, dismiss them and continue
- Maximum iterations: {max_iterations} - plan your actions accordingly
- If you get stuck, use the reset instructions to recover

EXECUTION GUIDELINES:
- Be methodical: Complete each step before moving to the next
- Be observant: Take screenshots to verify each action worked
- Be adaptive: Use fallback actions if primary methods fail
- Be clear: Provide specific details in your final response"""

def create_smart_cua_task_prompt(task_description: str, context: dict = None) -> tuple:
    """Intelligently generate a CUA prompt and determine optimal parameters based on task description.
    
    This function analyzes the task description and automatically selects the best
    prompt template and parameters for the CUA to execute the task effectively.
    
    Args:
        task_description: Natural language description of what needs to be done
        context: Optional context dict with additional parameters
        
    Returns:
        Tuple of (prompt, start_url, max_iterations) optimized for the task
    """
    context = context or {}
    
    # Normalize the task description
    task_lower = task_description.lower()
    
    # Search and like pattern detection
    if any(phrase in task_lower for phrase in [
        "find a tweet", "search for", "look for a tweet", "find and like"
    ]) and any(phrase in task_lower for phrase in ["like", "heart", "engage"]):
        
        # Extract search query from the description
        search_query = "OpenAI"  # Default fallback
        
        # Try to extract specific hashtags or search terms
        import re
        hashtag_match = re.search(r'#\w+', task_description)
        if hashtag_match:
            search_query = hashtag_match.group()
        elif 'about' in task_lower:
            # Extract text after "about"
            about_match = re.search(r'about [\'"]?([^\'"\.\,]+)', task_description, re.IGNORECASE)
            if about_match:
                search_query = about_match.group(1).strip()
        
        prompt = get_search_and_like_tweet_prompt(search_query, max_iterations=30)
        return prompt, "https://x.com", 30
    
    # Direct tweet liking (when URL is provided)
    elif "like" in task_lower and any(url_indicator in task_lower for url_indicator in [
        "http", "x.com", "twitter.com", "tweet"
    ]):
        # Try to extract URL from context or description
        tweet_url = context.get('tweet_url', 'https://x.com')
        if 'http' in task_description:
            import re
            url_match = re.search(r'https?://[^\s]+', task_description)
            if url_match:
                tweet_url = url_match.group()
        
        prompt = get_tweet_like_prompt(tweet_url)
        return prompt, tweet_url, 20
    
    # Timeline reading
    elif any(phrase in task_lower for phrase in [
        "read timeline", "browse timeline", "check timeline", "timeline tweets"
    ]):
        num_tweets = 5  # Default
        # Try to extract number
        import re
        num_match = re.search(r'(\d+)\s*tweets?', task_description)
        if num_match:
            num_tweets = int(num_match.group(1))
        
        prompt = get_timeline_reading_prompt(num_tweets)
        return prompt, "https://x.com", 25
    
    # Tweet posting
    elif any(phrase in task_lower for phrase in [
        "post tweet", "create tweet", "publish tweet", "send tweet"
    ]):
        tweet_text = context.get('tweet_text', 'Hello from AI agent!')
        prompt = get_tweet_posting_prompt(tweet_text)
        return prompt, "https://x.com", 15
    
    # Search functionality
    elif any(phrase in task_lower for phrase in [
        "search for", "find tweets about", "search x", "look up"
    ]):
        query = context.get('search_query', 'AI')
        num_results = context.get('num_results', 5)
        prompt = get_search_x_prompt(query, num_results)
        return prompt, "https://x.com", 20
    
    # Fallback: Create a generic structured task
    else:
        steps = [
            "Take a screenshot to see current page state",
            "Navigate to the appropriate page if needed",
            "Execute the requested action using keyboard shortcuts when possible",
            "Verify the action was successful",
            "Take a final screenshot for confirmation"
        ]
        
        prompt = get_structured_cua_task_prompt(
            main_objective=task_description,
            steps=steps,
            success_criteria="The requested action was completed successfully",
            fallback_actions=[
                "Use mouse clicks if keyboard shortcuts fail",
                "Refresh the page (F5) if it becomes unresponsive",
                "Navigate to home page (g+h) and retry if lost"
            ],
            max_iterations=25
        )
        
        return prompt, "https://x.com", 25 