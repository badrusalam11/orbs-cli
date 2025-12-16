# File: orbs/keyword/mobile.py
"""
Mobile automation keywords for Orbs framework
Provides high-level Appium operations with automatic driver management
"""

import time
import threading
from typing import Union, List, Optional, Dict, Any
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from ..mobile_factory import MobileFactory
from ..thread_context import get_context, set_context


class Mobile:
    """High-level mobile automation keywords"""
    
    _driver = None
    _wait_timeout = 10
    _lock = threading.Lock()
    
    @classmethod
    def _get_driver(cls):
        """Get or create the mobile driver instance (thread-safe)"""
        if cls._driver is None:
            with cls._lock:
                if cls._driver is None:
                    cls._driver = MobileFactory.create_driver()
                    set_context('mobile_driver', cls._driver)
        return cls._driver
    
    @classmethod
    def use_driver(cls, driver):
        """Use an existing driver instance"""
        with cls._lock:
            cls._driver = driver
            set_context('mobile_driver', driver)
        return driver
    
    @classmethod
    def sync_with_context(cls, behave_context):
        """Sync Mobile driver with behave context"""
        with cls._lock:
            if hasattr(behave_context, 'driver') and behave_context.driver:
                cls._driver = behave_context.driver
                set_context('mobile_driver', behave_context.driver)
            else:
                behave_context.driver = cls._get_driver()
        return cls._driver
    
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
    def launch_app(cls):
        """Launch the application"""
        driver = cls._get_driver()
        driver.launch_app()
        print("App launched")
    
    @classmethod
    def close_app(cls):
        """Close the application"""
        driver = cls._get_driver()
        driver.close_app()
        print("App closed")
    
    @classmethod
    def reset_app(cls):
        """Reset the application"""
        driver = cls._get_driver()
        driver.reset()
        print("App reset")
    
    @classmethod
    def activate_app(cls, bundle_id: str):
        """Activate app by bundle ID"""
        driver = cls._get_driver()
        driver.activate_app(bundle_id)
        print(f"Activated app: {bundle_id}")
    
    @classmethod
    def terminate_app(cls, bundle_id: str):
        """Terminate app by bundle ID"""
        driver = cls._get_driver()
        driver.terminate_app(bundle_id)
        print(f"Terminated app: {bundle_id}")
    
    # Element interaction methods
    @classmethod
    def tap(cls, locator: str, timeout: Optional[int] = None, retry_count: int = 3):
        """Tap on an element with retry logic"""
        wait_time = timeout or cls._wait_timeout
        
        for attempt in range(retry_count):
            try:
                driver = cls._get_driver()
                by, value = cls._parse_locator(locator)
                wait = WebDriverWait(driver, wait_time)
                
                element = wait.until(EC.element_to_be_clickable((by, value)))
                element.click()
                print(f"Tapped element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1:
                    print(f"Stale element detected, retrying tap on {locator} (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"Tap failed, retrying: {e}")
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    def long_press(cls, locator: str, duration: int = 1000, timeout: Optional[int] = None):
        """Long press on an element"""
        from appium.webdriver.common.touch_action import TouchAction
        
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        action = TouchAction(driver)
        action.long_press(element, duration=duration).release().perform()
        print(f"Long pressed element: {locator} for {duration}ms")
    
    @classmethod
    def double_tap(cls, locator: str, timeout: Optional[int] = None):
        """Double tap on an element"""
        element = cls._find_element(locator, timeout)
        driver = cls._get_driver()
        
        driver.execute_script("mobile: doubleClickGesture", {
            "elementId": element.id
        })
        print(f"Double tapped element: {locator}")
    
    @classmethod
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
                print(f"Set text '{text}' into mobile element: {locator}")
                return
                
            except StaleElementReferenceException:
                if attempt < retry_count - 1:
                    print(f"Stale element detected, retrying set_text on {locator} (attempt {attempt + 1})")
                    time.sleep(0.5)
                    continue
                else:
                    raise
            except Exception as e:
                if attempt < retry_count - 1:
                    print(f"Set text failed, retrying: {e}")
                    time.sleep(0.5)
                    continue
                else:
                    raise
    
    @classmethod
    def clear_text(cls, locator: str, timeout: Optional[int] = None):
        """Clear text from an element"""
        element = cls._find_element(locator, timeout)
        element.clear()
        print(f"Cleared mobile element: {locator}")
    
    # Gesture methods
    @classmethod
    def swipe(cls, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000):
        """Swipe from start coordinates to end coordinates"""
        driver = cls._get_driver()
        driver.swipe(start_x, start_y, end_x, end_y, duration)
        print(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    
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
    def scroll_to_element(cls, locator: str, max_scrolls: int = 5, direction: str = "up"):
        """Scroll until element is found"""
        for i in range(max_scrolls):
            if cls.element_exists(locator, timeout=2):
                print(f"Found element after {i} scrolls: {locator}")
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
    def wait_for_element(cls, locator: str, timeout: Optional[int] = None):
        """Wait for element to be present"""
        cls._find_element(locator, timeout)
        print(f"Mobile element found: {locator}")
    
    @classmethod
    def wait_for_visible(cls, locator: str, timeout: Optional[int] = None):
        """Wait for element to be visible"""
        driver = cls._get_driver()
        by, value = cls._parse_locator(locator)
        wait_time = timeout or cls._wait_timeout
        
        try:
            wait = WebDriverWait(driver, wait_time)
            wait.until(EC.visibility_of_element_located((by, value)))
            print(f"Mobile element is visible: {locator}")
        except TimeoutException:
            raise TimeoutException(f"Mobile element not visible: {locator} (timeout: {wait_time}s)")
    
    @classmethod
    def sleep(cls, seconds: float):
        """Sleep for specified seconds"""
        time.sleep(seconds)
        print(f"Slept for {seconds} seconds")
    
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
    def get_text(cls, locator: str, timeout: Optional[int] = None) -> str:
        """Get text content of element"""
        element = cls._find_element(locator, timeout)
        text = element.text
        print(f"Got text '{text}' from mobile element: {locator}")
        return text
    
    @classmethod
    def get_attribute(cls, locator: str, attribute: str, timeout: Optional[int] = None) -> str:
        """Get attribute value of element"""
        element = cls._find_element(locator, timeout)
        value = element.get_attribute(attribute)
        print(f"Got attribute '{attribute}' = '{value}' from mobile element: {locator}")
        return value
    
    @classmethod
    def verify_text(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text matches expected"""
        actual_text = cls.get_text(locator, timeout)
        if actual_text != expected_text:
            raise AssertionError(f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'")
        print(f"Text verified: '{expected_text}' in mobile element: {locator}")
    
    @classmethod
    def verify_text_contains(cls, locator: str, expected_text: str, timeout: Optional[int] = None):
        """Verify element text contains expected text"""
        actual_text = cls.get_text(locator, timeout)
        if expected_text not in actual_text:
            raise AssertionError(f"Text '{expected_text}' not found in actual text: '{actual_text}'")
        print(f"Text contains verified: '{expected_text}' in mobile element: {locator}")
    
    # Device management
    @classmethod
    def set_timeout(cls, seconds: int):
        """Set default wait timeout"""
        cls._wait_timeout = seconds
        print(f"Default mobile timeout set to {seconds} seconds")
    
    @classmethod
    def get_device_size(cls) -> Dict[str, int]:
        """Get device screen size"""
        driver = cls._get_driver()
        size = driver.get_window_size()
        print(f"Device size: {size}")
        return size
    
    @classmethod
    def get_orientation(cls) -> str:
        """Get device orientation"""
        driver = cls._get_driver()
        orientation = driver.orientation
        print(f"Device orientation: {orientation}")
        return orientation
    
    @classmethod
    def set_orientation(cls, orientation: str):
        """Set device orientation (PORTRAIT or LANDSCAPE)"""
        driver = cls._get_driver()
        driver.orientation = orientation.upper()
        print(f"Set device orientation to: {orientation}")
    
    @classmethod
    def take_screenshot(cls, filename: str = None) -> str:
        """Take screenshot and return path"""
        driver = cls._get_driver()
        if filename is None:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mobile_screenshot_{timestamp}.png"
        
        path = driver.save_screenshot(filename)
        print(f"Mobile screenshot saved: {filename}")
        return filename
    
    @classmethod
    def back(cls):
        """Press device back button"""
        driver = cls._get_driver()
        driver.back()
        print("Pressed back button")
    
    @classmethod
    def hide_keyboard(cls):
        """Hide device keyboard"""
        driver = cls._get_driver()
        try:
            driver.hide_keyboard()
            print("Keyboard hidden")
        except Exception:
            print("No keyboard to hide")
    
    # Driver management
    @classmethod
    def reset_driver(cls):
        """Reset driver for clean state between test cases (thread-safe)"""
        with cls._lock:
            if cls._driver:
                try:
                    cls._driver.quit()
                    print("Mobile driver quit successfully")
                except Exception as e:
                    print(f"Warning: Error quitting mobile driver: {e}")
                finally:
                    cls._driver = None
                    print("Mobile driver reset for next test case")
    
    @classmethod
    def quit(cls):
        """Quit mobile driver and end session (thread-safe)"""
        with cls._lock:
            if cls._driver:
                try:
                    cls._driver.quit()
                    print("Mobile session ended")
                except Exception as e:
                    print(f"Warning: Error during mobile quit: {e}")
                finally:
                    cls._driver = None
    
    @classmethod
    def is_driver_alive(cls) -> bool:
        """Check if mobile driver is still alive and responsive"""
        if cls._driver is None:
            return False
        
        try:
            cls._driver.get_window_size()
            return True
        except Exception:
            return False
    
    @classmethod
    def get_driver_status(cls) -> dict:
        """Get mobile driver status for debugging"""
        return {
            "driver_exists": cls._driver is not None,
            "driver_alive": cls.is_driver_alive(),
            "device_size": cls.get_device_size() if cls.is_driver_alive() else None,
            "orientation": cls.get_orientation() if cls.is_driver_alive() else None
        }