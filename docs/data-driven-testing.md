# Data-Driven Testing

Run the same test logic across multiple data rows using the `@ddt` decorator.

---

## Table of Contents

* [Introduction](#introduction)
* [Quick Start](#quick-start)
* [How It Works](#how-it-works)
* [API Reference](#api-reference)
* [Filtering with `where`](#filtering-with-where)
* [Scenario Naming](#scenario-naming)
* [Report Integration](#report-integration)
* [Best Practices](#best-practices)
* [Examples](#examples)
* [DDT vs Scenario Outline (BDD)](#ddt-vs-scenario-outline-bdd)
* [Troubleshooting](#troubleshooting)

---

## Introduction

Data-Driven Testing (DDT) allows you to execute the same test function multiple times with different input data from a CSV file. Each row becomes an independent scenario with its own pass/fail status, duration, and keyword steps in the report.

Key features:

* **CSV-based data source** - Uses the same environment-aware CSV loader as `load_data`
* **Automatic iteration** - Each CSV row is executed as a separate scenario
* **Isolated execution** - Browser is reset between scenarios for clean state
* **Per-scenario reporting** - Each scenario appears individually in HTML and PDF reports
* **Scenario labeling** - Use a CSV column as scenario name, or auto-generate `row1`, `row2`, etc.
* **Fail-safe continuation** - A failing scenario does not stop remaining scenarios from running

---

## Quick Start

### 1. Prepare CSV Data

Create a CSV file in your `data/` directory:

```csv
scenario,username,password,expected
valid_login,admin,secret123,success
invalid_password,admin,wrongpwd,failure
empty_username,,secret123,failure
```

Save as `data/cred/login.csv`.

### 2. Write a Data-Driven Test Case

```python
from orbs.data import ddt
from orbs.keyword import web

@ddt("cred/login.csv", scenario="scenario")
def run(data):
    web.open("https://example.com/login")
    web.set_text("id=username", data["username"])
    web.set_text("id=password", data["password"])
    web.click("id=login-btn")

    if data["expected"] == "success":
        web.wait_for_element("id=dashboard")
    else:
        web.wait_for_element("id=error-message")
```

### 3. Run the Test

```bash
orbs run testcases/login_ddt.py --platform=chrome
```

Each row produces a separate scenario in the test report: `valid_login`, `invalid_password`, `empty_username`.

---

## How It Works

The `@ddt` decorator wraps your test function with the following lifecycle:

```
1. Load CSV file (environment-aware resolution)
2. For each row:
   a. Determine scenario name (from column or auto-generated)
   b. Reset browser driver for clean state
   c. Clear keyword steps context
   d. Execute test function with row data as dict
   e. Capture status (PASSED/FAILED), duration, steps, and error
3. Store all scenario results in thread context
4. If any scenario failed, raise exception with failure summary
```

The environment-aware path resolution follows the same priority as `load_data`:

1. `data.local/<path>` — Local overrides (git-ignored)
2. `data/<ENV>/<path>` — Environment-specific data
3. `data/<path>` — Default fallback

---

## API Reference

### `@ddt(path, scenario=None, where=None)`

Decorator that transforms a test function into a data-driven test.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | Yes | Relative path to CSV file (e.g. `"cred/login.csv"`) |
| `scenario` | `str` | No | Column name to use as scenario label. Defaults to `row1`, `row2`, etc. |
| `where` | `dict` | No | Column=value conditions to filter CSV rows before iteration |

**Decorated function signature:**

```python
def run(data: dict) -> None
```

The `data` parameter receives a dictionary where keys are CSV column headers and values are the row's cell values (as strings).

**Raises:**

- `ValueError` — If the CSV file contains no data rows
- `Exception` — After all scenarios complete, if any scenario failed (includes failure count)

---

## Filtering with `where`

The `where` parameter lets you filter CSV rows before iteration, so only matching rows are executed as scenarios.

### Basic Usage

Given `data/cred/login.csv`:

```csv
scenario,username,password,type,role
valid_admin,admin,Admin@123,valid,admin
valid_user,john,User@456,valid,user
invalid_login,bad,wrong,invalid,user
locked_admin,locked,Pass@789,valid,admin
```

Run only rows where `type` is `"valid"`:

```python
@ddt("cred/login.csv", scenario="scenario", where={"type": "valid"})
def run(data):
    # Only runs: valid_admin, valid_user, locked_admin
    ...
```

### Multiple Conditions

All conditions must match (AND logic):

```python
# Dict syntax
@ddt("cred/login.csv", scenario="scenario", where={"type": "valid", "role": "admin"})
def run(data):
    # Only runs: valid_admin, locked_admin
    ...

# dict() syntax
@ddt("cred/login.csv", scenario="scenario", where=dict(type="valid", role="admin"))
def run(data):
    # Same result
    ...
```

### Use Cases

**Run only positive scenarios:**

```python
@ddt("checkout/payment.csv", scenario="scenario", where={"expected": "success"})
def run(data):
    ...
```

**Run only a specific environment's data:**

```python
@ddt("test-cases.csv", scenario="scenario", where={"env": "staging"})
def run(data):
    ...
```

**Combine with a shared CSV for multiple test cases:**

```csv
scenario,username,password,type,test_group
admin_login,admin,Admin@123,valid,smoke
user_login,john,User@456,valid,regression
bad_login,bad,wrong,invalid,smoke
empty_login,,,invalid,regression
```

```python
# testcases/smoke_login.py
@ddt("cred/login.csv", scenario="scenario", where={"test_group": "smoke"})
def run(data):
    ...

# testcases/regression_login.py
@ddt("cred/login.csv", scenario="scenario", where={"test_group": "regression"})
def run(data):
    ...
```

---

### Using a CSV Column

Specify the `scenario` parameter to use a column value as the scenario name:

```csv
scenario,username,password
valid_admin,admin,secret123
locked_account,locked_user,pass456
```

```python
@ddt("cred/login.csv", scenario="scenario")
def run(data):
    # Scenarios: "valid_admin", "locked_account"
    ...
```

### Auto-Generated Names

Omit the `scenario` parameter to use auto-generated names:

```python
@ddt("cred/login.csv")
def run(data):
    # Scenarios: "row1", "row2", "row3"
    ...
```

### Missing Column Fallback

If the `scenario` column name doesn't exist in a row, it falls back to `rowN`:

```python
@ddt("data.csv", scenario="nonexistent_column")
def run(data):
    # Scenarios: "row1", "row2", etc.
    ...
```

---

## Report Integration

DDT scenarios are fully integrated into Orbs test reports.

### HTML Report

Each scenario appears as an expandable section under the test case with:

- Scenario name and pass/fail status
- Execution duration
- Keyword steps performed during that scenario
- Error traceback (if failed)

### PDF Report

Each scenario is rendered as a sub-section under the test case header with:

- Scenario name, status, and duration
- Keyword step table
- Error details for failed scenarios

### Console Output

During execution, each scenario is logged:

```
INFO  DDT: Running run[valid_login]
INFO  DDT: Running run[invalid_password]
ERROR DDT: run[locked_account] FAILED: Element not found: id=dashboard
```

After completion, a summary is raised if any scenario failed:

```
Exception: DDT: 1/3 scenarios failed
```

---

## Best Practices

### Keep CSV Data Simple

Use clear column names and keep data flat:

```csv
scenario,email,password,expected_error
valid_user,user@example.com,Pass123!,
empty_email,,Pass123!,Email is required
invalid_format,not-an-email,Pass123!,Invalid email format
```

### Use the `scenario` Column

Always include a descriptive `scenario` column for readable reports:

```python
# Good - clear scenario names in report
@ddt("login.csv", scenario="scenario")

# Avoid - generic row1, row2 names
@ddt("login.csv")
```

### One Assertion Per Scenario

Each row should test one specific condition:

```csv
scenario,input,expected
positive_number,42,Valid
negative_number,-1,Invalid
zero,0,Valid
boundary_max,999999,Valid
exceed_max,1000000,Invalid
```

### Organize Data Files

Group DDT CSV files by feature:

```
data/
├── cred/
│   ├── login.csv
│   └── register.csv
├── checkout/
│   ├── payment.csv
│   └── shipping.csv
└── search/
    └── queries.csv
```

### Environment-Specific Data

Use environment directories for different data sets:

```
data/
├── cred/login.csv              # Default credentials
├── staging/
│   └── cred/login.csv          # Staging credentials
└── production/
    └── cred/login.csv          # Production credentials
```

---

## Examples

### Login Scenarios

```csv
scenario,username,password,expected
valid_admin,admin,Admin@123,dashboard
valid_user,john,User@456,home
wrong_password,admin,wrong,error
empty_fields,,,error
sql_injection,admin' OR '1'='1,pass,error
```

```python
from orbs.data import ddt
from orbs.keyword import web

@ddt("cred/login.csv", scenario="scenario")
def run(data):
    web.open("https://example.com/login")
    web.set_text("id=username", data["username"])
    web.set_text("id=password", data["password"])
    web.click("id=login-btn")

    if data["expected"] == "error":
        assert web.is_visible("css=.error-message"), "Error message not shown"
    else:
        web.wait_for_element(f"id={data['expected']}")
```

### Form Validation

```csv
scenario,field,value,error_message
required_name,,Name is required
max_length,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,Name too long
special_chars,<script>alert(1)</script>,Invalid characters
valid_name,John Doe,
```

```python
from orbs.data import ddt
from orbs.keyword import web

@ddt("validation/name_field.csv", scenario="scenario")
def run(data):
    web.open("https://example.com/form")
    web.set_text("id=name", data["value"])
    web.click("id=submit")

    if data["error_message"]:
        error = web.get_text("css=.field-error")
        assert error == data["error_message"], f"Expected '{data['error_message']}', got '{error}'"
    else:
        web.wait_for_element("id=success")
```

### API Testing with DDT

```csv
scenario,endpoint,method,status_code,body
get_users,/api/users,GET,200,
create_user,/api/users,POST,201,{"name":"test"}
not_found,/api/users/999,GET,404,
unauthorized,/api/admin,GET,401,
```

```python
from orbs.data import ddt
from orbs.keyword import api

@ddt("api/endpoints.csv", scenario="scenario")
def run(data):
    if data["method"] == "GET":
        response = api.get(data["endpoint"])
    elif data["method"] == "POST":
        response = api.post(data["endpoint"], body=data["body"])

    assert str(response.status_code) == data["status_code"], \
        f"Expected {data['status_code']}, got {response.status_code}"
```

### Combining DDT with load_data

You can use `@ddt` for iteration and `load_data` for supplementary data:

```python
from orbs.data import ddt, load_data
from orbs.keyword import web

@ddt("test-cases/checkout.csv", scenario="scenario")
def run(data):
    # Get user credentials from separate data file
    user = load_data("cred/users.csv").one(role=data["user_role"])
    
    web.open("https://example.com/login")
    web.set_text("id=username", user["username"])
    web.set_text("id=password", user["password"])
    web.click("id=login-btn")
    
    # Continue with checkout flow using DDT data
    web.click(f"id=product-{data['product_id']}")
    web.click("id=checkout")
```

---

## DDT vs Scenario Outline (BDD)

`@ddt` is a **Python decorator** and can only be used on Python test functions. It **cannot** be applied to `.feature` files.

For BDD feature files, Gherkin already provides a native data-driven mechanism: **`Scenario Outline`** + **`Examples`** table.

### Comparison

| | `@ddt` (Python) | `Scenario Outline` (BDD) |
|---|---|---|
| **Used in** | Python test cases (`testcases/*.py`) | Feature files (`include/features/*.feature`) |
| **Data source** | External CSV file | Inline `Examples` table in `.feature` file |
| **Data location** | `data/` directory (environment-aware) | Embedded in the feature file |
| **Syntax** | `@ddt("file.csv")` decorator | `Scenario Outline:` + `Examples:` |
| **Parameterization** | `data["column"]` dict access | `<column>` angle-bracket placeholders |

### Python Test Case with @ddt

```python
from orbs.data import ddt
from orbs.keyword import web

@ddt("cred/login.csv", scenario="scenario")
def run(data):
    web.open("https://example.com/login")
    web.set_text("id=username", data["username"])
    web.set_text("id=password", data["password"])
    web.click("id=login-btn")
```

### BDD Feature File with Scenario Outline

```gherkin
Feature: Login functionality

  @positive
  Scenario Outline: Successful login
    Given the user opens the login page
    When the user fill username <username> and password <password>
    Then the user should see the dashboard

  Examples:
    | username | password           |
    | John Doe | ThisIsNotAPassword |
    | admin    | Admin@123          |
    | user1    | User@456           |
```

Step definition (`include/steps/login_steps.py`):

```python
from behave import given, when, then
from orbs.keyword import web

@given('the user opens the login page')
def step_impl(context):
    web.open("https://example.com/login")

@when('the user fill username {username} and password {password}')
def step_impl(context, username, password):
    web.set_text("id=username", username)
    web.set_text("id=password", password)
    web.click("id=login-btn")

@then('the user should see the dashboard')
def step_impl(context):
    web.wait_for_element("id=dashboard")
```

### When to Use Which

- **Use `@ddt`** when you write Python test cases and want to load test data from an external CSV file (especially with environment-aware resolution)
- **Use `Scenario Outline`** when you write BDD feature files and want data-driven scenarios with Gherkin syntax

---

## Troubleshooting

### ValueError: No data found

**Problem:** `DDT: No data found in cred/login.csv`

**Solution:**
- Verify the CSV file exists in `data/`, `data/<ENV>/`, or `data.local/`
- Check that the CSV has at least one data row (not just headers)
- Verify the file path is relative to the `data/` directory

### All scenarios fail with the same error

**Problem:** Every scenario fails with an identical error.

**Solution:**
- Check if the error is in shared setup code (e.g., URL, selectors)
- Verify the application under test is accessible
- Ensure browser configuration is correct

### Scenario names show as row1, row2

**Problem:** Report shows `row1`, `row2` instead of meaningful names.

**Solution:**
- Add a `scenario` column to your CSV file
- Pass `scenario="scenario"` (or your column name) to the `@ddt` decorator

### Browser state leaks between scenarios

**Problem:** Data from a previous scenario affects the next one.

**Solution:**
- The `@ddt` decorator automatically resets the browser between scenarios
- If you have non-browser state (e.g., variables, files), clean them up manually at the start of each scenario

### FileNotFoundError

**Problem:** CSV file not found.

**Solution:**
- Check file path spelling and case sensitivity
- Ensure the file is in one of the data directories: `data.local/`, `data/<ENV>/`, or `data/`
- Verify working directory is the project root
