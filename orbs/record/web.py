# record/web.py

import json
import os
import time
import threading
from uuid import uuid4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from .base import RecordRunner
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from InquirerPy import inquirer
import typer


class WebRecordRunner(RecordRunner):
    def __init__(self, url, testcase_name=None, output_dir="testcases"):
        self.url = url
        self.testcase_name = testcase_name
        self.output_dir = output_dir
        self.driver = None
        self.poll_thread = None
        self._poll_logs = False
        self._current_url = None
        self._listeners_injected = False
        self.recorded_actions = []
        self.recording_active = False
        
        # Template setup
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "jinja")
        self.env = Environment(loader=FileSystemLoader(tpl_dir), trim_blocks=True, lstrip_blocks=True)
        
        # Ensure output directory exists
        Path(output_dir).mkdir(exist_ok=True)

    def start(self):
        """Start the recording session"""
        if not self.testcase_name:
            self.testcase_name = self._prompt_testcase_name()
        
        # Prepare Chrome with logging
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Navigate to URL
        if self.url and not self.url.startswith(('http://', 'https://')):
            self.url = 'https://' + self.url
            
        self.driver.get(self.url)
        self._current_url = self.driver.current_url
        
        print(f"[RECORD] 🎬 Starting recording session for '{self.testcase_name}'")
        print(f"[RECORD] 🌐 Opened: {self.url}")
        
        self._inject_recording_listeners()
        
        # Start log polling
        self._poll_logs = True
        self.recording_active = True
        self.poll_thread = threading.Thread(target=self._poll_browser_logs, daemon=True)
        self.poll_thread.start()
        
        print(f"[RECORD] ✅ Recording started! Interact with the page normally.")
        print(f"[RECORD] 🛑 Click 'Stop Recording' button in the page or press Ctrl+C to stop.")

    def stop(self):
        """Stop recording and generate test case"""
        self.recording_active = False
        self._poll_logs = False
        
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join(timeout=2)
        
        print(f"\n[RECORD] 🛑 Stopping recording...")
        
        # Fetch actions directly from JavaScript (more reliable than browser logs)
        try:
            if self.driver and self._listeners_injected:
                js_actions = self.driver.execute_script("return window.recordedActions || [];")
                if js_actions:
                    # Merge with any actions we got from logs (avoid duplicates by id)
                    existing_ids = {a.get('id') for a in self.recorded_actions}
                    for action in js_actions:
                        if action.get('id') not in existing_ids:
                            self.recorded_actions.append(action)
                    print(f"[RECORD] 📥 Retrieved {len(js_actions)} actions from browser")
        except Exception as e:
            print(f"[RECORD] ⚠️ Could not retrieve actions from browser: {e}")
        
        # Generate test case
        if self.recorded_actions:
            self._generate_testcase()
        else:
            print("[RECORD] ⚠️ No actions recorded.")
        
        if self.driver:
            self.driver.quit()
            
        print("[RECORD] ✅ Recording session ended.")

    def _prompt_testcase_name(self):
        """Prompt user for test case name if not provided"""
        print("\n" + "="*50)
        print("🎬 Orbs Web Recorder - Interactive Mode")
        print("="*50)
        print("Record user interactions and generate test cases automatically!")
        print("")
        
        name = inquirer.text(
            message="Test case name:",
            default="test_recorded_scenario",
            validate=lambda x: len(x.strip()) > 0
        ).execute()
        
        return name.strip()

    def _inject_recording_listeners(self):
        """Inject JavaScript recording listeners"""
        try:
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            js_file = Path(__file__).parent / "js" / "web_record_listener.js"
            with open(js_file, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            self.driver.execute_script(js_content)
            self._listeners_injected = True
            print("[RECORD] 📝 Recording listeners injected successfully")
            
        except Exception as e:
            print(f"[RECORD] Error injecting listeners: {e}")
            self._listeners_injected = False

    def _poll_browser_logs(self):
        """Poll browser console logs for recorded actions"""
        while self._poll_logs:
            try:
                logs = self.driver.get_log('browser')
                for log_entry in logs:
                    message = log_entry.get('message', '')
                    
                    # Parse recorded actions from browser console
                    # Chrome log format: "console-api 123:45 \"[ORBS_RECORD] {...}\""
                    if '[ORBS_RECORD]' in message and 'Recording initialized' not in message and 'ORBS_RECORD_START' not in message:
                        try:
                            # Try to extract JSON from the message
                            # The message might be escaped or have various formats
                            
                            # Method 1: Find [ORBS_RECORD] and extract JSON after it
                            marker = '[ORBS_RECORD]'
                            marker_pos = message.find(marker)
                            if marker_pos != -1:
                                # Get everything after the marker
                                after_marker = message[marker_pos + len(marker):]
                                
                                # Find the JSON object
                                json_start = after_marker.find('{')
                                if json_start != -1:
                                    # Try to find matching closing brace
                                    brace_count = 0
                                    json_end = -1
                                    in_string = False
                                    escape_next = False
                                    
                                    for i, char in enumerate(after_marker[json_start:]):
                                        if escape_next:
                                            escape_next = False
                                            continue
                                        if char == '\\':
                                            escape_next = True
                                            continue
                                        if char == '"' and not escape_next:
                                            in_string = not in_string
                                        if not in_string:
                                            if char == '{':
                                                brace_count += 1
                                            elif char == '}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    json_end = json_start + i + 1
                                                    break
                                    
                                    if json_end > json_start:
                                        json_str = after_marker[json_start:json_end]
                                        # Unescape if needed
                                        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
                                        action_data = json.loads(json_str)
                                        
                                        # Avoid duplicates
                                        if not any(a.get('id') == action_data.get('id') for a in self.recorded_actions):
                                            self.recorded_actions.append(action_data)
                                            self._print_action_summary(action_data)
                        except (json.JSONDecodeError, Exception) as e:
                            # Try simpler extraction for escaped JSON
                            try:
                                # Look for escaped JSON pattern
                                import re
                                pattern = r'\[ORBS_RECORD\]\s*(\{.*\})'
                                # Handle escaped quotes
                                cleaned = message.replace('\\"', '"').replace('\\\\', '\\')
                                match = re.search(pattern, cleaned)
                                if match:
                                    json_str = match.group(1)
                                    action_data = json.loads(json_str)
                                    if not any(a.get('id') == action_data.get('id') for a in self.recorded_actions):
                                        self.recorded_actions.append(action_data)
                                        self._print_action_summary(action_data)
                            except:
                                pass
                    
                    elif '[ORBS_RECORD_END]' in message:
                        self.recording_active = False
                        break
                        
                time.sleep(0.3)
                
            except Exception as e:
                if self.recording_active:
                    pass  # Silently continue
                time.sleep(0.5)

    def _print_action_summary(self, action):
        """Print a summary of the recorded action"""
        action_type = action.get('type', 'unknown')
        element = action.get('element', {})
        value = action.get('value')
        
        if action_type == 'click':
            target = element.get('text', '') or element.get('id', '') or element.get('tagName', '')
            print(f"  🖱️  Click: {target[:30]}")
            
        elif action_type == 'input':
            target = element.get('id', '') or element.get('tagName', '')
            if value == '***PASSWORD***':
                print(f"  ⌨️  Type: {target} (password)")
            else:
                display_value = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                print(f"  ⌨️  Type: {target} = '{display_value}'")
                
        elif action_type == 'change':
            target = element.get('id', '') or element.get('tagName', '')
            print(f"  🔄 Change: {target} = {value}")
            
        elif action_type == 'navigation':
            print(f"  🔗 Navigate: {value}")
            
        elif action_type == 'page_load':
            print(f"  📄 Page Load: {action.get('url', '')}")

    def _generate_testcase(self):
        """Generate test case from recorded actions"""
        print(f"\n[RECORD] 📝 Generating test case...")
        
        # Create testcase content
        testcase_content = self._build_python_testcase()
        
        # Save to file
        filename = f"{self.testcase_name}.py"
        filepath = Path(self.output_dir) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(testcase_content)
        
        print(f"[RECORD] ✅ Test case generated: {filepath}")
        print(f"[RECORD] 📊 Actions recorded: {len(self.recorded_actions)}")
        print(f"\n[RECORD] 🚀 Run your test case with:")
        print(f"   python {filepath}")

    def _build_python_testcase(self):
        """Build Python test case from recorded actions"""
        
        # Group actions by type and optimize
        optimized_actions = self._optimize_actions(self.recorded_actions)
        
        # Generate Python code
        lines = []
        lines.append("#!/usr/bin/env python3")
        lines.append('"""')
        lines.append(f"Generated test case: {self.testcase_name}")
        lines.append(f"Created by Orbs Recorder on {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append('"""')
        lines.append("")
        lines.append("from orbs.keyword.web import Web")
        lines.append("")
        lines.append("")
        lines.append("def run():")
        lines.append(f'    """Generated test case for {self.testcase_name}"""')
        lines.append("")
        
        # Add setup
        lines.append("    # Setup")
        lines.append(f'    Web.open("{self.url}")')
        lines.append("")
        
        # Add recorded actions
        lines.append("    # Recorded interactions")
        
        for action in optimized_actions:
            python_code = self._action_to_python(action)
            if python_code:
                lines.append(f"    {python_code}")
        
        lines.append("")
        lines.append("    # Cleanup")
        lines.append("    Web.close()")
        
        return "\n".join(lines)

    def _optimize_actions(self, actions):
        """Optimize recorded actions (remove duplicates, combine sequences)"""
        optimized = []
        
        for action in actions:
            action_type = action.get('type')
            element = action.get('element', {})
            
            # Skip certain action types
            if action_type in ['page_load', 'summary']:
                continue
            
            # Skip interactions with recording UI elements
            element_id = element.get('id', '')
            if element_id in ['record-stop-btn', 'record-info-box', 'action-count']:
                continue
                
            # Skip rapid duplicate inputs on same element
            if (action_type == 'input' and optimized and 
                optimized[-1].get('type') == 'input' and
                optimized[-1].get('element', {}).get('xpath') == action.get('element', {}).get('xpath')):
                # Replace the last input with current (final value)
                optimized[-1] = action
                continue
            
            optimized.append(action)
        
        return optimized

    def _action_to_python(self, action):
        """Convert a recorded action to Python code"""
        action_type = action.get('type')
        element = action.get('element', {})
        value = action.get('value')
        
        # Build locator
        locator = self._build_locator(element)
        if not locator:
            return f"# Could not generate locator for {action_type}"
        
        if action_type == 'click':
            return f'Web.click("{locator}")'
            
        elif action_type == 'input':
            if value == '***PASSWORD***':
                return f'Web.set_text("{locator}", "your_password_here")  # TODO: Replace with actual password'
            else:
                escaped_value = str(value).replace('"', '\\"')
                return f'Web.set_text("{locator}", "{escaped_value}")'
                
        elif action_type == 'change':
            if isinstance(value, dict) and 'text' in value:
                # Select dropdown
                escaped_text = str(value['text']).replace('"', '\\"')
                return f'Web.select_by_text("{locator}", "{escaped_text}")'
            elif isinstance(value, bool):
                # Checkbox/radio
                if value:
                    return f'Web.click("{locator}")  # Check'
                else:
                    return f'# Uncheck: Web.click("{locator}") if needed'
            else:
                escaped_value = str(value).replace('"', '\\"')
                return f'Web.set_text("{locator}", "{escaped_value}")'
                
        elif action_type == 'keypress':
            if value == 'Enter':
                return f'# Press Enter (consider using submit or wait_for_element instead)'
            elif value == 'Tab':
                return f'# Tab to next field'
            else:
                return f'# Key press: {value}'
                
        elif action_type == 'navigation':
            return f'# Navigation: {value}'
        
        return f'# Unknown action: {action_type}'

    def _build_locator(self, element):
        """Build the best locator for an element"""
        if not element:
            return None
            
        # Prefer ID
        if element.get('id'):
            return f"id={element['id']}"
        
        # Try XPath
        xpath = element.get('xpath')
        if xpath:
            return f"xpath={xpath}"
            
        # Fallback to CSS selector
        selector = element.get('selector')
        if selector:
            return f"css={selector}"
        
        return None