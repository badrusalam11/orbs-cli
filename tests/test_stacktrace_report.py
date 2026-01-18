import unittest
import os
import json
import tempfile
import shutil
from datetime import datetime
from xml.etree import ElementTree as ET

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orbs.report_generator import ReportGenerator


class TestStacktraceInReports(unittest.TestCase):
    """Test stacktrace integration in all report formats"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.rg = ReportGenerator(base_dir=self.test_dir)
        
        # Sample stacktrace
        self.sample_stacktrace = """Traceback (most recent call last):
  File "test_login.py", line 45, in test_login_invalid
    assert login_page.is_error_displayed(), "Error message not shown"
AssertionError: Error message not shown"""
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_stacktrace_in_json_report(self):
        """Test that stacktrace is saved in JSON report"""
        # Record a failed test case with stacktrace
        self.rg.record_test_case_result(
            name="testcases/login_failed.py",
            status="FAILED",
            duration=5.5,
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=5.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        # Save JSON
        self.rg.save_json()
        
        # Verify result.json contains stacktrace
        with open(self.rg.overview_path, 'r') as f:
            result_data = json.load(f)
        
        self.assertEqual(len(result_data['testcase_results']), 1)
        tc_result = result_data['testcase_results'][0]
        self.assertEqual(tc_result['status'], 'FAILED')
        self.assertIn('error_message', tc_result)
        self.assertIn('AssertionError', tc_result['error_message'])
        self.assertIn('test_login.py', tc_result['error_message'])
    
    def test_stacktrace_in_junit_xml(self):
        """Test that stacktrace appears in JUnit XML <failure> element"""
        self.rg.record_test_case_result(
            name="testcases/login_failed.py",
            status="FAILED",
            duration=5.5,
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=5.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        # Generate JUnit XML
        junit_path = self.rg.generate_junit_xml()
        
        # Parse and verify
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        # Find the failed testcase
        testcase = root.find('.//testcase[@name="testcases/login_failed.py"]')
        self.assertIsNotNone(testcase)
        
        # Check failure element has stacktrace
        failure = testcase.find('failure')
        self.assertIsNotNone(failure, "Failed testcase must have <failure> element")
        self.assertIn('AssertionError', failure.text)
        self.assertIn('test_login.py', failure.text)
        self.assertIn('line 45', failure.text)
    
    def test_stacktrace_in_cucumber_scenario(self):
        """Test stacktrace in cucumber scenario"""
        # Record failed scenario with stacktrace
        self.rg.record(
            feature="Login Feature",
            scenario="Login with invalid credentials",
            status="failed",
            duration=3.5,
            steps_info=[
                {"keyword": "Given", "name": "I am on login page", "status": "PASSED", "duration": 1.0},
                {"keyword": "When", "name": "I enter invalid credentials", "status": "PASSED", "duration": 0.5},
                {"keyword": "Then", "name": "I should see error message", "status": "FAILED", "duration": 2.0}
            ],
            category="negative",
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_test_case_result(
            name="testcases/login.py",
            status="FAILED",
            duration=3.5,
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=3.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        # Check JSON
        self.rg.save_json()
        with open(self.rg.json_path, 'r') as f:
            cucumber_data = json.load(f)
        
        self.assertEqual(len(cucumber_data), 1)
        scenario = cucumber_data[0]
        self.assertIn('error_message', scenario)
        self.assertIsNotNone(scenario['error_message'])
        self.assertIn('AssertionError', scenario['error_message'])
    
    def test_stacktrace_in_html_report(self):
        """Test that HTML report contains stacktrace in expandable section"""
        self.rg.record_test_case_result(
            name="testcases/login_failed.py",
            status="FAILED",
            duration=5.5,
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=5.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        # Generate HTML
        html_path = self.rg.generate_html_report()
        
        # Read and verify HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Check for stacktrace section
        self.assertIn('Failed Test Cases - Error Details', html_content)
        self.assertIn('stacktrace', html_content)
        self.assertIn('AssertionError', html_content)
        self.assertIn('test_login.py', html_content)
        
        # Check for collapsible functionality
        self.assertIn('toggleDetail', html_content)
        self.assertIn('detail-content', html_content)
    
    def test_stacktrace_with_cucumber_in_html(self):
        """Test stacktrace in HTML for cucumber scenario"""
        self.rg.record(
            feature="Login Feature",
            scenario="Login with invalid credentials",
            status="failed",
            duration=3.5,
            steps_info=[
                {"keyword": "Given", "name": "I am on login page", "status": "PASSED", "duration": 1.0},
                {"keyword": "Then", "name": "I should see error", "status": "FAILED", "duration": 2.0}
            ],
            error_message=self.sample_stacktrace
        )
        
        self.rg.record_test_case_result(
            name="testcases/login.py",
            status="FAILED",
            duration=3.5
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=3.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        # Generate HTML
        html_path = self.rg.generate_html_report()
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Check for error details section in scenario (note HTML encoding)
        self.assertIn('Error Details', html_content)
        self.assertIn('Stacktrace', html_content)
        self.assertIn('AssertionError', html_content)


if __name__ == '__main__':
    unittest.main()
