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

class FileIOException(OrbsException):
    """Exception for file I/O operations."""
    def __init__(self, message=None, file_path=None):
        self.file_path = file_path
        if message is None:
            message = f"File I/O error{f' for {file_path}' if file_path else ''}"
        super().__init__(message, error_code="FILE_IO_ERROR")

class PDFGenerationException(ReportGenerationException):
    """Exception for PDF generation failures."""
    def __init__(self, message=None):
        if message is None:
            message = "PDF generation failed"
        super().__init__(message)
        self.error_code = "PDF_ERROR"

class JSONGenerationException(ReportGenerationException):
    """Exception for JSON report generation failures."""
    def __init__(self, message=None):
        if message is None:
            message = "JSON generation failed"
        super().__init__(message)
        self.error_code = "JSON_ERROR"

class ImageProcessingException(ReportGenerationException):
    """Exception for image/screenshot processing failures."""
    def __init__(self, message=None, image_path=None):
        self.image_path = image_path
        if message is None:
            message = f"Image processing failed{f' for {image_path}' if image_path else ''}"
        super().__init__(message)
        self.error_code = "IMAGE_ERROR"

class DirectoryCreationException(FileIOException):
    """Exception for directory creation failures."""
    def __init__(self, message=None, dir_path=None):
        if message is None:
            message = f"Directory creation failed{f' for {dir_path}' if dir_path else ''}"
        super().__init__(message, file_path=dir_path)
        self.error_code = "DIR_CREATE_ERROR"

class ConfigurationException(OrbsException):
    """Exception for configuration related errors."""
    def __init__(self, message=None):
        if message is None:
            message = "Configuration error occurred"
        super().__init__(message, error_code="CONFIG_ERROR")
