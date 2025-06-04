#!/usr/bin/env python3
"""
Helper script for setting up authenticated browser session for CUA operations.

This script launches a Playwright browser with persistent context to allow
manual login to X.com. The session state will be saved for subsequent
automated CUA operations.

Usage:
    python scripts/setup_cua_authentication.py

Prerequisites:
    1. Set X_CUA_USER_DATA_DIR environment variable in .env file
    2. Ensure Playwright is installed: pip install playwright
    3. Install browser: playwright install chromium
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root directory to Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright

from core.config import settings


async def setup_authenticated_session() -> None:
    """Set up an authenticated browser session for CUA operations."""
    logger = logging.getLogger(__name__)
    
    if not settings.x_cua_user_data_dir:
        logger.error("X_CUA_USER_DATA_DIR environment variable not set.")
        logger.error("Please set X_CUA_USER_DATA_DIR=data/cua_profile in your .env file")
        return
    
    user_data_dir = Path(settings.x_cua_user_data_dir)
    # Make path relative to project root if it's not absolute
    if not user_data_dir.is_absolute():
        user_data_dir = project_root / user_data_dir
    
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Setting up authenticated browser session...")
    logger.info("User data directory: %s", user_data_dir.absolute())
    logger.info("Please complete the following steps:")
    logger.info("1. Browser will open to X.com")
    logger.info("2. Manually log in to your designated test account")
    logger.info("3. Complete any MFA or verification steps")
    logger.info("4. Check 'Remember me' if available")
    logger.info("5. Navigate to a few pages to confirm authentication")
    logger.info("6. Close the browser when done")
    logger.info("7. Your session will be saved for automated CUA operations")
    
    input("\nPress Enter to launch browser...")
    
    async with async_playwright() as playwright:
        # Launch persistent browser context
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=["--window-size=1024,768"],
            viewport={"width": 1024, "height": 768},
        )
        
        # Navigate to X.com
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://x.com")
        
        logger.info("Browser launched. Please complete authentication manually.")
        logger.info("Close the browser window when you're done to save the session.")
        
        # Wait for browser to be closed manually
        try:
            await context.wait_for_event("close", timeout=0)  # Wait indefinitely
        except Exception:
            # Browser was closed manually
            pass
        
        logger.info("Browser closed. Authentication session saved.")
        logger.info("You can now run CUA operations with authenticated access.")


def main() -> None:
    """Main entry point for the authentication setup script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("X Agentic Unit - CUA Authentication Setup")
    logger.info("Project root: %s", project_root.absolute())
    
    try:
        asyncio.run(setup_authenticated_session())
    except KeyboardInterrupt:
        print("\nSetup cancelled by user.")
    except Exception as e:
        logging.error("Authentication setup failed: %s", e, exc_info=True)


if __name__ == "__main__":
    main() 