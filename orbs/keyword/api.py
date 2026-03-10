"""
API automation keywords for Orbs framework
Provides high-level HTTP operations with automatic request/response logging

Usage:
    from orbs.keyword.api import API

    API.set_base_url("https://api.example.com")
    API.set_default_headers({"Authorization": "Bearer token"})

    response = API.get("/users")
    response = API.post("/users", json={"name": "John"})
"""

import time
import functools
import requests
from typing import Optional

from ..thread_context import get_context, set_context
from ..guard import orbs_guard
from ..exception import ApiActionException
from ..log import log
from .failure_handling import FailureHandling, handle_failure


def track_keyword(func):
    """Decorator to track API keyword execution in live logger"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        live_logger = get_context("live_logger")
        testcase = get_context("current_testcase")

        if live_logger and testcase:
            testcase_id = testcase.replace("\\", "/").replace(".py", "")
            keyword_name = func.__name__

            # Build description from args
            object_parts = []
            if len(args) > 1:
                if keyword_name in ("get", "post", "put", "patch", "delete", "head", "options", "request"):
                    # First arg after cls is path/url
                    path = args[1]
                    if keyword_name == "request" and len(args) > 2:
                        method = args[1]
                        path = args[2]
                        object_parts = [f"{method} {path}"]
                    else:
                        object_parts = [str(path)[:120]]
                elif keyword_name == "set_base_url":
                    object_parts = [str(args[1])[:120]]
                elif keyword_name == "verify_status_code":
                    object_parts = [f"expected={args[2]}"]
                elif keyword_name.startswith("verify_json"):
                    object_parts = [f"field={args[2]}"]
                else:
                    first_arg = args[1]
                    object_parts = [str(first_arg)[:80]]

            object_desc = " ".join(object_parts) if object_parts else None

            step_id = live_logger.step_started(
                testcase_id=testcase_id,
                keyword=f"API.{keyword_name.upper()}",
                object_name=object_desc
            )

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                live_logger.step_passed(testcase_id=testcase_id, step_id=step_id, duration=duration)

                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": f"API.{keyword_name.upper()}",
                    "name": object_desc or "",
                    "status": "PASSED",
                    "duration": round(duration, 2),
                    "error": None
                })
                set_context("keyword_steps", keyword_steps)

                return result
            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                live_logger.step_failed(testcase_id=testcase_id, step_id=step_id, duration=duration, error=error_msg)

                keyword_steps = get_context("keyword_steps") or []
                keyword_steps.append({
                    "keyword": f"API.{keyword_name.upper()}",
                    "name": object_desc or "",
                    "status": "FAILED",
                    "duration": round(duration, 2),
                    "error": error_msg
                })
                set_context("keyword_steps", keyword_steps)

                raise
        else:
            return func(*args, **kwargs)

    return wrapper


def _api_context(*args, **kwargs):
    """Build context string for orbs_guard error messages"""
    if len(args) > 1:
        return f"API.{args[0].__name__ if hasattr(args[0], '__name__') else ''}"
    return "API"


class API:
    """
    High-level API testing keywords for Orbs framework.

    All methods are classmethods for stateless, thread-safe usage.
    State (base_url, headers, session) is stored in thread-local context
    so parallel test execution is safe.

    Usage:
        from orbs.keyword.api import API

        API.set_base_url("https://api.example.com")
        response = API.get("/users/1")
        API.verify_status_code(response, 200)
    """

    # ── Session Management ──────────────────────────────────────────

    @classmethod
    def _get_session(cls) -> requests.Session:
        """Get or create thread-local requests session"""
        session = get_context("api_session")
        if session is None:
            session = requests.Session()
            set_context("api_session", session)
        return session

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def set_base_url(cls, url: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Set the base URL for all subsequent API requests.

        Args:
            url: Base URL (e.g., "https://api.example.com")
            failure_handling: How to handle failures

        Example:
            API.set_base_url("https://api.example.com")
        """
        set_context("api_base_url", url.rstrip('/'))
        log.info(f"API base URL set to: {url}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def set_default_headers(cls, headers: dict, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Set default headers for all subsequent requests.

        Args:
            headers: Dictionary of headers
            failure_handling: How to handle failures

        Example:
            API.set_default_headers({
                "Content-Type": "application/json",
                "Authorization": "Bearer token123"
            })
        """
        session = cls._get_session()
        session.headers.update(headers)
        log.info(f"API default headers updated: {list(headers.keys())}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def set_bearer_token(cls, token: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Set Bearer token for authentication.

        Args:
            token: Bearer token string
            failure_handling: How to handle failures

        Example:
            API.set_bearer_token("eyJhbGciOiJIUzI1...")
        """
        session = cls._get_session()
        session.headers["Authorization"] = f"Bearer {token}"
        log.info("API Bearer token set")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def set_basic_auth(cls, username: str, password: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Set Basic authentication credentials.

        Args:
            username: Username
            password: Password
            failure_handling: How to handle failures

        Example:
            API.set_basic_auth("admin", "secret123")
        """
        session = cls._get_session()
        session.auth = (username, password)
        log.info(f"API Basic auth set for user: {username}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def set_timeout(cls, timeout: int, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Set default timeout (seconds) for all requests.

        Args:
            timeout: Timeout in seconds
            failure_handling: How to handle failures

        Example:
            API.set_timeout(30)
        """
        set_context("api_timeout", timeout)
        log.info(f"API timeout set to: {timeout}s")

    # ── HTTP Methods ────────────────────────────────────────────────

    @classmethod
    def _build_url(cls, path: str) -> str:
        """Build full URL from base_url + path"""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base_url = get_context("api_base_url") or ""
        if base_url:
            return f"{base_url}/{path.lstrip('/')}"
        return path

    @classmethod
    def _record_call(cls, method: str, url: str, response: Optional[requests.Response], **kwargs):
        """Record API call to thread context for reporting"""
        record = {
            "method": method,
            "url": url,
        }
        if response is not None:
            record["status_code"] = response.status_code
            record["response_body"] = response.text[:5000]
        api_calls = get_context("api_calls") or []
        api_calls.append(record)
        set_context("api_calls", api_calls)

    @classmethod
    def _do_request(cls, method: str, path: str, **kwargs) -> requests.Response:
        """Internal: execute HTTP request (no decorators)"""
        session = cls._get_session()
        url = cls._build_url(path)
        timeout = kwargs.pop("timeout", get_context("api_timeout") or 30)

        log.info(f"API {method} {url}")
        response = session.request(method, url, timeout=timeout, **kwargs)
        cls._record_call(method, url, response)
        log.info(f"API {method} {url} → {response.status_code}")

        return response

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def request(cls, method: str, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
            path: URL path (appended to base_url) or full URL
            failure_handling: How to handle failures
            **kwargs: Passed to requests (params, json, data, headers, files, etc.)

        Returns:
            requests.Response object

        Example:
            response = API.request("GET", "/users/1")
            response = API.request("POST", "/users", json={"name": "John"})
        """
        return cls._do_request(method, path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def get(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a GET request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures
            **kwargs: params, headers, etc.

        Returns:
            requests.Response object

        Example:
            response = API.get("/users")
            response = API.get("/users", params={"page": 1, "limit": 10})
        """
        return cls._do_request("GET", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def post(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a POST request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures
            **kwargs: json, data, headers, files, etc.

        Returns:
            requests.Response object

        Example:
            response = API.post("/users", json={"name": "John", "email": "john@test.com"})
            response = API.post("/login", data={"user": "admin", "pass": "secret"})
        """
        return cls._do_request("POST", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def put(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a PUT request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures
            **kwargs: json, data, headers, etc.

        Returns:
            requests.Response object

        Example:
            response = API.put("/users/1", json={"name": "John Updated"})
        """
        return cls._do_request("PUT", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def patch(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a PATCH request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures
            **kwargs: json, data, headers, etc.

        Returns:
            requests.Response object

        Example:
            response = API.patch("/users/1", json={"email": "new@test.com"})
        """
        return cls._do_request("PATCH", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def delete(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a DELETE request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures
            **kwargs: params, headers, etc.

        Returns:
            requests.Response object

        Example:
            response = API.delete("/users/1")
        """
        return cls._do_request("DELETE", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def head(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send a HEAD request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures

        Returns:
            requests.Response object

        Example:
            response = API.head("/users/1")
        """
        return cls._do_request("HEAD", path, **kwargs)

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def options(cls, path: str, failure_handling=FailureHandling.STOP_ON_FAILURE, **kwargs) -> requests.Response:
        """
        Send an OPTIONS request.

        Args:
            path: URL path or full URL
            failure_handling: How to handle failures

        Returns:
            requests.Response object

        Example:
            response = API.options("/users")
        """
        return cls._do_request("OPTIONS", path, **kwargs)

    # ── Response Helpers ────────────────────────────────────────────

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def get_json(cls, response: requests.Response, failure_handling=FailureHandling.STOP_ON_FAILURE) -> dict:
        """
        Parse response body as JSON.

        Args:
            response: Response object
            failure_handling: How to handle failures

        Returns:
            Parsed JSON as dict/list

        Example:
            response = API.get("/users/1")
            data = API.get_json(response)
        """
        return response.json()

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def get_status_code(cls, response: requests.Response, failure_handling=FailureHandling.STOP_ON_FAILURE) -> int:
        """
        Get response status code.

        Args:
            response: Response object
            failure_handling: How to handle failures

        Returns:
            HTTP status code

        Example:
            status = API.get_status_code(response)
        """
        return response.status_code

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def get_header(cls, response: requests.Response, header_name: str, failure_handling=FailureHandling.STOP_ON_FAILURE) -> Optional[str]:
        """
        Get a specific response header value.

        Args:
            response: Response object
            header_name: Name of the header
            failure_handling: How to handle failures

        Returns:
            Header value or None

        Example:
            content_type = API.get_header(response, "Content-Type")
        """
        return response.headers.get(header_name)

    # ── Verification ────────────────────────────────────────────────

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_status_code(cls, response: requests.Response, expected: int, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify the response status code matches expected value.

        Args:
            response: Response object
            expected: Expected HTTP status code
            failure_handling: How to handle failures

        Example:
            API.verify_status_code(response, 200)
            API.verify_status_code(response, 201)
        """
        actual = response.status_code
        assert actual == expected, f"Expected status {expected}, got {actual}. Body: {response.text[:500]}"
        log.info(f"API status code verified: {actual} == {expected}")

    @classmethod
    def _resolve_json_field(cls, data, field: str):
        """
        Resolve a JSON field supporting dot notation and bracket syntax.
        
        Examples:
            "name"              → data["name"]
            "user.email"        → data["user"]["email"]
            "items[0].id"       → data["items"][0]["id"]
            "data.users[2].name"→ data["data"]["users"][2]["name"]
        """
        import re
        # Split "items[0].name" into tokens: ["items", "[0]", "name"]
        tokens = re.findall(r'[^.\[\]]+|\[\d+\]', field)
        current = data
        for token in tokens:
            if token.startswith('[') and token.endswith(']'):
                # Array index: [0], [1], etc.
                idx = int(token[1:-1])
                if not isinstance(current, list):
                    raise KeyError(f"Expected array for index {token}, got {type(current).__name__}")
                if idx >= len(current):
                    raise KeyError(f"Index {idx} out of range (length {len(current)})")
                current = current[idx]
            elif isinstance(current, dict):
                if token not in current:
                    raise KeyError(f"Field '{token}' not found. Available keys: {list(current.keys())}")
                current = current[token]
            else:
                raise KeyError(f"Cannot resolve '{token}' on {type(current).__name__}")
        return current

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_equals(cls, response: requests.Response, field: str, expected, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON field equals the expected value.
        Supports dot notation for nested fields.

        Args:
            response: Response object
            field: JSON field path (e.g., "name", "user.email", "items.0.id")
            expected: Expected value
            failure_handling: How to handle failures

        Example:
            API.verify_json_equals(response, "name", "John")
            API.verify_json_equals(response, "user.role", "admin")
            API.verify_json_equals(response, "items[0].id", 1)
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual == expected, f"Expected '{field}' == {expected!r}, got {actual!r}"
        log.info(f"API verify: {field} == {expected!r}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_not_equals(cls, response: requests.Response, field: str, unexpected, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON field does NOT equal the given value.

        Args:
            response: Response object
            field: JSON field path
            unexpected: Value that should NOT match
            failure_handling: How to handle failures

        Example:
            API.verify_json_not_equals(response, "status", "error")
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual != unexpected, f"Expected '{field}' != {unexpected!r}, but got {actual!r}"
        log.info(f"API verify: {field} != {unexpected!r}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_contains(cls, response: requests.Response, field: str, substring: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON string field contains a substring.

        Args:
            response: Response object
            field: JSON field path
            substring: Text that should be contained in the field value
            failure_handling: How to handle failures

        Example:
            API.verify_json_contains(response, "message", "success")
            API.verify_json_contains(response, "email", "@example.com")
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert isinstance(actual, str), f"Field '{field}' is {type(actual).__name__}, expected string"
        assert substring in actual, f"Expected '{field}' to contain '{substring}', got '{actual}'"
        log.info(f"API verify: {field} contains '{substring}'")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_greater_than(cls, response: requests.Response, field: str, value, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON numeric field is greater than the given value.

        Args:
            response: Response object
            field: JSON field path
            value: Value to compare against
            failure_handling: How to handle failures

        Example:
            API.verify_json_greater_than(response, "count", 0)
            API.verify_json_greater_than(response, "price", 9.99)
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual > value, f"Expected '{field}' > {value}, got {actual}"
        log.info(f"API verify: {field} ({actual}) > {value}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_less_than(cls, response: requests.Response, field: str, value, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON numeric field is less than the given value.

        Args:
            response: Response object
            field: JSON field path
            value: Value to compare against
            failure_handling: How to handle failures

        Example:
            API.verify_json_less_than(response, "error_count", 5)
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual < value, f"Expected '{field}' < {value}, got {actual}"
        log.info(f"API verify: {field} ({actual}) < {value}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_is_null(cls, response: requests.Response, field: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON field is null.

        Args:
            response: Response object
            field: JSON field path
            failure_handling: How to handle failures

        Example:
            API.verify_json_is_null(response, "deleted_at")
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual is None, f"Expected '{field}' to be null, got {actual!r}"
        log.info(f"API verify: {field} is null")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_is_not_null(cls, response: requests.Response, field: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON field is not null.

        Args:
            response: Response object
            field: JSON field path
            failure_handling: How to handle failures

        Example:
            API.verify_json_is_not_null(response, "id")
        """
        data = response.json()
        actual = cls._resolve_json_field(data, field)
        assert actual is not None, f"Expected '{field}' to not be null"
        log.info(f"API verify: {field} is not null")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_field_exists(cls, response: requests.Response, field: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a JSON field exists in the response.
        Supports dot notation for nested fields.

        Args:
            response: Response object
            field: JSON field path (e.g., "id", "user.name")
            failure_handling: How to handle failures

        Example:
            API.verify_json_field_exists(response, "id")
            API.verify_json_field_exists(response, "data.user.email")
        """
        data = response.json()
        try:
            cls._resolve_json_field(data, field)
        except KeyError as e:
            raise AssertionError(f"Field '{field}' not found in response: {e}")
        log.info(f"API verify: {field} exists")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_response_contains(cls, response: requests.Response, text: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify the response body contains the given text.

        Args:
            response: Response object
            text: Text to search for in response body
            failure_handling: How to handle failures

        Example:
            API.verify_response_contains(response, "success")
        """
        assert text in response.text, f"Response body does not contain '{text}'. Body: {response.text[:500]}"
        log.info(f"API response contains: '{text}'")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_json_array_length(cls, response: requests.Response, expected_length: int, field: Optional[str] = None, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify the length of a JSON array in the response.

        Args:
            response: Response object
            expected_length: Expected array length
            field: Optional field name if array is nested (default: root)
            failure_handling: How to handle failures

        Example:
            API.verify_json_array_length(response, 10)
            API.verify_json_array_length(response, 3, field="items")
        """
        data = response.json()
        if field:
            data = data[field]
        actual = len(data)
        assert actual == expected_length, f"Expected array length {expected_length}, got {actual}"
        log.info(f"API JSON array length verified: {actual} == {expected_length}")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_response_time(cls, response: requests.Response, max_ms: int, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify the response time is within the expected limit.

        Args:
            response: Response object
            max_ms: Maximum allowed response time in milliseconds
            failure_handling: How to handle failures

        Example:
            API.verify_response_time(response, 2000)  # Must respond within 2s
        """
        elapsed_ms = response.elapsed.total_seconds() * 1000
        assert elapsed_ms <= max_ms, f"Response time {elapsed_ms:.0f}ms exceeded limit of {max_ms}ms"
        log.info(f"API response time verified: {elapsed_ms:.0f}ms <= {max_ms}ms")

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def verify_header(cls, response: requests.Response, header_name: str, expected_value: str, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Verify a response header has the expected value.

        Args:
            response: Response object
            header_name: Header name
            expected_value: Expected header value
            failure_handling: How to handle failures

        Example:
            API.verify_header(response, "Content-Type", "application/json")
        """
        actual = response.headers.get(header_name)
        assert actual is not None, f"Header '{header_name}' not found in response"
        assert expected_value in actual, f"Header '{header_name}': expected '{expected_value}' in '{actual}'"
        log.info(f"API header verified: {header_name} contains '{expected_value}'")

    # ── Cleanup ─────────────────────────────────────────────────────

    @classmethod
    @track_keyword
    @handle_failure
    @orbs_guard(ApiActionException)
    def close_session(cls, failure_handling=FailureHandling.STOP_ON_FAILURE):
        """
        Close the current HTTP session and clean up context.

        Example:
            API.close_session()
        """
        session = get_context("api_session")
        if session:
            session.close()
            set_context("api_session", None)
        set_context("api_base_url", None)
        set_context("api_timeout", None)
        set_context("api_calls", None)
        log.info("API session closed")
