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
    def __init__(self, url, testcase_name=None, output_dir="testcases", no_write=False):
        self.url = url
        self.testcase_name = testcase_name
        self.output_dir = output_dir
        self.no_write = no_write
        self.driver = None
        self.poll_thread = None
        self._poll_logs = False
        self._current_url = None
        self._listeners_injected = False
        self.recorded_actions = []
        self.recording_active = False
        self._seen_action_keys = set()  # for deduping actions across page navigations
        self._spy_saved_elements = {}   # xpath -> object_name mapping for find_test_obj
        
        # Template setup for object repository
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "jinja", "object_repository")
        self.env = Environment(loader=FileSystemLoader(tpl_dir), trim_blocks=True, lstrip_blocks=True)
        self.spy_template = self.env.get_template("WebElementEntity.json.j2")
        
        # Ensure output directories exist
        Path(output_dir).mkdir(exist_ok=True)
        Path("object_repository").mkdir(exist_ok=True)

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

        # Start log polling after listener injection
        self._poll_logs = True
        self.recording_active = True
        self.poll_thread = threading.Thread(target=self._poll_browser_logs, daemon=True)
        self.poll_thread.start()

        print(f"[RECORD] ✅ Recording started! Interact with the page normally.")
        print(f"[RECORD] 🛑 Click 'Stop Recording' button in the page or press Ctrl+C to stop.")

    def _ensure_listeners_on_navigation(self):
        """Re-inject listeners when the browser navigates to a new URL."""
        try:
            current_url = self.driver.current_url
        except Exception:
            return

        if current_url != self._current_url:
            self._current_url = current_url
            print(f"[RECORD] 🔄 Navigation detected: {current_url}. Re-injecting listeners...")
            self._inject_recording_listeners()

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
            if self.no_write:
                print(f"[RECORD] 📊 Actions recorded: {len(self.recorded_actions)}")
                print("[RECORD] ℹ️ --no-write mode: skipping test case file generation (Studio will handle it)")
            else:
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
                # Re-inject listeners on full page navigations (new document)
                self._ensure_listeners_on_navigation()

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
                                        
                                        # Avoid duplicates (id can reset after full navigation load)
                                        action_key = (action_data.get('id'), action_data.get('url'))
                                        if action_key not in self._seen_action_keys:
                                            self._seen_action_keys.add(action_key)
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
                                    action_key = (action_data.get('id'), action_data.get('url'))
                                    if action_key not in self._seen_action_keys:
                                        self._seen_action_keys.add(action_key)
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
        """Print a summary of the recorded action and spy element to object repository"""
        action_type = action.get('type', 'unknown')
        element = action.get('element', {})
        value = action.get('value')
        
        # Spy the element to object repository (for click, input, change actions)
        obj_name = None
        if action_type in ('click', 'input', 'change') and element:
            obj_name = self._spy_element(element)
        
        # In no_write mode, emit structured JSON events for Studio
        if self.no_write:
            self._emit_json_event(action_type, element, value, obj_name, action)
            return

        if action_type == 'click':
            target = obj_name or element.get('text', '') or element.get('id', '') or element.get('tagName', '')
            print(f"  🖱️  Click: {target[:30]}")
            
        elif action_type == 'input' or action_type == 'change':
            target = obj_name or element.get('id', '') or element.get('tagName', '')
            if element.get('type') == 'password':
                print(f"  ⌨️  Type: {target} = '***PASSWORD***'")
            else:
                display_value = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                print(f"  ⌨️  Type: {target} = '{display_value}'")
                
        elif action_type == 'change':
            target = obj_name or element.get('id', '') or element.get('tagName', '')
            print(f"  🔄 Change: {target} = {value}")
            
        elif action_type == 'navigation':
            print(f"  🔗 Navigate: {value}")
            
        elif action_type == 'page_load':
            print(f"  📄 Page Load: {action.get('url', '')}")

    def _emit_json_event(self, action_type, element, value, obj_name, action):
        """Emit a structured JSON event line for Studio consumption."""
        obj_file = f"{obj_name}.json" if obj_name else None

        if action_type == 'click':
            event = {"event": "record_action", "action": "click", "object": obj_file}
            print(json.dumps(event), flush=True)

        elif action_type in ('input', 'change'):
            is_password = element.get('type') == 'password'
            if element.get('tagName', '').lower() == 'select' or (isinstance(value, dict) and 'text' in value):
                sel_value = value.get('text', '') if isinstance(value, dict) else str(value)
                event = {"event": "record_action", "action": "select_by_text", "object": obj_file, "value": sel_value}
            elif is_password:
                event = {"event": "record_action", "action": "set_text", "object": obj_file, "value": str(value) if value else "", "isPassword": True}
            else:
                event = {"event": "record_action", "action": "set_text", "object": obj_file, "value": str(value) if value else ""}
            print(json.dumps(event), flush=True)

        elif action_type == 'navigation':
            event = {"event": "record_action", "action": "navigate", "value": str(value) if value else ""}
            print(json.dumps(event), flush=True)

        elif action_type == 'page_load':
            event = {"event": "record_action", "action": "page_load", "value": action.get('url', '')}
            print(json.dumps(event), flush=True)

    def _spy_element(self, element):
        """Save element to object repository and return its object name for find_test_obj"""
        xpath = element.get('xpath', '')
        if not xpath:
            return None
        
        # If already spied, return cached name
        if xpath in self._spy_saved_elements:
            return self._spy_saved_elements[xpath]
        
        tag = element.get('tagName', 'element')
        text = (element.get('text', '') or '').strip()
        element_id = element.get('id', '')
        
        # Build a descriptive name: tag_text or tag_id
        if element_id:
            name = f"{tag}_{element_id}"
        elif text:
            words = text.split()
            if len(words) > 3:
                text = ' '.join(words[:3])
            name = f"{tag}_{text.lower().replace(' ', '_')}"
        else:
            name = f"{tag}_{len(self._spy_saved_elements) + 1}"
        
        # Clean name for filename safety
        name = name.replace(':', '_').replace('#', '').replace('/', '_').replace('\\', '_')
        name = name.replace('"', '').replace("'", '').replace(' ', '_')
        
        # Get attributes from element (use enhanced attributes if available)
        attributes = element.get('attributes', {})
        
        # Fallback: build attributes from element dict if 'attributes' not present
        if not attributes:
            attributes = {}
            if element_id:
                attributes['id'] = element_id
            if element.get('className'):
                attributes['class'] = element['className']
            if element.get('type'):
                attributes['type'] = element['type']
        
        guid = uuid4()
        
        # Render and save object repository JSON
        # Replace double quotes in xpath with single quotes for valid JSON
        safe_xpath = xpath.replace('"', "'")

        if self.no_write:
            # Build test object and emit as single-line JSONL event
            props = [
                {"name": "tag", "value": tag, "isSelected": True, "matchCondition": "equals", "type": "Main"}
            ]
            for attr_name, attr_value in attributes.items():
                props.append({
                    "name": attr_name,
                    "value": attr_value,
                    "isSelected": False,
                    "matchCondition": "equals",
                    "type": "Main"
                })
            test_obj = {
                "name": name,
                "description": "",
                "tag": tag,
                "elementGuidId": str(guid),
                "selectorCollection": {"XPATH": safe_xpath},
                "selectorMethod": "XPATH",
                "webElementProperties": props
            }
            event_line = json.dumps({"event": "spy_result", "data": test_obj})
            print(event_line, flush=True)
        else:
            try:
                json_content = self.spy_template.render(
                    name=name,
                    guid=guid,
                    xpath=safe_xpath,
                    tag=tag,
                    text=text,
                    attributes=attributes
                )
                obj_path = os.path.join("object_repository", f"{name}.json")
                with open(obj_path, 'w', encoding='utf-8') as f:
                    f.write(json_content)
                print(f"  🔍 Spy: saved {obj_path}")
            except Exception as e:
                print(f"  ⚠️ Spy save failed: {e}")
        
        self._spy_saved_elements[xpath] = name
        return name

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
        lines.append("from orbs.keyword import find_test_obj")
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
        last_field_index = {}

        for action in actions:
            action_type = action.get('type')
            element = action.get('element', {})
            xpath = element.get('xpath')

            # Skip certain action types
            if action_type in ['page_load', 'summary']:
                continue

            # Skip interactions with recording UI elements
            element_id = element.get('id', '')
            if element_id in ['record-stop-btn', 'record-info-box', 'action-count']:
                continue

            # Prefer input events only once per form field (last value wins)
            if action_type in ['input', 'change'] and xpath:
                # For non-form value change events (dropdown/checkbox), we still keep final state
                if xpath in last_field_index:
                    optimized[last_field_index[xpath]] = action
                    continue
                else:
                    last_field_index[xpath] = len(optimized)
                    optimized.append(action)
                    continue

            # Keep clicks and navigation actions
            optimized.append(action)

        return optimized

    def _action_to_python(self, action):
        """Convert a recorded action to Python code using find_test_obj for locators"""
        action_type = action.get('type')
        element = action.get('element', {})
        value = action.get('value')
        
        # Try to use find_test_obj if element was spied to object repository
        xpath = element.get('xpath', '')
        obj_name = self._spy_saved_elements.get(xpath) if xpath else None
        
        if obj_name:
            locator_expr = f'find_test_obj("{obj_name}.json")'
        else:
            # Fallback to direct locator
            raw_locator = self._build_locator(element)
            if not raw_locator:
                return f"# Could not generate locator for {action_type}"
            locator_expr = f'"{raw_locator}"'
        
        if action_type == 'click':
            return f'Web.click({locator_expr})'
            
        elif action_type == 'input':
            if element.get('type') == 'password':
                return f'Web.set_text({locator_expr}, "your_password_here", secret=True)  # TODO: Replace with actual password'
            else:
                escaped_value = str(value).replace('"', '\\"')
                return f'Web.set_text({locator_expr}, "{escaped_value}")'
                
        elif action_type == 'change':
            if isinstance(value, dict) and 'text' in value:
                escaped_text = str(value['text']).replace('"', '\\"')
                return f'Web.select_by_text({locator_expr}, "{escaped_text}")'
            elif isinstance(value, bool):
                if value:
                    return f'Web.click({locator_expr})  # Check'
                else:
                    return f'# Uncheck: Web.click({locator_expr}) if needed'
            else:
                escaped_value = str(value).replace('"', '\\"')
                return f'Web.set_text({locator_expr}, "{escaped_value}")'
                
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