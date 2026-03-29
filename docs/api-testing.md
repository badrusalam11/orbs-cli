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
from orbs.keyword import API

def run():
    API.set_base_url("https://jsonplaceholder.typicode.com")

    # Implicit mode — response is stored automatically
    API.get("/users")
    API.verify_status_code(200)
    API.verify_json_field_exists("[0].id")

    # Explicit mode — capture response for direct control
    response = API.get("/users/1")
    API.verify_status_code(response, 200)
    API.verify_json_equals(response, "name", "Leanne Graham")

    # POST request
    API.post("/users", json={
        "name": "John Doe",
        "email": "john@example.com"
    })
    API.verify_status_code(201)

    API.close_session()
```

> **Tip:** Every HTTP method stores the response internally. Verification keywords
> can use it implicitly (no `response` argument) or you can pass the response
> explicitly for full control. Both styles can be mixed freely.

---

## Setup

### Set Base URL

All request paths are appended to the base URL. You can also pass full URLs directly.

```python
API.set_base_url("https://API.example.com")

# These are equivalent:
API.get("/users/1")                          # uses base URL
API.get("https://API.example.com/users/1")   # full URL
```

### Set Default Headers

Headers set here are sent with every request in the session.

```python
API.set_default_headers({
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-API-Key": "your-api-key"
})
```

### Set Timeout

Default request timeout (in seconds). Default is 30s.

```python
API.set_timeout(60)  # 60 second timeout
```

---

## Making Requests

### GET

```python
# Simple GET
response = API.get("/users")

# With query parameters
response = API.get("/users", params={"page": 1, "limit": 10})

# With custom headers
response = API.get("/users", headers={"Accept": "application/xml"})
```

### POST

```python
# JSON body
response = API.post("/users", json={
    "name": "John Doe",
    "email": "john@example.com"
})

# Form data
response = API.post("/login", data={
    "username": "admin",
    "password": "secret"
})

# File upload
with open("file.pdf", "rb") as f:
    response = API.post("/upload", files={"file": f})
```

### PUT

```python
response = API.put("/users/1", json={
    "name": "Updated Name",
    "email": "updated@example.com"
})
```

### PATCH

```python
response = API.patch("/users/1", json={
    "email": "newemail@example.com"
})
```

### DELETE

```python
response = API.delete("/users/1")
```

### HEAD / OPTIONS

```python
response = API.head("/users/1")
response = API.options("/users")
```

### Generic Request

```python
response = API.request("GET", "/users/1")
response = API.request("POST", "/users", json={"name": "John"})
```

---

## Response Handling

Every request returns a standard `requests.Response` object **and** stores it
internally for implicit use by subsequent verification/helper keywords.

### Get JSON Body

```python
# Explicit
response = API.get("/users/1")
data = API.get_json(response)

# Implicit
API.get("/users/1")
data = API.get_json()
```

### Get Status Code

```python
status = API.get_status_code(response)  # explicit
status = API.get_status_code()          # implicit
```

### Get Header

```python
content_type = API.get_header(response, "Content-Type")  # explicit
content_type = API.get_header("Content-Type")             # implicit
```

### Direct Access

Since it's a standard `requests.Response`, you can also access directly:

```python
response = API.get("/users/1")

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
API.verify_status_code(response, 200)

# Implicit
API.get("/users")
API.verify_status_code(200)
```

### Verify JSON Equals

```python
# Explicit
API.verify_json_equals(response, "name", "John Doe")
API.verify_json_equals(response, "[0].id", 1)

# Implicit
API.verify_json_equals("name", "John Doe")
API.verify_json_equals("[0].id", 1)
```

### Verify JSON Field Exists

```python
API.verify_json_field_exists(response, "id")    # explicit
API.verify_json_field_exists("[0].id")           # implicit
```

### Verify Response Contains Text

```python
API.verify_response_contains(response, "success")  # explicit
API.verify_response_contains("success")             # implicit
```

### Verify JSON Array Length

```python
# Root array
API.verify_json_array_length(response, 10)              # explicit
API.verify_json_array_length(10)                         # implicit

