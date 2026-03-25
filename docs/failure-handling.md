# Failure Handling

## Overview

ORBS provides flexible failure handling strategies that allow you to control how keyword failures are handled during test execution. This is especially useful for:

- **Optional actions** that shouldn't fail the test
- **Exploratory testing** where some actions might fail
- **Conditional logic** where failures are expected
- **Non-critical verifications** that can be skipped

## Failure Handling Strategies

### 1. STOP_ON_FAILURE (Default)
Stops test execution immediately when the keyword fails and raises an exception.

```python
from orbs.keyword import web, FailureHandling

# Default behavior - will fail test if element not found
web.click("id=submit_button")

# Explicitly specify STOP_ON_FAILURE
web.click("id=submit_button", failure_handling=FailureHandling.STOP_ON_FAILURE)
```

**Use when:**
- The action is critical for the test flow
- Failure should stop the test immediately
- You need complete test reliability

### 2. CONTINUE_ON_FAILURE
Logs the error but continues test execution. Returns `None` on failure.

**Important:** Test case will be marked as **FAILED** if any CONTINUE_ON_FAILURE error occurs, but execution continues to collect all failures.

```python
from orbs.keyword import web, FailureHandling

# Try to close popup, but continue if it doesn't exist
web.click("id=close_popup", failure_handling=FailureHandling.CONTINUE_ON_FAILURE)

# Continue with main test flow
web.set_text("id=username", "admin")
web.set_text("id=password", "pass123")
web.click("id=login")
```

**Use when:**
- Action failure shouldn't stop the test
- You want to collect all failures and review them later
- Running smoke tests where you want to see all issues
- Non-critical UI interactions

**Test Status:** FAILED (if any error occurs)

### 3. OPTIONAL
Treats the action as completely optional. Suppresses all errors and logs as info only.

**Important:** Test case remains **PASSED** even if OPTIONAL actions fail, because they are truly optional.

```python
from orbs.keyword import web, FailureHandling

# Optional banner - ignore if not present
web.click("id=optional_banner_close", failure_handling=FailureHandling.OPTIONAL)

# Optional cookie consent - may or may not exist
web.click("id=accept_cookies", failure_handling=FailureHandling.OPTIONAL)

# Main test flow
web.open("https://example.com")
web.set_text("id=search", "automation")
web.click("id=search_button")
```

**Use when:**
- Action is truly optional
- Element may or may not exist
- You don't want any error logging for missing elements
- Testing across multiple environments with different UI states

**Test Status:** PASSED (failures are ignored)

## Supported Keywords

### Web Keywords
All major web keywords support failure handling:

- `web.open()`
- `web.click()`
- `web.double_click()`
- `web.right_click()`
- `web.set_text()`
- `web.get_text()`
- `web.get_attribute()`
- `web.select_by_text()`
- `web.select_by_value()`
- `web.select_by_index()`
- `web.wait_for_element()`
- `web.wait_for_visible()`
- `web.wait_for_clickable()`
- `web.verify_text()`
- `web.verify_element_visible()`

### Mobile Keywords
All major Mobile keywords support failure handling:

- `mobile.tap()`
- `mobile.long_press()`
- `mobile.double_tap()`
- `mobile.set_text()`
- `mobile.get_text()`
- `mobile.get_attribute()`
- `mobile.wait_for_element()`
- `mobile.wait_for_visible()`

## Usage Examples

### Example 1: Handle Optional Popups

```python
from orbs.keyword import web, FailureHandling

def test_login_with_optional_popup():
    web.open("https://example.com")
    
    # Optional: Close marketing popup if it appears
    web.click(
        "id=marketing_popup_close", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Optional: Dismiss notification banner
    web.click(
        "id=notification_dismiss", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Critical: Main login flow (will fail test if errors)
    web.set_text("id=username", "admin")
    web.set_text("id=password", "password123")
    web.click("id=login_button")
    
    web.verify_text("id=welcome_message", "Welcome, Admin!")
```

### Example 2: Smoke Test with CONTINUE_ON_FAILURE

