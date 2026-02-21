from playwright.async_api import Page
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class InstagramAuth:
    """Handle Instagram authentication."""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.is_logged_in = False
    
    async def login(self, page: Page) -> bool:
        """
        Login to Instagram.
        
        Args:
            page: Playwright page instance
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            logger.info(f"Attempting to login as {self.username}")
            
            # Navigate to Instagram
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Check if already logged in
            if await self._is_logged_in(page):
                logger.info("Already logged in")
                self.is_logged_in = True
                return True
            
            # Fill username
            username_input = await page.wait_for_selector('input[name="username"]', timeout=10000)
            await username_input.fill(self.username)
            await page.wait_for_timeout(500)
            
            # Fill password
            password_input = await page.query_selector('input[name="password"]')
            await password_input.fill(self.password)
            await page.wait_for_timeout(500)
            
            # Click login button
            login_button = await page.query_selector('button[type="submit"]')
            await login_button.click()
            
            # Wait for navigation
            await page.wait_for_timeout(5000)
            
            # Check for errors
            error_element = await page.query_selector('p[data-testid="login-error-message"]')
            if error_element:
                error_text = await error_element.inner_text()
                logger.error(f"Login failed: {error_text}")
                return False
            
            # Handle "Save Your Login Info" prompt
            try:
                not_now_button = await page.wait_for_selector('button:has-text("Not Now")', timeout=5000)
                await not_now_button.click()
                await page.wait_for_timeout(1000)
            except:
                pass
            
            # Handle "Turn on Notifications" prompt
            try:
                not_now_button = await page.wait_for_selector('button:has-text("Not Now")', timeout=5000)
                await not_now_button.click()
                await page.wait_for_timeout(1000)
            except:
                pass
            
            # Verify login
            if await self._is_logged_in(page):
                logger.info("Login successful")
                self.is_logged_in = True
                return True
            else:
                logger.error("Login verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    async def _is_logged_in(self, page: Page) -> bool:
        """Check if currently logged in."""
        try:
            # Check for profile icon or home feed
            profile_icon = await page.query_selector('svg[aria-label="Home"]')
            return profile_icon is not None
        except:
            return False
    
    async def save_session(self, context) -> Optional[dict]:
        """Save session cookies for reuse."""
        try:
            cookies = await context.cookies()
            storage_state = await context.storage_state()
            logger.info("Session saved")
            return storage_state
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return None
    
    async def load_session(self, context, storage_state: dict) -> bool:
        """Load saved session."""
        try:
            await context.add_cookies(storage_state.get('cookies', []))
            logger.info("Session loaded")
            return True
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False

# Made with Bob
