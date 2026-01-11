# File: orbs/browser_factory.py
import os
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
from orbs.config import config
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
            browser = config.get("browser", "chrome").lower()
        
        # Load browser configuration from settings/browser.properties
        headless = config.get_bool("headless", False)
        window_size = config.get("window_size", None)
        driver_path = config.get("driver_path", None)
        
        # Get browser arguments from settings (comma-separated)
        # Framework handles browser-specific compatibility automatically
        args_list = config.get_list("args", sep=",")
        
        log.debug(f"Creating {browser} driver (headless={headless}, window_size={window_size}, args={args_list})")

        if browser == "chrome":
            options = ChromeOptions()
            
            # Add headless mode
            if headless:
                options.add_argument("--headless=new")
            
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

            return original_save(path, *a, **kw)

        driver.save_screenshot = save_to_report
        return driver