```python
from orbs.keyword import web, FailureHandling

def test_smoke_navigation():
    """Smoke test that checks multiple pages without stopping on first failure"""
    web.open("https://example.com")
    
    results = {}
    
    # Test all navigation links - don't stop on first failure
    pages = [
        ("id=home_link", "Home"),
        ("id=products_link", "Products"),
        ("id=about_link", "About"),
        ("id=contact_link", "Contact"),
        ("id=blog_link", "Blog")
    ]
    
    for locator, page_name in pages:
        # Continue even if a link fails
        web.click(locator, failure_handling=FailureHandling.CONTINUE_ON_FAILURE)
        time.sleep(1)
        
        # Try to verify page loaded
        title = web.get_text(
            "css=h1", 
            failure_handling=FailureHandling.CONTINUE_ON_FAILURE
        )
        results[page_name] = title is not None
    
    # Review results
    failed = [name for name, success in results.items() if not success]
    if failed:
        print(f"Failed to navigate to: {', '.join(failed)}")
```

### Example 3: Cross-Environment Test

```python
from orbs.keyword import web, FailureHandling

def test_form_submission():
    """Test that works across dev, staging, and prod environments"""
    web.open("https://example.com/form")
    
    # Dev environment has debug panel - optional
    web.click(
        "id=debug_panel_close", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Staging has beta warning - optional
    web.click(
        "id=beta_warning_dismiss", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Fill form (critical)
    web.set_text("id=name", "John Doe")
    web.set_text("id=email", "john@example.com")
    
    # Optional newsletter checkbox (not in all environments)
    web.click(
        "id=newsletter_checkbox", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Submit (critical)
    web.click("id=submit_button")
    web.verify_text("id=success_message", "Form submitted successfully!")
```

### Example 4: Mobile Testing with Optional Elements

```python
from orbs.keyword import Mobile, FailureHandling

def test_mobile_app_login():
    mobile.launch("com.example.app", ".MainActivity")
    
    # Optional: Skip onboarding if already seen
    mobile.tap(
        "id=skip_onboarding", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Optional: Dismiss permission dialogs
    mobile.tap(
        "id=allow_notifications", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    mobile.tap(
        "id=allow_location", 
        failure_handling=FailureHandling.OPTIONAL
    )
    
    # Critical: Login flow
    mobile.tap("id=login_button")
    mobile.set_text("id=username", "testuser")
    mobile.set_text("id=password", "pass123")
    mobile.tap("id=submit_login")
    
    mobile.wait_for_element("id=home_screen")
```

## Logging Behavior

Each failure handling mode produces different log output:

### STOP_ON_FAILURE
```
[ERROR] [STOP_ON_FAILURE] click failed: Element not found: id=submit_button
```
→ Exception raised, test stops

### CONTINUE_ON_FAILURE
```
[ERROR] [CONTINUE_ON_FAILURE] click failed: Element not found: id=optional_button
[WARNING] Test execution continues despite failure in click
```
→ No exception, test continues

### OPTIONAL
```
[INFO] [OPTIONAL] click failed (ignored): Element not found: id=optional_banner
```
→ No exception, minimal logging

## Test Case Status Behavior

The failure handling strategy affects the final test case status:

| Strategy | Error Occurs | Test Status | Execution |
|----------|-------------|-------------|-----------|
| **STOP_ON_FAILURE** | ✗ Exception | **FAILED** | Stops immediately |
| **CONTINUE_ON_FAILURE** | ✗ Logged | **FAILED** | Continues to end |
| **OPTIONAL** | ✗ Ignored | **PASSED** | Continues to end |

### Example: Different Status Outcomes

```python
# Test 1: Will be marked as FAILED
def test_with_continue_on_failure():
    web.open("https://example.com")
    web.click("id=missing_button", failure_handling=FailureHandling.CONTINUE_ON_FAILURE)  # Error!
    web.click("id=another_button")  # This still runs
    # Result: Test case marked as FAILED (but all steps executed)

# Test 2: Will be marked as PASSED
def test_with_optional():
    web.open("https://example.com")
    web.click("id=missing_banner", failure_handling=FailureHandling.OPTIONAL)  # Ignored
    web.click("id=main_button")  # Success
    # Result: Test case marked as PASSED (optional action ignored)

# Test 3: Will be marked as FAILED
def test_with_stop_on_failure():
    web.open("https://example.com")
    web.click("id=missing_button")  # Default: STOP_ON_FAILURE
    web.click("id=another_button")  # This won't run
    # Result: Test case marked as FAILED (execution stopped)
```

### Why CONTINUE_ON_FAILURE Marks Test as Failed

`CONTINUE_ON_FAILURE` is designed for **collecting all failures** in a single test run (e.g., smoke tests). The test continues to gather all errors, but the final status reflects that problems were encountered:

