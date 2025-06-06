"""
Module providing a Playwright-based AsyncComputer implementation.
"""

import asyncio
import base64
import logging
from typing import Literal, Optional, Union

from playwright.async_api import Playwright, Browser, BrowserContext, Page, async_playwright

from agents import AsyncComputer, Environment, Button

_CUA_KEY_TO_PLAYWRIGHT_KEY: dict[str, str] = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}


class LocalPlaywrightComputer(AsyncComputer):
    """A computer, implemented using a local Playwright browser."""

    def __init__(self, user_data_dir_path: Optional[str] = None) -> None:
        """
        Initialize the LocalPlaywrightComputer with optional persistent user data directory.
        
        Args:
            user_data_dir_path: Optional path to persistent browser user data directory.
                              If provided, enables authenticated sessions with saved cookies/state.
        """
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._browser_context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self.user_data_dir_path = user_data_dir_path
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "LocalPlaywrightComputer":
        """Enter context manager: start Playwright and initialize browser and page."""
        self._playwright = await async_playwright().start()
        await self._initialize_browser_and_page()
        return self

    async def __aexit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[any]) -> None:
        """Exit context manager: close browser and stop Playwright."""
        if self._browser_context:
            await self._browser_context.close()
        elif self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _initialize_browser_and_page(self) -> None:
        """Initialize the browser and page with specified dimensions and default URL."""
        width, height = self.dimensions
        
        # Enhanced browser launch args to prevent automation detection
        # and improve compatibility with X.com
        browser_args = [
            f"--window-size={width},{height}",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=VizDisplayCompositor",
            "--disable-web-security",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-background-timer-throttling",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        if self.user_data_dir_path:
            # Use persistent browser context for authenticated sessions
            self._browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir_path,
                headless=False,
                args=browser_args,
                viewport={"width": width, "height": height},
                # Additional context options to improve X.com compatibility
                ignore_https_errors=True,
                java_script_enabled=True,
                bypass_csp=True,
            )
            # For persistent context, get the first (default) page or create new one
            pages = self._browser_context.pages
            if pages:
                self._page = pages[0]
                await self._page.set_viewport_size({"width": width, "height": height})
            else:
                self._page = await self._browser_context.new_page()
        else:
            # Use standard browser launch for non-persistent sessions
            self._browser = await self.playwright.chromium.launch(
                headless=False,
                args=browser_args,
            )
            self._browser_context = await self._browser.new_context(
                viewport={"width": width, "height": height},
                ignore_https_errors=True,
                java_script_enabled=True,
                bypass_csp=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = await self._browser_context.new_page()
        
        # Enhance page settings to prevent automation detection
        await self._page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock languages and plugins
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)
        
        # Set extra HTTP headers
        await self._page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        await self._page.goto("https://x.com")
        
        # Wait for page to fully load and stabilize
        await self._page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)  # Additional stabilization time

    @property
    def playwright(self) -> Playwright:
        """Access the Playwright instance."""
        assert self._playwright is not None, "Playwright is not initialized"
        return self._playwright

    @property
    def browser(self) -> Union[Browser, BrowserContext]:
        """Access the Browser or BrowserContext instance."""
        if self._browser_context:
            return self._browser_context
        assert self._browser is not None, "Browser is not initialized"
        return self._browser

    @property
    def page(self) -> Page:
        """Access the Page instance."""
        assert self._page is not None, "Page is not initialized"
        return self._page

    @property
    def environment(self) -> Environment:
        """Return the environment type."""
        return "browser"

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return the default viewport dimensions."""
        return (1024, 768)

    async def screenshot(self) -> str:
        """Capture the viewport as a base64-encoded PNG."""
        self.logger.info("SDK called screenshot()")
        png_bytes = await self.page.screenshot(full_page=False)
        result = base64.b64encode(png_bytes).decode("utf-8")
        self.logger.info(f"Screenshot captured: {len(result)} characters")
        return result

    async def click(self, x: int, y: int, button: Button = "left") -> None:
        """Click at the specified coordinates."""
        self.logger.info(f"SDK called click({x}, {y}, {button})")
        playwright_button: Literal["left", "middle", "right"] = "left"
        if button in ("left", "middle", "right"):
            playwright_button = button  # type: ignore
        
        # Enhanced click with better timing and interaction
        try:
            # Move to the element first to ensure hover state
            await self.page.mouse.move(x, y)
            await asyncio.sleep(0.1)  # Brief pause for hover effects
            
            # Perform the click with force to ensure it registers
            await self.page.mouse.click(x, y, button=playwright_button, delay=50)
            
            # Brief pause after click to allow any JavaScript to execute
            await asyncio.sleep(0.3)
            
            self.logger.info(f"Enhanced click executed at ({x}, {y})")
        except Exception as e:
            self.logger.error(f"Error during enhanced click at ({x}, {y}): {e}")
            # Fallback to simple click
            await self.page.mouse.click(x, y, button=playwright_button)
            self.logger.info(f"Fallback click executed at ({x}, {y})")

    async def double_click(self, x: int, y: int) -> None:
        """Double-click at the specified coordinates."""
        self.logger.info(f"SDK called double_click({x}, {y})")
        await self.page.mouse.dblclick(x, y)
        self.logger.info(f"Double-click executed at ({x}, {y})")

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Scroll by the specified offsets starting from given coordinates."""
        self.logger.info(f"SDK called scroll({x}, {y}, {scroll_x}, {scroll_y})")
        await self.page.mouse.move(x, y)
        await self.page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")
        self.logger.info(f"Scroll executed at ({x}, {y}) by ({scroll_x}, {scroll_y})")

    async def type(self, text: str) -> None:
        """Type text using the keyboard."""
        self.logger.info(f"SDK called type('{text}')")
        await self.page.keyboard.type(text)
        self.logger.info(f"Text typed: '{text}'")

    async def wait(self) -> None:
        """Wait for a short default duration."""
        self.logger.info("SDK called wait()")
        await asyncio.sleep(1)
        self.logger.info("Wait completed (1 second)")

    async def move(self, x: int, y: int) -> None:
        """Move mouse to the specified coordinates."""
        self.logger.info(f"SDK called move({x}, {y})")
        await self.page.mouse.move(x, y)
        self.logger.info(f"Mouse moved to ({x}, {y})")

    async def keypress(self, keys: list[str]) -> None:
        """Press and release the specified keys."""
        self.logger.info(f"SDK called keypress({keys})")
        
        # Handle single character keys (like 'N', 'j', 'k', 'l', 'r', 't', 's', 'b' for X.com shortcuts)
        if len(keys) == 1 and len(keys[0]) == 1:
            key = keys[0]
            # For single letter keys, just press them directly
            await self.page.keyboard.press(key)
            self.logger.info(f"Single X.com shortcut key pressed: {key}")
            return
        
        # Handle X.com "g+" navigation shortcuts (e.g., ['g', 'h'] for home)
        if len(keys) == 2 and keys[0].lower() == 'g':
            # Press 'g' first, then the second key
            await self.page.keyboard.press('g')
            await asyncio.sleep(0.1)  # Brief pause between keys
            await self.page.keyboard.press(keys[1].lower())
            self.logger.info(f"X.com navigation shortcut pressed: g+{keys[1]}")
            return
        
        # Handle X.com "a+" audio dock shortcuts (e.g., ['a', 'd'] for audio dock)
        if len(keys) == 2 and keys[0].lower() == 'a':
            # Press 'a' first, then the second key
            await self.page.keyboard.press('a')
            await asyncio.sleep(0.1)  # Brief pause between keys
            await self.page.keyboard.press(keys[1].lower())
            self.logger.info(f"X.com audio shortcut pressed: a+{keys[1]}")
            return
        
        # Special handling for common X.com posting shortcuts
        if keys == ['CTRL', 'SHIFT', 'ENTER'] or keys == ['CMD', 'SHIFT', 'ENTER']:
            # Use the more reliable keyboard.press with the full combination
            if keys[0] == 'CMD':
                await self.page.keyboard.press('Meta+Shift+Enter')
            else:
                await self.page.keyboard.press('Control+Shift+Enter')
            self.logger.info(f"X.com post shortcut pressed: {keys}")
            return
        
        # Handle Ctrl+Enter or Cmd+Enter shortcuts
        if keys == ['CTRL', 'ENTER'] or keys == ['CMD', 'ENTER']:
            if keys[0] == 'CMD':
                await self.page.keyboard.press('Meta+Enter')
            else:
                await self.page.keyboard.press('Control+Enter')
            self.logger.info(f"X.com send shortcut pressed: {keys}")
            return
        
        # Handle special single keys with descriptive names
        special_keys = {
            'SPACE': 'Space',
            'ENTER': 'Enter',
            'ESCAPE': 'Escape',
            'TAB': 'Tab',
            'BACKSPACE': 'Backspace',
            'DELETE': 'Delete',
            'ARROWUP': 'ArrowUp',
            'ARROWDOWN': 'ArrowDown',
            'ARROWLEFT': 'ArrowLeft',
            'ARROWRIGHT': 'ArrowRight',
            '/': 'Slash',
            '?': 'Shift+Slash',
            '.': 'Period'
        }
        
        if len(keys) == 1 and keys[0].upper() in special_keys:
            key_to_press = special_keys[keys[0].upper()]
            await self.page.keyboard.press(key_to_press)
            self.logger.info(f"Special X.com key pressed: {keys[0]} -> {key_to_press}")
            return
        
        # Handle key combinations or complex multi-key sequences
        mapped_keys = [
            _CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys
        ]
        
        # Press all keys down first (for simultaneous combinations)
        for key in mapped_keys:
            await self.page.keyboard.down(key)
            await asyncio.sleep(0.05)  # Brief delay between key downs
        
        # Release all keys in reverse order
        for key in reversed(mapped_keys):
            await self.page.keyboard.up(key)
            await asyncio.sleep(0.05)  # Brief delay between key ups
        
        self.logger.info(f"Complex key combination pressed: {keys} -> {mapped_keys}")

    async def drag(self, path: list[tuple[int, int]]) -> None:
        """Drag the mouse along the specified path."""
        self.logger.info(f"SDK called drag({path})")
        if not path:
            self.logger.info("Empty drag path, skipping")
            return
        await self.page.mouse.move(path[0][0], path[0][1])
        await self.page.mouse.down()
        for px, py in path[1:]:
            await self.page.mouse.move(px, py)
        await self.page.mouse.up()
        self.logger.info(f"Drag executed along {len(path)} points") 