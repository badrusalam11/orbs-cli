# spy/web.py

import json
import os
import time
import threading
from uuid import uuid4
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import SpyRunner
from jinja2 import Environment, FileSystemLoader
import ast


class WebSpyRunner(SpyRunner):
    def __init__(self, url, output_dir="object_repository"):
        self.url = url
        self.output_dir = output_dir
        self.driver = None
        self.poll_thread = None
        self._poll_logs = False
        self._current_url = None
        self._listeners_injected = False
        # Template setup
        tpl_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "jinja", "object_repository")
        self.env = Environment(loader=FileSystemLoader(tpl_dir), trim_blocks=True, lstrip_blocks=True)
        self.template = self.env.get_template("WebElementEntity.xml.j2")

    def start(self):
        options = Options()
        # ensure logs are captured
        options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
        # Initialize driver with both options and capabilities
        self.driver = webdriver.Chrome(options=options)

        self.driver.get(self.url)
        self._current_url = self.driver.current_url
        print(f"[SPY] Started Web session on {self.url}")
        self._inject_listeners()
        # Start log polling
        self._poll_logs = True
        self.poll_thread = threading.Thread(target=self._poll_browser_logs, daemon=True)
        self.poll_thread.start()

    def stop(self):
        self._poll_logs = False
        if self.poll_thread and self.poll_thread.is_alive():
            self.poll_thread.join()
        if self.driver:
            self.driver.quit()
        print("[SPY] Stopped Web session.")

    def _check_and_reinject_listeners(self):
        """Check if page has changed and re-inject listeners if needed"""
        try:
            current_url = self.driver.current_url
            
            # Check if URL has changed or if listeners are not present
            if current_url != self._current_url or not self._are_listeners_present():
                print(f"[SPY] Page changed or listeners missing. Re-injecting...")
                print(f"[SPY] Previous URL: {self._current_url}")
                print(f"[SPY] Current URL: {current_url}")
                
                self._current_url = current_url
                self._inject_listeners()
                
        except Exception as e:
            print(f"[SPY] Error checking page state: {e}")

    def _are_listeners_present(self):
        """Check if our listeners are still present on the page"""
        try:
            # Check if our spy marker exists
            result = self.driver.execute_script("""
                return window._spy_listeners_injected === true;
            """)
            return result
        except:
            return False

    def _inject_listeners(self):
        """Inject mouse and keyboard listeners with improved error handling"""
        try:
            # Wait for document to be ready
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            js = self._load_js_file('web_spy_listener.js')
            
            self.driver.execute_script(js)
            self._listeners_injected = True
            print("[SPY] JavaScript listeners injected successfully")
            
        except Exception as e:
            print(f"[SPY] Error injecting listeners: {e}")
            self._listeners_injected = False

    def _load_js_file(self, filename):
        """Load JavaScript code from external file"""
        js_dir = os.path.join(os.path.dirname(__file__), "js")
        js_path = os.path.join(js_dir, filename)
        
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"[SPY] JavaScript file not found: {js_path}")
            raise
        except Exception as e:
            print(f"[SPY] Error reading JavaScript file: {e}")
            raise
        
    def _poll_browser_logs(self):
        seen = set()
        while self._poll_logs:
            try:
                # Check and re-inject listeners if needed
                self._check_and_reinject_listeners()
                
                for entry in self.driver.get_log('browser'):
                    msg = entry.get('message', '')
                    if '[SPY]' in msg:
                        raw = msg.split('[SPY]', 1)[-1].strip()
                        print(f"[SPY] Raw log: {raw}")

                        # Hapus quote luar jika ada
                        if raw.startswith('"'):
                            raw = raw[1:]  # buang " luar
                        if raw.endswith('"'):
                            raw = raw[:-1]
                        # Decode escape sequence dari Chrome logs
                        try:
                            unescaped = bytes(raw, "utf-8").decode("unicode_escape")
                            print(f"[SPY] Unescaped: {unescaped}")
                            data = json.loads(unescaped)
                        except Exception as e:
                            print(f"[SPY] JSON decode error: {e}")
                            continue

                        selector = data.get("selector")
                        if selector in seen:
                            continue
                        seen.add(selector)
                        self._save_element(data)
                        
            except Exception as e:
                print(f"[SPY] Error in poll loop: {e}")
                
            time.sleep(0.5)

    def _save_element(self, data):
        print(f"[SPY] Found element: {data.get('selector', '')}")
        selector = data.get("selector", "")
        tag = data.get("tag", "")
        text = data.get("text", "")
        base_name = selector.split('>').pop().replace(':','_').replace('#','').replace(' ', '_')
        # only take first 3 words for name
        if text:
            words = text.split()
            if len(words) > 3:
                text = ' '.join(words[:3])
        else:
            text = base_name
        name = f"{tag.lower()}_{text.lower().replace(' ', '_')}"
        xml = self.template.render(
            name=name,
            guid=uuid4(),
            xpath=data.get("xpath", ""),
            # selector_type='CSS',
            # selector_value=selector,
            tag=tag,
            text=text,
            attributes=data.get("attributes", {})
        )
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"{name}.xml")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml)
        print(f"[SPY] Saved: {path}")

    def manual_reinject(self):
        """Manual method to re-inject listeners if needed"""
        print("[SPY] Manually re-injecting listeners...")
        self._inject_listeners()