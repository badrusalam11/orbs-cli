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
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Union, List, Optional, Dict
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
                
                # Check if it's a ResolvableElement (from find_test_obj)
                # Use hasattr to avoid circular import issues
                if hasattr(locator, '_json_path') and hasattr(locator, '_name'):
                    # It's a ResolvableElement - use __str__ which returns filename
                    return str(locator)
                # Check if it's our WebElementEntity first (from object repository)
                elif isinstance(locator, WebElementEntity):
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
                    secret = kwargs.get('secret', False)
                    locator_str = get_locator_str(locator)
                    text_str = str(text)[:50]

                    from ..utils import mask_sensitive_value
                    text_str = mask_sensitive_value(text_str, locator=locator_str, secret=secret)

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


class ResolvableElement:
    """
    A wrapper that holds both WebElement and its locator information.
    This allows keywords to re-resolve the element when StaleElementReferenceException occurs.
    
    For React/dynamic apps, this class supports LAZY resolution - the element is only
    resolved when actually needed, not when find_test_obj() is called.
    """
    
    def __init__(self, element: WebElement = None, locators: List[tuple] = None, json_path: str = None, name: str = None, lazy: bool = False):
        """
        Args:
            element: The resolved WebElement (can be None if lazy=True)
            locators: List of (strategy, value) tuples for re-resolving
            json_path: Original JSON path (for caching)
            name: Element name (for logging)
            lazy: If True, element will be resolved on first access
        """
        self._element = element
        self._locators = locators or []
        self._json_path = json_path
        self._name = name or "element"
        self._lazy = lazy
        self._resolved = element is not None
    
    @property
    def element(self) -> WebElement:
        """Get the underlying WebElement, resolving lazily if needed"""
        if not self._resolved or self._element is None:
            self._resolve_now()
        return self._element
    
    def _resolve_now(self):
        """Resolve the element now"""
        if not self._locators:
            raise ValueError("Cannot resolve: no locators available")
        
        # Import here to avoid circular dependency
        element, used_locator, _ = Web._find_element_with_healing(
            self._locators, None, self._json_path
        )
        self._element = element
        self._resolved = True
        log.debug(f"Lazy-resolved element '{self._name}' using: {used_locator}")
    
    def re_resolve(self, web_cls, timeout: Optional[int] = None) -> WebElement:
        """Re-resolve the element using stored locators"""
        if not self._locators:
            raise ValueError("Cannot re-resolve: no locators available")
        
        element, used_locator, _ = web_cls._find_element_with_healing(
            self._locators, timeout, self._json_path
        )
        self._element = element
        self._resolved = True
        log.debug(f"Re-resolved element '{self._name}' using: {used_locator}")
        return element
    
    def __str__(self) -> str:
        """Return readable name for logging and reports"""
        # Return the json_path as-is for clear tracing
        if self._json_path:
            return self._json_path
        return self._name or "element"
    
    def __repr__(self) -> str:
        """Return readable representation"""
        return self.__str__()
    
    # Delegate common WebElement methods to make it work like a WebElement
    def __getattr__(self, name):
        """Delegate attribute access to the underlying WebElement"""
        return getattr(self.element, name)


