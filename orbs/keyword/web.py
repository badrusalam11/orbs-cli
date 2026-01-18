# File: orbs/web.py
"""
Web automation keywords for Orbs framework
Provides high-level Selenium operations with automatic driver management

IMPORTANT: This class uses thread-local storage for driver instances to support
parallel test execution. Each thread gets its own driver instance stored in 
thread context, preventing driver conflicts when running multiple test suites
concurrently with different browser configurations.
"""

import time
import threading
from typing import Union, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..browser_factory import BrowserFactory
from ..thread_context import get_context, set_context
from ..guard import orbs_guard
from ..exception import WebActionException
from ..log import log


class Web:
    """High-level web automation keywords"""
    
    _wait_timeout = 10
    _lock = threading.Lock()  # Thread safety for driver creation
    
    @classmethod
    def _get_driver(cls):
        """Get or create the WebDriver instance (thread-safe, thread-local)"""
        # Use thread context to store driver per thread
        driver = get_context('web_driver')
        if driver is None:
            with cls._lock:
                # Double-check in case another thread just created it
                driver = get_context('web_driver')
                if driver is None:
                    driver = BrowserFactory.create_driver()
                    set_context('web_driver', driver)
        return driver
    
    @classmethod
    def use_driver(cls, driver):
        """Use an existing driver instance (for behave context integration)"""
        set_context('web_driver', driver)
        return driver
    
    @classmethod
    def sync_with_context(cls, behave_context):
        """Sync Web driver with behave context"""
        if hasattr(behave_context, 'driver') and behave_context.driver:
            set_context('web_driver', behave_context.driver)
        else:
            behave_context.driver = cls._get_driver()
        return get_context('web_driver')
    
    @classmethod
    def _parse_locator(cls, locator: str) -> tuple:
        """
        Parse locator string into (By strategy, value)
        Supported formats:
        - id=element_id
        - xpath=//div[@id='test']
        - css=.class-name
        - name=element_name
        - class=class-name
        - tag=div
        - link=Link Text
        - partial_link=Partial Link
        """
        if '=' not in locator:
            # If no strategy specified, assume it's an ID
            return By.ID, locator
            
        strategy, value = locator.split('=', 1)
        strategy = strategy.lower().strip()
        value = value.strip()
        
        strategy_map = {
            'id': By.ID,
            'xpath': By.XPATH,
            'css': By.CSS_SELECTOR,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'link': By.LINK_TEXT,
            'partial_link': By.PARTIAL_LINK_TEXT
        }
        
        if strategy not in strategy_map:
            raise ValueError(f"Unsupported locator strategy: {strategy}. "
                           f"Supported: {list(strategy_map.keys())}")
        
        return strategy_map[strategy], value
    
    @classmethod
    def _find_element(cls, locator: str, timeout: Optional[int] = None) -> WebElement:
        """Find a single element with wait"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            element = wait.until(EC.presence_of_element_located((by, value)))
            return element
        except TimeoutException:
            raise NoSuchElementException(f"Element not found: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    def _find_elements(cls, locator: str, timeout: Optional[int] = None) -> List[WebElement]:
        """Find multiple elements with wait"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            # Wait for at least one element to be present
            wait.until(EC.presence_of_element_located((by, value)))
            return driver.find_elements(by, value)
        except TimeoutException:
            return []
    
    # Navigation methods
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda url, **_: f"Failed to open URL: {url}"
    )
    def open(cls, url: str):
        """Open a URL in the browser"""
        driver = cls._get_driver()
        driver.get(url)
        log.action(f"Opened URL: {url}")
    
    @classmethod
    def refresh(cls):
        """Refresh the current page"""
        driver = cls._get_driver()
        driver.refresh()
        log.action("Page refreshed")
    
    @classmethod
    def back(cls):
        """Go back to previous page"""
        driver = cls._get_driver()
        driver.back()
        log.action("Navigated back")
    
    @classmethod
    def forward(cls):
        """Go forward to next page"""
        driver = cls._get_driver()
        driver.forward()
        log.action("Navigated forward")
    
    # Element interaction methods
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Click failed on element: {locator}"
    )
    def click(cls, locator: str, timeout: Optional[int] = None, retry_count: int = 3):
        """Click on an element with retry logic for stale elements"""
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                driver = cls._get_driver()
                by, value = cls._parse_locator(locator)
                wait = WebDriverWait(driver, wait_time)
                
                # Wait for element to be clickable (combines presence + clickable checks)
                element = wait.until(EC.element_to_be_clickable((by, value)))
                element.click()
                log.action(f"Clicked element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1:
                    log.debug(f"Stale element detected, retrying click on {locator} (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except TimeoutException:
                raise TimeoutException(f"Element not clickable: {locator} (timeout: {wait_time}s)")
            except Exception as e:
                if attempt < retry_count - 1:
                    log.debug(f"Click failed, retrying: {e}")
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Double click failed on element: {locator}"
    )
    def double_click(cls, locator: str, timeout: Optional[int] = None):
        """Double click on an element"""
        from selenium.webdriver.common.action_chains import ActionChains
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        actions = ActionChains(driver)
        actions.double_click(element).perform()
        log.action(f"Double clicked element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Right click failed on element: {locator}"
    )
    def right_click(cls, locator: str, timeout: Optional[int] = None):
        """Right click on an element"""
        from selenium.webdriver.common.action_chains import ActionChains
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        actions = ActionChains(driver)
        actions.context_click(element).perform()
        log.action(f"Right clicked element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, text, **_: f"Set text '{text}' failed on element: {locator}"
    )
    def set_text(cls, locator: str, text: str, timeout: Optional[int] = None, clear_first: bool = True, retry_count: int = 3):
        """Set text into an element with retry logic"""
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                driver = cls._get_driver()
                by, value = cls._parse_locator(locator)
                wait = WebDriverWait(driver, wait_time)
                
                element = wait.until(EC.element_to_be_clickable((by, value)))
                
                if clear_first:
                    element.clear()
                
                element.send_keys(text)
                log.action(f"Set text '{text}' into element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1:
                    log.debug(f"Stale element detected, retrying set_text on {locator} (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < retry_count - 1:
                    log.debug(f"Set text failed, retrying: {e}")
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    def type(cls, locator: str, text: str, timeout: Optional[int] = None, clear_first: bool = True):
        """Type text into an element (deprecated: use set_text instead)"""
        log.warning("Web.type() is deprecated, use Web.set_text() instead")
        return cls.set_text(locator, text, timeout, clear_first)
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Clear failed on element: {locator}"
    )
    def clear(cls, locator: str, timeout: Optional[int] = None):
        """Clear text from an element"""
        element = cls._find_element(locator, timeout)
        element.clear()
        log.action(f"Cleared element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Submit failed on form element: {locator}"
    )
    def submit(cls, locator: str, timeout: Optional[int] = None):
        """Submit a form element"""
        element = cls._find_element(locator, timeout)
        element.submit()
        log.action(f"Submitted form element: {locator}")
    
    # Selection methods
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, text, **_: f"Select by text '{text}' failed on element: {locator}"
    )
    def select_by_text(cls, locator: str, text: str, timeout: Optional[int] = None):
        """Select option by visible text"""
        element = cls._find_element(locator, timeout)
        select = Select(element)
        select.select_by_visible_text(text)
        log.action(f"Selected option '{text}' from element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, value, **_: f"Select by value '{value}' failed on element: {locator}"
    )
    def select_by_value(cls, locator: str, value: str, timeout: Optional[int] = None):
        """Select option by value"""
        element = cls._find_element(locator, timeout)
        select = Select(element)
        select.select_by_value(value)
        log.action(f"Selected option with value '{value}' from element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, index, **_: f"Select by index {index} failed on element: {locator}"
    )
    def select_by_index(cls, locator: str, index: int, timeout: Optional[int] = None):
        """Select option by index"""
        element = cls._find_element(locator, timeout)
        select = Select(element)
        select.select_by_index(index)
        log.action(f"Selected option at index {index} from element: {locator}")
    
    # Wait methods
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for element failed: {locator}"
    )
    def wait_for_element(cls, locator: str, timeout: Optional[int] = None):
        """Wait for element to be present"""
        cls._find_element(locator, timeout)
        log.action(f"Element found: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for visible failed: {locator}"
    )
    def wait_for_visible(cls, locator: str, timeout: Optional[int] = None):
        """Wait for element to be visible"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.visibility_of_element_located((by, value)))
            log.action(f"Element is visible: {locator}")
        except TimeoutException:
            raise TimeoutException(f"Element not visible: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for clickable failed: {locator}"
    )
    def wait_for_clickable(cls, locator: str, timeout: Optional[int] = None):
        """Wait for element to be clickable"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.element_to_be_clickable((by, value)))
            log.action(f"Element is clickable: {locator}")
        except TimeoutException:
            raise TimeoutException(f"Element not clickable: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    def sleep(cls, seconds: float):
        """Sleep for specified seconds"""
        time.sleep(seconds)
        log.action(f"Slept for {seconds} seconds")
    
    # Verification methods
    @classmethod
    def element_exists(cls, locator: str, timeout: Optional[int] = None) -> bool:
        """Check if element exists"""
        try:
            cls._find_element(locator, timeout)
            return True
        except NoSuchElementException:
            return False
    
    @classmethod
    def element_visible(cls, locator: str, timeout: Optional[int] = None) -> bool:
        """Check if element is visible"""
        try:
            cls.wait_for_visible(locator, timeout)
            return True
        except TimeoutException:
            return False
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Get text failed on element: {locator}"
    )
    def get_text(cls, locator: str, timeout: Optional[int] = None) -> str:
        """Get text content of element"""
        element = cls._find_element(locator, timeout)
        text = element.text
        log.action(f"Got text '{text}' from element: {locator}")
        return text
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, attribute, **_: f"Get attribute '{attribute}' failed on element: {locator}"
    )
    def get_attribute(cls, locator: str, attribute: str, timeout: Optional[int] = None) -> str:
        """Get attribute value of element"""
        element = cls._find_element(locator, timeout)
        value = element.get_attribute(attribute)
        log.action(f"Got attribute '{attribute}' = '{value}' from element: {locator}")
        return value
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, expected_text, **_: f"Verify text '{expected_text}' failed on element: {locator}"
    )
    def verify_text(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text matches expected"""
        actual_text = cls.get_text(locator, timeout)
        if actual_text != expected_text:
            raise AssertionError(f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'")
        log.action(f"Text verified: '{expected_text}' in element: {locator}")
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, expected_text, **_: f"Verify text contains '{expected_text}' failed on element: {locator}"
    )
    def verify_text_contains(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text contains expected text"""
        actual_text = cls.get_text(locator, timeout)
        if expected_text not in actual_text:
            raise AssertionError(f"Text '{expected_text}' not found in actual text: '{actual_text}'")
        log.action(f"Text contains verified: '{expected_text}' in element: {locator}")
    
    # Browser management
    @classmethod
    def set_timeout(cls, seconds: int):
        """Set default wait timeout"""
        cls._wait_timeout = seconds
        log.action(f"Default timeout set to {seconds} seconds")
    
    @classmethod
    def maximize_window(cls):
        """Maximize browser window"""
        driver = cls._get_driver()
        driver.maximize_window()
        log.action("Browser window maximized")
    
    @classmethod
    def set_window_size(cls, width: int, height: int):
        """Set browser window size"""
        driver = cls._get_driver()
        driver.set_window_size(width, height)
        log.action(f"Window size set to {width}x{height}")
    
    @classmethod
    def get_title(cls) -> str:
        """Get page title"""
        driver = cls._get_driver()
        title = driver.title
        log.action(f"Page title: {title}")
        return title
    
    @classmethod
    def get_url(cls) -> str:
        """Get current URL"""
        driver = cls._get_driver()
        url = driver.current_url
        log.action(f"Current URL: {url}")
        return url
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda filename=None, **_: f"Take screenshot failed: {filename or 'auto-generated'}"
    )
    def take_screenshot(cls, filename: str = None) -> str:
        """Take screenshot and return path"""
        driver = cls._get_driver()
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        path = driver.save_screenshot(filename)
        log.action(f"Screenshot saved: {filename}")
        return filename
    
    @classmethod
    def close(cls):
        """Close current browser window"""
        driver = get_context('web_driver')
        if driver:
            driver.close()
            log.info("Browser window closed")
    
    @classmethod
    def quit(cls):
        """Quit browser and end session (thread-safe)"""
        with cls._lock:
            driver = get_context('web_driver')
            if driver:
                try:
                    driver.quit()
                    log.info("Browser session ended")
                except Exception as e:
                    log.warning(f"Error during quit: {e}")
                finally:
                    from ..thread_context import delete_context
                    delete_context('web_driver')
    
    @classmethod
    def is_driver_alive(cls) -> bool:
        """Check if driver is still alive and responsive"""
        driver = get_context('web_driver')
        if driver is None:
            return False
        
        try:
            # Try a simple operation to test if driver is responsive
            driver.current_url
            return True
        except Exception:
            return False
    
    @classmethod
    def get_driver_status(cls) -> dict:
        """Get driver status for debugging"""
        driver = get_context('web_driver')
        return {
            "driver_exists": driver is not None,
            "driver_alive": cls.is_driver_alive(),
            "current_url": cls.get_url() if cls.is_driver_alive() else None,
            "window_handles": len(driver.window_handles) if cls.is_driver_alive() and driver else 0
        }
    
    @classmethod
    def reset_driver(cls):
        """Reset driver for clean state between test cases (thread-safe)"""
        with cls._lock:
            driver = get_context('web_driver')
            if driver:
                try:
                    driver.quit()
                    log.debug("Driver quit successfully")
                except Exception as e:
                    log.warning(f"Error quitting driver: {e}")
                    # Force kill any remaining processes
                    try:
                        import psutil
                        import os
                        current_pid = os.getpid()
                        for proc in psutil.process_iter(['pid', 'name']):
                            if proc.info['name'] in ['chrome.exe', 'firefox.exe', 'msedge.exe']:
                                # Don't kill current process
                                if proc.info['pid'] != current_pid:
                                    try:
                                        proc.terminate()
                                    except:
                                        pass
                    except ImportError:
                        # psutil not available, continue without force kill
                        pass
                finally:
                    # Clear driver from thread context
                    from ..thread_context import delete_context
                    delete_context('web_driver')
                    log.info("Driver reset for next test case")