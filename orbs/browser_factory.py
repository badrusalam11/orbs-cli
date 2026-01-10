# File: orbs/browser_factory.py
import os
from orbs.exception import BrowserDriverException
from orbs.guard import orbs_guard
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from orbs.config import config
from orbs.thread_context import get_context, set_context

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
            # Fallback to browser config
            browser = config.get("browser", "chrome").lower()
            
        extra_args = config.get_list("args")
        print(f"Creating {browser} driver with args: {extra_args}")

        if browser == "chrome":
            options = ChromeOptions()
            for arg in extra_args:
                options.add_argument(arg)
            driver = webdriver.Chrome(options=options)

        elif browser == "firefox":
            options = FirefoxOptions()
            for arg in extra_args:
                if arg == "--headless":
                    options.add_argument(arg)
                elif arg == "--incognito":
                    options.set_preference("browser.privatebrowsing.autostart", True)
                else:
                    options.add_argument(arg)
            driver = webdriver.Firefox(options=options)

        else:
            raise Exception(f"Unsupported browser: {browser}")

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