# Standalone function for easier syntax
def find_test_obj(json_path: str, timeout: Optional[int] = None) -> ResolvableElement:
    """
    Find element from object repository JSON with self-healing (standalone function)
    
    This is a convenience function that can be used directly without the Web class prefix.
    Perfect for inline usage with other Web keywords.
    
    Args:
        json_path: Path to the JSON file in object repository 
                 (e.g., "input_login-button.json" or "subfolder/input_login-button.json")
        timeout: Maximum time to wait for the element (default: 10s)
        
    Returns:
        ResolvableElement: A wrapper containing the WebElement that can be re-resolved on stale errors
        
    Raises:
        FileNotFoundError: If JSON file not found
        NoSuchElementException: If element not found with any locator
        
    Example:
        # Direct usage with filename
        find_test_obj("input_username.json").send_keys("admin")
        
        # With subfolder
        find_test_obj("sauce_demo/input_username.json").send_keys("admin")
        
        # With Web keywords - auto handles stale element!
        Web.set_text(find_test_obj("input_username.json"), "admin")
        Web.click(find_test_obj("button_login.json"))
    """
    # Pass through to Web.find_test_obj - path resolution is handled by WebElementEntity
    return Web.find_test_obj(json_path, timeout)


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
    def _resolve_element(cls, locator_or_element: Union[str, WebElement, 'WebElementEntity'], timeout: Optional[int] = None) -> WebElement:
        """
        Resolve element from locator string, WebElement, or WebElementEntity
        
        Args:
            locator_or_element: Either a locator string (e.g., "id=login"), WebElement, or WebElementEntity
            timeout: Timeout for finding element if locator string is provided
            
        Returns:
            WebElement
        """
        if isinstance(locator_or_element, WebElement):
            return locator_or_element
        elif isinstance(locator_or_element, str):
            return cls._find_element(locator_or_element, timeout)
        elif isinstance(locator_or_element, WebElementEntity):
            # Re-find element using WebElementEntity (supports self-healing)
            locators = locator_or_element.get_all_locators()
            if not locators:
                raise ValueError(f"No valid locators found in WebElementEntity: {locator_or_element.name}")
            
            # Use json_path for caching
            json_filename = locator_or_element.json_path.replace('\\', '/')
            element, _, _ = cls._find_element_with_healing(locators, timeout, json_filename)
            return element
        else:
            raise TypeError(f"Expected str, WebElement, or WebElementEntity, got {type(locator_or_element)}")
    
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
    
    # Class variable to store project root for caching
    _cache_project_root: Optional[Path] = None
    
    @classmethod
    def _set_cache_project_root(cls, json_path: str):
        """
        Set project root path from object repository JSON path.
        e.g., if json_path resolves to /project/object_repository/subfolder/file.json
        then project root is /project/
        """
        if cls._cache_project_root is not None:
            return  # Already set
        
        try:
            # Find the actual path of the JSON file
            normalized = json_path.replace('\\', '/')
            if not normalized.startswith('object_repository/'):
                normalized = f"object_repository/{normalized}"
            
            log.info(f"🔍 Setting cache project root, looking for: {normalized}")
            
            # Search for the file
            current = Path.cwd()
            log.info(f"🔍 Current working directory: {current}")
            
            for parent in [current] + list(current.parents):
                potential = parent / normalized
                if potential.exists():
                    log.info(f"🔍 Found JSON at: {potential}")
                    # Found! Project root is the parent of object_repository
                    # e.g., /project/object_repository/file.json -> /project/
                    obj_repo_path = potential.parent
                    while obj_repo_path.name != 'object_repository' and obj_repo_path != obj_repo_path.parent:
                        obj_repo_path = obj_repo_path.parent
                    
                    if obj_repo_path.name == 'object_repository':
                        cls._cache_project_root = obj_repo_path.parent
                        log.info(f"✅ Cache project root set to: {cls._cache_project_root}")
                    break
            
            # Fallback to cwd if not found
            if cls._cache_project_root is None:
                cls._cache_project_root = current
                log.info(f"⚠️ Cache project root fallback to cwd: {cls._cache_project_root}")
        except Exception as e:
            import traceback
            log.warning(f"❌ Failed to set cache project root: {e}")
            log.warning(f"Traceback: {traceback.format_exc()}")
            cls._cache_project_root = Path.cwd()
    
    @classmethod
    def _get_cache_file_path(cls) -> Path:
        """Get path to resolved locator cache file"""
        project_root = cls._cache_project_root or Path.cwd()
        cache_dir = project_root / ".cache"
        return cache_dir / "resolved_locator.json"
    
    @classmethod
    def _load_locator_cache(cls) -> Dict:
        """Load resolved locator cache from .cache/resolved_locator.json"""
        try:
            cache_file = cls._get_cache_file_path()
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.debug(f"Failed to load locator cache: {e}")
        return {}
    
    @classmethod
    def _save_locator_cache(cls, cache_data: Dict):
        """Save resolved locator cache to .cache/resolved_locator.json"""
        try:
            cache_file = cls._get_cache_file_path()
            log.debug(f"Saving cache to: {cache_file}")
            cache_file.parent.mkdir(parents=True, exist_ok=True)  # Ensure .cache dir exists
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=4, ensure_ascii=False)
            log.info(f"✅ Cache saved to: {cache_file}")
        except Exception as e:
            import traceback
            log.warning(f"❌ Failed to save locator cache: {e}")
            log.warning(f"Traceback: {traceback.format_exc()}")
    
    @classmethod
    def _get_cached_locator(cls, json_filename: str) -> Optional[tuple]:
        """
        Get cached locator for a test object
        
        Args:
            json_filename: Just the filename (e.g., "input_username.json")
            
        Returns:
            Tuple of (strategy, value) if cached, None otherwise
        """
        try:
            environment = get_context("environment") or "dev"
            cache = cls._load_locator_cache()
            
            if environment in cache and json_filename in cache[environment]:
                cached = cache[environment][json_filename]
                # Cache format: {"xpath": "//input[@id='username']", "last_update": "..."}
                # Return first strategy/value pair (excluding last_update)
                for key, value in cached.items():
                    if key != "last_update":
                        log.debug(f"Cache hit for '{json_filename}' in env '{environment}': {key}={value}")
                        return (key, value)
        except Exception as e:
            log.debug(f"Failed to get cached locator: {e}")
        return None
    
    @classmethod
    def _save_cached_locator(cls, json_filename: str, strategy: str, value: str):
        """
        Save successful locator to cache
        
        Args:
            json_filename: Just the filename (e.g., "input_username.json")
            strategy: Locator strategy (e.g., "xpath", "id")
            value: Locator value
        """
        try:
            environment = get_context("environment") or "dev"
            log.info(f"💾 Caching locator for '{json_filename}' in env '{environment}'...")
            
            cache = cls._load_locator_cache()
            
            if environment not in cache:
                cache[environment] = {}
            
            cache[environment][json_filename] = {
                strategy: value,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            cls._save_locator_cache(cache)
        except Exception as e:
            import traceback
            log.warning(f"❌ Failed to save cached locator: {e}")
            log.warning(f"Traceback: {traceback.format_exc()}")
    
    @classmethod
    def _check_locators_via_js(cls, locators: List[tuple]) -> Dict[int, int]:
        """
        Fast check of multiple locators via JavaScript injection.
        
        Returns a dict mapping locator index -> element count found.
        This is MUCH faster than looping through Selenium calls.
        
        Args:
            locators: List of (strategy, value) tuples to check
            
        Returns:
            Dict[int, int]: {locator_index: element_count}
        """
        driver = cls._get_driver()
        
        # Build JavaScript to check all locators at once
        js_code = """
        function countElements(locators) {
            var results = {};
            for (var i = 0; i < locators.length; i++) {
                var loc = locators[i];
                var strategy = loc[0];
                var value = loc[1];
                var count = 0;
                
                try {
                    if (strategy === 'xpath') {
                        var xpathResult = document.evaluate(value, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                        count = xpathResult.snapshotLength;
                    } else if (strategy === 'css') {
                        count = document.querySelectorAll(value).length;
                    } else if (strategy === 'id') {
                        var el = document.getElementById(value);
                        count = el ? 1 : 0;
                    } else if (strategy === 'name') {
                        count = document.getElementsByName(value).length;
                    } else if (strategy === 'class') {
                        count = document.getElementsByClassName(value).length;
                    } else if (strategy === 'tag') {
                        count = document.getElementsByTagName(value).length;
                    } else if (strategy === 'link') {
                        var links = document.querySelectorAll('a');
                        for (var j = 0; j < links.length; j++) {
                            if (links[j].textContent.trim() === value) count++;
                        }
                    } else if (strategy === 'partial_link') {
                        var plinks = document.querySelectorAll('a');
                        for (var k = 0; k < plinks.length; k++) {
                            if (plinks[k].textContent.includes(value)) count++;
                        }
                    }
                } catch (e) {
                    count = 0;
                }
                
                results[i] = count;
            }
            return results;
        }
        return countElements(arguments[0]);
        """
        
        try:
            # Convert locators to JS-compatible format
            locator_list = [[strategy, value] for strategy, value in locators]
            result = driver.execute_script(js_code, locator_list)
            # Convert string keys to int (JS object keys become strings)
            return {int(k): v for k, v in result.items()} if result else {}
        except Exception as e:
            log.debug(f"JS locator check failed: {e}, falling back to sequential")
            return {}
    
    @classmethod
    def _find_element_with_healing(cls, locators: List[tuple], timeout: Optional[int] = None, json_filename: Optional[str] = None) -> tuple:
        """
        Try multiple locators with self-healing (optimized with JS pre-check and caching)
        
        Args:
            locators: List of (strategy, value) tuples to try
            timeout: Timeout in seconds
            json_filename: Filename for caching (e.g., "input_username.json")
            
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
        
        if not self_healing_enabled and len(locators) > 1:
            log.debug(f"Self-healing disabled, using primary locator only (not trying {len(locators) - 1} alternatives)")
        
        last_exception = None
        
        # === STEP 0: Try cached locator first (fastest path) ===
        if json_filename and self_healing_enabled:
            cached_locator = cls._get_cached_locator(json_filename)
            if cached_locator:
                cached_strategy, cached_value = cached_locator
                try:
                    locator_str = f"{cached_strategy}={cached_value}"
                    by, val = cls._parse_locator(locator_str)
                    
                    # Use short timeout for cached locator (it should be fast if still valid)
                    wait = WebDriverWait(driver, min(wait_time, 2))
                    element = wait.until(EC.presence_of_element_located((by, val)))
                    
                    log.info(f"Found element using cached locator: {locator_str}")
                    # Return with special index -1 to indicate cache hit
                    return element, locator_str, -1
                    
                except (TimeoutException, NoSuchElementException) as e:
                    log.debug(f"Cached locator failed, falling back to normal resolution")
                    last_exception = e
                    # Continue to normal locator resolution
        
        # Log total locators available for debugging
        log.debug(f"Finding element with {len(locators)} locators available")
        
        # === STEP 1: Try primary locator first ===
        if locators:
            primary_strategy, primary_value = locators[0]
            log.debug(f"Trying primary locator: {primary_strategy}={primary_value[:50]}...")
            try:
                locator_str = f"{primary_strategy}={primary_value}"
                by, val = cls._parse_locator(locator_str)
                
                wait = WebDriverWait(driver, wait_time)
                element = wait.until(EC.presence_of_element_located((by, val)))
                
                return element, locator_str, 0
                
            except (TimeoutException, NoSuchElementException) as e:
                log.debug(f"Primary locator failed: {type(e).__name__}")
                last_exception = e
                # Primary failed, continue to fallback
        
        # If self-healing disabled or only 1 locator, stop here
        if not self_healing_enabled or len(locators) <= 1:
            raise NoSuchElementException(f"Element not found with primary locator (timeout: {wait_time}s)") from last_exception
        
        # === STEP 2: Fast JS check for all alternative locators ===
        # Use ALL alternatives, not limited by max_attempts (that's for retry, not locator count)
        alternative_locators = locators[1:]
        
        if not alternative_locators:
            raise NoSuchElementException(f"Element not found, no alternative locators available") from last_exception
        
        log.debug(f"Primary locator failed, checking {len(alternative_locators)} alternatives via JS...")
        
        # Get element counts for all alternatives in ONE JS call
        js_counts = cls._check_locators_via_js(alternative_locators)
        
        if js_counts:
            # Log the JS check results with actual locator values
            for i, count in js_counts.items():
                if count > 0:
                    strategy, value = alternative_locators[int(i)]
                    log.debug(f"  JS found {count} element(s) with: {strategy}={value[:60]}...")
            count_summary = {f"{alternative_locators[i][0]}": js_counts.get(i, 0) for i in range(len(alternative_locators))}
            log.debug(f"JS locator check summary: {count_summary}")
            
            # Prioritize locators: first those with count=1, then count>1, ignore count=0
            prioritized = []
            
            # First: exact matches (count = 1) - most reliable
            for idx, count in js_counts.items():
                if count == 1:
                    prioritized.append((idx, count))
            
            # Second: multiple matches (count > 1) - less reliable but might work
            for idx, count in js_counts.items():
                if count > 1:
                    prioritized.append((idx, count))
            
            # === STEP 3: Try prioritized locators via Selenium ===
            for alt_idx, count in prioritized:
                strategy, value = alternative_locators[alt_idx]
                original_idx = alt_idx + 1  # +1 because primary is at index 0
                
                try:
                    locator_str = f"{strategy}={value}"
                    by, val = cls._parse_locator(locator_str)
                    
                    # Use shorter timeout since JS already confirmed element exists
                    wait = WebDriverWait(driver, min(wait_time, 2))
                    element = wait.until(EC.presence_of_element_located((by, val)))
                    
                    log.info(f"Self-healing: Element found using alternative locator #{original_idx + 1} "
                            f"(JS found {count}): {strategy}={value}")
                    
                    return element, locator_str, original_idx
                    
                except (TimeoutException, NoSuchElementException) as e:
                    last_exception = e
                    continue
            
            # If JS check found elements but Selenium couldn't get them, log it
            found_any = any(c > 0 for c in js_counts.values())
            if found_any:
                log.debug(f"JS found elements but Selenium couldn't retrieve them")
        
        # === FALLBACK: Sequential check (if JS failed or found nothing) ===
        if not js_counts:
            log.debug(f"JS check unavailable, falling back to sequential locator check")
            
            for alt_idx, (strategy, value) in enumerate(alternative_locators):
                original_idx = alt_idx + 1
                try:
                    locator_str = f"{strategy}={value}"
                    by, val = cls._parse_locator(locator_str)
                    
                    wait = WebDriverWait(driver, min(wait_time, 3))
                    element = wait.until(EC.presence_of_element_located((by, val)))
                    
                    log.info(f"Self-healing: Element found using alternative locator #{original_idx + 1}: {strategy}={value}")
                    
                    return element, locator_str, original_idx
                    
                except (TimeoutException, NoSuchElementException) as e:
                    last_exception = e
                    continue
        
        # If we get here, none of the locators worked
        tried_count = 1 + len(alternative_locators)  # primary + alternatives tried
        total_count = len(locators)
        
        if tried_count < total_count:
            error_msg = f"Element not found with {tried_count} locators (tried {tried_count}/{total_count}, timeout: {wait_time}s)"
        else:
            error_msg = f"Element not found with any of the {tried_count} locators (timeout: {wait_time}s)"
        
        raise NoSuchElementException(error_msg) from last_exception
    
    @classmethod
    def find_test_obj(cls, json_path: str, timeout: Optional[int] = None) -> 'ResolvableElement':
        """
        Find element from object repository JSON with self-healing
        
        This keyword loads element locators from a WebElementEntity JSON file
        and attempts to find the element using the primary locator first,
        then falls back to alternative locators if needed (self-healing).
        
        For React/dynamic web apps, this method uses LAZY RESOLUTION - the element
        is only resolved when actually needed (when keyword like click/set_text is called),
        not when find_test_obj() is called. This prevents stale element issues.
        
        Args:
            json_path: Path to the JSON file in object repository 
                     (e.g., "object_repository/input_login-button.json")
            timeout: Maximum time to wait for the element (default: _wait_timeout)
            
        Returns:
            ResolvableElement: A wrapper containing the WebElement that can be re-resolved on stale errors
            
        Raises:
            FileNotFoundError: If JSON file not found
            NoSuchElementException: If element not found with any locator
            
        Example:
            element = Web.find_test_obj("object_repository/input_login-button.json")
            element.click()
        """
        # Allow shorthand filenames like "input_username.json" by resolving
        # them under the project's `object_repository/` directory.
        adj_path = json_path
        if '/' not in json_path and '\\' not in json_path:
            adj_path = f"object_repository/{json_path}"

        # Set project root for caching (derives from object_repository path)
        cls._set_cache_project_root(adj_path)
        
        # Extract cache key - include subfolder for uniqueness
        # e.g., "instagram/input_r_4.json" or just "input_r_4.json"
        json_filename = json_path.replace('\\', '/')
        
        # Parse the JSON file
        web_element = WebElementEntity(adj_path)
        
        # Get all locators (primary + alternatives)
        locators = web_element.get_all_locators()
        
        if not locators:
            raise ValueError(f"No valid locators found in {json_path}")
        
        log.debug(f"Prepared element '{web_element.name}' from {json_path} "
                f"(primary: {locators[0][0]}={locators[0][1]}, {len(locators) - 1} alternatives) - will resolve lazily")
        
        # Return LAZY ResolvableElement - element will be resolved when first accessed
        # This is critical for React apps where DOM changes frequently
        return ResolvableElement(
            element=None,  # Don't resolve yet!
            locators=locators,
            json_path=json_filename,
            name=web_element.name,
            lazy=True
        )
    
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
    def click(cls, locator: Union[str, WebElement, 'WebElementEntity', 'ResolvableElement'], timeout: Optional[int] = None, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Click on an element with retry logic for stale elements
        
        Args:
            locator: Element locator string (e.g., 'id=login'), WebElement, WebElementEntity, or ResolvableElement
            timeout: Wait timeout in seconds
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException
        
        wait_time = timeout or cls._wait_timeout
        
        # Check if locator is re-resolvable
        can_re_resolve = isinstance(locator, (str, WebElementEntity, ResolvableElement))
        
        for attempt in range(retry_count):
            try:
                # ALWAYS re-resolve element fresh on each attempt for React apps
                # This is the key to handling dynamic DOM
                if isinstance(locator, ResolvableElement):
                    if attempt > 0:
                        # Re-resolve on retry - wait a bit for DOM to stabilize
                        time.sleep(0.3)
                    locator.re_resolve(cls, wait_time)
                    element = locator.element
                elif isinstance(locator, WebElement):
                    element = locator
                elif isinstance(locator, WebElementEntity):
                    element = cls._resolve_element(locator, wait_time)
                else:
                    # String locator - always get fresh element
                    driver = cls._get_driver()
                    by, value = cls._parse_locator(locator)
                    wait = WebDriverWait(driver, wait_time)
                    element = wait.until(EC.element_to_be_clickable((by, value)))
                
                driver = cls._get_driver()
                
                # Scroll element into view for React apps (element might be off-screen)
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", element)
                    time.sleep(0.1)  # Small wait for scroll to complete
                except:
                    pass  # Ignore scroll errors
                
                # Try to click directly - don't wait for clickable separately
                # This is faster and more reliable for dynamic apps
                element.click()
                log.action(f"Clicked element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1 and can_re_resolve:
                    log.debug(f"Stale element, re-resolving (attempt {attempt + 1}/{retry_count})")
                    continue
                else:
                    raise
            except ElementClickInterceptedException:
                # Element is covered by another element (overlay, modal, etc.)
                log.debug(f"Click intercepted, trying JS click (attempt {attempt + 1}/{retry_count})")
                # Try JS click immediately as fallback
                try:
                    driver = cls._get_driver()
                    if isinstance(locator, ResolvableElement):
                        locator.re_resolve(cls, wait_time)
                        element = locator.element
                    driver.execute_script("arguments[0].click();", element)
                    log.action(f"Clicked element (via JS): {locator}")
                    return
                except:
                    if attempt < retry_count - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        raise
            except ElementNotInteractableException:
                # Element found but not interactable - try JS click
                log.debug(f"Element not interactable, trying JS click (attempt {attempt + 1}/{retry_count})")
                try:
                    driver = cls._get_driver()
                    if isinstance(locator, ResolvableElement):
                        locator.re_resolve(cls, wait_time)
                        element = locator.element
                    driver.execute_script("arguments[0].click();", element)
                    log.action(f"Clicked element (via JS): {locator}")
                    return
                except:
                    if attempt < retry_count - 1:
                        time.sleep(0.5)
                        continue
                    else:
                        raise
            except TimeoutException:
                # Timeout from WebDriverWait - element not found/clickable
                if attempt < retry_count - 1:
                    log.debug(f"Timeout waiting for element, retrying (attempt {attempt + 1}/{retry_count})")
                    time.sleep(0.5)
                    continue
                else:
                    raise TimeoutException(f"Element not clickable: {locator} (timeout: {wait_time}s)")
            except Exception as e:
                if attempt < retry_count - 1:
                    log.debug(f"Click failed ({type(e).__name__}), retrying (attempt {attempt + 1}/{retry_count})")
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
    def double_click(cls, locator: Union[str, WebElement, 'WebElementEntity', 'ResolvableElement'], timeout: Optional[int] = None, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Double click on an element with retry logic for stale elements
        
        Args:
            locator: Element locator string, WebElement, WebElementEntity, or ResolvableElement
            timeout: Wait timeout in seconds
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        can_re_resolve = isinstance(locator, (str, WebElementEntity, ResolvableElement))
        
        for attempt in range(retry_count):
            try:
                if isinstance(locator, ResolvableElement):
                    element = locator.element
                else:
                    element = cls._resolve_element(locator, timeout)
                driver = cls._get_driver()
                
                actions = ActionChains(driver)
                actions.double_click(element).perform()
                log.action(f"Double clicked element: {locator}")
                return
            except StaleElementReferenceException:
                if attempt < retry_count - 1 and can_re_resolve:
                    log.debug(f"Stale element detected, re-resolving and retrying double_click (attempt {attempt + 1}/{retry_count})")
                    if isinstance(locator, ResolvableElement):
                        locator.re_resolve(cls, timeout)
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, **_: f"Right click failed on element: {locator}"
    )
    def right_click(cls, locator: Union[str, WebElement, 'WebElementEntity', 'ResolvableElement'], timeout: Optional[int] = None, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Right click on an element with retry logic for stale elements
        
        Args:
            locator: Element locator string, WebElement, WebElementEntity, or ResolvableElement
            timeout: Wait timeout in seconds
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        can_re_resolve = isinstance(locator, (str, WebElementEntity, ResolvableElement))
        
        for attempt in range(retry_count):
            try:
                if isinstance(locator, ResolvableElement):
                    element = locator.element
                else:
                    element = cls._resolve_element(locator, timeout)
                driver = cls._get_driver()
                
                actions = ActionChains(driver)
                actions.context_click(element).perform()
                log.action(f"Right clicked element: {locator}")
                return
            except StaleElementReferenceException:
                if attempt < retry_count - 1 and can_re_resolve:
                    log.debug(f"Stale element detected, re-resolving and retrying right_click (attempt {attempt + 1}/{retry_count})")
                    if isinstance(locator, ResolvableElement):
                        locator.re_resolve(cls, timeout)
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        WebActionException,
        context_fn=lambda locator, text, **_: f"Set text '{text}' failed on element: {locator}"
    )
    def set_text(cls, locator: Union[str, WebElement, 'WebElementEntity', 'ResolvableElement'], text: str, timeout: Optional[int] = None, clear_first: bool = True, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE, secret: bool = False):
        """Set text into an element with retry logic
        
        Args:
            locator: Element locator string (e.g., 'id=username'), WebElement, WebElementEntity, or ResolvableElement
            text: Text to input
            timeout: Wait timeout in seconds
            clear_first: Clear existing text before typing
            retry_count: Number of retry attempts for stale elements
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
            secret: Whether the text is sensitive and should be masked in logs and reports
        """
        from selenium.common.exceptions import ElementNotInteractableException, InvalidElementStateException
        from selenium.webdriver.common.keys import Keys
        
        wait_time = timeout or cls._wait_timeout
        driver = cls._get_driver()
        
        # Check if locator is re-resolvable
        can_re_resolve = isinstance(locator, (str, WebElementEntity, ResolvableElement))
        
        def get_fresh_element():
            """Helper to get fresh element reference"""
            if isinstance(locator, ResolvableElement):
                locator.re_resolve(cls, wait_time)
                return locator.element
            elif isinstance(locator, WebElement):
                return locator
            elif isinstance(locator, WebElementEntity):
                return cls._resolve_element(locator, wait_time)
            else:
                by, value = cls._parse_locator(locator)
                wait = WebDriverWait(driver, wait_time)
                return wait.until(EC.element_to_be_clickable((by, value)))
        
        for attempt in range(retry_count):
            try:
                # ALWAYS get fresh element on each attempt
                element = get_fresh_element()
                
                # Scroll element into view
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", element)
                    time.sleep(0.1)
                except:
                    pass
                
                # Click element first to focus (important for React inputs)
                try:
                    element.click()
                    time.sleep(0.2)  # Wait for React to re-render after click
                    # Re-resolve element after click because React might re-render DOM
                    if can_re_resolve:
                        element = get_fresh_element()
                except:
                    pass  # Ignore click/resolve errors, just try to continue
                
                # Try to clear and type
                text_set = False
                
                # Method 1: Standard clear + send_keys
                if clear_first:
                    try:
                        element.clear()
                        element.send_keys(str(text))
                        text_set = True
                    except (InvalidElementStateException, ElementNotInteractableException):
                        pass
                
                # Method 2: Select all + type (for React inputs)
                if not text_set:
                    try:
                        # Re-resolve element
                        if can_re_resolve:
                            element = get_fresh_element()
                        # Use Cmd+A on macOS, Ctrl+A on others
                        import platform
                        select_all_key = Keys.COMMAND if platform.system() == 'Darwin' else Keys.CONTROL
                        element.send_keys(select_all_key + "a")
                        element.send_keys(str(text))
                        text_set = True
                    except (InvalidElementStateException, ElementNotInteractableException):
                        pass
                
                # Method 3: JS setValue for React inputs (last resort)
                if not text_set:
                    try:
                        # Re-resolve element
                        if can_re_resolve:
                            element = get_fresh_element()
                        # Use JS to set value and trigger React events
                        driver.execute_script("""
                            var element = arguments[0];
                            var text = arguments[1];
                            
                            // Focus the element
                            element.focus();
                            
                            // Clear and set value
                            element.value = text;
                            
                            // Trigger input event for React
                            var inputEvent = new Event('input', { bubbles: true });
                            element.dispatchEvent(inputEvent);
                            
                            // Trigger change event
                            var changeEvent = new Event('change', { bubbles: true });
                            element.dispatchEvent(changeEvent);
                        """, element, str(text))
                        text_set = True
                    except Exception as js_error:
                        log.debug(f"JS setValue failed: {js_error}")
                
                if text_set:
                    from ..utils import mask_sensitive_value
                    logged_text = mask_sensitive_value(str(text), locator=locator, secret=secret)
                    log.action(f"Set text '{logged_text}' into element: {locator}")
                    return
                else:
                    raise ElementNotInteractableException(f"Could not set text on element: {locator}")
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1 and can_re_resolve:
                    log.debug(f"Stale element, re-resolving (attempt {attempt + 1}/{retry_count})")
                    time.sleep(0.3)
                    continue
                else:
                    raise
            except ElementNotInteractableException:
                if attempt < retry_count - 1:
                    log.debug(f"Element not interactable, retrying (attempt {attempt + 1}/{retry_count})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except InvalidElementStateException:
                if attempt < retry_count - 1:
                    log.debug(f"Invalid element state, retrying (attempt {attempt + 1}/{retry_count})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < retry_count - 1:
                    log.debug(f"Set text failed ({type(e).__name__}), retrying (attempt {attempt + 1}/{retry_count})")
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

