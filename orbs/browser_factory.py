# File: orbs/browser_factory.py
import os
import base64
from orbs.exception import BrowserDriverException
from orbs.guard import orbs_guard
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from orbs.config import setting, env
from orbs.thread_context import get_context, set_context
from orbs.log import log
class BrowserFactory:
    @staticmethod
    @orbs_guard(BrowserDriverException)
    def create_driver():
        
        # Check if platform is set in context (from CLI --platform or collection)
        platform_from_context = get_context('platform')
        if platform_from_context:
            # Use platform from CLI/context as browser
            browser = platform_from_context.lower()
        else:
            # Fallback to browser config from settings/browser.properties
            browser = setting.get("browser", "chrome").lower()
        
        # Load browser configuration from settings/browser.properties
        headless = setting.get_bool("headless", False)
        private_mode = setting.get_bool("private_mode", False)
        window_size = setting.get("window_size", None)
        driver_path = setting.get("driver_path", None)
        
        # Get browser arguments from settings (semicolon-separated)
        # Framework handles browser-specific compatibility automatically
        args_list = setting.get_list("args", sep=";")
        
        log.debug(f"Creating {browser} driver (headless={headless}, private_mode={private_mode}, window_size={window_size}, args={args_list})")

        if browser == "chrome":
            options = ChromeOptions()
            
            # Add headless mode
            if headless:
                options.add_argument("--headless=new")
            
            # Add private/incognito mode
            if private_mode:
                options.add_argument("--incognito")
            
            # Add window size
            if window_size:
                options.add_argument(f"--window-size={window_size.replace('x', ',')}")
            
            # Add browser arguments (all chrome args are supported)
            for arg in args_list:
                options.add_argument(arg)
            
            # Create driver with optional custom driver path
            if driver_path:
                service = ChromeService(executable_path=driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)

        elif browser == "firefox":
            options = FirefoxOptions()
            
            # Add headless mode
            if headless:
                options.add_argument("--headless")
            
            # Add window size
            if window_size:
                width, height = window_size.split('x')
                options.add_argument(f"--width={width}")
                options.add_argument(f"--height={height}")
            
            # Add browser arguments with Firefox compatibility handling
            for arg in args_list:
                if arg == "--incognito":
                    # Firefox calls it "private browsing"
                    options.set_preference("browser.privatebrowsing.autostart", True)
                elif arg.startswith("--"):
                    options.add_argument(arg)
            
            # Add private/incognito mode
            if private_mode:
                options.set_preference("browser.privatebrowsing.autostart", True)
            
            # Create driver with optional custom driver path
            if driver_path:
                service = FirefoxService(executable_path=driver_path)
                driver = webdriver.Firefox(service=service, options=options)
            else:
                driver = webdriver.Firefox(options=options)

        elif browser == "edge":
            options = EdgeOptions()
            
            # Add headless mode
            if headless:
                options.add_argument("--headless=new")
            
            # Add window size
            if window_size:
                options.add_argument(f"--window-size={window_size.replace('x', ',')}")
            
            # Add browser arguments (Edge supports Chrome args)
            for arg in args_list:
                options.add_argument(arg)
            
            # Add private/inprivate mode
            if private_mode:
                options.add_argument("--inprivate")
            
            # Create driver with optional custom driver path
            if driver_path:
                service = EdgeService(executable_path=driver_path)
                driver = webdriver.Edge(service=service, options=options)
            else:
                driver = webdriver.Edge(options=options)

        elif browser == "safari":
            options = SafariOptions()
            
            # Safari doesn't support headless mode natively
            # Window size is set after driver creation
            
            driver = webdriver.Safari(options=options)
            
            # Set window size if specified
            if window_size and not headless:
                width, height = window_size.split('x')
                driver.set_window_size(int(width), int(height))

        else:
            raise Exception(f"Unsupported browser: {browser}")
        
        # Apply timeout configurations from execution.properties
        implicit_timeout = setting.get_int("implicit_timeout", 5)
        page_load_timeout = setting.get_int("page_load_timeout", 30)
        
        driver.implicitly_wait(implicit_timeout)
        driver.set_page_load_timeout(page_load_timeout)
        
        log.debug(f"Applied timeouts - implicit: {implicit_timeout}s, page_load: {page_load_timeout}s")
        
        # Set window size for browsers that support it (if not already set)
        if window_size and browser not in ["safari"]:
            try:
                width, height = window_size.split('x')
                driver.set_window_size(int(width), int(height))
            except:
                pass  # Ignore if already set via arguments

        # Ensure screenshots list exists for this thread
        if get_context("screenshots") is None:
            set_context("screenshots", [])

        original_save = driver.save_screenshot
        
        # Get screenshot_full_page config
        screenshot_full_page = setting.get_bool("screenshot_full_page", False)

        def save_to_report(path, *a, **kw):
            # Determine full path to save into
            if not os.path.isabs(path):
                try:
                    rpt = get_context("report")
                    rpt_dir = rpt.screenshots_dir
                except Exception:
                    rpt_dir = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(rpt_dir, exist_ok=True)

                filename = path
                base, ext = os.path.splitext(filename)
                path = os.path.join(rpt_dir, filename)
                i = 1
                while os.path.exists(path):
                    path = os.path.join(rpt_dir, f"{base}_{i}{ext}")
                    i += 1

            # Append the screenshot path to the context
            abs_path = os.path.abspath(path)
            screenshots = get_context("screenshots") or []
            screenshots.append(abs_path)
            set_context("screenshots", screenshots)

            # Take full page screenshot if enabled
            if screenshot_full_page:
                try:
                    if browser in ["chrome", "edge"]:
                        # Chrome/Edge: Get full page dimensions and take full screenshot
                        # Get page dimensions
                        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
                        width = metrics['contentSize']['width']
                        height = metrics['contentSize']['height']
                        
                        # Set device metrics to full page size
                        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                            "width": width,
                            "height": height,
                            "deviceScaleFactor": 1,
                            "mobile": False
                        })
                        
                        # Take screenshot with full page viewport
                        result = driver.execute_cdp_cmd("Page.captureScreenshot", {
                            "format": "png",
                            "captureBeyondViewport": True
                        })
                        
                        # Clear device metrics override
                        driver.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
                        
                        # Decode base64 and save to file
                        with open(path, 'wb') as f:
                            f.write(base64.b64decode(result['data']))
                        log.debug(f"Full page screenshot saved (CDP) - {width}x{height}: {path}")
                        return True
                    elif browser == "firefox":
                        # Firefox: Native full page screenshot support
                        screenshot_data = driver.get_full_page_screenshot_as_png()
                        with open(path, 'wb') as f:
                            f.write(screenshot_data)
                        log.debug(f"Full page screenshot saved (Firefox): {path}")
                        return True
                    else:
                        # Safari and others: Fall back to normal screenshot
                        log.debug(f"Full page screenshot not supported for {browser}, using viewport screenshot")
                        return original_save(path, *a, **kw)
                except Exception as e:
                    # If full page screenshot fails, fallback to normal screenshot
                    log.warning(f"Full page screenshot failed, using viewport screenshot: {e}")
                    return original_save(path, *a, **kw)
            else:
                # Normal viewport screenshot
                return original_save(path, *a, **kw)

        driver.save_screenshot = save_to_report
        return driver
