class OrbsException(Exception):
    """Base exception for all Orbs framework errors."""
    def __init__(self, message=None, error_code=None):
        self.error_code = error_code
        if message is None:
            message = "Orbs framework error occurred"
        super().__init__(message)

class FeatureException(OrbsException):
    """Custom exception for feature failures."""
    def __init__(self, message=None):
        if message is None:
            message = "Feature failed"
        super().__init__(message, error_code="FEATURE_ERROR")

class ReportGenerationException(OrbsException):
    """Exception for report generation failures."""
    def __init__(self, message=None):
        if message is None:
            message = "Report generation failed"
        super().__init__(message, error_code="REPORT_ERROR")

class ReportListenerException(OrbsException):
    """Exception for report listener errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Report listener error occurred"
        super().__init__(message, error_code="REPORT_LISTENER_ERROR")

class RunnerException(OrbsException):
    """Exception for test runner errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Test runner error occurred"
        super().__init__(message, error_code="RUNNER_ERROR")

class ConfigurationException(OrbsException):
    """Exception for configuration related errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Configuration error occurred"
        super().__init__(message, error_code="CONFIG_ERROR")

class BrowserDriverException(OrbsException):
    """Exception for browser driver related errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Browser driver error occurred"
        super().__init__(message, error_code="BROWSER_DRIVER_ERROR")

class MobileDriverException(OrbsException):
    """Exception for mobile driver related errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Mobile driver error occurred"
        super().__init__(message, error_code="MOBILE_DRIVER_ERROR")

class ListenerLoadException(OrbsException):
    """Exception for listener loading failures."""
    def __init__(self, message=None, listener_name=None):
        self.listener_name = listener_name
        if message is None:
            message = f"Listener load error{f' for {listener_name}' if listener_name else ''}"
        super().__init__(message, error_code="LISTENER_LOAD_ERROR")

class DependencyException(OrbsException):
    def __init__(self, message=None):
        super().__init__(
            message or "Dependency check failed",
            error_code="DEPENDENCY_ERROR"
        )
  
class WebActionException(OrbsException):
    """Exception for web action failures."""
    def __init__(self, message=None):
        if message is None:
            message = "Web action error occurred"
        super().__init__(message, error_code="WEB_ACTION_ERROR")

class MobileActionException(OrbsException):
    """Exception for mobile action failures."""
    def __init__(self, message=None):
        if message is None:
            message = "Mobile action error occurred"
        super().__init__(message, error_code="MOBILE_ACTION_ERROR")