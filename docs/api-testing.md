# API Testing with Orbs

Complete guide to REST API testing using Orbs framework.

---

## Table of Contents

* [Introduction](#introduction)
* [Quick Start](#quick-start)
* [API Client](#api-client)
* [Making Requests](#making-requests)
* [Response Validation](#response-validation)
* [Authentication](#authentication)
* [Writing Test Cases](#writing-test-cases)
* [Best Practices](#best-practices)
* [Advanced Topics](#advanced-topics)
* [Troubleshooting](#troubleshooting)

---

## Introduction

Orbs provides a powerful API testing client built on `requests` library with additional features:

* **Automatic request/response logging** - All API calls are recorded for debugging
* **Thread-safe execution** - Parallel API test support
* **Session management** - Persistent headers and cookies
* **Base URL configuration** - Centralized endpoint management
* **Flexible authentication** - Support for various auth methods
* **Response validation helpers** - Built-in assertion utilities

---

## Quick Start

### 1. Initialize Project

```bash
orbs init api-testing
cd api-testing
```

### 2. Configure Base URL

Edit `.env`:

```env
API_BASE_URL=https://api.example.com
API_KEY=your-api-key-here
```

### 3. Create API Test Case

```bash
orbs create-testcase user_api
```

Edit `testcases/user_api.py`:

```python
import os
from orbs.api_client import ApiClient

def test_get_user():
    """Test GET /users/{id} endpoint"""
    
    # Initialize client
    base_url = os.getenv("API_BASE_URL")
    api = ApiClient(base_url)
    
    # Send GET request
    response = api.get("/users/1")
    
    # Verify response
    assert response.status_code == 200
    
    # Parse JSON
    user = response.json()
    
    # Validate response structure
    assert "id" in user
    assert "name" in user
    assert "email" in user
    
    # Validate data
    assert user["id"] == 1
    assert isinstance(user["name"], str)
    assert "@" in user["email"]
    
    print(f"✅ Retrieved user: {user['name']}")

def test_create_user():
    """Test POST /users endpoint"""
    
    api = ApiClient(os.getenv("API_BASE_URL"))
    
    # Request payload
    new_user = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    }
    
    # Send POST request
    response = api.post("/users", json=new_user)
    
    # Verify created
    assert response.status_code == 201
    
    # Verify response
    created_user = response.json()
    assert created_user["name"] == new_user["name"]
    assert created_user["email"] == new_user["email"]
    assert "id" in created_user
    
    print(f"✅ Created user with ID: {created_user['id']}")
```

### 4. Run Tests

```bash
orbs run testcases/user_api.py
```

---

## API Client

### Initialization

```python
from orbs.api_client import ApiClient

# Basic initialization
api = ApiClient(base_url="https://api.example.com")

# With default headers
api = ApiClient(
    base_url="https://api.example.com",
    default_headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer your-token"
    }
)
```

### Base URL

The base URL is automatically prepended to all requests:

```python
api = ApiClient(base_url="https://api.example.com")

# These are equivalent:
api.get("/users/1")
api.get("users/1")

# Both send request to: https://api.example.com/users/1
```

### Session Management

ApiClient uses `requests.Session` internally, which:

* Persists headers across requests
* Manages cookies automatically
* Connection pooling for performance

```python
api = ApiClient(base_url="https://api.example.com")

# Set headers for all subsequent requests
api.session.headers.update({
    "X-API-Key": "your-api-key"
})

# All requests now include X-API-Key header
response1 = api.get("/endpoint1")
response2 = api.get("/endpoint2")
```

---

## Making Requests

### HTTP Methods

#### GET Request

```python
# Simple GET
response = api.get("/users")

# With query parameters
response = api.get("/users", params={"page": 1, "limit": 10})

# With headers
response = api.get("/users", headers={"Accept": "application/json"})
```

#### POST Request

```python
# JSON payload
response = api.post("/users", json={"name": "John", "email": "john@example.com"})

# Form data
response = api.post("/login", data={"username": "admin", "password": "secret"})

# With headers
response = api.post("/users", json=payload, headers={"X-Custom": "value"})
```

#### PUT Request

```python
# Update resource
response = api.put("/users/1", json={"name": "John Updated"})
```

#### PATCH Request

```python
# Partial update
response = api.patch("/users/1", json={"email": "newemail@example.com"})
```

#### DELETE Request

```python
# Delete resource
response = api.delete("/users/1")
```

#### HEAD Request

```python
# Get headers only
response = api.head("/users/1")
```

#### OPTIONS Request

```python
# Get allowed methods
response = api.options("/users")
```

### Request Parameters

#### Query Parameters

```python
# Using params
response = api.get("/search", params={
    "q": "automation",
    "page": 1,
    "limit": 20
})
# Sends: GET /search?q=automation&page=1&limit=20
```

#### JSON Body

```python
payload = {
    "name": "John Doe",
    "email": "john@example.com",
    "roles": ["admin", "user"]
}

response = api.post("/users", json=payload)
```

#### Form Data

```python
form_data = {
    "username": "admin",
    "password": "secret123"
}

response = api.post("/login", data=form_data)
```

#### Custom Headers

```python
response = api.get("/users", headers={
    "Authorization": "Bearer token123",
    "X-Request-ID": "abc-123",
    "Accept": "application/json"
})
```

#### File Upload

```python
files = {
    "file": open("document.pdf", "rb"),
    "type": "application/pdf"
}

response = api.post("/upload", files=files)
```

#### Timeout

```python
# Timeout in seconds
response = api.get("/users", timeout=5)
```

---

## Response Validation

### Status Code

```python
response = api.get("/users/1")

# Exact match
assert response.status_code == 200

# Range check
assert 200 <= response.status_code < 300

# raise_for_status (raises exception for 4xx/5xx)
response.raise_for_status()
```

### Response Body

#### JSON Response

```python
response = api.get("/users/1")
data = response.json()

# Validate structure
assert "id" in data
assert "name" in data
assert "email" in data

# Validate values
assert data["id"] == 1
assert isinstance(data["name"], str)
assert "@" in data["email"]
```

#### Text Response

```python
response = api.get("/health")
assert response.text == "OK"
```

#### Binary Response

```python
response = api.get("/download/file.pdf")
with open("downloaded.pdf", "wb") as f:
    f.write(response.content)
```

### Response Headers

```python
response = api.get("/users")

# Check specific header
assert response.headers["Content-Type"] == "application/json"

# Case-insensitive access
assert "application/json" in response.headers.get("content-type")
```

### Response Time

```python
import time

start = time.time()
response = api.get("/users")
elapsed = time.time() - start

# Validate performance
assert elapsed < 2.0, f"API too slow: {elapsed}s"
```

---

## Authentication

### Bearer Token

```python
api = ApiClient(
    base_url="https://api.example.com",
    default_headers={
        "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
    }
)

response = api.get("/protected")
```

### API Key

#### Header-based

```python
api = ApiClient(
    base_url="https://api.example.com",
    default_headers={
        "X-API-Key": os.getenv("API_KEY")
    }
)
```

#### Query parameter

```python
api_key = os.getenv("API_KEY")
response = api.get("/users", params={"api_key": api_key})
```

### Basic Authentication

```python
from requests.auth import HTTPBasicAuth

response = api.get(
    "/users",
    auth=HTTPBasicAuth("username", "password")
)
```

### OAuth 2.0

```python
def get_access_token():
    """Obtain OAuth token"""
    auth_api = ApiClient(base_url="https://auth.example.com")
    response = auth_api.post("/oauth/token", json={
        "grant_type": "client_credentials",
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET")
    })
    return response.json()["access_token"]

# Use token
token = get_access_token()
api = ApiClient(
    base_url="https://api.example.com",
    default_headers={
        "Authorization": f"Bearer {token}"
    }
)
```

---

## Writing Test Cases

### Simple API Test

```python
from orbs.api_client import ApiClient
import os

def test_list_users():
    """Test GET /users endpoint"""
    api = ApiClient(base_url=os.getenv("API_BASE_URL"))
    
    response = api.get("/users")
    
    assert response.status_code == 200
    users = response.json()
    
    assert isinstance(users, list)
    assert len(users) > 0
    
    # Validate first user structure
    user = users[0]
    assert "id" in user
    assert "name" in user
    assert "email" in user
```

### CRUD Test Flow

```python
from orbs.api_client import ApiClient
import os

def test_user_crud():
    """Test complete CRUD operations"""
    api = ApiClient(base_url=os.getenv("API_BASE_URL"))
    
    # CREATE
    new_user = {
        "name": "Test User",
        "email": "test@example.com"
    }
    
    create_response = api.post("/users", json=new_user)
    assert create_response.status_code == 201
    
    user = create_response.json()
    user_id = user["id"]
    
    # READ
    get_response = api.get(f"/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == new_user["name"]
    
    # UPDATE
    update_data = {"name": "Updated Name"}
    update_response = api.put(f"/users/{user_id}", json=update_data)
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Name"
    
    # DELETE
    delete_response = api.delete(f"/users/{user_id}")
    assert delete_response.status_code == 204
    
    # Verify deletion
    verify_response = api.get(f"/users/{user_id}")
    assert verify_response.status_code == 404
    
    print("✅ CRUD test passed")
```

### Error Handling

```python
def test_not_found():
    """Test 404 error handling"""
    api = ApiClient(base_url=os.getenv("API_BASE_URL"))
    
    response = api.get("/users/999999")
    
    assert response.status_code == 404
    
    error = response.json()
    assert "error" in error or "message" in error

def test_validation_error():
    """Test 400 validation error"""
    api = ApiClient(base_url=os.getenv("API_BASE_URL"))
    
    invalid_user = {
        "name": "",  # Invalid: empty name
        "email": "not-an-email"  # Invalid format
    }
    
    response = api.post("/users", json=invalid_user)
    
    assert response.status_code == 400
    
    error = response.json()
    assert "errors" in error or "message" in error
```

### Test Suite

`testsuites/api_regression.yml`:

```yaml
name: API Regression Suite
description: Complete API endpoint testing

testcases:
  - testcases.user_api.test_list_users
  - testcases.user_api.test_get_user
  - testcases.user_api.test_create_user
  - testcases.user_api.test_update_user
  - testcases.user_api.test_delete_user
  - testcases.user_api.test_not_found
  - testcases.user_api.test_validation_error

platform: chrome  # Platform not used for API tests
```

---

## Best Practices

### 1. Environment Variables

Store sensitive data in `.env`:

```env
API_BASE_URL=https://staging.api.example.com
API_KEY=sk_test_abc123
API_USERNAME=testuser
API_PASSWORD=testpass
```

Use in tests:

```python
import os
api = ApiClient(
    base_url=os.getenv("API_BASE_URL"),
    default_headers={"X-API-Key": os.getenv("API_KEY")}
)
```

### 2. Reusable API Helper

Create `helpers/api_helper.py`:

```python
import os
from orbs.api_client import ApiClient

def get_api_client():
    """Get configured API client"""
    return ApiClient(
        base_url=os.getenv("API_BASE_URL"),
        default_headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        }
    )

def create_test_user(name="Test User"):
    """Helper to create test user"""
    api = get_api_client()
    response = api.post("/users", json={
        "name": name,
        "email": f"{name.lower().replace(' ', '.')}@test.com"
    })
    return response.json()

def cleanup_user(user_id):
    """Helper to delete test user"""
    api = get_api_client()
    api.delete(f"/users/{user_id}")
```

Use in tests:

```python
from helpers.api_helper import get_api_client, create_test_user, cleanup_user

def test_with_helper():
    api = get_api_client()
    
    # Create test data
    user = create_test_user("John Doe")
    user_id = user["id"]
    
    try:
        # Test logic
        response = api.get(f"/users/{user_id}")
        assert response.status_code == 200
    finally:
        # Cleanup
        cleanup_user(user_id)
```

### 3. Schema Validation

Use JSON Schema for validation:

```python
from jsonschema import validate

user_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "created_at": {"type": "string", "format": "date-time"}
    },
    "required": ["id", "name", "email"]
}

def test_user_schema():
    api = get_api_client()
    response = api.get("/users/1")
    
    user = response.json()
    validate(instance=user, schema=user_schema)
```

### 4. Parameterized Tests

```python
import pytest

@pytest.mark.parametrize("user_id,expected_status", [
    (1, 200),
    (2, 200),
    (999, 404),
])
def test_get_user_status(user_id, expected_status):
    api = get_api_client()
    response = api.get(f"/users/{user_id}")
    assert response.status_code == expected_status
```

### 5. Request Logging

API calls are automatically logged in thread context:

```python
from orbs.thread_context import get_context

def test_with_logging():
    api = get_api_client()
    
    api.get("/users")
    api.post("/users", json={"name": "Test"})
    
    # Get all API calls made in this thread
    api_calls = get_context("api_calls")
    
    for call in api_calls:
        print(f"{call['method']} {call['url']}")
        print(f"Status: {call['status_code']}")
        print(f"Response: {call['response_body']}")
```

---

## Advanced Topics

### Custom Assertions

```python
def assert_valid_user(user_dict):
    """Custom assertion for user object"""
    assert "id" in user_dict, "User missing ID"
    assert "name" in user_dict, "User missing name"
    assert "email" in user_dict, "User missing email"
    assert "@" in user_dict["email"], "Invalid email format"
    assert user_dict["id"] > 0, "Invalid user ID"

def test_user_validation():
    api = get_api_client()
    response = api.get("/users/1")
    user = response.json()
    
    assert_valid_user(user)
```

### Retry Logic

```python
import time

def api_call_with_retry(api, method, path, max_retries=3, **kwargs):
    """Retry API call on failure"""
    for attempt in range(max_retries):
        try:
            response = getattr(api, method)(path, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(2 ** attempt)  # Exponential backoff
```

### Mock API Responses

```python
from unittest.mock import patch

def test_with_mock():
    """Test with mocked API response"""
    mock_response = {
        "id": 1,
        "name": "Mock User",
        "email": "mock@example.com"
    }
    
    with patch.object(ApiClient, 'get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200
        
        api = ApiClient(base_url="http://mock.api")
        response = api.get("/users/1")
        
        assert response.json() == mock_response
```

### Performance Testing

```python
import time

def test_api_performance():
    """Test API response time"""
    api = get_api_client()
    
    response_times = []
    
    for _ in range(10):
        start = time.time()
        api.get("/users")
        elapsed = time.time() - start
        response_times.append(elapsed)
    
    avg_time = sum(response_times) / len(response_times)
    
    assert avg_time < 0.5, f"Average response time too slow: {avg_time}s"
    print(f"Average response time: {avg_time:.3f}s")
```

---

## Troubleshooting

### Connection Errors

```python
import requests

try:
    response = api.get("/users")
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to API server")
except requests.exceptions.Timeout:
    print("❌ Request timed out")
except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
```

### SSL Verification

```python
# Disable SSL verification (not recommended for production)
api.session.verify = False

# Or specify custom CA bundle
api.session.verify = "/path/to/ca-bundle.crt"
```

### Debug Requests

```python
import logging

# Enable requests logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

# Now all requests will be logged
api.get("/users")
```

### Inspect Request

```python
# Use PreparedRequest to inspect before sending
from requests import Request

req = Request('GET', 'https://api.example.com/users')
prepared = api.session.prepare_request(req)

print(f"URL: {prepared.url}")
print(f"Headers: {prepared.headers}")
```

---

## Next Steps

* [Web Testing Guide](web-testing.md)
* [Mobile Testing Guide](mobile-testing.md)
* [Architecture Overview](architecture.md)
* [CLI Reference](cli-reference.md)
