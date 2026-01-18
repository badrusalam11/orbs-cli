# File: orbs/report_listener.py

import os
import sys
import time
import traceback
from orbs.exception import ReportListenerException
from orbs.guard import orbs_guard
from orbs.report_generator import ReportGenerator
from orbs.listener_manager import (
    BeforeTestSuite, AfterTestSuite,
    BeforeScenario, AfterScenario,
    BeforeStep, AfterStep,
    BeforeTestCase, AfterTestCase
)
from orbs.log import log, add_test_file_handler, remove_test_file_handler
from orbs.thread_context import get_context, set_context, clear_context

_scenario_start = {}
_steps_info = {}
_step_start = {}
_testcase_start = {}
_suite_start = {}
_start_time = {}
_scenario_screenshot_start_index = {}  # Track starting index of screenshots for each scenario
_scenario_api_calls_start_index = {}   # Track starting index of API calls for each scenario

@BeforeTestSuite
@orbs_guard(ReportListenerException)
def init_report(suite_path):
    _suite_start[suite_path] = time.time()
    _start_time[suite_path] = _suite_start[suite_path]

    rg = ReportGenerator(base_dir="reports")
    set_context("report", rg)
    log.info(f"Initialized reporting for suite: {suite_path}")

    # Setup file logging for this test
    add_test_file_handler(rg.id_test)
    set_context("test_id", rg.id_test)

    user_properties_path = os.path.join("settings", "user.properties")
    if not os.path.exists(user_properties_path):
        with open(user_properties_path, "w") as f:
            f.write("tester_name= Unknown Tester")

@BeforeTestCase
def before_test_case(case, data=None):
    log.info(f"Before test case: {case}")
    _testcase_start[case] = time.time()
    # Store current test case name in context for scenario tracking
    set_context('current_testcase', case)

@BeforeScenario
def start_scenario_timer(context, scenario):
    _scenario_start[scenario.name] = time.time()
    _step_start[scenario.name] = 0
    _steps_info[scenario.name] = [
        {
            "keyword": getattr(step, "keyword", "STEP"),
            "name": step.name,
            "status": "SKIPPED",  # Default to SKIPPED
            "duration": 0.0
        }
        for step in scenario.steps
    ]
    
    # Record the current length of screenshots list as starting point for this scenario
    current_screenshots = get_context("screenshots") or []
    _scenario_screenshot_start_index[scenario.name] = len(current_screenshots)
    
    # Record the current length of API calls list as starting point for this scenario
    current_api_calls = get_context("api_calls") or []
    _scenario_api_calls_start_index[scenario.name] = len(current_api_calls)
    
    log.info(f"Scenario '{scenario.name}' started with {len(current_screenshots)} existing screenshots and {len(current_api_calls)} existing API calls")

@BeforeStep
def start_step_timer(context, step):
    scenario_name = context.scenario.name
    _step_start[scenario_name] = time.time()

@AfterStep
def record_step_info(context, step):
    scenario_name = context.scenario.name
    start = _step_start.get(scenario_name, time.time())
    duration = time.time() - start
    status = getattr(step.status, 'name', str(step.status)).upper()

    # Find and update matching step
    for s in _steps_info[scenario_name]:
        if s['name'] == step.name and s['status'] == 'SKIPPED':
            s['status'] = status
            s['duration'] = round(duration, 2)
            break


