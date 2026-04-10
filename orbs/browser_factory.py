# File: orbs/browser_factory.py
import os
import sys
import base64
import logging
import atexit
import weakref
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

# Suppress verbose Selenium logging (significant speedup on macOS)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Track all created drivers for cleanup
_active_drivers = weakref.WeakSet()


def _cleanup_all_drivers():
    """Cleanup all active drivers on exit"""
    for driver in list(_active_drivers):
        try:
            driver.quit()
        except Exception:
            pass
    
    # Note: We intentionally do NOT pkill chromedriver here because:
    # 1. It would kill chromedriver processes from parallel tests
    # 2. It would kill chromedriver from other projects/users
    # 3. The WeakSet tracking + driver.quit() should handle cleanup properly
    # If orphan processes remain, user can manually run: pkill -f chromedriver


# Register cleanup on Python exit
atexit.register(_cleanup_all_drivers)


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
        
        # Performance optimization toggle (default: enabled)
        # Set performance_mode=false in browser.properties to disable
        performance_mode = setting.get_bool("performance_mode", True)
        
        # Get browser arguments from settings (semicolon-separated)
        # Framework handles browser-specific compatibility automatically
        args_list = setting.get_list("args", sep=";")
        
        log.debug(f"Creating {browser} driver (headless={headless}, private_mode={private_mode}, window_size={window_size}, args={args_list})")

        if browser == "chrome":
            options = ChromeOptions()
            
            # === PERFORMANCE FLAGS FOR macOS ===
            # macOS Chrome is significantly slower without these optimizations
            # These flags reduce cold start time and make actions feel snappier
            is_macos = sys.platform == "darwin"
            
            if is_macos and performance_mode:
                # === CORE PERFORMANCE FLAGS (proven to work) ===
                # Disable GPU-related overhead (major macOS slowdown)
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-software-rasterizer")
                
                # Disable unnecessary Chrome features that slow down startup
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-default-apps")
                options.add_argument("--disable-sync")
                options.add_argument("--disable-translate")
                options.add_argument("--disable-background-networking")
                options.add_argument("--disable-dev-shm-usage")
                
                # Skip first run and default browser check
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                
                # === ADDITIONAL macOS SPEEDUP FLAGS ===
                # Disable sandbox (significant startup speedup on macOS)
                options.add_argument("--no-sandbox")
                
                # Disable site isolation (faster process startup)
                options.add_argument("--disable-site-isolation-trials")
                
                # Disable features that slow down Chrome startup
                options.add_argument("--disable-features=VizDisplayCompositor")
                options.add_argument("--disable-breakpad")  # Disable crash reporter
                options.add_argument("--disable-component-update")  # Disable component updates
                options.add_argument("--disable-domain-reliability")  # Disable domain reliability monitoring
                
                # Reduce IPC overhead
                options.add_argument("--disable-ipc-flooding-protection")
                
                # Memory optimizations
                options.add_argument("--memory-pressure-off")
                options.add_argument("--disable-backing-store-limit")
                
                # Disable logging overhead
                options.add_argument("--log-level=3")
                options.add_argument("--silent")
                options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Disable notifications and password manager
                prefs = {
                    "profile.default_content_setting_values.notifications": 2,
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False,
                }
                options.add_experimental_option("prefs", prefs)
                
                # Use 'eager' page load strategy - don't wait for all resources
                options.page_load_strategy = 'eager'
                
                log.debug("Applied macOS Chrome performance optimizations")
            
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
            
            # === FIREFOX PERFORMANCE OPTIMIZATIONS ===
            # Firefox cold start is significantly slower than Chrome (32s macOS, 6s Windows)
            # These optimizations reduce startup time dramatically
            is_macos = sys.platform == "darwin"
            
            # === ENVIRONMENT VARIABLES (applied before browser starts) ===
            # These are critical for reducing cold start time
            os.environ['MOZ_CRASHREPORTER_DISABLE'] = '1'  # Disable crash reporter
            os.environ['MOZ_DISABLE_CONTENT_SANDBOX'] = '1'  # Faster content process startup
            if is_macos:
                # macOS-specific: Reduce Mach port overhead
                os.environ['MOZ_DISABLE_NPAPI_SANDBOX'] = '1'
            
            if performance_mode:
                # === DISABLE GECKO LOGGING (reduces disk I/O) ===
                os.environ['MOZ_LOG'] = ''
                os.environ['NSPR_LOG_MODULES'] = ''
                
                # === CORE STARTUP OPTIMIZATIONS ===
                # Disable first-run checks and welcome pages
                options.set_preference("browser.startup.homepage_override.mstone", "ignore")
                options.set_preference("browser.startup.page", 0)  # Blank page
                options.set_preference("browser.startup.couldRestoreSession.count", 0)
                options.set_preference("browser.shell.checkDefaultBrowser", False)
                options.set_preference("browser.shell.skipDefaultBrowserCheckOnFirstRun", True)
                options.set_preference("toolkit.telemetry.reportingpolicy.firstRun", False)
                options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
                
                # === DISABLE NETWORK-HEAVY FEATURES ===
                # These cause significant startup delays waiting for network
                options.set_preference("network.prefetch-next", False)
                options.set_preference("network.predictor.enabled", False)
                options.set_preference("network.dns.disablePrefetch", True)
                options.set_preference("network.http.speculative-parallel-limit", 0)
                options.set_preference("browser.safebrowsing.enabled", False)
                options.set_preference("browser.safebrowsing.downloads.enabled", False)
                options.set_preference("browser.safebrowsing.malware.enabled", False)
                options.set_preference("browser.safebrowsing.phishing.enabled", False)
                options.set_preference("services.sync.enabled", False)
                options.set_preference("browser.newtabpage.enabled", False)
                options.set_preference("browser.newtabpage.activity-stream.feeds.section.topstories", False)
                options.set_preference("browser.newtabpage.activity-stream.showSponsored", False)
                options.set_preference("browser.newtabpage.activity-stream.enabled", False)
                
                # === DISABLE TELEMETRY & UPDATES ===
                # Telemetry causes significant disk/network I/O during startup
                options.set_preference("toolkit.telemetry.enabled", False)
                options.set_preference("toolkit.telemetry.unified", False)
                options.set_preference("toolkit.telemetry.server", "")
                options.set_preference("toolkit.telemetry.archive.enabled", False)
                options.set_preference("app.update.enabled", False)
                options.set_preference("app.update.checkInstallTime", False)
                options.set_preference("extensions.update.enabled", False)
                options.set_preference("browser.search.update", False)
                
                # === DISABLE UI ANIMATIONS ===
                # Animations slow down perceived startup
                options.set_preference("ui.prefersReducedMotion", 1)
                options.set_preference("toolkit.cosmeticAnimations.enabled", False)
                
                # === DISABLE EXTENSION/ADDON FEATURES ===
                options.set_preference("extensions.getAddons.cache.enabled", False)
                options.set_preference("extensions.blocklist.enabled", False)
                options.set_preference("xpinstall.signatures.required", False)
                options.set_preference("extensions.autoDisableScopes", 0)
                
                # === SESSION RESTORE OPTIMIZATION ===
                options.set_preference("browser.sessionstore.resume_from_crash", False)
                options.set_preference("browser.sessionstore.max_tabs_undo", 0)
                options.set_preference("browser.sessionstore.max_windows_undo", 0)
                
                # === CACHE & MEMORY OPTIMIZATION ===
                options.set_preference("browser.cache.disk.enable", False)  # Avoid disk writes
                options.set_preference("browser.cache.memory.enable", True)
                options.set_preference("browser.cache.memory.capacity", 65536)  # 64MB memory cache
                
                # === REDUCE DISK I/O ===
                # Disk I/O is especially slow on macOS with APFS
                options.set_preference("browser.places.database.growthIncrementKiB", 0)
                options.set_preference("places.database.growthIncrementKiB", 0)
                
                # === CONTENT PROCESS OPTIMIZATION ===
                # Fewer content processes = faster startup (default is 8)
                options.set_preference("dom.ipc.processCount", 2)
                options.set_preference("dom.ipc.processCount.webIsolated", 1)
                
                # === DISABLE POCKET & EXPERIMENTS ===
                options.set_preference("extensions.pocket.enabled", False)
                options.set_preference("browser.ping-centre.telemetry", False)
                options.set_preference("experiments.enabled", False)
                options.set_preference("experiments.activeExperiment", False)
                
                # === macOS SPECIFIC ===
                if is_macos:
                    # macOS-specific: Disable hardware acceleration (APFS + GPU = slow)
                    options.set_preference("gfx.compositor.glcontext.opaque", True)
                    options.set_preference("layers.acceleration.disabled", True) 
                    options.set_preference("gfx.canvas.azure.accelerated", False)
                    options.set_preference("gfx.webrender.all", False)
                    # Disable Rosetta translation overhead on Apple Silicon
                    options.set_preference("security.sandbox.content.mac.disconnect-windowserver", False)
                    log.debug("Applied macOS Firefox performance optimizations")
                
                # === PAGE LOAD STRATEGY ===
                # Don't wait for full page load
                options.page_load_strategy = 'eager'
                
                # === COMMAND LINE ARGS ===
                options.add_argument('-no-remote')  # Allow multiple instances
                
                log.debug("Applied Firefox performance optimizations")
            
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
            # Use service_log_path to reduce geckodriver disk I/O
            log_path = os.devnull if performance_mode else None
            if driver_path:
                service = FirefoxService(
                    executable_path=driver_path,
                    log_output=log_path
                )
                driver = webdriver.Firefox(service=service, options=options)
            else:
                service = FirefoxService(log_output=log_path) if performance_mode else None
                driver = webdriver.Firefox(service=service, options=options) if service else webdriver.Firefox(options=options)

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
        
        # Register driver for cleanup on exit
        _active_drivers.add(driver)
        
        # Apply timeout configurations from execution.properties
        # On macOS with performance_mode, use lower implicit timeout for faster response
        is_macos = sys.platform == "darwin"
        if is_macos and performance_mode:
            # Lower implicit timeout on macOS - explicit waits are more reliable
            implicit_timeout = setting.get_int("implicit_timeout", 2)
            page_load_timeout = setting.get_int("page_load_timeout", 20)
        else:
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
