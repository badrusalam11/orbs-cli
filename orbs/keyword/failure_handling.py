# File: orbs/keyword/failure_handling.py
"""
Failure handling strategies for test automation keywords.

This module provides mechanisms to control how keyword failures are handled,
allowing tests to continue or stop based on the severity of the failure.
"""

from enum import Enum
from functools import wraps
from typing import Callable, Any, Optional
from ..log import log
from ..thread_context import get_context, set_context


class FailureHandling(Enum):
    """
    Failure handling strategies for keyword execution.
    
    Attributes:
        STOP_ON_FAILURE: Stop execution and raise exception immediately (default behavior)
        CONTINUE_ON_FAILURE: Log error but continue test execution
        OPTIONAL: Treat action as optional, suppress all errors
    """
    STOP_ON_FAILURE = "STOP_ON_FAILURE"
    CONTINUE_ON_FAILURE = "CONTINUE_ON_FAILURE"
    OPTIONAL = "OPTIONAL"


def handle_failure(func: Callable) -> Callable:
    """
    Decorator to handle keyword failures based on failure_handling parameter.
    
    This decorator wraps keyword methods and intercepts exceptions based on
    the failure_handling strategy provided to the method.
    
    Args:
        func: The keyword method to wrap
        
    Returns:
        Wrapped function with failure handling logic
        
    Usage:
        @handle_failure
        def click(self, locator, failure_handling=FailureHandling.STOP_ON_FAILURE):
            # Implementation
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract failure_handling from kwargs, default to STOP_ON_FAILURE
        failure_handling = kwargs.get('failure_handling', FailureHandling.STOP_ON_FAILURE)
        
        # Ensure it's a FailureHandling enum
        if not isinstance(failure_handling, FailureHandling):
            failure_handling = FailureHandling.STOP_ON_FAILURE
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get function name for logging
            func_name = func.__name__
            
            if failure_handling == FailureHandling.STOP_ON_FAILURE:
                # Default behavior: raise exception
                log.error(f"[STOP_ON_FAILURE] {func_name} failed: {str(e)}")
                raise
            
            elif failure_handling == FailureHandling.CONTINUE_ON_FAILURE:
                # Log error but continue
                log.error(f"[CONTINUE_ON_FAILURE] {func_name} failed: {str(e)}")
                log.warning(f"Test execution continues despite failure in {func_name}")
                # Mark test case as having continued failures (will be marked as FAILED)
                set_context('test_has_continued_failures', True)
                return None
            
            elif failure_handling == FailureHandling.OPTIONAL:
                # Suppress error, just log as info
                log.info(f"[OPTIONAL] {func_name} failed (ignored): {str(e)}")
                return None
            
            else:
                # Fallback to default
                raise
    
    return wrapper


def with_failure_handling(
    failure_handling: FailureHandling,
    func: Callable,
    *args,
    **kwargs
) -> Any:
    """
    Execute a function with specified failure handling strategy.
    
    Alternative to decorator approach for dynamic failure handling.
    
    Args:
        failure_handling: The failure handling strategy to use
        func: The function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result of func execution or None on handled failure
        
    Example:
        result = with_failure_handling(
            FailureHandling.OPTIONAL,
            Web.click,
            "id=optional_button"
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        
        if failure_handling == FailureHandling.STOP_ON_FAILURE:
            log.error(f"[STOP_ON_FAILURE] {func_name} failed: {str(e)}")
            raise
        
        elif failure_handling == FailureHandling.CONTINUE_ON_FAILURE:
            log.error(f"[CONTINUE_ON_FAILURE] {func_name} failed: {str(e)}")
            log.warning(f"Test execution continues despite failure in {func_name}")
            # Mark test case as having continued failures (will be marked as FAILED)
            set_context('test_has_continued_failures', True)
            return None
        
        elif failure_handling == FailureHandling.OPTIONAL:
            log.info(f"[OPTIONAL] {func_name} failed (ignored): {str(e)}")
            return None
        
        else:
            raise
