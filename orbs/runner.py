from concurrent.futures import ThreadPoolExecutor
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import yaml
import inspect
from behave.__main__ import main as behave_main
from orbs.guard import orbs_guard
from orbs.thread_context import set_context, get_context
from orbs.log import log
from orbs.dependency import check_dependencies
from orbs.listener_manager import enabled_listeners, load_suite_listeners
from orbs.exception import FeatureException, RunnerException
from orbs.config import config
from orbs.keyword.web import Web
from orbs.utils import load_module_from_path
from ._constant import PLATFORM_LIST
import sys


class Runner:
    def __init__(self):
        pass

    def _normalized_path(self, target):
        normalized_path = target.replace('\\', '/').replace('//', '/')
        return normalized_path

    def run_case(self, case_path):
        # Ensure report is initialized (for standalone test case execution)
        from orbs.report_listener import ensure_report_initialized
        is_standalone = ensure_report_initialized(context_key=f"case:{case_path}")
        
        log.info(f"Running test case: {case_path}")
        
        # For standalone test case, manually call BeforeTestCase hooks
        if is_standalone:
            for hook in enabled_listeners.get('before_test_case', []):
                self._invoke_hook(hook, case_path)
        
        # Run the test case
        status = "passed"
        exception = None
        try:
            mod = load_module_from_path(case_path)
            if hasattr(mod, "run"):
                mod.run()
            else:
                raise Exception(f"No 'run()' function found in {case_path}")
        except Exception as e:
            log.error(f"Error running test case {case_path}: {e}", exc_info=True)
            status = "failed"
            exception = e
        
        # For standalone test case, manually call AfterTestCase hooks
        if is_standalone:
            data = {"status": status, "name": case_path, "exception": exception}
            for hook in enabled_listeners.get('after_test_case', []):
                self._invoke_hook(hook, case_path, data)
            
            # Finalize report for standalone execution
            self._finalize_standalone_report(case_path)
        
    def _invoke_hook(self, hook, *args):
        """
        Invoke a hook, matching its signature: if it expects no args, call without args,
        otherwise pass the provided args.
        """
        try:
            sig = inspect.signature(hook)
            if len(sig.parameters) == 0:
                hook()
            else:
                hook(*args)
        except Exception as e:
            log.error(f"Error invoking hook {hook.__name__}: {e}", exc_info=True)
    
    def _finalize_standalone_report(self, context_key):
        """
        Finalize report for standalone test case/feature execution.
        This replicates AfterTestSuite behavior for standalone runs.
        """
        import time
        import sys
        from orbs.console_summary import ConsoleSummary
        
        rg = get_context("report")
        if not rg:
            return
        
        # Calculate duration from report creation time
        end_time = time.time()
        start_time = getattr(rg, 'start_time', end_time)
        duration = end_time - start_time
        
        # Record overview
        rg.record_overview(context_key, round(duration, 2), start_time, end_time)
        run_dir = rg.finalize(context_key)
        log.info(f"Report generated at: {run_dir}")
        
        # Print console summary
        ConsoleSummary.print_summary(rg.overriew)
        
        # Flush output
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Store exit code
        exit_code = ConsoleSummary.get_exit_code(rg.overriew)
        set_context('exit_code', exit_code)
        
        # Log execution finish to live logger
        live_logger = get_context("live_logger")
        if live_logger:
            overall_status = "PASSED" if exit_code == 0 else "FAILED"
            live_logger.execution_finished(status=overall_status, duration=duration)
        
        # Cleanup
        from orbs.log import remove_test_file_handler
        remove_test_file_handler()
        set_context('test_id', None)

    @orbs_guard(RunnerException)
    def run_suite(self, suite_path):
        # 1) Load ONLY the suite-specific hooks for this suite
        load_suite_listeners(suite_path)
        # 🔹 Global BeforeTestSuite hooks
        for hook in enabled_listeners.get('before_test_suite', []):
            self._invoke_hook(hook, suite_path)

        # 🔹 Suite-specific SetUp hooks (@SetUp)
        for hook in enabled_listeners.get('setup', []):
            self._invoke_hook(hook, suite_path)

        # Load the suite YAML
        with open(suite_path) as f:
            suite = yaml.safe_load(f)

        for case in suite.get("test_cases", []):
            # Handle both old and new format
            if isinstance(case, dict):
                # New format with enabled field
                case_path = case.get("path")
                enabled = case.get("enabled", False)  # default to False
                if not enabled:
                    log.info(f"Skipping disabled test case: {case_path}")
                    continue
                case = case_path
            
            case = self._normalized_path(case)
            # 🔹 Per-case SetupTestCase hooks (@SetupTestCase)
            for hook in enabled_listeners.get('setup_test_case', []):
                self._invoke_hook(hook, case, None)

            # 🔹 Global BeforeTestCase hooks
            for hook in enabled_listeners.get('before_test_case', []):
                self._invoke_hook(hook, case)

            # Run the test case and capture status with retry logic
            retry_enabled = config.get_bool("retry_enabled", False)
            retry_max_attempts = config.get_int("retry_max_attempts", 2)
            screenshot_on_fail = config.get_bool("screenshot_on_fail", False)
            screenshot_on_retry = config.get_bool("screenshot_on_retry", False)
            
            status = "passed"
            exception = None
            attempt = 1
            max_attempts = retry_max_attempts if retry_enabled else 1
            
            while attempt <= max_attempts:
                try:
                    if attempt > 1:
                        log.info(f"Retrying test case {case} (attempt {attempt}/{max_attempts})")
                        # Increment retry counter in context
                        retry_count = get_context("retry_count") or 0
                        set_context("retry_count", retry_count + 1)
                        
                        # Reset drivers for clean state before retry
                        try:
                            Web.reset_driver()
                        except ImportError:
                            pass
                        
                        try:
                            from orbs.keyword.mobile import Mobile
                            Mobile.reset_driver()
                        except ImportError:
                            pass
                    
                    self.run_case(case)
                    status = "passed"
                    exception = None
                    break  # Success, exit retry loop
                except Exception as e:
                    log.error(f"Error running test case {case} (attempt {attempt}/{max_attempts}): {e}", exc_info=True)
                    status = "failed"
                    exception = e
                    
                    # Take screenshot before cleanup/retry (capture failure state)
                    if attempt < max_attempts and screenshot_on_retry:
                        # Screenshot on retry - capture before reset driver
                        try:
                            driver = Web._get_driver()
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            screenshot_filename = f"retry_attempt_{attempt}_{os.path.basename(case)}_{timestamp}.png"
                            driver.save_screenshot(screenshot_filename)
                            log.info(f"Screenshot taken before retry: {screenshot_filename}")
                        except Exception as screenshot_error:
                            log.warning(f"Failed to take screenshot on retry: {screenshot_error}")
                    elif attempt == max_attempts and screenshot_on_fail:
                        # Screenshot on final fail - capture before cleanup
                        try:
                            driver = Web._get_driver()
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            screenshot_filename = f"fail_{os.path.basename(case)}_{timestamp}.png"
                            driver.save_screenshot(screenshot_filename)
                            log.info(f"Screenshot taken on fail: {screenshot_filename}")
                        except Exception as screenshot_error:
                            log.warning(f"Failed to take screenshot on fail: {screenshot_error}")
                    
                    if attempt < max_attempts:
                        log.info(f"Test case {case} failed, will retry...")
                        attempt += 1
                    else:
                        log.error(f"Test case {case} failed after {max_attempts} attempts")
                        break

            # Check if test had CONTINUE_ON_FAILURE errors (should mark as failed)
            has_continued_failures = get_context('test_has_continued_failures')
            if has_continued_failures and status == "passed":
                status = "failed"
                log.warning(f"Test case {case} marked as FAILED due to CONTINUE_ON_FAILURE errors")
            
            # Clear the flag for next test
            set_context('test_has_continued_failures', False)
            
            data = {"status": status, "name": case, "exception": exception}

            # Reset drivers for clean state between test cases
            try:
                Web.reset_driver()
            except ImportError:
                pass
            
            try:
                from orbs.keyword.mobile import Mobile
                Mobile.reset_driver()
            except ImportError:
                pass

            # 🔹 Global AfterTestCase hooks
            for hook in enabled_listeners.get('after_test_case', []):
                self._invoke_hook(hook, case, data)

            # 🔹 Per-case TeardownTestCase hooks (@TeardownTestCase)
            for hook in enabled_listeners.get('teardown_test_case', []):
                self._invoke_hook(hook, case, data)

        # 🔹 Suite-specific Teardown hooks (@Teardown)
        for hook in enabled_listeners.get('teardown', []):
            self._invoke_hook(hook, suite_path)

        # 🔹 Global AfterTestSuite hooks
        for hook in enabled_listeners.get('after_test_suite', []):
            self._invoke_hook(hook, suite_path)

    @orbs_guard(FeatureException)
    def run_feature(self, feature_path, tags=None):
        # Ensure report is initialized (for standalone feature execution)
        from orbs.report_listener import ensure_report_initialized
        is_standalone = ensure_report_initialized(context_key=f"feature:{feature_path}")
        
        log.info(f"is feature {feature_path} exist: {os.path.exists(feature_path)}")
        log.info(f"Running feature: {feature_path} with tags: {tags}")
        args = []
        if tags:
            args.extend(["--tags", tags])
        args.append(feature_path)

        result_code = behave_main(args)  # <--- Capture the result code
        
        # Finalize report for standalone execution
        if is_standalone:
            self._finalize_standalone_report(feature_path)
        
        if result_code != 0:
            log.error(f"Feature run failed with code: {result_code}")
            raise FeatureException(f"Feature run failed with code: {result_code}")
        # You can optionally store this somewhere to use in run_case
        return result_code
    
    @orbs_guard(RunnerException)
    def run_suite_collection(self, collection_path: str):
        """
        Run a collection of test suites defined in a YAML file.

        Enhanced format supports per-suite metadata:

        testsuites:
          - testsuite: testsuites/login.yml
            platform: android
            device_id: emulator0054
          - testsuite: testsuites/login_web.yml
            platform: chrome
        """
        if not os.path.exists(collection_path):
            raise FileNotFoundError(f"Collection file not found: {collection_path}")

        project_root = os.getcwd()
        spec = yaml.safe_load(open(collection_path))
        method = spec.get("execution_method", "sequential")
        max_inst = spec.get("max_concurrent_instances", 1)
        delay = spec.get("delay_between_instances(s)", 0)
        entries = spec.get("testsuites", [])

        def _run_entry(entry):
            # Support string or dict entry
            if isinstance(entry, str):
                path = entry
                platform = None
                device_id = None
                enabled = False  # default enabled for old format
            else:
                path = entry.get("testsuite")
                platform = entry.get("platform")
                device_id = entry.get("device_id")
                enabled = entry.get("enabled", False)  # default to False

            # Skip if disabled
            if not enabled:
                log.info(f"Skipping disabled testsuite: {path}")
                return

            try:
                # set context device_id to the thread context if provided. to appium driver
                set_context("device_id", device_id)
                # set platform context if specified in collection
                if platform:
                    set_context("platform", platform)
                if platform in PLATFORM_LIST["mobile"]:
                    check_dependencies()
                suite_path = os.path.join(project_root, self._normalized_path(path))
                self.run_suite(suite_path)
            finally:
                # Clean up thread context after suite execution
                # This ensures no driver/platform context leaks to next suite in same thread
                from orbs.thread_context import clear_context
                clear_context()

        if method == "parallel" and max_inst > 1:
            with ThreadPoolExecutor(max_workers=max_inst) as executor:
                futures = []
                for entry in entries:
                    futures.append(executor.submit(_run_entry, entry))
                    if delay:
                        time.sleep(delay)
                for f in futures:
                    f.result()
        else:
            for entry in entries:
                _run_entry(entry)
                if delay:
                    time.sleep(delay)
