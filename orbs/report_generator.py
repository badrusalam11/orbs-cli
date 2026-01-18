import os
import json
import platform
import textwrap
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

from orbs.config import config
from orbs.exception import ReportGenerationException
from orbs.guard import orbs_guard

class ReportGenerator:
    @orbs_guard(ReportGenerationException)
    def __init__(self, base_dir="reports"):
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamp = self.generate_report_name(datetime.now())
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        self.run_dir = os.path.join(base_dir, timestamp)
        os.makedirs(self.run_dir, exist_ok=True)
        self.screenshots_dir = os.path.join(self.run_dir, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

        self.id_test = timestamp
        self.json_path = os.path.join(self.run_dir, "cucumber.json")
        self.pdf_path = os.path.join(self.run_dir, f"{timestamp}.pdf")
        self.overview_path = os.path.join(self.run_dir, "result.json")
        self.screenshot_path = os.path.join(self.run_dir, "screenshot.json")
        self.junit_path = os.path.join(self.run_dir, "junit.xml")
        self.html_path = os.path.join(self.run_dir, "report.html")

        self.c = canvas.Canvas(self.pdf_path, pagesize=letter)
        self.width, self.height = letter
        self.y = self.height - 50
        self.results = []
        self.testcase_result = []  # Track test case results
        self.overview = {}
        self.testcase_screenshots = []  # Track screenshots per test case
        self.current_page = 1  # Track current page number
        self.testcase_api_calls = {}
        self.testcase_scenarios = {}  # Track scenarios per test case: {testcase_name: [scenarios]}  
    
    def generate_report_name(self, timestamp):
        now = timestamp
        ts_sec = now.strftime("%Y%m%d_%H%M%S")          # e.g. "20250707_221530"
        # ms     = now.strftime("%f")[:3]                 # first 3 digits of microseconds → milliseconds
        # ts     = f"{ts_sec}_{ms}"                       # e.g. "20250707_221530_123"
        return ts_sec

    @orbs_guard(ReportGenerationException)
    def record(self, feature, scenario, status, duration, screenshot_paths=None, steps_info=None, category="positive", api_calls=None, error_message=None):
        """Record scenario with screenshots, steps, API calls, and error message/stacktrace"""
        self.results.append({
            "feature": feature,
            "scenario": scenario,
            "status": status,
            "duration": duration,
            "screenshot": screenshot_paths or [],
            "steps": steps_info or [],
            "category": category,
            "api_calls": api_calls or [],  # Add API calls to scenario record
            "error_message": error_message  # Add stacktrace/error message
        })

    @orbs_guard(ReportGenerationException)
    def record_test_case_result(self, name, status, duration, error_message=None, cucumber=None):
        self.testcase_result.append({
            "name": name,
            "status": status,
            "duration": duration,
            "error_message": error_message,  # Add stacktrace/error message
            "cucumber": cucumber or []  # Add cucumber scenarios
        }) 

    @orbs_guard(ReportGenerationException)
    def record_scenario_for_testcase(self, testcase_name, scenario_data):
        """Record a scenario that belongs to a specific test case"""
        if testcase_name not in self.testcase_scenarios:
            self.testcase_scenarios[testcase_name] = []
        self.testcase_scenarios[testcase_name].append(scenario_data)
    
    @orbs_guard(ReportGenerationException)
    def record_screenshot(self, testcase_name, screenshot_path):
        # Check if testcase entry exists
        for entry in self.testcase_screenshots:
            if entry["testcase_name"] == testcase_name:
                entry["screenshots"].append(screenshot_path)
                return
        # If not found, create new entry
        self.testcase_screenshots.append({
            "testcase_name": testcase_name,
            "screenshots": [screenshot_path]
        })

    @orbs_guard(ReportGenerationException)
    def record_overview(self, suite_path, duration, start_time, end_time):
        self.overriew = {
            "testsuite_id": os.path.relpath(suite_path, os.getcwd()),
            "tester_name": config.get("tester_name", "Unknown Tester"),
            "environent": config.get("environment", "Unknown Environment"),
            "host_name": platform.node(),
            "os": platform.system(),
            "duration": duration,
            "start_time": datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": datetime.fromtimestamp(end_time).strftime("%Y-%m-%d %H:%M:%S"),
            "total_testcase": len(self.testcase_result),
            "passed": sum(1 for r in self.testcase_result if r['status'].lower() == 'passed'),
            "failed": sum(1 for r in self.testcase_result if r['status'].lower() == 'failed'),
            "skipped": sum(1 for r in self.testcase_result if r['status'].lower() == 'skipped'),
            "testcase_results": self.testcase_result,
        }

    @orbs_guard(ReportGenerationException)
    def save_json(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        with open(os.path.join(self.overview_path), 'w') as f:
            json.dump(self.overriew, f, indent=2)
        
        with open(os.path.join(self.screenshot_path), 'w') as f:
            json.dump(self.testcase_screenshots, f, indent=2)
    
    @orbs_guard(ReportGenerationException)
    def generate_junit_xml(self):
        """Generate JUnit XML report for CI/CD integration"""
        from xml.etree.ElementTree import Element, SubElement, tostring
        from xml.dom import minidom
        
        # Use testcase_result as primary source (from result.json)
        total_tests = len(self.testcase_result)
        total_failures = sum(1 for r in self.testcase_result if r.get('status', '').lower() == 'failed')
        total_skipped = sum(1 for r in self.testcase_result if r.get('status', '').lower() == 'skipped')
        total_errors = 0  # Orbs doesn't distinguish errors from failures
        total_time = self.overriew.get('duration', 0)
        
        # Root element
        testsuites = Element('testsuites')
        testsuites.set('name', self.overriew.get('testsuite_id', 'Test Suite'))
        testsuites.set('tests', str(total_tests))
        testsuites.set('failures', str(total_failures))
        testsuites.set('errors', str(total_errors))
        testsuites.set('skipped', str(total_skipped))
        testsuites.set('time', f"{total_time:.3f}")
        testsuites.set('timestamp', self.overriew.get('start_time', ''))
        
        # Create one testsuite for all test cases
        testsuite = SubElement(testsuites, 'testsuite')
        testsuite.set('name', 'Test Cases')
        testsuite.set('tests', str(total_tests))
        testsuite.set('failures', str(total_failures))
        testsuite.set('errors', '0')
        testsuite.set('skipped', str(total_skipped))
        testsuite.set('time', f"{total_time:.3f}")
        
        # Add each test case as <testcase>
        for tc in self.testcase_result:
            testcase = SubElement(testsuite, 'testcase')
            testcase.set('name', tc['name'])
            testcase.set('classname', tc['name'])
            testcase.set('time', f"{tc['duration']:.3f}")
            
            status = tc['status'].lower()
            
            # Add failure info if failed
            if status == 'failed':
                failure = SubElement(testcase, 'failure')
                failure.set('message', f"Test case '{tc['name']}' failed")
                failure.set('type', 'AssertionError')
                
                # Build failure text with cucumber scenarios if available
                failure_text = []
                
                # Add cucumber scenario details if available
                cucumber_scenarios = tc.get('cucumber', [])
                if cucumber_scenarios:
                    for scenario in cucumber_scenarios:
                        failure_text.append(f"\n--- Scenario: {scenario['scenario']} ---")
                        failure_text.append(f"Status: {scenario['status']}")
                        failure_text.append(f"Duration: {scenario['duration']:.2f}s")
                        
                        # Add step details
                        for step in scenario.get('steps', []):
                            step_status = step.get('status', 'UNKNOWN')
                            failure_text.append(f"  {step['keyword']} {step['name']} - {step_status} ({step['duration']}s)")
                        
                        # Add scenario stacktrace if available
                        if scenario.get('error_message'):
                            failure_text.append('\n--- Scenario Stacktrace ---')
                            failure_text.append(scenario['error_message'])
                
                # Add test case stacktrace if available
                if tc.get('error_message'):
                    failure_text.append('\n--- Test Case Stacktrace ---')
                    failure_text.append(tc['error_message'])
                
                if failure_text:
                    failure.text = '\n'.join(failure_text)
            
            elif status == 'skipped':
                skipped = SubElement(testcase, 'skipped')
                skipped.set('message', 'Test skipped')
            
            # Add properties for cucumber scenarios (optional metadata)
            cucumber_scenarios = tc.get('cucumber', [])
            if cucumber_scenarios:
                properties = SubElement(testcase, 'properties')
                for idx, scenario in enumerate(cucumber_scenarios, 1):
                    prop = SubElement(properties, 'property')
                    prop.set('name', f'cucumber_scenario_{idx}')
                    prop.set('value', f"{scenario['scenario']} - {scenario['status']} ({scenario['duration']:.2f}s)")
        
        # Pretty print XML
        xml_string = minidom.parseString(tostring(testsuites, encoding='utf-8')).toprettyxml(indent="  ")
        
        # Write to file
        with open(self.junit_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        return self.junit_path

    @orbs_guard(ReportGenerationException)
    def generate_html_report(self):
        """Generate modern HTML report similar to Katalon"""
        import base64
        
        # Prepare data
        overview = self.overriew
        test_cases = self.testcase_result
        scenarios = self.results
        screenshots_data = self.testcase_screenshots
        
        # Calculate pass rate
        total = overview.get('total_testcase', 0)
        passed = overview.get('passed', 0)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Encode screenshots to base64 for embedding
        def encode_image(img_path):
            try:
                with open(img_path, 'rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    ext = os.path.splitext(img_path)[1].lower()
                    mime = 'image/png' if ext == '.png' else 'image/jpeg'
                    return f"data:{mime};base64,{encoded}"
            except Exception:
                return ""
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Execution Report - {overview.get('testsuite_id', 'Test Suite')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #2c3e50;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        
        .stat-card {{
            text-align: center;
        }}
        
        .stat-card .number {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        
        .stat-card .label {{
            font-size: 14px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.total .number {{ color: #3498db; }}
        .stat-card.passed .number {{ color: #27ae60; }}
        .stat-card.failed .number {{ color: #e74c3c; }}
        .stat-card.skipped .number {{ color: #f39c12; }}
        
        .info-card {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 10px;
            font-size: 14px;
        }}
        
        .info-card .label {{
            font-weight: 600;
            color: #7f8c8d;
        }}
        
        .info-card .value {{
            color: #2c3e50;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        table {{
            width: 100%;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background: #34495e;
            color: white;
        }}
        
        thead th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        tbody tr {{
            border-bottom: 1px solid #ecf0f1;
            transition: background 0.2s;
            cursor: pointer;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        tbody td {{
            padding: 15px;
            font-size: 14px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge.passed {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge.failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .badge.skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .controls {{
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 250px;
            padding: 12px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .filter-btn {{
            padding: 10px 20px;
            border: 2px solid #e0e0e0;
            background: white;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        
        .filter-btn:hover {{
            border-color: #667eea;
            color: #667eea;
        }}
        
        .filter-btn.active {{
            background: #667eea;
            color: white;
            border-color: #667eea;
        }}
        
        .detail-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .detail-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .detail-header:hover {{
            background: #e9ecef;
        }}
        
        .detail-header h3 {{
            font-size: 18px;
            color: #2c3e50;
        }}
        
        .collapse-icon {{
            transition: transform 0.3s;
        }}
        
        .collapse-icon.open {{
            transform: rotate(180deg);
        }}
        
        .detail-content {{
            display: none;
            padding: 20px 0;
        }}
        
        .detail-content.show {{
            display: block;
        }}
        
        .step {{
            padding: 12px 15px;
            margin: 8px 0;
            border-left: 4px solid #3498db;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        
        .step.passed {{
            border-left-color: #27ae60;
            background: #d4edda;
        }}
        
        .step.failed {{
            border-left-color: #e74c3c;
            background: #f8d7da;
        }}
        
        .step .keyword {{
            font-weight: 700;
            margin-right: 8px;
        }}
        
        .step .duration {{
            float: right;
            color: #7f8c8d;
            font-size: 12px;
        }}
        
        .screenshot-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .screenshot-item {{
            position: relative;
            cursor: pointer;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        
        .screenshot-item:hover {{
            transform: scale(1.05);
        }}
        
        .screenshot-item img {{
            width: 100%;
            height: 150px;
            object-fit: cover;
            display: block;
        }}
        
        .api-call {{
            margin: 15px 0;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .api-header {{
            display: flex;
            align-items: center;
            padding: 12px 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .api-method {{
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 12px;
            margin-right: 12px;
        }}
        
        .api-method.GET {{ background: #61affe; color: white; }}
        .api-method.POST {{ background: #49cc90; color: white; }}
        .api-method.PUT {{ background: #fca130; color: white; }}
        .api-method.DELETE {{ background: #f93e3e; color: white; }}
        .api-method.PATCH {{ background: #50e3c2; color: white; }}
        
        .api-url {{
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #2c3e50;
            word-break: break-all;
        }}
        
        .api-body {{
            padding: 15px;
        }}
        
        .api-body h4 {{
            font-size: 13px;
            margin-bottom: 8px;
            color: #7f8c8d;
        }}
        
        .api-body pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            line-height: 1.5;
        }}
        
        .stacktrace {{
            background: #2c3e50;
            color: #e74c3c;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.6;
            margin-top: 10px;
            border-left: 4px solid #e74c3c;
        }}
        
        .stacktrace .error-line {{
            color: #ff6b6b;
        }}
        
        .stacktrace .file-line {{
            color: #4ecdc4;
        }}
        
        .error-alert {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 12px 15px;
            border-radius: 6px;
            margin-top: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .error-alert::before {{
            content: '⚠️';
            font-size: 20px;
        }}
        
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            justify-content: center;
            align-items: center;
        }}
        
        .modal.show {{
            display: flex;
        }}
        
        .modal img {{
            max-width: 90%;
            max-height: 90%;
            object-fit: contain;
        }}
        
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 40px;
            font-size: 40px;
            color: white;
            cursor: pointer;
        }}
        
        .section-title {{
            font-size: 24px;
            margin: 30px 0 20px 0;
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        @media (max-width: 768px) {{
            .dashboard {{
                grid-template-columns: 1fr;
            }}
            
            .controls {{
                flex-direction: column;
            }}
            
            .search-box, .filter-btn {{
                width: 100%;
            }}
            
            .screenshot-gallery {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>🎯 Test Execution Report</h1>
            <p>{overview.get('testsuite_id', 'Test Suite')} • Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </header>
    
    <div class="container">
        <!-- Dashboard Stats -->
        <div class="dashboard">
            <div class="card stat-card total">
                <div class="label">Total Tests</div>
                <div class="number">{total}</div>
            </div>
            <div class="card stat-card passed">
                <div class="label">Passed</div>
                <div class="number">{passed}</div>
            </div>
            <div class="card stat-card failed">
                <div class="label">Failed</div>
                <div class="number">{overview.get('failed', 0)}</div>
            </div>
            <div class="card stat-card skipped">
                <div class="label">Skipped</div>
                <div class="number">{overview.get('skipped', 0)}</div>
            </div>
        </div>
        
        <!-- Info and Chart -->
        <div class="dashboard">
            <div class="card info-card">
                <div class="label">Executor:</div>
                <div class="value">{overview.get('tester_name', 'Unknown')}</div>
                
                <div class="label">Environment:</div>
                <div class="value">{overview.get('environent', 'Unknown')}</div>
                
                <div class="label">Host:</div>
                <div class="value">{overview.get('host_name', 'Unknown')}</div>
                
                <div class="label">OS:</div>
                <div class="value">{overview.get('os', 'Unknown')}</div>
                
                <div class="label">Start Time:</div>
                <div class="value">{overview.get('start_time', '')}</div>
                
                <div class="label">End Time:</div>
                <div class="value">{overview.get('end_time', '')}</div>
                
                <div class="label">Duration:</div>
                <div class="value">{int(overview.get('duration', 0)//60)}m {int(overview.get('duration', 0)%60)}s</div>
                
                <div class="label">Pass Rate:</div>
                <div class="value" style="color: {'#27ae60' if pass_rate >= 80 else '#e74c3c'}; font-weight: 700;">{pass_rate:.1f}%</div>
            </div>
            
            <div class="card">
                <div class="chart-container">
                    <canvas id="pieChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Test Cases Table -->
        <h2 class="section-title">📋 Test Cases</h2>
        
        <div class="controls">
            <input type="text" class="search-box" id="searchBox" placeholder="🔍 Search test cases...">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="passed">Passed</button>
            <button class="filter-btn" data-filter="failed">Failed</button>
            <button class="filter-btn" data-filter="skipped">Skipped</button>
        </div>
        
        <div class="card">
            <table id="testTable">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Test Case ID</th>
                        <th>Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Add test case rows
        for idx, tc in enumerate(test_cases, 1):
            status = tc['status'].lower()
            duration = tc['duration']
            dur_str = f"{int(duration//60)}m {int(duration%60)}s"
            
            html += f"""                    <tr class="test-row" data-status="{status}" data-index="{idx}">
                        <td>{idx}</td>
                        <td>{tc['name']}</td>
                        <td>{dur_str}</td>
                        <td><span class="badge {status}">{status.upper()}</span></td>
                    </tr>
"""
        
        html += """                </tbody>
            </table>
        </div>
        
        <!-- Detailed Results -->
        <h2 class="section-title">📊 Detailed Results</h2>
"""
        
        # Render test cases with their details (now using tc['cucumber'] array)
        for tc_idx, tc in enumerate(test_cases, 1):
            tc_name = tc['name']
            tc_status = tc['status'].lower()
            tc_duration = tc['duration']
            tc_id = tc_name.replace('/', '-').replace('\\', '-').replace('.', '-')
            
            # Find screenshots for this test case
            tc_screenshots = []
            for entry in screenshots_data:
                if entry['testcase_name'] == tc_name:
                    tc_screenshots = entry['screenshots']
                    break
            
            # Find API calls for this test case
            tc_api_calls = self.testcase_api_calls.get(tc_name, [])
            
            # Start test case section
            html += f"""        <div class="detail-section">
            <div class="detail-header" onclick="toggleDetail('tc-{tc_id}')">
                <h3>
                    <span class="badge {tc_status}">{tc_status.upper()}</span>
                    {tc_idx}. {tc_name}
                    <span style="float: right; color: #7f8c8d; font-size: 14px; margin-left: 15px;">{int(tc_duration//60)}m {int(tc_duration%60)}s</span>
                </h3>
                <span class="collapse-icon" id="icon-tc-{tc_id}">▼</span>
            </div>
            <div class="detail-content" id="tc-{tc_id}">
"""
            
            # If test case failed and has error message (no cucumber scenarios)
            if tc_status == 'failed' and tc.get('error_message'):
                error_msg = tc['error_message']
                error_msg = error_msg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                html += f"""                <div class="error-alert">
                    <div>
                        <strong>Test case failed with error:</strong>
                        <div class="stacktrace" style="margin-top: 10px;">{error_msg}</div>
                    </div>
                </div>
"""
            
            # Get cucumber scenarios for this specific test case
            tc_cucumber_scenarios = tc.get('cucumber', [])
            
            # If this test case has cucumber scenarios
            if tc_cucumber_scenarios:
                # Show scenarios (grouped by feature)
                current_feature = None
                for scenario_idx, scenario in enumerate(tc_cucumber_scenarios, 1):
                    # Start new feature group if needed
                    if scenario['feature'] != current_feature:
                        if current_feature is not None:
                            html += "                </div>\n"  # Close previous feature group
                        current_feature = scenario['feature']
                        html += f"""                <div style="margin: 20px 0; padding: 15px; background: #f0f4ff; border-radius: 8px;">
                    <h4 style="margin-bottom: 15px; color: #667eea;">🎭 Feature: {current_feature}</h4>
"""
                    
                    # Scenario detail
                    status_class = scenario['status'].lower()
                    html += f"""                    <div style="margin: 15px 0; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid {'#27ae60' if status_class == 'passed' else '#e74c3c' if status_class == 'failed' else '#f39c12'};">
                        <h5 style="margin-bottom: 10px;">
                            <span class="badge {status_class}">{scenario['status'].upper()}</span>
                            Scenario: {scenario['scenario']}
                            <span style="float: right; color: #7f8c8d; font-size: 13px;">{scenario['duration']:.2f}s</span>
                        </h5>
"""
                    
                    # Steps
                    if scenario.get('steps'):
                        html += """                        <div style="margin-top: 15px;">
                            <strong style="font-size: 13px;">Steps:</strong>
"""
                        for step in scenario['steps']:
                            step_status = step['status'].lower()
                            html += f"""                            <div class="step {step_status}">
                                <span class="keyword">{step['keyword']}</span>{step['name']}
                                <span class="duration">{step['duration']:.2f}s</span>
                            </div>
"""
                        html += "                        </div>\n"
                    
                    # Error stacktrace for failed scenarios
                    if status_class == 'failed' and scenario.get('error_message'):
                        error_msg = scenario['error_message']
                        error_msg = error_msg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        
                        html += f"""                        <div style="margin-top: 15px;">
                            <div class="detail-header" onclick="toggleDetail('scenario-error-{tc_id}-{scenario_idx}')">
                                <strong style="color: #e74c3c;">⚠️ Error Details</strong>
                                <span class="collapse-icon" id="icon-scenario-error-{tc_id}-{scenario_idx}">▼</span>
                            </div>
                            <div class="detail-content" id="scenario-error-{tc_id}-{scenario_idx}">
                                <div class="stacktrace">{error_msg}</div>
                            </div>
                        </div>
"""
                    
                    # API Calls for this scenario
                    if scenario.get('api_calls'):
                        html += f"""                        <div style="margin-top: 15px;">
                            <div class="detail-header" onclick="toggleDetail('scenario-api-{tc_id}-{scenario_idx}')">
                                <strong>🌐 API Calls ({len(scenario['api_calls'])} calls)</strong>
                                <span class="collapse-icon" id="icon-scenario-api-{tc_id}-{scenario_idx}">▼</span>
                            </div>
                            <div class="detail-content" id="scenario-api-{tc_id}-{scenario_idx}">
"""
                        
                        for api_idx, call in enumerate(scenario['api_calls'], 1):
                            method = call.get('method', '').upper()
                            url = call.get('url', '')
                            req = call.get('kwargs', {})
                            resp = call.get('response_body', '')
                            
                            html += f"""                                <div class="api-call">
                                    <div class="api-header">
                                        <span class="api-method {method}">{method}</span>
                                        <span class="api-url">{url}</span>
                                    </div>
                                    <div class="api-body">
"""
                            
                            if req:
                                if 'json' in req:
                                    req_body = json.dumps(req['json'], indent=2)
                                else:
                                    req_body = str(req.get('data', ''))
                                
                                if req_body and req_body.strip():
                                    html += f"""                                        <h4>Request:</h4>
                                        <pre>{req_body[:500]}{'...' if len(req_body) > 500 else ''}</pre>
"""
                            
                            if resp and resp.strip():
                                html += f"""                                        <h4>Response:</h4>
                                        <pre>{resp[:500]}{'...' if len(resp) > 500 else ''}</pre>
"""
                            
                            html += """                                    </div>
                                </div>
"""
                        
                        html += """                            </div>
                        </div>
"""
                    
                    # Screenshots for this scenario
                    if scenario.get('screenshot'):
                        screenshots_list = scenario['screenshot']
                        html += f"""                        <div style="margin-top: 15px;">
                            <div class="detail-header" onclick="toggleDetail('scenario-ss-{tc_id}-{scenario_idx}')">
                                <strong>📸 Screenshots ({len(screenshots_list)} images)</strong>
                                <span class="collapse-icon" id="icon-scenario-ss-{tc_id}-{scenario_idx}">▼</span>
                            </div>
                            <div class="detail-content" id="scenario-ss-{tc_id}-{scenario_idx}">
                                <div class="screenshot-gallery">
"""
                        
                        for img_idx, img_path in enumerate(screenshots_list):
                            img_data = encode_image(img_path)
                            if img_data:
                                html += f"""                                    <div class="screenshot-item" onclick="showModal('{img_data}')">
                                        <img src="{img_data}" alt="Screenshot {img_idx + 1}">
                                    </div>
"""
                        
                        html += """                                </div>
                            </div>
                        </div>
"""
                    
                    html += "                    </div>\n"
                
                if current_feature:
                    html += "                </div>\n"  # Close last feature group
            
            # If no cucumber scenarios, show screenshots directly (test case level)
            elif tc_screenshots:
                html += f"""                <div style="margin-top: 15px;">
                    <strong>📸 Screenshots ({len(tc_screenshots)} images)</strong>
                    <div class="screenshot-gallery" style="margin-top: 10px;">
"""
                
                for img_idx, img_path in enumerate(tc_screenshots):
                    img_data = encode_image(img_path)
                    if img_data:
                        html += f"""                        <div class="screenshot-item" onclick="showModal('{img_data}')">
                            <img src="{img_data}" alt="Screenshot {img_idx + 1}">
                        </div>
"""
                
                html += """                    </div>
                </div>
"""
            
            # Close test case section
            html += "            </div>\n        </div>\n"
        
        # Modal and scripts
        html += f"""    </div>
    
    <!-- Image Modal -->
    <div class="modal" id="imageModal" onclick="closeModal()">
        <span class="modal-close">&times;</span>
        <img id="modalImage" src="" alt="Full size">
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script>
        // Pie Chart
        const ctx = document.getElementById('pieChart').getContext('2d');
        new Chart(ctx, {{
            type: 'doughnut',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{passed}, {overview.get('failed', 0)}, {overview.get('skipped', 0)}],
                    backgroundColor: ['#27ae60', '#e74c3c', '#f39c12'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{
                                size: 14
                            }},
                            padding: 15
                        }}
                    }},
                    title: {{
                        display: true,
                        text: 'Test Results Distribution',
                        font: {{
                            size: 16,
                            weight: 'bold'
                        }},
                        padding: 20
                    }}
                }}
            }}
        }});
        
        // Filter functionality
        const filterBtns = document.querySelectorAll('.filter-btn');
        const testRows = document.querySelectorAll('.test-row');
        const searchBox = document.getElementById('searchBox');
        
        filterBtns.forEach(btn => {{
            btn.addEventListener('click', () => {{
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                const filter = btn.dataset.filter;
                testRows.forEach(row => {{
                    const status = row.dataset.status;
                    if (filter === 'all' || status === filter) {{
                        row.style.display = '';
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
            }});
        }});
        
        // Search functionality
        searchBox.addEventListener('input', (e) => {{
            const searchTerm = e.target.value.toLowerCase();
            testRows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            }});
        }});
        
        // Toggle detail sections
        function toggleDetail(id) {{
            const content = document.getElementById(id);
            const icon = document.getElementById('icon-' + id);
            
            if (content.classList.contains('show')) {{
                content.classList.remove('show');
                icon.classList.remove('open');
            }} else {{
                content.classList.add('show');
                icon.classList.add('open');
            }}
        }}
        
        // Modal functions
        function showModal(imgSrc) {{
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modalImg.src = imgSrc;
            modal.classList.add('show');
        }}
        
        function closeModal() {{
            document.getElementById('imageModal').classList.remove('show');
        }}
        
        // Keyboard support for modal
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});
    </script>
</body>
</html>"""
        
        # Write HTML file
        with open(self.html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return self.html_path

    def _new_page_if_needed(self, height_needed=100):
        if self.y < height_needed:
            self._add_footer()  # Add footer before new page
            self.c.showPage()
            self.current_page += 1  # Increment page number
            self.y = self.height - 50

    def _wrap_text(self, text, max_width, font_name, font_size):
        """
        Wrap text to fit within max_width.
        - Splits on spaces when possible
        - Chops words longer than max_width into smaller pieces
        """
        if not text:
            return [""]
            
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            # if adding this word still fits, do it
            if self.c.stringWidth(test, font_name, font_size) <= max_width:
                current = test
            else:
                # flush the current line
                if current:
                    lines.append(current)
                # now handle the too-long word itself
                if self.c.stringWidth(word, font_name, font_size) <= max_width:
                    # it fits on its own line
                    current = word
                else:
                    # break the word into sub‑chunks
                    part = ""
                    for ch in word:
                        if self.c.stringWidth(part + ch, font_name, font_size) <= max_width:
                            part += ch
                        else:
                            if part:
                                lines.append(part)
                            part = ch
                    current = part
        if current:
            lines.append(current)
        return lines

    def _calculate_row_height(self, texts, col_widths, font_name="Helvetica", font_size=10, min_height=20):
        """Calculate the height needed for a table row based on wrapped text"""
        max_lines = 1
        for text, width in zip(texts, col_widths):
            if text:
                wrapped = self._wrap_text(str(text), width - 10, font_name, font_size)  # -10 for padding
                max_lines = max(max_lines, len(wrapped))
        
        line_height = font_size + 2
        return max(min_height, max_lines * line_height + 10)  # +10 for padding

    def _draw_wrapped_text_in_cell(self, text, x, y, width, font_name="Helvetica", font_size=10, color=colors.black):
        """Draw wrapped text within a cell"""
        self.c.setFont(font_name, font_size)
        self.c.setFillColor(color)
        
        wrapped = self._wrap_text(str(text), width - 10, font_name, font_size)
        line_height = font_size + 2
        
        for i, line in enumerate(wrapped):
            self.c.drawString(x + 5, y - 15 - (i * line_height), line)

    def _add_footer(self):
        """Add copyright footer with clickable LinkedIn link and page numbering"""
        footer_y = 20  # Position from bottom
        copyright_text = "© Copyright Muhamad Badru Salam"
        page_text = f"Page {self.current_page}"
        linkedin_url = "https://www.linkedin.com/in/muhamad-badru-salam-3bab2531b/"
        
        # Save current state
        self.c.saveState()
        
        # Set footer font and color
        self.c.setFont("Helvetica", 8)
        self.c.setFillColor(colors.grey)
        
        # Calculate positions
        copyright_width = self.c.stringWidth(copyright_text, "Helvetica", 8)
        page_width = self.c.stringWidth(page_text, "Helvetica", 8)
        
        # Center the copyright text
        copyright_x = (self.width - copyright_width) / 2
        
        # Position page number on the right
        page_x = self.width - 50 - page_width
        
        # Draw the copyright footer with clickable LinkedIn link
        self.c.linkURL(linkedin_url, (copyright_x, footer_y - 2, copyright_x + copyright_width, footer_y + 10))
        self.c.drawString(copyright_x, footer_y, copyright_text)
        
        # Draw page number
        self.c.drawString(page_x, footer_y, page_text)
        
        # Restore state
        self.c.restoreState()

    def add_header(self, suite_name):
        self.c.setFont("Helvetica-Bold", 16)
        self.c.drawString(50, self.y, f"Test Suite Report: {suite_name}")
        self.y -= 20
        self.c.setFont("Helvetica", 10)
        self.c.drawString(50, self.y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.y -= 30

    def add_section_title(self, title, font_size=14, spacing=10):
        """Draw a bold title and advance the y-cursor."""
        self._new_page_if_needed(font_size + spacing)
        self.c.setFont("Helvetica-Bold", font_size)
        self.c.drawString(50, self.y, title)
        self.y -= (font_size + spacing)
        self.c.setFont("Helvetica", 10)   # reset for following content

    def add_summary_section(self):
        data = self.overriew
        line_h = 15
        left = 50
        mid = 180
        right = 400

        # Make sure we have room
        self._new_page_if_needed(6 * line_h + 20)

        # Block 1: executor, id, environment, host, os
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawString(left,        self.y,           "Executor")
        self.c.drawString(left,        self.y - line_h,  "ID")
        self.c.drawString(left,        self.y - 2*line_h,"Environment")
        self.c.drawString(left,        self.y - 3*line_h,"Host")
        self.c.drawString(left,        self.y - 4*line_h,"OS")

        self.c.setFont("Helvetica", 10)
        self.c.drawString(mid,         self.y,           data.get("tester_name", "Unknown"))
        self.c.drawString(mid,         self.y - line_h,  data.get("testsuite_id", "Unknown"))
        self.c.drawString(mid,         self.y - 2*line_h,data.get("environent", ""))
        self.c.drawString(mid,         self.y - 3*line_h,data.get("host_name", ""))
        self.c.drawString(mid,         self.y - 4*line_h,data.get("os", ""))

        # Block 2: counts
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawString(left,        self.y - 6*line_h, "Total")
        self.c.drawString(left,        self.y - 7*line_h, "Passed")
        self.c.drawString(left,        self.y - 8*line_h, "Failed")

        self.c.setFont("Helvetica", 10)
        self.c.setFillColor(colors.black)
        self.c.drawString(mid,         self.y - 6*line_h, str(data.get("total_testcase", 0)))
        self.c.setFillColor(colors.green)
        self.c.drawString(mid,         self.y - 7*line_h, str(data.get("passed", 0)))
        self.c.setFillColor(colors.red)
        self.c.drawString(mid,         self.y - 8*line_h, str(data.get("failed", 0)))

        # Block 3: time info
        self.c.setFillColor(colors.black)
        self.c.setFont("Helvetica-Bold", 11)
        self.c.drawString(right,       self.y - 6*line_h, "Start")
        self.c.drawString(right,       self.y - 7*line_h, "End")
        self.c.drawString(right,       self.y - 8*line_h, "Elapsed")

        self.c.setFont("Helvetica", 10)
        self.c.drawString(right + 60,  self.y - 6*line_h, data.get("start_time", ""))
        self.c.drawString(right + 60,  self.y - 7*line_h, data.get("end_time", ""))
        dur = data.get("duration", 0)
        elapsed = f"{int(dur//60)}m - {int(dur%60)}s"
        self.c.drawString(right + 60,  self.y - 8*line_h, elapsed)

        # reset color and move cursor
        self.c.setFillColor(colors.black)
        self.y -= (9 * line_h)
        
    def add_cucumber_summary_table(self):
        left_margin = 50
        table_width = self.width - 100

        col_widths = [
            table_width * 0.06,   # #
            table_width * 0.22,   # Feature
            table_width * 0.40,   # Scenario
            table_width * 0.16,   # Category
            table_width * 0.16    # Status
        ]

        # Draw section title
        self.y -= 10
        self.add_section_title("Cucumber Scenario", font_size=12, spacing=8)

        # Header background
        header_height = 25
        self._new_page_if_needed(header_height + 5)
        self.c.setFillColor(HexColor("#4a90e2"))
        self.c.rect(left_margin, self.y - header_height, table_width, header_height, fill=1, stroke=0)

        # Draw headers
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 11)
        x = left_margin
        headers = ["#", "Fitur", "Scenario", "Category", "Status"]
        for header, w in zip(headers, col_widths):
            self.c.drawString(x + 5, self.y - 18, header)
            x += w
        self.y -= header_height

        # Draw rows with dynamic heights
        for idx, item in enumerate(self.results, 1):
            # Prepare row data
            row_data = [
                str(idx),
                item["feature"],
                item["scenario"],
                item.get("category", "positive").capitalize(),
                item["status"].upper()
            ]
            
            # Calculate row height based on wrapped text
            row_height = self._calculate_row_height(row_data, col_widths, font_size=10, min_height=25)
            
            # Check if we need a new page
            self._new_page_if_needed(row_height + 5)
            
            # Draw row background for category column
            category = item.get("category", "positive").lower()
            if category == "positive":
                bg_color = HexColor("#d6e9c6")
            elif category == "negative":
                bg_color = HexColor("#f2dede")
            else:
                bg_color = colors.lightgrey
            
            # Draw category background
            cat_x = left_margin + col_widths[0] + col_widths[1] + col_widths[2]
            self.c.setFillColor(bg_color)
            self.c.rect(cat_x, self.y - row_height, col_widths[3], row_height, fill=1, stroke=0)
            
            # Draw cell content
            x = left_margin
            for i, (text, width) in enumerate(zip(row_data, col_widths)):
                if i == 4:  # Status column - colored text
                    status = text
                    color = colors.green if status == "PASSED" else (colors.red if status == "FAILED" else colors.orange)
                    self._draw_wrapped_text_in_cell(text, x, self.y, width, color=color)
                else:
                    self._draw_wrapped_text_in_cell(text, x, self.y, width)
                x += width
            
            self.y -= row_height

        self.y -= 10
        self.c.setFillColor(colors.black)

    def add_testcase_table(self):
        left_margin = 50
        table_width = self.width - 100

        col_widths = [
            table_width * 0.10,   # #
            table_width * 0.50,   # ID (increased width)
            table_width * 0.20,   # Duration
            table_width * 0.20,   # Status
        ]

        # Header background
        header_height = 25
        self._new_page_if_needed(header_height + 10)
        self.c.setFillColor(HexColor("#4a90e2"))
        self.c.rect(left_margin, self.y - header_height, table_width, header_height, fill=1, stroke=0)

        # Draw headers
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 11)
        x = left_margin
        headers = ["#", "ID Testcase", "Duration", "Status"]
        for header, w in zip(headers, col_widths):
            self.c.drawString(x + 5, self.y - 18, header)
            x += w
        self.y -= header_height

        # Draw rows with dynamic heights
        for idx, case in enumerate(self.testcase_result, start=1):
            # Prepare row data
            dur = case['duration']
            dur_str = f"{int(dur//60)}m - {int(dur%60)}s"
            
            row_data = [
                str(idx),
                case['name'],
                dur_str,
                case['status'].upper()
            ]
            
            # Calculate row height based on wrapped text
            row_height = self._calculate_row_height(row_data, col_widths, font_size=10, min_height=25)
            
            # Check if we need a new page
            self._new_page_if_needed(row_height + 5)
            
            # Draw cell content
            x = left_margin
            for i, (text, width) in enumerate(zip(row_data, col_widths)):
                if i == 3:  # Status column - colored text
                    status = text
                    color = colors.green if status == "PASSED" else (colors.red if status == "FAILED" else colors.orange)
                    self._draw_wrapped_text_in_cell(text, x, self.y, width, color=color)
                else:
                    self._draw_wrapped_text_in_cell(text, x, self.y, width)
                x += width
            
            self.y -= row_height

        # Reset fill color
        self.c.setFillColor(colors.black)
        self.y -= 10

    def add_feature_section(self, feature_name):
        # Calculate height needed for wrapped feature name
        full_width = self.width - 100
        wrapped_feature = self._wrap_text(f"Feature: {feature_name}", full_width - 10, "Helvetica-Bold", 12)
        stripe_height = max(25, len(wrapped_feature) * 16 + 10)
        
        self._new_page_if_needed(stripe_height + 60)
        
        # Green feature header with wider margins
        self.c.setFillColor(HexColor("#4a90e2"))
        self.c.rect(50, self.y - stripe_height, full_width, stripe_height, stroke=0, fill=1)
        
        # White text on green background - wrapped
        self.c.setFillColor(colors.white)
        self.c.setFont("Helvetica-Bold", 12)
        
        # Draw wrapped feature name
        for i, line in enumerate(wrapped_feature):
            self.c.drawString(55, self.y - 18 - (i * 16), line)
        
        self.y -= stripe_height
        self.c.setFillColor(colors.black)

    def add_scenario_section(self, scenario_data):
        # Ensure enough room
        self._new_page_if_needed(200)

        # 1) Wrap the scenario title
        full_width = self.width - 100    # 50px margin each side
        text       = (f"Scenario: {scenario_data['scenario']} "
                    f"({scenario_data['status']}, {scenario_data['duration']:.2f}s)")
        wrapped    = self._wrap_text(text, full_width - 10, "Helvetica-Bold", 11)
        line_h     = 14
        stripe_h   = max(25, len(wrapped) * line_h + 10)  # Increased padding

        # 2) Draw header stripe at current y
        stripe_top = self.y
        stripe_bottom = stripe_top - stripe_h
        if scenario_data['status'].lower() == "passed":
            hex_background = "#f4f4dc"
        else:
            hex_background = "#f26f6f" 
        self.c.setFillColor(HexColor(hex_background))
        self.c.rect(50, stripe_bottom, full_width, stripe_h, stroke=0, fill=1)

        # 3) Draw each wrapped line
        self.c.setFillColor(colors.black)
        self.c.setFont("Helvetica-Bold", 11)
        text_x = 55
        # start ~10px down from stripe_top
        start_y = stripe_top - 12
        for i, line in enumerate(wrapped):
            self.c.drawString(text_x, start_y - i*line_h, line)

        # 4) Now move self.y BELOW the stripe (no padding - direct connection)
        self.y = stripe_bottom

        # 5) Draw steps starting from current y
        box_width   = full_width
        left_margin = 50
        text_margin = 60
        right_pad   = 15

        for step in scenario_data['steps']:
            keyword = step['keyword']
            name    = step['name']
            dur_txt = f"{step['duration']:.2f}s"

            # calculate height & wrap
            dur_w   = self.c.stringWidth(dur_txt, "Helvetica", 10)
            avail_w = box_width - (text_margin - left_margin) - right_pad - dur_w - 20
            lines   = self._wrap_text(f"{keyword} {name}", avail_w, "Helvetica", 10)
            step_h  = max(25, len(lines) * line_h + 10)  # Increased minimum height

            # page break if needed
            self._new_page_if_needed(step_h + 5)

            # draw step background
            if step['status'].lower() == "passed":
                hex_background = "#c7d98d"
            elif step['status'].lower() == "failed":
                hex_background = "#f5b0b0"
            else: 
                hex_background="#e3dede"
            self.c.setFillColor(HexColor(hex_background))
            self.c.rect(left_margin, self.y - step_h, box_width, step_h, stroke=0, fill=1)

            # draw text + bold keyword
            y0 = self.y - 12
            x0 = text_margin

            # first line: bold keyword
            first = lines[0]
            if first.startswith(keyword + " "):
                self.c.setFont("Helvetica-Bold", 10)
                self.c.setFillColor(colors.black)
                self.c.drawString(x0, y0, keyword)
                kw_w = self.c.stringWidth(keyword + " ", "Helvetica-Bold", 10)
                self.c.setFont("Helvetica", 10)
                self.c.drawString(x0 + kw_w, y0, first[len(keyword)+1:])
            else:
                self.c.setFont("Helvetica", 10)
                self.c.setFillColor(colors.black)
                self.c.drawString(x0, y0, first)

            # additional lines
            self.c.setFont("Helvetica", 10)
            for idx, ln in enumerate(lines[1:], start=1):
                self.c.drawString(text_margin, y0 - idx*line_h, ln)

            # duration at right
            self.c.drawString(
                left_margin + box_width - right_pad - dur_w,
                y0,
                dur_txt
            )

            # advance y position
            self.y -= step_h
            
        # 6) API Calls: Display scenario-specific API calls AFTER steps
        scenario_api_calls = scenario_data.get('api_calls', [])
        if scenario_api_calls:
            self.add_api_section(scenario_api_calls, f"API Calls for Scenario: {scenario_data['scenario']}")
            
        # 7) Screenshots: Display AFTER steps and API calls
        screenshots = scenario_data.get('screenshot', [])
        if screenshots:
            self.y -= 10
            margin_left = 50
            margin_right = self.width - 50
            x_cursor = margin_left
            max_row_h = 0
            gap = 10
            # setelah kamu punya full_width, margin_left, margin_right, gap
            for img_file in screenshots:
                img_reader = ImageReader(img_file)
                iw, ih = img_reader.getSize()
                ratio = iw / ih

                if ratio > 1.5:  # treat as web screenshot
                    # full‑width layout
                    self._new_page_if_needed(ih + gap)
                    max_w = full_width
                    scale = max_w / iw
                    w, h = iw * scale, ih * scale
                    y_pos = self.y - h
                    self.c.drawImage(img_reader, margin_left, y_pos, width=w, height=h)
                    self.y = y_pos - gap
                    # reset grid cursors
                    x_cursor = margin_left
                    max_row_h = 0
                else:
                    # grid layout (mobile)
                    self._new_page_if_needed(150 + gap)  # minimal height
                    max_w = (margin_right - margin_left) / 3
                    max_h = 150
                    scale = min(max_w / iw, max_h / ih)
                    w, h = iw * scale, ih * scale

                    if x_cursor + w > margin_right:
                        self.y -= (max_row_h + gap)
                        x_cursor = margin_left
                        max_row_h = 0

                    y_pos = self.y - h
                    self.c.drawImage(img_reader, x_cursor, y_pos, width=w, height=h)
                    x_cursor += w + gap
                    max_row_h = max(max_row_h, h)

            # setelah loop, baris terakhir:
            self.y -= (max_row_h + gap)

        # 8) Add spacing before next scenario
        self.y -= 15
        self.c.setFillColor(colors.black)

    METHOD_COLORS = {
        "GET":    HexColor("#61affe"),
        "POST":   HexColor("#49cc90"),
        "PUT":    HexColor("#fca130"),
        "DELETE": HexColor("#f93e3e"),
        "PATCH":  HexColor("#50e3c2"),
    }

    def add_api_section(self, api_calls, section_title=None):
        """
        ✅ REUSABLE method for displaying API calls
        Can be called from both scenarios and test cases
        """
        if not api_calls:
            return

        # Add section title if provided
        if section_title:
            self.y -= 10
            self.add_section_title(section_title, font_size=10, spacing=6)

        for call in api_calls:
            method = call.get("method", "").upper()
            url = call.get("url", "")
            req = call.get("kwargs", {})
            resp = call.get("response_body", "")

            margin = 50
            full_width = self.width - 2*margin
            badge_w = 50
            text_x = margin + badge_w + 5
            wrap_width = full_width - badge_w - 10

            # 1) Header
            header_h = 20
            self._new_page_if_needed(header_h + 200)
            # border
            self.c.setStrokeColor(self.METHOD_COLORS.get(method, colors.black))
            self.c.rect(margin, self.y - header_h, full_width, header_h, fill=0)
            # badge
            self.c.setFillColor(self.METHOD_COLORS.get(method, colors.black))
            self.c.rect(margin, self.y - header_h, badge_w, header_h, fill=1, stroke=0)
            self.c.setFillColor(colors.white)
            self.c.setFont("Helvetica-Bold", 9)
            self.c.drawCentredString(margin + badge_w/2, self.y - header_h + 5, method)
            # URL (wrapped)
            self.c.setFillColor(colors.black)
            self.c.setFont("Helvetica", 8)
            url_lines = self._wrap_text(url, wrap_width, "Helvetica", 8)
            for i, line in enumerate(url_lines):
                self.c.drawString(text_x, self.y - header_h + 5 - i*10, line)
            # step down
            self.y -= (header_h + 5)

            # 2) Request box (light blue) - ULTRA STRICT WIDTH CONTROL
            if req:
                if "json" in req:
                    payload = json.dumps(req["json"], ensure_ascii=False)
                else:
                    payload = str(req.get("data", ""))
                
                if payload and payload.strip():
                    # ✅ MAXIMUM WIDTH SAFETY - Batas width sangat ketat
                    max_content_width = full_width - 100  # Margin super besar
                    
                    # Split payload into manageable chunks if too long
                    if len(payload) > 300:  # Limit panjang payload
                        payload = payload[:300] + "... (truncated)"
                    
                    req_lines = []
                    words = payload.split()
                    current_line = ""
                    
                    for word in words:
                        test_line = f"{current_line} {word}".strip()
                        # ✅ STRICT WIDTH CHECK - Cek width setiap kata
                        if self.c.stringWidth(test_line, "Helvetica", 7) <= max_content_width:
                            current_line = test_line
                        else:
                            if current_line:
                                req_lines.append(current_line)
                            current_line = word
                    
                    if current_line:
                        req_lines.append(current_line)
                    
                    req_h = 12 + len(req_lines)*8
                    self._new_page_if_needed(req_h + 20)
                    
                    self.c.setFillColor(HexColor("#e3f2fd"))
                    self.c.rect(margin, self.y - req_h, full_width, req_h, fill=1, stroke=0)
                    self.c.setFillColor(colors.black)
                    self.c.setFont("Helvetica-Bold", 8)
                    self.c.drawString(margin + 5, self.y - 12, "Request:")
                    self.c.setFont("Helvetica", 7)
                    
                    for i, line in enumerate(req_lines):
                        x_pos = margin + 60
                        y_pos = self.y - 12 - i*8
                        # ✅ FINAL SAFETY CHECK - Potong jika masih terlalu panjang
                        while self.c.stringWidth(line, "Helvetica", 7) > max_content_width and len(line) > 10:
                            line = line[:-10] + "..."
                        self.c.drawString(x_pos, y_pos, line)
                    
                    self.y -= (req_h + 5)

            # 3) Response box (light green) - ULTRA STRICT WIDTH CONTROL
            if resp and resp.strip():
                # ✅ MAXIMUM WIDTH SAFETY - Batas width sangat ketat
                max_content_width = full_width - 100  # Margin super besar
                
                # Split response into manageable chunks if too long
                if len(resp) > 300:  # Limit panjang response
                    resp = resp[:300] + "... (truncated)"
                
                resp_lines = []
                words = resp.split()
                current_line = ""
                
                for word in words:
                    test_line = f"{current_line} {word}".strip()
                    # ✅ STRICT WIDTH CHECK - Cek width setiap kata
                    if self.c.stringWidth(test_line, "Helvetica", 7) <= max_content_width:
                        current_line = test_line
                    else:
                        if current_line:
                            resp_lines.append(current_line)
                        current_line = word
                
                if current_line:
                    resp_lines.append(current_line)
                
                resp_h = 12 + len(resp_lines)*8
                self._new_page_if_needed(resp_h + 20)
                
                self.c.setFillColor(HexColor("#e8f5e9"))
                self.c.rect(margin, self.y - resp_h, full_width, resp_h, fill=1, stroke=0)
                self.c.setFillColor(colors.black)
                self.c.setFont("Helvetica-Bold", 8)
                self.c.drawString(margin + 5, self.y - 12, "Response:")
                self.c.setFont("Helvetica", 7)
                
                for i, line in enumerate(resp_lines):
                    x_pos = margin + 60
                    y_pos = self.y - 12 - i*8
                    # ✅ FINAL SAFETY CHECK - Potong jika masih terlalu panjang
                    while self.c.stringWidth(line, "Helvetica", 7) > max_content_width and len(line) > 10:
                        line = line[:-10] + "..."
                    self.c.drawString(x_pos, y_pos, line)
                
                self.y -= (resp_h + 15)
                self._new_page_if_needed(50)

    def add_api_section_for_test_case(self, case_name):
        """
        ✅ WRAPPER method for test case API calls
        Uses the generic add_api_section method
        """
        calls = self.testcase_api_calls.get(case_name, [])
        if not calls:
            return

        # Add spacing and call the generic method
        self.y -= 15
        self.add_api_section(calls, f"API Calls for {case_name}")

    @orbs_guard(ReportGenerationException)
    def finalize(self, suite_path):
        suite_name = os.path.basename(suite_path)
        
        # 1. Add header
        self.add_header(suite_name)
        
        # 2. Add summary section
        self.add_summary_section()
        
        # 3. Add test case table (always first)
        self.add_testcase_table()

        # 4. If we have cucumber results, add cucumber sections
        if self.results:
            # Add cucumber summary table
            self.add_cucumber_summary_table()
            
            # Add detailed cucumber scenarios
            self.y -= 20
            self.add_section_title("Cucumber Detail", font_size=12, spacing=8)

            # Group scenarios by feature and display them properly
            current_feature = None
            for item in self.results:
                # Add feature header if this is a new feature
                if item['feature'] != current_feature:
                    if current_feature is not None:  # Add spacing between features
                        self.y -= 20
                    self.add_feature_section(item['feature'])
                    current_feature = item['feature']
                
                # Add the scenario with its steps and screenshots
                self.add_scenario_section(item)

        # 5. Screenshot-only summary when no cucumber scenarios but we have screenshots
        elif self.testcase_screenshots:
            self.c.showPage()
            self.current_page += 1
            self.y = self.height - 50
            self.add_section_title("Screenshot Attachment", font_size=14, spacing=12)

            left = 50
            line_h = 18
            table_width = self.width - 100
            col_widths = [30, 270, 80, 80]

            # Header row background and white text
            self._new_page_if_needed(line_h + 5)
            self.c.setFillColor(HexColor("#4a90e2"))
            self.c.rect(left, self.y - line_h, table_width, line_h, fill=1, stroke=0)
            self.c.setFillColor(colors.white)
            self.c.setFont("Helvetica-Bold", 11)
            x = left
            for header, w in zip(["#", "Description", "Elapsed", "Status"], col_widths):
                self.c.drawString(x + 5, self.y - 15, header)
                x += w

            self.y -= line_h

            # Data rows without outlines
            self.c.setFont("Helvetica", 10)
            for idx, entry in enumerate(self.testcase_screenshots, start=1):
                name = entry["testcase_name"]
                match = next((r for r in self.testcase_result if r["name"] == name), {})
                dur = match.get("duration", 0)
                elapsed = f"{int(dur//60)}m {int(dur%60)}s"
                status = match.get("status", "").upper()

                self._new_page_if_needed(line_h + 120)
                y_top = self.y

                # Text columns
                self.c.setFillColor(colors.black)
                self.c.drawString(left + 5, y_top - 15, str(idx))
                self.c.drawString(left + col_widths[0] + 5, y_top - 15, name)
                self.c.drawString(left + sum(col_widths[:2]) + 5, y_top - 15, elapsed)
                color = colors.green if status == "PASSED" else (colors.red if status == "FAILED" else colors.orange)
                self.c.setFillColor(color)
                self.c.drawString(left + sum(col_widths[:3]) + 5, y_top - 15, status)
                self.c.setFillColor(colors.black)

                # Draw screenshot image below text
                if entry["screenshots"]:
                    img_path = entry["screenshots"][-1]
                    try:
                        img = ImageReader(img_path)
                        iw, ih = img.getSize()
                        max_w = col_widths[1]
                        max_h = 100
                        scale = min(max_w/iw, max_h/ih)
                        w, h = iw*scale, ih*scale
                        img_x = left + col_widths[0] + 5
                        img_y = y_top - line_h - h - 5
                        self.c.drawImage(img, img_x, img_y, width=w, height=h, preserveAspectRatio=True)
                    except Exception:
                        # Draw placeholder if image fails to load
                        self.c.setFillColor(colors.lightgrey)
                        self.c.rect(left + col_widths[0] + 5, y_top - line_h - 50, col_widths[1], 50, fill=1, stroke=0)
                        self.c.setFillColor(colors.black)

                self.y = y_top - line_h - 120 - 10    

        # 6. Add API sections for each test case
        # ✅ Only show test case API calls if no scenarios have API calls
        has_scenario_api_calls = any(item.get('api_calls') for item in self.results)
        if not has_scenario_api_calls:
            for case in (c["name"] for c in self.testcase_result):
                self.add_api_section_for_test_case(case)
        
        # 7. Add footer and save
        self._add_footer()
        self.save_json()
        self.generate_junit_xml()  # Generate JUnit XML for CI/CD
        self.generate_html_report()  # Generate HTML report
        self.c.save()
        return self.run_dir

# Convenience function
def create_suite_report(suite_path, results):
    rg = ReportGenerator()
    for rec in results:
        rg.record(rec['feature'], rec['scenario'], rec['status'], rec['duration'], rec.get('screenshot'), rec.get('steps'))
    return rg.finalize(suite_path)