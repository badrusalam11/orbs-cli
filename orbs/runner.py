from concurrent.futures import ThreadPoolExecutor
import os
import time
from dotenv import load_dotenv
import yaml
import inspect
from behave.__main__ import main as behave_main
from orbs.guard import orbs_guard
from orbs.thread_context import set_context
from orbs.log import log
from orbs.dependency import check_dependencies
from orbs.listener_manager import enabled_listeners, load_suite_listeners
from orbs.exception import FeatureException, RunnerException
import sys

from orbs.utils import load_module_from_path
from ._constant import PLATFORM_LIST



class Runner:
    def __init__(self):
        pass

    def _normalized_path(self, target):
        normalized_path = target.replace('\\', '/').replace('//', '/')
        return normalized_path

    def run_case(self, case_path):
        log.info(f"Running test case: {case_path}")
        mod = load_module_from_path(case_path)
        if hasattr(mod, "run"):
            mod.run()
        else:
            raise Exception(f"No 'run()' function found in {case_path}")
        
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

            # Run the test case and capture status
            status = "passed"
            try:
                self.run_case(case)
            except Exception as e:
                log.error(f"Error running test case {case}: {e}", exc_info=True)
                status = "failed"

            data = {"status": status, "name": case}

            # Reset drivers for clean state between test cases
            try:
                from orbs.keyword.web import Web
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
        log.info(f"is feature {feature_path} exist: {os.path.exists(feature_path)}")
        log.info(f"Running feature: {feature_path} with tags: {tags}")
        args = []
        if tags:
            args.extend(["--tags", tags])
        args.append(feature_path)

        result_code = behave_main(args)  # <--- Capture the result code
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