@AfterScenario
def record_scenario_result(context, scenario):
    scenario_name = scenario.name
    start = _scenario_start.pop(scenario_name, None) or 0
    duration = time.time() - start
    status = getattr(scenario.status, 'name', str(scenario.status)).upper()
    tags = getattr(scenario, 'tags', [])
    category = tags[0] if tags else "Uncategorized"
    steps = _steps_info.pop(scenario_name, [])
    feature = getattr(scenario, 'feature', None)
    feature_name = feature.name if feature else "Unknown Feature"
    
    # Capture stacktrace if scenario failed
    error_message = None
    if status == 'FAILED':
        # Try to get exception from failed step
        for step in scenario.steps:
            if hasattr(step, 'exception') and step.exception:
                error_message = ''.join(traceback.format_exception(
                    type(step.exception), 
                    step.exception, 
                    step.exception.__traceback__
                ))
                break
        
        # Fallback: try scenario exception
        if not error_message and hasattr(scenario, 'exception') and scenario.exception:
            error_message = ''.join(traceback.format_exception(
                type(scenario.exception),
                scenario.exception,
                scenario.exception.__traceback__
            ))
        
        # Last resort: generic error
        if not error_message:
            error_message = f"Scenario '{scenario_name}' failed without stacktrace"

    rg = get_context("report")
    if not rg:
        return

    # Get screenshots that were added during this scenario
    all_screenshots = get_context("screenshots") or []
    screenshot_start_index = _scenario_screenshot_start_index.pop(scenario_name, 0)
    scenario_screenshots = all_screenshots[screenshot_start_index:]
    
    # Get API calls that were made during this scenario
    all_api_calls = get_context("api_calls") or []
    api_calls_start_index = _scenario_api_calls_start_index.pop(scenario_name, 0)
    scenario_api_calls = all_api_calls[api_calls_start_index:]
    
    log.info(f"Scenario '{scenario_name}' captured {len(scenario_screenshots)} screenshots and {len(scenario_api_calls)} API calls")

    # Build scenario data
    scenario_data = {
        "feature": feature_name,
        "scenario": scenario_name,
        "status": status,
        "duration": round(duration, 2),
        "screenshot": scenario_screenshots,
        "steps": steps,
        "category": category,
        "api_calls": scenario_api_calls,
        "error_message": error_message
    }

    # Record scenario globally (for cucumber.json)
    rg.record(
        feature_name,
        scenario_name,
        status,
        round(duration, 2),
        scenario_screenshots,  # Screenshots from this scenario
        steps,
        category=category,
        api_calls=scenario_api_calls,  # API calls from this scenario
        error_message=error_message  # Stacktrace if failed
    )
    
    # Also record scenario for current test case
    current_testcase = get_context('current_testcase')
    if current_testcase:
        rg.record_scenario_for_testcase(current_testcase, scenario_data)
        log.info(f"Linked scenario to test case: {current_testcase}")

    log.info(f"Recorded scenario: {scenario_name} - {status} - {duration:.2f}s - Screenshots: {len(scenario_screenshots)} - API calls: {len(scenario_api_calls)}")

@AfterTestCase
def after_test_case(case, data=None):
    log.info(f"After test case: {case}")
    start = _testcase_start.pop(case, None) or 0
    duration = time.time() - start
    status = data.get('status', 'passed').upper() if data else 'PASSED'
    
    # Capture stacktrace if test case failed
    error_message = None
    if status == 'FAILED':
        # Method 1: Try to get exception from data (passed by runner)
        if data and 'exception' in data and data['exception']:
            exc = data['exception']
            error_message = ''.join(traceback.format_exception(
                type(exc),
                exc,
                exc.__traceback__
            ))
        # Method 2: Fallback to sys.exc_info() for current exception
        elif sys.exc_info()[0] is not None:
            error_message = ''.join(traceback.format_exception(*sys.exc_info()))
        # Method 3: Try error field
        elif data and 'error' in data:
            error_message = str(data['error'])

    rg = get_context("report")
    if not rg:
        return

    # Get cucumber scenarios for this test case
    cucumber_scenarios = rg.testcase_scenarios.get(case, [])

    rg.record_test_case_result(case, status, round(duration, 2), error_message=error_message, cucumber=cucumber_scenarios)

    # Record all screenshots for the testcase (unchanged behavior)
    screenshots = get_context("screenshots") or []
    for path in screenshots:
        rg.record_screenshot(case, path)

    # Record all API calls for the testcase (unchanged behavior)
    api_calls = get_context("api_calls") or []
    if api_calls:
        rg.testcase_api_calls[case] = api_calls

    log.info(f"Recorded testcase: {case} - {status} - {duration:.2f}s - Total Screenshots: {len(screenshots)} - Total API calls: {len(api_calls)} - Cucumber scenarios: {len(cucumber_scenarios)}")

    # cleanup
    set_context("screenshots", [])
    set_context("api_calls", [])
    set_context('current_testcase', None)  # Clear current test case

@AfterTestSuite
@orbs_guard(ReportListenerException)
def finalize_report(suite_path):
    end_time = time.time()
    start = _suite_start.pop(suite_path, None) or 0
    start_time = _start_time.pop(suite_path, None) or start
    duration = end_time - start

    rg = get_context("report")
    if not rg:
        return

    rg.record_overview(suite_path, round(duration, 2), start_time, end_time)
    run_dir = rg.finalize(suite_path)
    log.info(f"Report generated at: {run_dir}")
    
    # Clear any remaining tracking data
    _scenario_screenshot_start_index.clear()
    _scenario_api_calls_start_index.clear()
    
    # Cleanup test_id and file handler (AFTER all logging is done)
    remove_test_file_handler()
    set_context('test_id', None)