import os
from appium import webdriver
from appium.options.common.base import AppiumOptions
from orbs.config import Config
from orbs.thread_context import get_context, set_context
class MobileFactory:
    @staticmethod
    def create_driver(
        app_package: str = None,
        app_activity: str = None,
        capabilities: dict = None
    ):
        cfg = Config()
        server_url = cfg.get("appium_url", "http://localhost:4723/wd/hub")
        platform = cfg.get("platformName", "Android")
        device_name = cfg.get("deviceName", "")

        # Use user-provided or config-based capabilities
        extra_caps = capabilities or cfg.get_dict("capabilities") or {}

        options = AppiumOptions()
        options.platform_name = platform
        options.device_name = device_name

        # Injected appPackage and appActivity override config
        final_app_package = app_package or cfg.get("appPackage", None)
        final_app_activity = app_activity or cfg.get("appActivity", None)

        if final_app_package and final_app_activity:
            options.set_capability("appPackage", final_app_package)
            options.set_capability("appActivity", final_app_activity)

        for key, value in extra_caps.items():
            options.set_capability(key, value)

        driver = webdriver.Remote(
            command_executor=server_url,
            options=options
        )

        # ... screenshot logic remains unchanged ...
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
            shots.append(abs_path)
            set_context("screenshots", shots)
            return original(path, *args, **kwargs)

        driver.get_screenshot_as_file = save_to_report
        return driver
