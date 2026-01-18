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


class TestReportGeneratorJUnit(unittest.TestCase):
    """Test JUnit XML generation in ReportGenerator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.rg = ReportGenerator(base_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_junit_with_failed_testcase(self):
        """Test JUnit XML generation with failed test case - BUG REPRODUCTION"""
        # Setup: Record a FAILED test case
        self.rg.record_test_case_result(
            name="testcases/mobile/login_sauce.py",
            status="FAILED",
            duration=16.38
        )
        
        # Setup: Record overview
        self.rg.record_overview(
            suite_path="testsuites/login_sauce.yml",
            duration=16.38,
            start_time=datetime(2026, 1, 18, 18, 5, 4).timestamp(),
            end_time=datetime(2026, 1, 18, 18, 5, 20).timestamp()
        )
        
        # Generate JUnit XML
        junit_path = self.rg.generate_junit_xml()
        
        # Parse the generated XML
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        # Assertions
        self.assertEqual(root.tag, 'testsuites')
        self.assertEqual(root.get('tests'), '1', "Should have 1 test")
        self.assertEqual(root.get('failures'), '1', "Should have 1 failure - THIS WAS THE BUG!")
        self.assertEqual(root.get('errors'), '0', "Should have 0 errors")
        
        # Check testsuite
        testsuite = root.find('testsuite')
        self.assertIsNotNone(testsuite)
        self.assertEqual(testsuite.get('tests'), '1')
        self.assertEqual(testsuite.get('failures'), '1', "Testsuite should also show 1 failure")
        
        # Check testcase has failure element
        testcase = testsuite.find('testcase')
        self.assertIsNotNone(testcase)
        self.assertEqual(testcase.get('name'), 'testcases/mobile/login_sauce.py')
        
        failure = testcase.find('failure')
        self.assertIsNotNone(failure, "Failed testcase MUST have <failure> element!")
        self.assertIn('failed', failure.get('message', '').lower())
    
    def test_junit_with_passed_testcase(self):
        """Test JUnit XML generation with passed test case"""
        self.rg.record_test_case_result(
            name="testcases/web/login.py",
            status="PASSED",
            duration=5.5
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=5.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        junit_path = self.rg.generate_junit_xml()
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        self.assertEqual(root.get('tests'), '1')
        self.assertEqual(root.get('failures'), '0')
        
        testcase = root.find('.//testcase')
        self.assertIsNotNone(testcase)
        failure = testcase.find('failure')
        self.assertIsNone(failure, "Passed testcase should NOT have <failure> element")
    
    def test_junit_with_cucumber_scenarios(self):
        """Test JUnit XML with cucumber scenarios"""
        # Record cucumber scenario
        self.rg.record(
            feature="Login Feature",
            scenario="Successful login",
            status="passed",
            duration=3.5,
            category="positive"
        )
        
        self.rg.record(
            feature="Login Feature",
            scenario="Failed login with wrong password",
            status="failed",
            duration=2.1,
            category="negative"
        )
        
        # Also record test case result (should be used for counts)
        self.rg.record_test_case_result(
            name="testcases/login.py",
            status="FAILED",
            duration=5.6
        )
        
        self.rg.record_overview(
            suite_path="testsuites/login.yml",
            duration=5.6,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        junit_path = self.rg.generate_junit_xml()
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        # ✅ FIX: When testcase_result exists, it takes priority for counts
        # This ensures accurate test counts even when cucumber scenarios exist
        self.assertEqual(root.get('tests'), '1', "Should use testcase_result count")
        self.assertEqual(root.get('failures'), '1')
        
        # Check that failed scenario has failure element
        testcases = root.findall('.//testcase')
        self.assertEqual(len(testcases), 2, "Should still show all cucumber scenarios")
        
        failed_testcase = next((tc for tc in testcases if 'wrong password' in tc.get('name')), None)
        self.assertIsNotNone(failed_testcase)
        failure = failed_testcase.find('failure')
        self.assertIsNotNone(failure, "Failed scenario MUST have <failure> element")
    
    def test_junit_with_mixed_results(self):
        """Test JUnit with multiple test cases - passed, failed, skipped"""
        self.rg.record_test_case_result("test1.py", "PASSED", 1.0)
        self.rg.record_test_case_result("test2.py", "FAILED", 2.0)
        self.rg.record_test_case_result("test3.py", "SKIPPED", 0.0)
        self.rg.record_test_case_result("test4.py", "PASSED", 1.5)
        
        self.rg.record_overview(
            suite_path="testsuites/mixed.yml",
            duration=4.5,
            start_time=datetime.now().timestamp(),
            end_time=datetime.now().timestamp()
        )
        
        junit_path = self.rg.generate_junit_xml()
        tree = ET.parse(junit_path)
        root = tree.getroot()
        
        self.assertEqual(root.get('tests'), '4')
        self.assertEqual(root.get('failures'), '1')
        self.assertEqual(root.get('skipped'), '1')
        
        testcases = root.findall('.//testcase')
        self.assertEqual(len(testcases), 4)
        
        # Count failures and skipped
        failures = [tc for tc in testcases if tc.find('failure') is not None]
        skipped = [tc for tc in testcases if tc.find('skipped') is not None]
        
        self.assertEqual(len(failures), 1, "Should have exactly 1 <failure> element")
        self.assertEqual(len(skipped), 1, "Should have exactly 1 <skipped> element")


if __name__ == '__main__':
    unittest.main()
