"""
Module providing a Playwright-based AsyncComputer implementation.
"""

import asyncio
import base64
from typing import Literal, Optional, Union

from playwright.async_api import Playwright, Browser, BrowserContext, Page, async_playwright

from core.computer_env.base import AsyncComputer, Environment, Button

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
        
        if self.user_data_dir_path:
            # Use persistent browser context for authenticated sessions
            self._browser_context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir_path,
                headless=False,
                args=[f"--window-size={width},{height}"],
                viewport={"width": width, "height": height},
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
                args=[f"--window-size={width},{height}"],
            )
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": width, "height": height})
        
        await self._page.goto("https://x.com")

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
        png_bytes = await self.page.screenshot(full_page=False)
        return base64.b64encode(png_bytes).decode("utf-8")

    async def click(self, x: int, y: int, button: Button = "left") -> None:
        """Click at the specified coordinates."""
        playwright_button: Literal["left", "middle", "right"] = "left"
        if button in ("left", "middle", "right"):
            playwright_button = button  # type: ignore
        await self.page.mouse.click(x, y, button=playwright_button)

    async def double_click(self, x: int, y: int) -> None:
        """Double-click at the specified coordinates."""
        await self.page.mouse.dblclick(x, y)

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """Scroll by the specified offsets starting from given coordinates."""
        await self.page.mouse.move(x, y)
        await self.page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

    async def type(self, text: str) -> None:
        """Type text using the keyboard."""
        await self.page.keyboard.type(text)

    async def wait(self) -> None:
        """Wait for a short default duration."""
        await asyncio.sleep(1)

    async def move(self, x: int, y: int) -> None:
        """Move mouse to the specified coordinates."""
        await self.page.mouse.move(x, y)

    async def keypress(self, keys: list[str]) -> None:
        """Press and release the specified keys."""
        mapped_keys = [
            _CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys
        ]
        for key in mapped_keys:
            await self.page.keyboard.down(key)
        for key in reversed(mapped_keys):
            await self.page.keyboard.up(key)

    async def drag(self, path: list[tuple[int, int]]) -> None:
        """Drag the mouse along the specified path."""
        if not path:
            return
        await self.page.mouse.move(path[0][0], path[0][1])
        await self.page.mouse.down()
        for px, py in path[1:]:
            await self.page.mouse.move(px, py)
        await self.page.mouse.up() 