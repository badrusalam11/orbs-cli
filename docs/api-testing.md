# API Testing with Orbs

Complete guide to REST API testing using the `API` keyword class.

---

## Table of Contents

* [Quick Start](#quick-start)
* [Setup](#setup)
* [Making Requests](#making-requests)
* [Response Handling](#response-handling)
* [Verification Keywords](#verification-keywords)
* [Authentication](#authentication)
* [Advanced Usage](#advanced-usage)
* [Keyword Reference](#keyword-reference)

---

## Quick Start

```python
from orbs.keyword import api

def run():
    api.set_base_url("https://jsonplaceholder.typicode.com")

    # Implicit mode — response is stored automatically
    api.get("/users")
    api.verify_status_code(200)
    api.verify_json_field_exists("[0].id")

    # Explicit mode — capture response for direct control
    response = api.get("/users/1")
    api.verify_status_code(response, 200)
    api.verify_json_equals(response, "name", "Leanne Graham")

    # POST request
    api.post("/users", json={
        "name": "John Doe",
        "email": "john@example.com"
    })
    api.verify_status_code(201)

    api.close_session()
```

> **Tip:** Every HTTP method stores the response internally. Verification keywords
> can use it implicitly (no `response` argument) or you can pass the response
> explicitly for full control. Both styles can be mixed freely.

---

## Setup

### Set Base URL

All request paths are appended to the base URL. You can also pass full URLs directly.

```python
api.set_base_url("https://api.example.com")

# These are equivalent:
api.get("/users/1")                          # uses base URL
api.get("https://api.example.com/users/1")   # full URL
```

### Set Default Headers

Headers set here are sent with every request in the session.

```python
api.set_default_headers({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-API-Key": "your-api-key"
})
```

### Set Timeout

Default request timeout (in seconds). Default is 30s.

```python
api.set_timeout(60)  # 60 second timeout
```

---

## Making Requests

### GET

```python
# Simple GET
response = api.get("/users")

# With query parameters
response = api.get("/users", params={"page": 1, "limit": 10})

# With custom headers
response = api.get("/users", headers={"Accept": "application/xml"})
```

### POST

```python
# JSON body
response = api.post("/users", json={
    "name": "John Doe",
    "email": "john@example.com"
})

# Form data
response = api.post("/login", data={
    "username": "admin",
    "password": "secret"
})

# File upload
with open("file.pdf", "rb") as f:
    response = api.post("/upload", files={"file": f})
```

### PUT

```python
response = api.put("/users/1", json={
    "name": "Updated Name",
    "email": "updated@example.com"
})
```

### PATCH

```python
response = api.patch("/users/1", json={
    "email": "newemail@example.com"
})
```

### DELETE

```python
response = api.delete("/users/1")
```

### HEAD / OPTIONS

```python
response = api.head("/users/1")
response = api.options("/users")
```

### Generic Request

```python
response = api.request("GET", "/users/1")
response = api.request("POST", "/users", json={"name": "John"})
```

---

## Response Handling

Every request returns a standard `requests.Response` object **and** stores it
internally for implicit use by subsequent verification/helper keywords.

### Get JSON Body

```python
# Explicit
response = api.get("/users/1")
data = api.get_json(response)

# Implicit
api.get("/users/1")
data = api.get_json()
```

### Get Status Code

```python
status = api.get_status_code(response)  # explicit
status = api.get_status_code()          # implicit
```

### Get Header

```python
content_type = api.get_header(response, "Content-Type")  # explicit
content_type = api.get_header("Content-Type")             # implicit
```

### Direct Access

Since it's a standard `requests.Response`, you can also access directly:

```python
response = api.get("/users/1")

response.status_code      # 200
response.json()           # {"id": 1, "name": "..."}
response.text             # raw body
response.headers          # response headers
response.elapsed          # response time
response.cookies          # cookies
```

---

## Verification Keywords

Built-in assertions that integrate with Orbs reporting.

### Verify Status Code

```python
# Explicit
api.verify_status_code(response, 200)

# Implicit
api.get("/users")
api.verify_status_code(200)
```

### Verify JSON Equals

```python
# Explicit
api.verify_json_equals(response, "name", "John Doe")
api.verify_json_equals(response, "[0].id", 1)

# Implicit
api.verify_json_equals("name", "John Doe")
api.verify_json_equals("[0].id", 1)
```

### Verify JSON Field Exists

```python
api.verify_json_field_exists(response, "id")    # explicit
api.verify_json_field_exists("[0].id")           # implicit
```

### Verify Response Contains Text

```python
api.verify_response_contains(response, "success")  # explicit
api.verify_response_contains("success")             # implicit
```

### Verify JSON Array Length

```python
# Root array
api.verify_json_array_length(response, 10)              # explicit
api.verify_json_array_length(10)                         # implicit

# Nested array
api.verify_json_array_length(response, 3, field="items") # explicit
api.verify_json_array_length(3, field="items")            # implicit
```

### Verify Response Time

```python
api.verify_response_time(response, 2000)   # explicit, max 2 seconds
api.verify_response_time(2000)             # implicit
```

### Verify Response Header

```python
api.verify_header(response, "Content-Type", "application/json")  # explicit
api.verify_header("Content-Type", "application/json")             # implicit
```

---

## Authentication

### Bearer Token

```python
api.set_bearer_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
```

### Basic Auth

```python
api.set_basic_auth("admin", "password123")
```

### API Key Header

```python
api.set_default_headers({"X-API-Key": "your-api-key"})
```

### OAuth / Custom Auth Flow

```python
def run():
    api.set_base_url("https://api.example.com")

    # Get token
    token_response = api.post("/auth/token", data={
        "grant_type": "client_credentials",
        "client_id": "my-client",
        "client_secret": "my-secret"
    })

    token = api.get_json(token_response)["access_token"]
    api.set_bearer_token(token)

    # Now all requests are authenticated
    response = api.get("/protected/resource")
    api.verify_status_code(response, 200)
```

---

## Advanced Usage

### Failure Handling

Control what happens when a keyword fails:

```python
from orbs.keyword.failure_handling import FailureHandling

# Stop test on failure (default)
api.verify_status_code(response, 200, failure_handling=FailureHandling.STOP_ON_FAILURE)

# Log error but continue test
api.verify_status_code(response, 200, failure_handling=FailureHandling.CONTINUE_ON_FAILURE)

# Ignore failure completely
api.verify_status_code(response, 200, failure_handling=FailureHandling.OPTIONAL)
```

### CRUD Flow Example

```python
from orbs.keyword import api

def run():
    api.set_base_url("https://api.example.com")
    api.set_bearer_token("your-token")

    # CREATE
    response = api.post("/users", json={
        "name": "Jane Doe",
        "email": "jane@example.com"
    })
    api.verify_status_code(response, 201)
    user_id = api.get_json(response)["id"]

    # READ
    response = api.get(f"/users/{user_id}")
    api.verify_status_code(response, 200)
    api.verify_json_equals(response, "name", "Jane Doe")

    # UPDATE
    response = api.put(f"/users/{user_id}", json={
        "name": "Jane Smith"
    })
    api.verify_status_code(response, 200)

    # DELETE
    response = api.delete(f"/users/{user_id}")
    api.verify_status_code(response, 200)

    # Verify deleted
    response = api.get(f"/users/{user_id}")
    api.verify_status_code(response, 404)

    api.close_session()
```

### Environment-based Configuration

```python
from orbs.keyword import api
from orbs.config import config
def run():
    api.set_base_url(config.target("API_URL", "https://api.staging.example.com"))
    api.set_bearer_token(config.target("API_TOKEN"))

    response = api.get("/health")
    api.verify_status_code(response, 200)
```

### Combining with Web Keywords

```python
from orbs.keyword import web
from orbs.keyword import api

def run():
    # API: Create test data
    api.set_base_url("https://api.example.com")
    response = api.post("/users", json={"name": "Test User", "email": "test@example.com"})
    user = api.get_json(response)

    # Web: Verify in UI
    web.open("https://example.com/users")
    web.verify_text_present(f"css=.user-list", user["name"])

    api.close_session()
    web.quit()
```

---

## Keyword Reference

| Keyword | Description |
|---------|-------------|
| `api.set_base_url(url)` | Set base URL for all requests |
| `api.set_default_headers(headers)` | Set default headers for the session |
| `api.set_bearer_token(token)` | Set Bearer token authentication |
| `api.set_basic_auth(user, pass)` | Set Basic authentication |
| `api.set_timeout(seconds)` | Set default request timeout |
| `api.request(method, path, **kwargs)` | Send generic HTTP request |
| `api.get(path, **kwargs)` | Send GET request |
| `api.post(path, **kwargs)` | Send POST request |
| `api.put(path, **kwargs)` | Send PUT request |
| `api.patch(path, **kwargs)` | Send PATCH request |
| `api.delete(path, **kwargs)` | Send DELETE request |
| `api.head(path, **kwargs)` | Send HEAD request |
| `api.options(path, **kwargs)` | Send OPTIONS request |
| `api.get_json(response)` | Parse response as JSON |
| `api.get_status_code(response)` | Get response status code |
| `api.get_header(response, name)` | Get a response header value |
| `api.verify_status_code(response, code)` | Assert status code matches |
| `api.verify_json_equals(response, field, value)` | Assert JSON field value |
| `api.verify_json_field_exists(response, field)` | Assert JSON field exists |
| `api.verify_response_contains(response, text)` | Assert body contains text |
| `api.verify_json_array_length(response, len)` | Assert array length |
| `api.verify_response_time(response, max_ms)` | Assert response time within limit |
| `api.verify_header(response, name, value)` | Assert response header value |
| `api.close_session()` | Close HTTP session and clean up |

> **Note:** All verification and response helper keywords accept an optional
> `response` parameter. When omitted, the last response from any HTTP method is
> used automatically (implicit mode).