```python
def smoke_test_all_links():
    """Check all navigation links - collect all failures"""
    links = ["id=home", "id=products", "id=about", "id=contact", "id=broken_link"]
    
    for link in links:
        web.click(link, failure_handling=FailureHandling.CONTINUE_ON_FAILURE)
    
    # All links are tested, report shows which ones failed
    # Test status: FAILED (because 'broken_link' failed)
```

### Why OPTIONAL Keeps Test Passed

`OPTIONAL` is for **truly optional elements** that have no impact on test success:

```python
def test_login_flow():
    """Login should work regardless of optional elements"""
    web.open("https://example.com")
    
    # Optional promotional banner
    web.click("id=promo_close", failure_handling=FailureHandling.OPTIONAL)
    
    # Critical login flow
    web.set_text("id=username", "admin")
    web.set_text("id=password", "pass123")
    web.click("id=login")
    web.verify_text("id=welcome", "Welcome, admin!")
    
    # Test status: PASSED (promo banner is truly optional)
```

## Return Values

- **STOP_ON_FAILURE**: Returns result or raises exception
- **CONTINUE_ON_FAILURE**: Returns result on success, `None` on failure
- **OPTIONAL**: Returns result on success, `None` on failure

```python
# Get text with optional handling
text = web.get_text("id=label", failure_handling=FailureHandling.OPTIONAL)

if text:
    print(f"Label text: {text}")
else:
    print("Label not found (optional)")
```

## Best Practices

### 1. Use STOP_ON_FAILURE for Critical Actions
```python
# Critical actions should fail the test
web.set_text("id=username", "admin")  # Default: STOP_ON_FAILURE
web.click("id=login")  # Default: STOP_ON_FAILURE
```

### 2. Use OPTIONAL for Environmental Differences
```python
# Elements that may vary across environments
web.click("id=dev_only_banner", failure_handling=FailureHandling.OPTIONAL)
```

### 3. Use CONTINUE_ON_FAILURE for Smoke Tests
```python
# When you want to see all issues at once
for link in navigation_links:
    web.click(link, failure_handling=FailureHandling.CONTINUE_ON_FAILURE)
```

### 4. Document Why You're Using Non-Default Handling
```python
# OPTIONAL because: Cookie banner only appears on first visit
web.click("id=accept_cookies", failure_handling=FailureHandling.OPTIONAL)

# CONTINUE_ON_FAILURE because: This is a non-critical verification
web.verify_text("id=optional_label", "Test", 
                failure_handling=FailureHandling.CONTINUE_ON_FAILURE)
```

### 5. Combine with Conditional Logic
```python
# Try optional action and react accordingly
popup_closed = web.click(
    "id=popup_close", 
    failure_handling=FailureHandling.OPTIONAL
)

if popup_closed:
    web.sleep(1)  # Wait for popup animation
```

## Comparison with Other Frameworks

| Framework | Feature Name | ORBS Equivalent |
|-----------|-------------|-----------------|
| Katalon | FailureHandling.STOP_ON_FAILURE | FailureHandling.STOP_ON_FAILURE |
| Katalon | FailureHandling.CONTINUE_ON_FAILURE | FailureHandling.CONTINUE_ON_FAILURE |
| Katalon | FailureHandling.OPTIONAL | FailureHandling.OPTIONAL |
| Robot Framework | Run Keyword And Continue On Failure | CONTINUE_ON_FAILURE |
| Robot Framework | Run Keyword And Ignore Error | OPTIONAL |

## Advanced: Dynamic Failure Handling

Use `with_failure_handling()` function for dynamic scenarios:

```python
from orbs.keyword import Web, FailureHandling
from orbs.keyword.failure_handling import with_failure_handling

def test_dynamic_handling():
    # Choose handling mode based on environment
    mode = FailureHandling.OPTIONAL if is_dev_env() else FailureHandling.STOP_ON_FAILURE
    
    with_failure_handling(
        mode,
        web.click,
        "id=debug_button"
    )
```

## Summary

FailureHandling in ORBS provides:
- ✅ **Flexible error handling** for different test scenarios
- ✅ **Better test resilience** across environments
- ✅ **Clearer test intent** through explicit failure strategies
- ✅ **Compatible** with both Web and Mobile keywords
- ✅ **Familiar API** similar to Katalon and other frameworks

Start using FailureHandling to make your tests more robust and maintainable!
