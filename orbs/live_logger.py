"""
Live execution logger that writes NDJSON format for real-time monitoring.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from orbs.thread_context import get_context


class LiveLogger:
    """
    Writes execution events to a NDJSON file for real-time monitoring by Studio.
    Each event is a single JSON object followed by a newline.
    Events are also printed to stdout with @@LIVE@@ prefix for Studio to parse.
    """
    
    def __init__(self, log_dir: str, execution_id: str):
        """
        Initialize live logger.
        
        Args:
            log_dir: Base log directory (default: "logs")
            execution_id: Unique execution identifier (e.g., "20260301_130411")
        """
        self.execution_id = execution_id
        self.log_dir = Path(log_dir) / execution_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.log_dir / "live.ndjson"
        self.step_counter = {}  # Track step numbers per test case
        self.selected_env = "default"  # Track selected environment for context in events   
        
        # Create/truncate the file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            pass
    
    def _sanitize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize event payload to mask sensitive values before writing."""
        def mask_string(value):
            if not isinstance(value, str):
                return value
            lower = value.lower()
            if 'password' in lower or 'pwd' in lower:
                import re
                def _mask_match(m):
                    quote = m.group(1)
                    return f'{quote}***PASSWORD***{quote}'
                masked = re.sub(r'(["\'])(.*?)(["\'])', _mask_match, value)
                return masked if masked != value else value
            return value

        event_copy = dict(event)

        if event_copy.get('type') == 'step_started':
            object_name = event_copy.get('object')
            if object_name:
                event_copy['object'] = mask_string(object_name)

            args = event_copy.get('args')
            if isinstance(args, list):
                event_copy['args'] = [mask_string(a) if isinstance(a, str) else a for a in args]

        elif event_copy.get('type') in ['step_failed', 'step_skipped']:
            error = event_copy.get('error')
            if error:
                event_copy['error'] = mask_string(error)

        return event_copy

    def _write_event(self, event: Dict[str, Any]) -> None:
        """Write a single event to the NDJSON file and print to stdout for Studio."""
        event = self._sanitize_event(event)
        line = json.dumps(event, ensure_ascii=False)
        
        # Write to file (for persistence/reports)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
        
        # Write to REAL stdout with prefix for Studio to parse in real-time.
        # Use sys.__stdout__ to bypass any stdout capture (e.g., behave's --capture)
        # which replaces sys.stdout with StringIO during BDD step execution.
        out = sys.__stdout__ or sys.stdout
        out.write(f"@@LIVE@@{line}\n")
        out.flush()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def execution_started(self, environment: Optional[str] = None, 
                         platform: Optional[str] = None) -> None:
        """Log execution start."""
        self.selected_env = environment
        event = {
            "type": "execution_started",
            "environment": self.selected_env,
            "execution_id": self.execution_id,
            "timestamp": self._get_timestamp()
        }
        if environment:
            event["environment"] = environment
        if platform:
            event["platform"] = platform
        
        self._write_event(event)
    
    def execution_finished(self, status: str, duration: float) -> None:
        """Log execution completion."""
        self._write_event({
            "type": "execution_finished",
            "execution_id": self.execution_id,
            "environment": self.selected_env,
            "status": status,
            "duration": round(duration, 2),
            "timestamp": self._get_timestamp()
        })
    
    def testcase_started(self, testcase_id: str, name: str, 
                        file_path: Optional[str] = None) -> None:
        """Log test case start."""
        self.step_counter[testcase_id] = 0  # Reset step counter
        event = {
            "type": "testcase_started",
            "testcase_id": testcase_id,
            "name": name,
            "environment": self.selected_env,
            "timestamp": self._get_timestamp()
        }
        if file_path:
            event["file_path"] = file_path
        
        self._write_event(event)
    
    def testcase_finished(self, testcase_id: str, status: str, 
                         duration: float) -> None:
        """Log test case completion."""
        self._write_event({
            "type": "testcase_finished",
            "testcase_id": testcase_id,
            "environment": self.selected_env,
            "status": status,
            "duration": round(duration, 2),
            "timestamp": self._get_timestamp()
        })
    
    def step_started(self, testcase_id: str, keyword: str,
                    object_name: Optional[str] = None,
                    args: Optional[list] = None) -> int:
        """
        Log step start.
        
        Returns:
            Step ID (auto-incremented)
        """
        self.step_counter[testcase_id] = self.step_counter.get(testcase_id, 0) + 1
        step_id = self.step_counter[testcase_id]
        
        event = {
            "type": "step_started",
            "testcase_id": testcase_id,
            "environment": self.selected_env,
            "step_id": step_id,
            "keyword": keyword,
            "timestamp": self._get_timestamp()
        }
        if object_name:
            event["object"] = object_name
        if args:
            event["args"] = args
        
        self._write_event(event)
        return step_id
    
    def step_passed(self, testcase_id: str, step_id: int, duration: float) -> None:
        """Log step success."""
        self._write_event({
            "type": "step_passed",
            "testcase_id": testcase_id,
            "environment": self.selected_env,
            "step_id": step_id,
            "duration": round(duration, 2),
            "timestamp": self._get_timestamp()
        })
    
    def step_failed(self, testcase_id: str, step_id: int, 
                   error: str, duration: float,
                   screenshot: Optional[str] = None) -> None:
        """Log step failure."""
        event = {
            "type": "step_failed",
            "testcase_id": testcase_id,
            "environment": self.selected_env,
            "step_id": step_id,
            "error": error,
            "duration": round(duration, 2),
            "timestamp": self._get_timestamp()
        }
        if screenshot:
            event["screenshot"] = screenshot
        
        self._write_event(event)
    
    def step_skipped(self, testcase_id: str, step_id: int, reason: str) -> None:
        """Log step skipped."""
        self._write_event({
            "type": "step_skipped",
            "testcase_id": testcase_id,
            "step_id": step_id,
            "environment": self.selected_env,
            "reason": reason,
            "timestamp": self._get_timestamp()
        })
    
    def testsuite_started(self, testsuite_id: str, name: str) -> None:
        """Log test suite start."""
        self._write_event({
            "type": "testsuite_started",
            "testsuite_id": testsuite_id,
            "name": name,
            "environment": self.selected_env,
            "timestamp": self._get_timestamp()
        })
    
    def testsuite_finished(self, testsuite_id: str, status: str, 
                          duration: float) -> None:
        """Log test suite completion."""
        self._write_event({
            "type": "testsuite_finished",
            "testsuite_id": testsuite_id,
            "environment": self.selected_env,
            "status": status,
            "duration": round(duration, 2),
            "timestamp": self._get_timestamp()
        })
