# File: orbs/keyword/mobile.py
"""
Mobile automation keywords for Orbs framework
Provides high-level Appium operations with automatic driver management

IMPORTANT: This class uses thread-local storage for driver instances to support
parallel test execution. Each thread gets its own driver instance stored in 
thread context, preventing driver conflicts when running multiple test suites
concurrently with different mobile platform configurations.
"""

import time
import threading
import functools
from typing import Union, List, Optional, Dict, Any
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..mobile_factory import MobileFactory
from ..thread_context import get_context, set_context
from ..log import log
from ..guard import orbs_guard
from ..exception import MobileActionException
from .failure_handling import FailureHandling, handle_failure


def track_keyword(func):
    """Decorator to track mobile keyword execution in live logger"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        live_logger = get_context("live_logger")
        testcase = get_context("current_testcase")

        if live_logger and testcase:
            testcase_id = testcase.replace("\\", "/").replace(".py", "")
            keyword_name = func.__name__

            # Build object description from args
            object_parts = []
            if len(args) > 1:
                if keyword_name in ("tap", "click", "long_press", "double_tap",
                                    "wait_for_element", "wait_for_visible",
                                    "verify_element_exists", "verify_element_visible",
                                    "clear_text", "get_text"):
                    object_parts = [str(args[1])[:80]]
                elif keyword_name in ("set_text", "type_text") and len(args) > 2:
                    object_parts = [str(args[1])[:80], f'"{str(args[2])[:50]}"']
                elif keyword_name in ("verify_text", "verify_text_contains") and len(args) > 2:
                    object_parts = [str(args[1])[:80], f'expected="{str(args[2])[:50]}"']
                elif keyword_name == "launch":
                    app_id = args[1] if len(args) > 1 else kwargs.get("id")
                    if app_id:
                        object_parts = [str(app_id)[:80]]
                elif keyword_name == "launch_and_install":
                    object_parts = [str(args[1])[:80]]
                elif keyword_name in ("activate_app", "terminate_app"):
                    object_parts = [str(args[1])[:80]]
                elif keyword_name == "take_screenshot":
                    filename = args[1] if len(args) > 1 else kwargs.get("filename", "auto")
                    object_parts = [str(filename)]
                elif keyword_name == "swipe" and len(args) > 4:
                    object_parts = [f"({args[1]},{args[2]}) → ({args[3]},{args[4]})"]
                elif keyword_name in ("swipe_up", "swipe_down", "swipe_left", "swipe_right"):
                    pass  # no extra info needed, keyword name is descriptive
                elif keyword_name == "scroll_to_element":
                    object_parts = [str(args[1])[:80]]
                elif keyword_name == "get_attribute" and len(args) > 2:
                    object_parts = [str(args[1])[:80], f'attr="{args[2]}"']
                elif keyword_name == "set_orientation":
                    object_parts = [str(args[1]).upper()]
                elif keyword_name == "sleep":
                    object_parts = [f"{args[1]}s"]
                else:
                    object_parts = [str(args[1])[:80]]

            object_desc = " ".join(object_parts) if object_parts else None

            step_id = live_logger.step_started(
                testcase_id=testcase_id,
                keyword=f"Mobile.{keyword_name.upper()}",
                object_name=object_desc
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                live_logger.step_passed(testcase_id=testcase_id, step_id=step_id, duration=duration)

                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": f"Mobile.{keyword_name.upper()}",
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

                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": f"Mobile.{keyword_name.upper()}",
                    "name": object_desc or "",
                    "status": "FAILED",
                    "duration": round(duration, 2),
                    "error": error_msg
                })
                set_context("keyword_steps", keyword_steps)

                raise
        else:
            return func(*args, **kwargs)

    return wrapper


class Mobile:
    """High-level mobile automation keywords"""
    
    _wait_timeout = 10
    _lock = threading.Lock()
    
    @classmethod
    def _get_driver(cls):
        """Get or create the mobile driver instance (thread-safe, thread-local)"""
        # Use thread context to store driver per thread
        driver = get_context('mobile_driver')
        if driver is None:
            with cls._lock:
                # Double-check in case another thread just created it
                driver = get_context('mobile_driver')
                if driver is None:
                    driver = MobileFactory.create_driver()
                    set_context('mobile_driver', driver)
        return driver

    @classmethod
    def _get_bare_driver(cls):
        """Create a bare Appium session without launching any app (for install-then-launch flow)"""
        with cls._lock:
            driver = MobileFactory.create_driver(skip_app_launch=True)
            set_context('mobile_driver', driver)
        return driver
    
    @classmethod
    def use_driver(cls, driver):
        """Use an existing driver instance"""
        set_context('mobile_driver', driver)
        return driver
    
    @classmethod
    def sync_with_context(cls, behave_context):
        """Sync Mobile driver with behave context"""
        if hasattr(behave_context, 'driver') and behave_context.driver:
            set_context('mobile_driver', behave_context.driver)
        else:
            behave_context.driver = cls._get_driver()
        return get_context('mobile_driver')
    
    @classmethod
    def _parse_locator(cls, locator: str) -> tuple:
        """
        Parse locator string into Appium locator
        Supported formats:
        - id=element_id
        - xpath=//android.widget.TextView[@text='test']
        - accessibility_id=accessibility_identifier
        - class=android.widget.Button
        - android_uiautomator=new UiSelector().text("Login")
        - ios_predicate=name == "Login"
        - ios_class_chain=**/XCUIElementTypeButton[`name == "Login"`]
        """
        if '=' not in locator:
            # Default to accessibility_id if no strategy specified
            return AppiumBy.ACCESSIBILITY_ID, locator
            
        strategy, value = locator.split('=', 1)
        strategy = strategy.lower().strip()
        value = value.strip()
        
        strategy_map = {
            'id': AppiumBy.ID,
            'xpath': AppiumBy.XPATH,
            'accessibility_id': AppiumBy.ACCESSIBILITY_ID,
            'class': AppiumBy.CLASS_NAME,
            'android_uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
            'ios_predicate': AppiumBy.IOS_PREDICATE,
            'ios_class_chain': AppiumBy.IOS_CLASS_CHAIN,
            'name': AppiumBy.NAME,
            'tag': AppiumBy.TAG_NAME
        }
        
        if strategy not in strategy_map:
            raise ValueError(f"Unsupported mobile locator strategy: {strategy}. "
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
            raise NoSuchElementException(f"Mobile element not found: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    def _find_elements(cls, locator: str, timeout: Optional[int] = None) -> List[WebElement]:
        """Find multiple elements with wait"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.presence_of_element_located((by, value)))
            return driver.find_elements(by, value)
        except TimeoutException:
            return []
    
    # App management methods
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda id=None, activity=None, **_: f"Launch app failed: {id or 'default'}/{activity or 'default'}"
    )
    def launch(cls, id: Optional[str] = None, activity: Optional[str] = None, reset: bool = False):
        """
        Launch an application with optional app package and activity.
        If id and activity are not provided, uses configuration from settings/appium.properties.
        
        Args:
            id: App package ID (e.g., 'com.android.chrome')
            activity: App main activity (e.g., 'com.google.android.apps.chrome.Main')
            reset: Whether to reset app state before launching
        
        Examples:
            # From config
            Mobile.launch()
            
            # Specific app
            Mobile.launch("com.android.chrome", "com.google.android.apps.chrome.Main")
            
            # With reset
            Mobile.launch("com.example.app", ".MainActivity", True)
            
            # Keyword args
            Mobile.launch(id="com.android.chrome", activity=".Main", reset=True)
        """
        driver = cls._get_driver()
        
        # Reset app if requested (reinstall and clear data)
        if reset:
            try:
                # Try to terminate first if app is running
                if id:
                    driver.terminate_app(id)
            except:
                pass
            
            try:
                driver.reset_app()
                log.action("App reset")
            except (AttributeError, Exception):
                # Fallback for older Appium versions
                log.debug("Reset not supported, continuing without reset")
        
        # If id and activity provided, start specific app
        if id and activity:
            try:
                # Try new Appium 2.x method (mobile command)
                driver.execute_script('mobile: startActivity', {
                    'intent': f'{id}/{activity}'
                })
                log.action(f"Launched app: {id}/{activity}")
            except:
                try:
                    # Fallback: try older start_activity method
                    driver.start_activity(id, activity)
                    log.action(f"Launched app: {id}/{activity}")
                except AttributeError:
                    # Last resort: just activate the app
                    driver.activate_app(id)
                    log.action(f"Activated app: {id} (activity parameter ignored)")
        elif id:
            # Just activate the app by package id
            driver.activate_app(id)
            log.action(f"Activated app: {id}")
        else:
            # Use default from capabilities
            driver.launch_app()
            log.action("App launched (from config)")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda apk, **_: f"Launch and install failed: {apk}"
    )
    def launch_and_install(cls, apk: str, id: Optional[str] = None, activity: Optional[str] = None, reset: bool = False):
        """
        Install APK and launch the application.
        
        Args:
            apk: Path to APK file (absolute or relative)
            id: App package ID (optional, will read from mobile.properties if not provided)
            activity: App main activity (optional, will read from mobile.properties if not provided)
            reset: Whether to reset app state after installation
        
        Example:
            # Auto-read from config
            Mobile.launch_and_install("apk/sauce_labs.apk")
            
            # Explicit app details
            Mobile.launch_and_install(
                apk="/apps/chrome.apk",
                id="com.android.chrome",
                activity=".Main",
                reset=True
            )
        """
        import os
        apk_path = os.path.abspath(apk) if not os.path.isabs(apk) else apk

        if not os.path.exists(apk_path):
            raise FileNotFoundError(f"APK file not found: {apk_path}")

        # Reset any existing session, then create a BARE session (no app launch)
        # This prevents Appium from trying to launch an app that isn't installed yet
        cls.reset_driver()
        driver = cls._get_bare_driver()

        driver.install_app(apk_path)
        log.action(f"App installed: {apk_path}")

        # If id/activity not provided, read from config
        if not id and not activity:
            from ..config import config as mobile_config
            id = mobile_config.get("appPackage", None)
            activity = mobile_config.get("appActivity", None)
            if id:
                log.debug(f"Read from config - appPackage: {id}, appActivity: {activity or 'none'}")

        # Launch the app (app is now installed, this will succeed)
        if id and activity:
            cls.launch(id=id, activity=activity, reset=reset)
        elif id:
            driver.activate_app(id)
            log.action(f"Activated app: {id}")
        else:
            log.warning("App installed but no app package/activity provided or found in config. Call Mobile.launch() manually.")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda bundle_id, **_: f"Activate app failed: {bundle_id}"
    )
    def activate_app(cls, bundle_id: str):
        """Activate app by bundle ID"""
        driver = cls._get_driver()
        driver.activate_app(bundle_id)
        log.action(f"Activated app: {bundle_id}")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda bundle_id, **_: f"Terminate app failed: {bundle_id}"
    )
    def terminate_app(cls, bundle_id: str):
        """Terminate app by bundle ID"""
        driver = cls._get_driver()
        driver.terminate_app(bundle_id)
        log.action(f"Terminated app: {bundle_id}")
    
    # Element interaction methods
    @classmethod
    def click(cls, locator: str, timeout: Optional[int] = None, retry_count: int = 3):
        """Click/tap on an element with retry logic (alias for tap)"""
        return cls.tap(locator, timeout, retry_count)
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Tap failed on element: {locator}"
    )
    def tap(cls, locator: str, timeout: Optional[int] = None, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Tap on an element with retry logic
        
        Args:
            locator: Element locator string
            timeout: Wait timeout in seconds
            retry_count: Number of retry attempts
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                driver = cls._get_driver()
                by, value = cls._parse_locator(locator)
                wait = WebDriverWait(driver, wait_time)
                
                element = wait.until(EC.element_to_be_clickable((by, value)))
                element.click()
                log.action(f"Tapped element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1:
                    log.debug(f"Stale element detected, retrying tap on {locator} (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < retry_count - 1:
                    log.debug(f"Tap failed, retrying: {e}")
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Long press failed on element: {locator}"
    )
    def long_press(cls, locator: str, duration: int = 1000, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Long press on an element
        
        Args:
            locator: Element locator string
            duration Duration in milliseconds
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        try:
            # Try Appium 2.x W3C Actions API
            actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            actions.pointer_action.move_to(element)
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(duration / 1000)  # Convert ms to seconds
            actions.pointer_action.pointer_up()
            actions.perform()
            log.action(f"Long pressed element: {locator} for {duration}ms")
        except Exception as e1:
            try:
                # Fallback to TouchAction (Appium 1.x)
                from appium.webdriver.common.touch_action import TouchAction
                action = TouchAction(driver)
                action.long_press(element, duration=duration).release().perform()
                log.action(f"Long pressed element: {locator} for {duration}ms")
            except Exception as e2:
                log.warning(f"Long press failed with both methods: {e1}, {e2}")
                raise
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Double tap failed on element: {locator}"
    )
    def double_tap(cls, locator: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Double tap on an element
        
        Args:
            locator: Element locator string
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        try:
            # Try Appium 2.x mobile command
            driver.execute_script("mobile: doubleClickGesture", {
                "elementId": element.id
            })
            log.action(f"Double tapped element: {locator}")
        except Exception:
            # Fallback: just tap twice
            element.click()
            time.sleep(0.1)
            element.click()
            log.action(f"Double tapped element (fallback): {locator}")
    
    @classmethod
    def type_text(cls, locator: str, text: str, timeout: Optional[int] = None, clear_first: bool = True, retry_count: int = 3):
        """Type text into an element (alias for set_text)"""
        return cls.set_text(locator, text, timeout, clear_first, retry_count)
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, text, **_: f"Set text '{text}' failed on element: {locator}"
    )
    def set_text(cls, locator: str, text: str, timeout: Optional[int] = None, clear_first: bool = True, retry_count: int = 3, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Set text into an element with retry logic
        
        Args:
            locator: Element locator string
            text: Text to input
            timeout: Wait timeout in seconds
            clear_first: Clear existing text before typing
            retry_count: Number of retry attempts
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
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
                log.action(f"Set text '{text}' into mobile element: {locator}")
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
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Clear text failed on element: {locator}"
    )
    def clear_text(cls, locator: str, timeout: Optional[int] = None):
        """Clear text from an element"""
        element = cls._find_element(locator, timeout)
        element.clear()
        log.action(f"Cleared mobile element: {locator}")
    
    # Gesture methods
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda start_x, start_y, end_x, end_y, **_: f"Swipe failed from ({start_x}, {start_y}) to ({end_x}, {end_y})"
    )
    def swipe(cls, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000):
        """Swipe from start coordinates to end coordinates"""
        driver = cls._get_driver()
        
        try:
            # Try legacy swipe method (Appium 1.x)
            driver.swipe(start_x, start_y, end_x, end_y, duration)
            log.action(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        except AttributeError:
            # Fallback to W3C Actions API (Appium 2.x)
            try:
                from selenium.webdriver.common.actions import interaction
                from selenium.webdriver.common.actions.action_builder import ActionBuilder
                from selenium.webdriver.common.actions.pointer_input import PointerInput
                
                actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
                actions.pointer_action.move_to_location(start_x, start_y)
                actions.pointer_action.pointer_down()
                actions.pointer_action.pause(duration / 1000 / 2)  # Half duration for movement
                actions.pointer_action.move_to_location(end_x, end_y)
                actions.pointer_action.pointer_up()
                actions.perform()
                log.action(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            except Exception as e:
                log.warning(f"Swipe failed: {e}")
                raise
    
    @classmethod
    def swipe_up(cls, start_x: Optional[int] = None, distance: int = 500, duration: int = 1000):
        """Swipe up from bottom of screen"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        
        start_x = start_x or size['width'] // 2
        start_y = size['height'] - 100
        end_y = start_y - distance
        
        cls.swipe(start_x, start_y, start_x, end_y, duration)
    
    @classmethod
    def swipe_down(cls, start_x: Optional[int] = None, distance: int = 500, duration: int = 1000):
        """Swipe down from top of screen"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        
        start_x = start_x or size['width'] // 2
        start_y = 100
        end_y = start_y + distance
        
        cls.swipe(start_x, start_y, start_x, end_y, duration)
    
    @classmethod
    def swipe_left(cls, start_y: Optional[int] = None, distance: int = 300, duration: int = 1000):
        """Swipe left"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        
        start_y = start_y or size['height'] // 2
        start_x = size['width'] - 100
        end_x = start_x - distance
        
        cls.swipe(start_x, start_y, end_x, start_y, duration)
    
    @classmethod
    def swipe_right(cls, start_y: Optional[int] = None, distance: int = 300, duration: int = 1000):
        """Swipe right"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        
        start_y = start_y or size['height'] // 2
        start_x = 100
        end_x = start_x + distance
        
        cls.swipe(start_x, start_y, end_x, start_y, duration)
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Scroll to element failed: {locator}"
    )
    def scroll_to_element(cls, locator: str, max_scrolls: int = 5, direction: str = "up"):
        """Scroll until element is found"""
        for i in range(max_scrolls):
            if cls.element_exists(locator, timeout=2):
                log.action(f"Found element after {i} scrolls: {locator}")
                return cls._find_element(locator)
            
            if direction.lower() == "up":
                cls.swipe_up()
            elif direction.lower() == "down":
                cls.swipe_down()
            else:
                raise ValueError("Direction must be 'up' or 'down'")
                
            time.sleep(1)
        
        raise NoSuchElementException(f"Element not found after {max_scrolls} scrolls: {locator}")
    
    # Wait methods
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Wait for element failed: {locator}"
    )
    def wait_for_element(cls, locator: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Wait for element to be present
        
        Args:
            locator: Element locator string
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        cls._find_element(locator, timeout)
        log.action(f"Mobile element found: {locator}")
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Wait for visible failed: {locator}"
    )
    def wait_for_visible(cls, locator: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE):
        """Wait for element to be visible
        
        Args:
            locator: Element locator string
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        """
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.visibility_of_element_located((by, value)))
            log.action(f"Mobile element is visible: {locator}")
        except TimeoutException:
            raise TimeoutException(f"Mobile element not visible: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    @track_keyword
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
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Get text failed for element: {locator}"
    )
    def get_text(cls, locator: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE) -> str:
        """Get text content of element
        
        Args:
            locator: Element locator string
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        
        Returns:
            str: Text content of the element
        """
        element = cls._find_element(locator, timeout)
        text = element.text
        log.action(f"Got text '{text}' from mobile element: {locator}")
        return text
    
    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, attribute, **_: f"Get attribute '{attribute}' failed for element: {locator}"
    )
    def get_attribute(cls, locator: str, attribute: str, timeout: Optional[int] = None, failure_handling: FailureHandling = FailureHandling.STOP_ON_FAILURE) -> str:
        """Get attribute value of element
        
        Args:
            locator: Element locator string
            attribute: Attribute name
            timeout: Wait timeout in seconds
            failure_handling: How to handle failures (STOP_ON_FAILURE, CONTINUE_ON_FAILURE, OPTIONAL)
        
        Returns:
            str: Attribute value
        """
        element = cls._find_element(locator, timeout)
        value = element.get_attribute(attribute)
        log.action(f"Got attribute '{attribute}' = '{value}' from mobile element: {locator}")
        return value
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, expected, **_: f"Verify text '{expected}' failed for element: {locator}"
    )
    def verify_text(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text matches expected"""
        actual_text = cls.get_text(locator, timeout)
        if actual_text != expected_text:
            raise AssertionError(f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'")
        log.action(f"Text verified: '{expected_text}' in mobile element: {locator}")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, expected, **_: f"Verify text contains '{expected}' failed for element: {locator}"
    )
    def verify_text_contains(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text contains expected text"""
        actual_text = cls.get_text(locator, timeout)
        if expected_text not in actual_text:
            raise AssertionError(f"Text '{expected_text}' not found in actual text: '{actual_text}'")
        log.action(f"Text contains verified: '{expected_text}' in mobile element: {locator}")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Verify element exists failed for: {locator}"
    )
    def verify_element_exists(cls, locator: str, timeout: Optional[int] = None):
        """Verify that element exists"""
        if not cls.element_exists(locator, timeout):
            raise AssertionError(f"Expected mobile element to exist but it does not: {locator}")
        log.action(f"Element existence verified: {locator}")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda locator, **_: f"Verify element visible failed for: {locator}"
    )
    def verify_element_visible(cls, locator: str, timeout: Optional[int] = None):
        """Verify that element is visible"""
        if not cls.element_visible(locator, timeout):
            raise AssertionError(f"Expected mobile element to be visible but it is not: {locator}")
        log.action(f"Element visibility verified: {locator}")

    # Device management
    @classmethod
    def set_timeout(cls, seconds: int):
        """Set default wait timeout"""
        cls._wait_timeout = seconds
        log.action(f"Default mobile timeout set to {seconds} seconds")
    
    @classmethod
    def get_device_size(cls) -> Dict[str, int]:
        """Get device screen size"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        log.action(f"Device size: {size}")
        return size
    
    @classmethod
    def get_orientation(cls) -> str:
        """Get device orientation"""
        driver = cls._get_driver()
        orientation = driver.orientation
        log.action(f"Device orientation: {orientation}")
        return orientation
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda orientation, **_: f"Set orientation failed: {orientation}"
    )
    def set_orientation(cls, orientation: str):
        """Set device orientation (PORTRAIT or LANDSCAPE)"""
        driver = cls._get_driver()
        driver.orientation = orientation.upper()
        log.action(f"Set device orientation to: {orientation}")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda filename=None, **_: f"Take screenshot failed: {filename or 'auto'}"
    )
    def take_screenshot(cls, filename: str = None) -> str:
        """Take screenshot and return path"""
        driver = cls._get_driver()
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mobile_screenshot_{timestamp}.png"
        
        path = driver.save_screenshot(filename)
        log.action(f"Mobile screenshot saved: {filename}")
        return filename
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda **_: "Press back button failed"
    )
    def back(cls):
        """Press device back button"""
        driver = cls._get_driver()
        driver.back()
        log.action("Pressed back button")
    
    @classmethod
    @track_keyword
    @orbs_guard(
        MobileActionException,
        context_fn=lambda **_: "Hide keyboard failed"
    )
    def hide_keyboard(cls):
        """Hide device keyboard"""
        driver = cls._get_driver()
        try:
            driver.hide_keyboard()
            log.action("Keyboard hidden")
        except AttributeError:
            # Try mobile command for Appium 2.x
            try:
                driver.execute_script('mobile: hideKeyboard')
                log.action("Keyboard hidden")
            except Exception:
                log.debug("No keyboard to hide or method not supported")
        except Exception:
            log.debug("No keyboard to hide")
    
    # Driver management
    @classmethod
    def reset_driver(cls):
        """Reset driver for clean state between test cases (thread-safe)"""
        with cls._lock:
            driver = get_context('mobile_driver')
            if driver:
                try:
                    driver.quit()
                    log.debug("Mobile driver quit successfully")
                except Exception as e:
                    log.warning(f"Error quitting mobile driver: {e}")
                finally:
                    from ..thread_context import delete_context
                    delete_context('mobile_driver')
                    log.info("Mobile driver reset for next test case")
    
    @classmethod
    @track_keyword
    def quit(cls):
        """Quit mobile driver and end session (thread-safe)"""
        with cls._lock:
            driver = get_context('mobile_driver')
            if driver:
                try:
                    driver.quit()
                    log.info("Mobile session ended")
                except Exception as e:
                    log.warning(f"Error during mobile quit: {e}")
                finally:
                    from ..thread_context import delete_context
                    delete_context('mobile_driver')
    
    @classmethod
    def is_driver_alive(cls) -> bool:
        """Check if mobile driver is still alive and responsive"""
        driver = get_context('mobile_driver')
        if driver is None:
            return False
        
        try:
            driver.get_window_size()
            return True
        except Exception:
            return False
    
    @classmethod
    def get_driver_status(cls) -> dict:
        """Get mobile driver status for debugging"""
        driver = get_context('mobile_driver')
        return {
            "driver_exists": driver is not None,
            "driver_alive": cls.is_driver_alive(),
            "device_size": cls.get_device_size() if cls.is_driver_alive() else None,
            "orientation": cls.get_orientation() if cls.is_driver_alive() else None
        }