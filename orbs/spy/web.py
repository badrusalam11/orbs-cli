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
            
            js = r"""
            // Remove existing listeners if any
            if (window._spy_cleanup) {
                window._spy_cleanup();
            }
            
            // Mouse move handler
            function handleMouseMove(e) {
                if (window._last_hover) {
                    window._last_hover.style.outline = '';
                }
                window._last_hover = e.target;
                e.target.style.outline = '2px solid blue';
            }
            
            // Keydown handler  
            function handleKeyDown(e) {
                if (e.ctrlKey && e.code === 'Backquote') {
                    e.preventDefault();
                    const el = window._last_hover;
                    if (!el) return;

                    function uniqueSelector(el) {
                        if (el.id) return '#' + el.id;
                        let path = [];
                        while (el.nodeType === 1 && el !== document.body) {
                            let idx = 1, sib = el;
                            while ((sib = sib.previousElementSibling)) if (sib.nodeName === el.nodeName) idx++;
                            path.unshift(el.nodeName.toLowerCase() + (idx > 1 ? `:nth-of-type(${idx})` : ''));
                            el = el.parentNode;
                        }
                        return path.join(' > ');
                    }

                    const selector = uniqueSelector(el);
                    function getXPath(el) {
                        if (el.id !== "") return 'id("' + el.id + '")';
                        if (el === document.body) return '/html/body';
                        let ix = 0;
                        const siblings = el.parentNode.childNodes;
                        for (let i = 0; i < siblings.length; i++) {
                            const sibling = siblings[i];
                            if (sibling === el) {
                                const path = getXPath(el.parentNode) + '/' + el.tagName.toLowerCase();
                                return ix > 0 ? path + `[${ix + 1}]` : path;
                            }
                            if (sibling.nodeType === 1 && sibling.tagName === el.tagName) {
                                ix++;
                            }
                        }
                    }

                    const xpath = getXPath(el);
                    const payload = {
                        selector,
                        xpath,
                        tag: el.tagName.toLowerCase(),
                        name: el.getAttribute('name') || '',
                        text: el.innerText || '',
                        attributes: {
                            id: el.id || '',
                            class: el.className || '',
                            href: el.getAttribute('href') || '',
                            text: el.innerText || '',
                            type: el.getAttribute('type') || '',
                            placeholder: el.getAttribute('placeholder') || '',
                            ariaLabel: el.getAttribute('aria-label') || ''
                        }
                    };
                    console.log('[SPY]' + JSON.stringify(payload));
                }
            }
            
            // Add event listeners
            document.addEventListener('mousemove', handleMouseMove, true);
            document.addEventListener('keydown', handleKeyDown, true);
            
            // Mark that listeners are injected
            window._spy_listeners_injected = true;
            
            // Cleanup function for removing listeners
            window._spy_cleanup = function() {
                document.removeEventListener('mousemove', handleMouseMove, true);
                document.removeEventListener('keydown', handleKeyDown, true);
                window._spy_listeners_injected = false;
                if (window._last_hover) {
                    window._last_hover.style.outline = '';
                    window._last_hover = null;
                }
            };
            
            console.log('[SPY] Listeners injected successfully');
            """
            
            self.driver.execute_script(js)
            self._listeners_injected = True
            print("[SPY] JavaScript listeners injected successfully")
            
        except Exception as e:
            print(f"[SPY] Error injecting listeners: {e}")
            self._listeners_injected = False

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