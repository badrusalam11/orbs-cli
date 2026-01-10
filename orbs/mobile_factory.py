import os
import subprocess
import time
from appium import webdriver
from appium.options.common.base import AppiumOptions
from orbs.config import config
from orbs.exception import MobileDriverException
from orbs.guard import orbs_guard
from orbs.thread_context import get_context, set_context

class MobileFactory:
    @staticmethod
    @orbs_guard(MobileDriverException)
    def _restart_uiautomator2():
        """Restart UiAutomator2 server to fix hanging issues"""
        try:
            subprocess.run(["adb", "shell", "am", "force-stop", "io.appium.uiautomator2.server"], 
                         timeout=10, capture_output=True)
            subprocess.run(["adb", "shell", "am", "force-stop", "io.appium.uiautomator2.server.test"], 
                         timeout=10, capture_output=True)
            time.sleep(2)  # Wait for processes to fully stop
            print("UiAutomator2 server restarted successfully")
        except Exception as e:
            print(f"Warning: Could not restart UiAutomator2: {e}")
    
    @staticmethod
    def create_driver(
        app_package: str = None,
        app_activity: str = None,
        capabilities: dict = None,
        retry_count: int = 2
    ):
        server_url = config.get("appium_url", "http://localhost:4723/wd/hub")
        platform = config.get("platformName", "Android")
        
        # Use context to determine device name or fallback to config
        device_name = get_context("platform", "")
        if not device_name:
            device_name = config.get("deviceName", "")

        # Use user-provided or config-based capabilities
        extra_caps = capabilities or config.get_dict("capabilities") or {}

        for attempt in range(retry_count + 1):
            try:
                options = AppiumOptions()
                options.platform_name = platform
                options.device_name = device_name

                # Add session stability capabilities
                options.set_capability("newCommandTimeout", 300)  # 5 minutes timeout
                options.set_capability("noReset", True)  # Don't reset app state
                options.set_capability("autoLaunch", True)  # Auto launch app
                options.set_capability("automationName", "UiAutomator2")
                options.set_capability("uiautomator2ServerLaunchTimeout", 60000)  # 60 seconds
                options.set_capability("uiautomator2ServerInstallTimeout", 60000)  # 60 seconds

                # Injected appPackage and appActivity override config
                final_app_package = app_package or config.get("appPackage", None)
                final_app_activity = app_activity or config.get("appActivity", None)

                if final_app_package and final_app_activity:
                    options.set_capability("appPackage", final_app_package)
                    options.set_capability("appActivity", final_app_activity)

                for key, value in extra_caps.items():
                    options.set_capability(key, value)

                driver = webdriver.Remote(
                    command_executor=server_url,
                    options=options
                )
                
                # Test session immediately
                try:
                    driver.current_activity  # Quick session validation
                    print(f"Driver created successfully on attempt {attempt + 1}")
                    break
                except Exception as session_error:
                    driver.quit()
                    raise session_error
                    
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retry_count:
                    print("Restarting UiAutomator2 and retrying...")
                    MobileFactory._restart_uiautomator2()
                    time.sleep(3)
                else:
                    raise Exception(f"Failed to create driver after {retry_count + 1} attempts. Last error: {e}")

        # Setup screenshot wrapper
        MobileFactory._setup_screenshot_wrapper(driver)
        return driver
    
    @staticmethod
    def _setup_screenshot_wrapper(driver):
        """Setup screenshot wrapper with better error handling"""
        if get_context("screenshots") is None:
            set_context("screenshots", [])

        original = driver.get_screenshot_as_file

        def save_to_report(path, *args, **kwargs):
            if not os.path.isabs(path):
                rpt = get_context("report")
                try:
                    base = rpt.screenshots_dir
                except Exception:
                    base = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(base, exist_ok=True)
                path = os.path.join(base, path)
            
            abs_path = os.path.abspath(path)
            shots = get_context("screenshots") or []
            
            try:
                # Session validation with retry
                for validation_attempt in range(2):
                    try:
                        driver.current_activity  # Session check
                        break
                    except Exception as session_error:
                        if validation_attempt == 0:
                            print(f"Session validation failed, retrying... ({session_error})")
                            time.sleep(2)
                        else:
                            raise session_error
                
                # Take screenshot
                result = original(path, *args, **kwargs)
                shots.append(abs_path)
                set_context("screenshots", shots)
                return result
                
            except Exception as e:
                import logging
                logging.warning(f"Failed to capture screenshot '{path}': {e}")
                
                # Create placeholder
                try:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path + ".error", "w") as f:
                        f.write(f"Screenshot failed: {str(e)}")
                except:
                    pass
                
                raise e

        driver.get_screenshot_as_file = save_to_report
