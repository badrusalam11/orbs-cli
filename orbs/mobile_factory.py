import os
import subprocess
import time
from urllib.parse import urlparse

import requests
from appium import webdriver
from appium.options.common.base import AppiumOptions
from orbs.config import setting
from orbs.exception import MobileDriverException
from orbs.guard import orbs_guard
from orbs.thread_context import get_context, set_context


def _get_appium_server_url() -> str:
    """
    Get the correct Appium server URL based on Appium version.
    Appium v3.x uses http://localhost:4723 (no /wd/hub)
    Appium v1.x/v2.x uses http://localhost:4723/wd/hub
    """
    configured_url = setting.get("appium_url", "") or ""
    configured_url = configured_url.strip()
    
    # Default values
    default_host = "localhost"
    default_port = 4723
    
    # Parse configured URL or use defaults
    if configured_url:
        parsed = urlparse(configured_url)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or default_host
        port = parsed.port or default_port
    else:
        scheme = "http"
        host = default_host
        port = default_port
    
    base_url = f"{scheme}://{host}:{port}"
    
    # Check if Appium v3.x (responds on /status without /wd/hub)
    try:
        resp = requests.get(f"{base_url}/status", timeout=2)
        if resp.status_code == 200:
            # Appium v3.x - use base URL without /wd/hub
            return base_url
    except Exception:
        pass
    
    # Check if Appium v1.x/v2.x (responds on /wd/hub/status)
    try:
        resp = requests.get(f"{base_url}/wd/hub/status", timeout=2)
        if resp.status_code == 200:
            return f"{base_url}/wd/hub"
    except Exception:
        pass
    
    # Fallback: if configured URL has /wd/hub, use it; otherwise use base URL (assume v3.x)
    if configured_url and "/wd/hub" in configured_url:
        return configured_url
    return base_url


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
        retry_count: int = 2,
        skip_app_launch: bool = False
    ):
        server_url = _get_appium_server_url()
        platform = setting.get("platformName", "Android")
        
        # Use context to determine device name or fallback to config
        device_name = get_context("platform", "")
        if not device_name:
            device_name = setting.get("deviceName", "")

        # Use user-provided or config-based capabilities
        extra_caps = capabilities or setting.get_dict("capabilities") or {}

        for attempt in range(retry_count + 1):
            try:
                options = AppiumOptions()
                options.platform_name = platform
                options.device_name = device_name

                # Add session stability capabilities
                options.set_capability("newCommandTimeout", 300)  # 5 minutes timeout
                options.set_capability("noReset", True)  # Don't reset app state
                options.set_capability("automationName", "UiAutomator2")
                options.set_capability("uiautomator2ServerLaunchTimeout", 60000)  # 60 seconds
                options.set_capability("uiautomator2ServerInstallTimeout", 60000)  # 60 seconds

                # Injected appPackage and appActivity override config
                # skip_app_launch=True forces a bare session (for launch_and_install: install first, launch later)
                if skip_app_launch:
                    options.set_capability("autoLaunch", False)
                else:
                    final_app_package = app_package or setting.get("appPackage", None)
                    final_app_activity = app_activity or setting.get("appActivity", None)

                    if final_app_package and final_app_activity:
                        options.set_capability("appPackage", final_app_package)
                        options.set_capability("appActivity", final_app_activity)
                        options.set_capability("autoLaunch", True)
                    else:
                        options.set_capability("autoLaunch", False)

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
