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
import functools
import re
from typing import Union, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..browser_factory import BrowserFactory
from ..thread_context import get_context, set_context
from ..guard import orbs_guard
from ..exception import WebActionException
from ..log import log
from .locator import WebElementEntity
from .failure_handling import FailureHandling, handle_failure
from ..config import config

def track_keyword(func):
    """Decorator to track keyword execution in live logger for non-BDD test cases"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        live_logger = get_context("live_logger")
        testcase = get_context("current_testcase")
        
        if live_logger and testcase:
            testcase_id = testcase.replace("\\", "/").replace(".py", "")
            
            # Build keyword description with arguments
            keyword_name = func.__name__
            
            # Helper to extract locator string
            def get_locator_str(locator):
                """Extract human-readable string from locator"""
                from .locator import WebElementEntity
                
                # Check if it's our WebElementEntity first (from object repository)
                if isinstance(locator, WebElementEntity):
                    return locator.name if locator.name else "object_repository_element"
                elif isinstance(locator, str):
                    # Plain string locator
                    return locator[:80]
                elif hasattr(locator, 'locator'):
                    # Some wrapper object with locator attribute
                    return str(locator.locator)
                else:
                    # Unknown type - try to get primary locator or use repr
                    if hasattr(locator, 'get_primary_locator'):
                        try:
                            strategy, value = locator.get_primary_locator()
                            return f"{strategy}={value[:60]}"
                        except:
                            pass
                    return str(type(locator).__name__)
            
            # Extract meaningful object description from args
            # args[0] is cls for classmethod, args[1:] are actual function arguments
            object_parts = []
            
            # Handle different keywords with their specific arguments
            if len(args) > 1:
                if keyword_name == "set_text" and len(args) > 2:
                    # set_text(locator, text, ...)
                    locator = args[1]
                    text = args[2] if len(args) > 2 else kwargs.get('text', '')
                    locator_str = get_locator_str(locator)
                    text_str = str(text)[:50]
                    object_parts = [locator_str, f'"{text_str}"']
                
                elif keyword_name == "click":
                    # click(locator, ...)
                    locator = args[1]
                    locator_str = get_locator_str(locator)
                    object_parts = [locator_str]
                
                elif keyword_name == "verify_element_visible":
                    # verify_element_visible(locator, ...)
                    locator = args[1]
                    locator_str = get_locator_str(locator)
                    object_parts = [locator_str]
                
                elif keyword_name == "open":
                    # open(url)
                    url = args[1]
                    object_parts = [str(url)]
                
                elif keyword_name == "take_screenshot":
                    # take_screenshot(filename)
                    filename = args[1] if len(args) > 1 else kwargs.get('filename', 'auto')
                    object_parts = [str(filename)]
                
                else:
                    # Generic handling
                    first_arg = args[1]
                    object_parts = [get_locator_str(first_arg) if not isinstance(first_arg, str) else first_arg[:80]]
            
            object_desc = " ".join(object_parts) if object_parts else None
            
            # Log step start - it returns the step_id
            step_id = live_logger.step_started(
                testcase_id=testcase_id,
                keyword=keyword_name.upper(),
                object_name=object_desc
            )
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                live_logger.step_passed(testcase_id=testcase_id, step_id=step_id, duration=duration)
                
                # Auto-screenshot after action (if enabled)
                if keyword_name != "take_screenshot" and config.get_bool("screenshot_after_action", False):
                    try:
                        driver = get_context('web_driver')
                        if driver:
                            import datetime
                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                            ss_name = f"after_{keyword_name}_{ts}.png"
                            driver.save_screenshot(ss_name)
                            # Store caption for this screenshot
                            screenshots = get_context("screenshots") or []
                            if screenshots:
                                captions = get_context("screenshot_captions") or {}
                                caption = f"{keyword_name.upper()} {object_desc or ''}".strip()
                                captions[screenshots[-1]] = caption
                                set_context("screenshot_captions", captions)
                    except Exception:
                        pass  # Don't fail the test for screenshot issues
                
                # Store step data for report (non-BDD test cases)
                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": keyword_name.upper(),
                    "name": object_desc or "",
                    "status": "PASSED",
                    "duration": round(duration, 2),
                    "error": None
                })
                set_context("keyword_steps", keyword_steps)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                live_logger.step_failed(testcase_id=testcase_id, step_id=step_id, duration=duration, error=error_msg)
                
                # Store failed step data for report (non-BDD test cases)
                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": keyword_name.upper(),
                    "name": object_desc or "",
                    "status": "FAILED",
                    "duration": round(duration, 2),
                    "error": error_msg
                })
                set_context("keyword_steps", keyword_steps)
                
                raise
        else:
            # No live logger or testcase context, just execute normally
            result = func(*args, **kwargs)
            if func.__name__ != "take_screenshot" and config.get_bool("screenshot_after_action", False):
                try:
                    driver = get_context('web_driver')
                    if driver:
                        import datetime
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        ss_name = f"after_{func.__name__}_{ts}.png"
                        driver.save_screenshot(ss_name)
                except Exception:
                    pass
            return result
    
    return wrapper


# Standalone function for easier syntax
def find_test_obj(xml_path: str, timeout: Optional[int] = None):
    """
    Find element from object repository XML with self-healing (standalone function)
    
    This is a convenience function that can be used directly without the Web class prefix.
    Perfect for inline usage with other Web keywords.
    
    Args:
        xml_path: Path to the XML file in object repository 
                 (e.g., "object_repository\\input_login-button.xml")
        timeout: Maximum time to wait for the element (default: 10s)
        
    Returns:
        WebElement: The found element
        
    Raises:
        FileNotFoundError: If XML file not found
        NoSuchElementException: If element not found with any locator
        
    Example:
        # Direct usage
        find_test_obj("object_repository\\input_username.xml").send_keys("admin")
        
        # With Web keywords
        Web.set_text(find_test_obj("object_repository\\input_username.xml"), "admin")
        Web.click(find_test_obj("object_repository\\button_login.xml"))
    """
    # Accept either full relative path (e.g. "object_repository/input.xml")
    # or just a filename (e.g. "input.xml"). If a bare filename is provided,
    # resolve it inside the project's `object_repository/` folder for convenience.
    adj = xml_path
    if '/' not in xml_path and '\\' not in xml_path:
        adj = f"object_repository/{xml_path}"
    return Web.find_test_obj(adj, timeout)


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
                    # Update wait timeout from execution.properties
                    explicit_timeout = config.get_int("explicit_timeout", 10)
                    cls._wait_timeout = explicit_timeout
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
    def _resolve_element(cls, locator_or_element: Union[str, WebElement], timeout: Optional[int] = None) -> WebElement:
        """
        Resolve element from locator string or WebElement
        
        Args:
            locator_or_element: Either a locator string (e.g., "id=login") or a WebElement
            timeout: Timeout for finding element if locator string is provided
            
        Returns:
            WebElement
        """
        if isinstance(locator_or_element, WebElement):
            return locator_or_element
        elif isinstance(locator_or_element, str):
            return cls._find_element(locator_or_element, timeout)
        else:
            raise TypeError(f"Expected str or WebElement, got {type(locator_or_element)}")
    
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
    
    @classmethod
    def _find_element_with_healing(cls, locators: List[tuple], timeout: Optional[int] = None) -> tuple:
        """
        Try multiple locators with self-healing
        
        Args:
            locators: List of (strategy, value) tuples to try
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (WebElement, locator_string, locator_index)
            
        Raises:
            NoSuchElementException: If element not found with any locator
        """
        driver = cls._get_driver()
        wait_time = timeout or cls._wait_timeout
        
        # Check if self-healing is enabled
        self_healing_enabled = config.get_bool("self_healing_enabled", True)
        max_attempts = config.get_int("self_healing_max_attempts", 5) if self_healing_enabled else 1
        
        # Limit locators to try based on self-healing config
        locators_to_try = locators[:max_attempts] if self_healing_enabled else locators[:1]
        
        if not self_healing_enabled and len(locators) > 1:
            log.debug(f"Self-healing disabled, using primary locator only (not trying {len(locators) - 1} alternatives)")
        
        last_exception = None
        
        for idx, (strategy, value) in enumerate(locators_to_try):
            try:
                # Convert strategy to locator string
                locator_str = f"{strategy}={value}"
                by, val = cls._parse_locator(locator_str)
                
                wait = WebDriverWait(driver, min(wait_time, 3))  # Use shorter timeout for alternatives
                element = wait.until(EC.presence_of_element_located((by, val)))
                
                # Log if we used a fallback locator
                if idx > 0:
                    log.info(f"Self-healing: Element found using alternative locator #{idx + 1}: {strategy}={value}")
                
                return element, locator_str, idx
                
            except (TimeoutException, NoSuchElementException) as e:
                last_exception = e
                continue
        
        # If we get here, none of the locators worked
        tried_count = len(locators_to_try)
        total_count = len(locators)
        
        if self_healing_enabled and tried_count < total_count:
            error_msg = f"Element not found with {tried_count} locators (tried {tried_count}/{total_count}, timeout: {wait_time}s)"
        else:
            error_msg = f"Element not found with any of the {tried_count} locators (timeout: {wait_time}s)"
        
        raise NoSuchElementException(error_msg) from last_exception
    
    @classmethod
    def find_test_obj(cls, xml_path: str, timeout: Optional[int] = None) -> WebElement:
        """
        Find element from object repository XML with self-healing
        
        This keyword loads element locators from a WebElementEntity XML file
        and attempts to find the element using the primary locator first,
        then falls back to alternative locators if needed (self-healing).
        
        Args:
            xml_path: Path to the XML file in object repository 
                     (e.g., "object_repository/input_login-button.xml")
            timeout: Maximum time to wait for the element (default: _wait_timeout)
            
        Returns:
            WebElement: The found element
            
        Raises:
            FileNotFoundError: If XML file not found
            NoSuchElementException: If element not found with any locator
            
        Example:
            element = Web.find_test_obj("object_repository/input_login-button.xml")
            element.click()
        """
        # Allow shorthand filenames like "input_username.xml" by resolving
        # them under the project's `object_repository/` directory.
        adj_path = xml_path
        if '/' not in xml_path and '\\' not in xml_path:
            adj_path = f"object_repository/{xml_path}"

        # Parse the XML file
        web_element = WebElementEntity(adj_path)
        
        # Get all locators (primary + alternatives)
        locators = web_element.get_all_locators()
        
        if not locators:
            raise ValueError(f"No valid locators found in {xml_path}")
        
        log.info(f"Finding element '{web_element.name}' from {xml_path} "
                f"(primary: {locators[0][0]}={locators[0][1]}, {len(locators) - 1} alternatives)")
        
        # Try to find element with self-healing
        try:
            element, used_locator, locator_idx = cls._find_element_with_healing(locators, timeout)
            
            if locator_idx == 0:
                log.action(f"Found '{web_element.name}' using primary locator: {used_locator}")
            else:
                log.action(f"Found '{web_element.name}' using alternative locator ({locator_idx + 1}/{len(locators)}): {used_locator}")
            
            return element
            
        except NoSuchElementException as e:
            log.error(f"Failed to find '{web_element.name}' from {adj_path}")
            raise
    
    # Navigation methods
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda url, **_: f"Failed to open URL: {url}"
    )
    def open(cls, url: str, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Open a URL in the browser
        
        Args:
            url: URL to navigate to
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
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
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Click failed on element: {locator}"
    )
    def click(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Click on an element with retry logic for stale elements
        
        Args:
            locator: Element locator string (e.g., 'id=login') or WebElement object
            timeout: Wait timeout in seconds
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                # Support both string locator and WebElement
                if isinstance(locator, WebElement):
                    element = locator
                else:
                    driver = cls._get_driver()
                    by, value = cls._parse_locator(locator)
                    wait = WebDriverWait(driver, wait_time)
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
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Double click failed on element: {locator}"
    )
    def double_click(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Double click on an element
        
        Args:
            locator: Element locator string or WebElement object
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        element = cls._resolve_element(locator, timeout)
        driver = cls._get_driver()
        
        actions = ActionChains(driver)
        actions.double_click(element).perform()
        log.action(f"Double clicked element: {locator}")
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Right click failed on element: {locator}"
    )
    def right_click(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Right click on an element
        
        Args:
            locator: Element locator string or WebElement object
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        element = cls._resolve_element(locator, timeout)
        driver = cls._get_driver()
        
        actions = ActionChains(driver)
        actions.context_click(element).perform()
        log.action(f"Right clicked element: {locator}")
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, text, **_: f"Set text '{text}' failed on element: {locator}"
    )
    def set_text(cls, locator: Union[str, WebElement], text: str, timeout: Optional[int] = None, clear_first: bool = True, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Set text into an element with retry logic
        
        Args:
            locator: Element locator string (e.g., 'id=username') or WebElement object
            text: Text to input
            timeout: Wait timeout in seconds
            clear_first: Clear existing text before typing
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                # Support both string locator and WebElement
                if isinstance(locator, WebElement):
                    element = locator
                else:
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
    def clear(cls, locator: Union[str, WebElement], timeout: Optional[int] = None):
        """Clear text from an element"""
        element = cls._resolve_element(locator, timeout)
        log.action(f"Cleared element: {locator}")
        element.clear()
    
    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Submit failed on form element: {locator}"
    )
    def submit(cls, locator: Union[str, WebElement], timeout: Optional[int] = None):
        """Submit a form element"""
        element = cls._resolve_element(locator, timeout)
        log.action(f"Submitted form element: {locator}")
        element.submit()
    
    # Selection methods
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, text, **_: f"Select by text '{text}' failed on element: {locator}"
    )
    def select_by_text(cls, locator: Union[str, WebElement], text: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Select option by visible text"""
        element = cls._resolve_element(locator, timeout)
        select = Select(element)
        select.select_by_visible_text(text)
        log.action(f"Selected option '{text}' from element: {locator}")
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, value, **_: f"Select by value '{value}' failed on element: {locator}"
    )
    def select_by_value(cls, locator: Union[str, WebElement], value: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Select option by value"""
        element = cls._resolve_element(locator, timeout)
        select = Select(element)
        select.select_by_value(value)
        log.action(f"Selected option with value '{value}' from element: {locator}")
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, index, **_: f"Select by index {index} failed on element: {locator}"
    )
    def select_by_index(cls, locator: Union[str, WebElement], index: int, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Select option by index"""
        element = cls._resolve_element(locator, timeout)
        select = Select(element)
        select.select_by_index(index)
        log.action(f"Selected option at index {index} from element: {locator}")
    
    # Wait methods
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for element failed: {locator}"
    )
    def wait_for_element(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Wait for element to be present"""
        element = cls._resolve_element(locator, timeout)
        log.action(f"Element found: {locator}")
        return element
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for visible failed: {locator}"
    )
    def wait_for_visible(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Wait for element to be visible"""
        driver = cls._get_driver()
        wait_time = timeout or cls._wait_timeout
        
        try:
            # If already a WebElement, check if displayed
            if isinstance(locator, WebElement):
                wait = WebDriverWait(driver, wait_time)
                wait.until(lambda d: locator.is_displayed())
                log.action(f"Element is visible: {locator}")
                return locator
            
            # If string locator, use standard WebDriverWait
            by, value = cls._parse_locator(locator)
            wait = WebDriverWait(driver, wait_time)
            element = wait.until(EC.visibility_of_element_located((by, value)))
            log.action(f"Element is visible: {locator}")
            return element
        except TimeoutException:
            raise TimeoutException(f"Element not visible: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Wait for clickable failed: {locator}"
    )
    def wait_for_clickable(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Wait for element to be clickable"""
        driver = cls._get_driver()
        wait_time = timeout or cls._wait_timeout
        
        try:
            # If already a WebElement, check if displayed and enabled
            if isinstance(locator, WebElement):
                wait = WebDriverWait(driver, wait_time)
                wait.until(lambda d: locator.is_displayed() and locator.is_enabled())
                log.action(f"Element is clickable: {locator}")
                return locator
            
            # If string locator, use standard WebDriverWait
            by, value = cls._parse_locator(locator)
            wait = WebDriverWait(driver, wait_time)
            element = wait.until(EC.element_to_be_clickable((by, value)))
            log.action(f"Element is clickable: {locator}")
            return element
        except TimeoutException:
            raise TimeoutException(f"Element not clickable: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    def sleep(cls, seconds: float):
        """Sleep for specified seconds"""
        time.sleep(seconds)
        log.action(f"Slept for {seconds} seconds")


    # Verification methods
    @classmethod
    def element_exists(cls, locator: Union[str, WebElement], timeout: Optional[int] = None) -> bool:
        """Check if element exists"""
        try:
            # If already WebElement, check if it's still valid
            if isinstance(locator, WebElement):
                try:
                    # Try to access an attribute to check if element is still valid
                    locator.is_enabled()
                    return True
                except:
                    return False
            # If string locator, try to find it
            cls._find_element(locator, timeout)
            return True
        except NoSuchElementException:
            return False
    
    @classmethod
    def element_visible(cls, locator: Union[str, WebElement], timeout: Optional[int] = None) -> bool:
        """Check if element is visible"""
        try:
            # If already WebElement, check if displayed
            if isinstance(locator, WebElement):
                return locator.is_displayed()
            # If string locator, wait for visibility
            cls.wait_for_visible(locator, timeout)
            return True
        except TimeoutException:
            return False
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Get text failed on element: {locator}"
    )
    def get_text(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE) -> str:
        """Get text content of element"""
        element = cls._resolve_element(locator, timeout)
        text = element.text
        log.action(f"Got text '{text}' from element: {locator}")
        return text
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, attribute, **_: f"Get attribute '{attribute}' failed on element: {locator}"
    )
    def get_attribute(cls, locator: Union[str, WebElement], attribute: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE) -> str:
        """Get attribute value of element"""
        element = cls._resolve_element(locator, timeout)
        value = element.get_attribute(attribute)
        log.action(f"Got attribute '{attribute}' = '{value}' from element: {locator}")
        return value
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, expected_text, **_: f"Verify text '{expected_text}' failed on element: {locator}"
    )
    def verify_text(cls, locator: Union[str, WebElement], expected_text: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Verify element text matches expected"""
        actual_text = cls.get_text(locator, timeout)
        if actual_text != expected_text:
            raise AssertionError(f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'")
        log.action(f"Text verified: '{expected_text}' in element: {locator}")
    
    # verify element visible
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Verify element visible failed: {locator}"
    )
    def verify_element_visible(cls, locator: Union[str, WebElement], timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Verify element is visible"""
        if not cls.element_visible(locator, timeout):
            raise AssertionError(f"Element not visible: {locator}")
        log.action(f"Element visibility verified: {locator}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda text, **_: f"Verify text present failed: '{text}'"
    )
    def verify_text_present(cls, text: str, is_regex: bool = False, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Verify that text is present anywhere on the page.
        
        Args:
            text: Text to search for (plain string or regex pattern)
            is_regex: If True, treat text as a regex pattern
            timeout: Not used, kept for API consistency
            failure_handling: How to handle failure (STOP_ON_FAILURE or CONTINUE_ON_FAILURE)
        """
        driver = cls._get_driver()
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if is_regex:
            if not re.search(text, body_text):
                raise AssertionError(f"Text pattern '{text}' not found on page")
        else:
            if text not in body_text:
                raise AssertionError(f"Text '{text}' not found on page")
        log.action(f"Text present verified: '{text}' (regex={is_regex})")

    @classmethod
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, expected_text, **_: f"Verify text contains '{expected_text}' failed on element: {locator}"
    )
    def verify_text_contains(cls, locator: Union[str, WebElement], expected_text: str, timeout: Optional[int] = None):
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
    @track_keyword
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
    @track_keyword
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


def __getattr__(name):
    """Proxy module-level function calls to Web class methods."""
    if hasattr(Web, name):
        def wrapper(*args, **kwargs):
            return getattr(Web, name)(*args, **kwargs)
        return wrapper
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__():
    return sorted(list(globals().keys()) + [m for m in dir(Web) if not m.startswith("_")])