# Nested array
API.verify_json_array_length(response, 3, field="items") # explicit
API.verify_json_array_length(3, field="items")            # implicit
```

### Verify Response Time

```python
API.verify_response_time(response, 2000)   # explicit, max 2 seconds
API.verify_response_time(2000)             # implicit
```

### Verify Response Header

```python
API.verify_header(response, "Content-Type", "application/json")  # explicit
API.verify_header("Content-Type", "application/json")             # implicit
```

---

## Authentication

### Bearer Token

```python
API.set_bearer_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
```

### Basic Auth

```python
API.set_basic_auth("admin", "password123")
```

### API Key Header

```python
API.set_default_headers({"X-API-Key": "your-api-key"})
```

### OAuth / Custom Auth Flow

```python
def run():
    API.set_base_url("https://API.example.com")

    # Get token
    token_response = API.post("/auth/token", data={
        "grant_type": "client_credentials",
        "client_id": "my-client",
        "client_secret": "my-secret"
    })

    token = API.get_json(token_response)["access_token"]
    API.set_bearer_token(token)

    # Now all requests are authenticated
    response = API.get("/protected/resource")
    API.verify_status_code(response, 200)
```

---

## Advanced Usage

### Failure Handling

Control what happens when a keyword fails:

```python
from orbs.keyword.failure_handling import FailureHandling

# Stop test on failure (default)
API.verify_status_code(response, 200, failure_handling=FailureHandling.STOP_ON_FAILURE)

# Log error but continue test
API.verify_status_code(response, 200, failure_handling=FailureHandling.CONTINUE_ON_FAILURE)

# Ignore failure completely
API.verify_status_code(response, 200, failure_handling=FailureHandling.OPTIONAL)
```

### CRUD Flow Example

```python
from orbs.keyword import API

def run():
    API.set_base_url("https://API.example.com")
    API.set_bearer_token("your-token")

    # CREATE
    response = API.post("/users", json={
        "name": "Jane Doe",
        "email": "jane@example.com"
    })
    API.verify_status_code(response, 201)
    user_id = API.get_json(response)["id"]

    # READ
    response = API.get(f"/users/{user_id}")
    API.verify_status_code(response, 200)
    API.verify_json_equals(response, "name", "Jane Doe")

    # UPDATE
    response = API.put(f"/users/{user_id}", json={
        "name": "Jane Smith"
    })
    API.verify_status_code(response, 200)

    # DELETE
    response = API.delete(f"/users/{user_id}")
    API.verify_status_code(response, 200)

    # Verify deleted
    response = API.get(f"/users/{user_id}")
    API.verify_status_code(response, 404)

    API.close_session()
```

### Environment-based Configuration

```python
from orbs.keyword import API
from orbs.config import config
def run():
    API.set_base_url(config.target("API_URL", "https://API.staging.example.com"))
    API.set_bearer_token(config.target("API_TOKEN"))

    response = API.get("/health")
    API.verify_status_code(response, 200)
```

### Combining with Web Keywords

```python
from orbs.keyword import Web
from orbs.keyword import API

def run():
    # API: Create test data
    API.set_base_url("https://API.example.com")
    response = API.post("/users", json={"name": "Test User", "email": "test@example.com"})
    user = API.get_json(response)

    # Web: Verify in UI
    Web.open("https://example.com/users")
    Web.verify_text_present(f"css=.user-list", user["name"])

    API.close_session()
    Web.quit()
```

---

## Keyword Reference

| Keyword | Description |
|---------|-------------|
| `API.set_base_url(url)` | Set base URL for all requests |
| `API.set_default_headers(headers)` | Set default headers for the session |
| `API.set_bearer_token(token)` | Set Bearer token authentication |
| `API.set_basic_auth(user, pass)` | Set Basic authentication |
| `API.set_timeout(seconds)` | Set default request timeout |
| `API.request(method, path, **kwargs)` | Send generic HTTP request |
| `API.get(path, **kwargs)` | Send GET request |
| `API.post(path, **kwargs)` | Send POST request |
| `API.put(path, **kwargs)` | Send PUT request |
| `API.patch(path, **kwargs)` | Send PATCH request |
| `API.delete(path, **kwargs)` | Send DELETE request |
| `API.head(path, **kwargs)` | Send HEAD request |
| `API.options(path, **kwargs)` | Send OPTIONS request |
| `API.get_json(response)` | Parse response as JSON |
| `API.get_status_code(response)` | Get response status code |
| `API.get_header(response, name)` | Get a response header value |
| `API.verify_status_code(response, code)` | Assert status code matches |
| `API.verify_json_equals(response, field, value)` | Assert JSON field value |
| `API.verify_json_field_exists(response, field)` | Assert JSON field exists |
| `API.verify_response_contains(response, text)` | Assert body contains text |
| `API.verify_json_array_length(response, len)` | Assert array length |
| `API.verify_response_time(response, max_ms)` | Assert response time within limit |
| `API.verify_header(response, name, value)` | Assert response header value |
| `API.close_session()` | Close HTTP session and clean up |

> **Note:** All verification and response helper keywords accept an optional
> `response` parameter. When omitted, the last response from any HTTP method is
> used automatically (implicit mode).
