# File: orbs/console_summary.py

"""
Console summary generator for test execution reporting.
Displays a formatted summary of test results to the console.
"""

from datetime import timedelta
from orbs.config import setting


class ConsoleSummary:
    """Generate and display test execution summary in console"""
    
    @staticmethod
    def format_duration(seconds):
        """Format duration in seconds to human-readable format (e.g., '1m 24s')"""
        if seconds < 60:
            return f"{int(seconds)}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    
    @staticmethod
    def get_status_color(status):
        """Get ANSI color code for status"""
        colors = {
            'PASSED': '\033[92m',  # Green
            'FAILED': '\033[91m',  # Red
            'SKIPPED': '\033[93m', # Yellow
        }
        return colors.get(status.upper(), '\033[0m')  # Default: reset
    
    @staticmethod
    def colorize(text, color_code):
        """Apply color to text with reset at the end"""
        reset = '\033[0m'
        return f"{color_code}{text}{reset}"
    
    @staticmethod
    def generate(overview_data):
        """
        Generate console summary from overview data.
        
        Args:
            overview_data (dict): Test execution overview data with keys:
                - total_testcase: Total number of test cases
                - passed: Number of passed tests
                - failed: Number of failed tests
                - skipped: Number of skipped tests
                - duration: Total duration in seconds
                - environent: Environment name (note: typo in original)
                - testsuite_id: Suite identifier
        
        Returns:
            str: Formatted console summary
        """
        total = overview_data.get('total_testcase', 0)
        passed = overview_data.get('passed', 0)
        failed = overview_data.get('failed', 0)
        skipped = overview_data.get('skipped', 0)
        duration = overview_data.get('duration', 0)
        environment = overview_data.get('environent', 'default')  # Note: typo in original key
        suite_id = overview_data.get('testsuite_id', 'Unknown')
        retries = overview_data.get('retries', 0)
        
        # Get platform from thread context first, fallback to config
        from orbs.thread_context import get_context
        platform = get_context('platform') or setting.get('default_platform', 'chrome')
        
        # Get headless mode - check multiple possible keys
        browser_headless = (
            setting.get_bool('headless', False) or 
            setting.get_bool('browser_headless', False)
        )
        browser_display = f"{platform.title()} ({'headless' if browser_headless else 'headed'})"
        
        self_healing = setting.get_bool('self_healing_enabled', False)
        retry_enabled = setting.get_bool('retry_enabled', False)
        retry_max = setting.get_int('retry_max_attempts', 2)
        
        # Determine overall status
        overall_status = 'PASSED' if failed == 0 else 'FAILED'
        status_color = ConsoleSummary.get_status_color(overall_status)
        
        # Build summary
        separator = "=" * 60
        
        # Color codes (can't use backslash directly in f-string expressions)
        green = '\033[92m'
        red = '\033[91m'
        yellow = '\033[93m'
        
        lines = [
            "",
            separator,
            "ORBS TEST EXECUTION SUMMARY".center(60),
            separator,
            f"Total Tests     : {total}",
            f"Passed          : {ConsoleSummary.colorize(str(passed), green)}",  # Green
            f"Failed          : {ConsoleSummary.colorize(str(failed), red)}",  # Red
            f"Skipped         : {ConsoleSummary.colorize(str(skipped), yellow)}",  # Yellow
            f"Retries         : {retries}",
            f"Duration        : {ConsoleSummary.format_duration(duration)}",
            f"Environment     : {environment}",
            f"Browser         : {browser_display}",
            f"Self-Healing    : {'Enabled' if self_healing else 'Disabled'}",
            f"Retry           : {'Enabled (max ' + str(retry_max) + ')' if retry_enabled else 'Disabled'}",
            separator,
            f"STATUS: {ConsoleSummary.colorize(overall_status, status_color)}",
            separator,
            ""
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def print_summary(overview_data):
        """Print the console summary directly"""
        summary = ConsoleSummary.generate(overview_data)
        print(summary)
    
    @staticmethod
    def get_exit_code(overview_data):
        """
        Get exit code based on test results for CI/CD integration.
        
        Returns:
            0: All tests passed
            1: One or more tests failed
        """
        failed = overview_data.get('failed', 0)
        return 0 if failed == 0 else 1
