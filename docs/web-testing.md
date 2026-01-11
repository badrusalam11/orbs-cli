# Web Testing with Orbs

Complete guide to web browser automation using Orbs framework.

---

## Table of Contents

* [Introduction](#introduction)
* [Quick Start](#quick-start)
* [Browser Configuration](#browser-configuration)
* [Locator Strategies](#locator-strategies)
* [Web Keywords](#web-keywords)
* [Writing Test Cases](#writing-test-cases)
* [BDD with Features](#bdd-with-features)
* [Best Practices](#best-practices)
* [Troubleshooting](#troubleshooting)

---

## Introduction

Orbs provides high-level web automation keywords built on Selenium WebDriver. The framework handles:

* **Automatic driver management** - No need to manually create/close drivers
* **Thread-safe execution** - Parallel test execution support
* **Smart waiting** - Automatic waits with configurable timeouts
* **Retry logic** - Handles stale element exceptions
* **Multiple browsers** - Chrome, Firefox, Edge, Safari support

---

## Quick Start

### 1. Initialize Project

```bash
orbs init web-automation
cd web-automation
```

### 2. Configure Browser

Edit `settings/browser.properties`:

```properties
browser=chrome
headless=false
args=--incognito;--window-size=1920,1080
```

### 3. Create Test Case

```bash
orbs create-testcase google_search
```

Edit `testcases/google_search.py`:

```python
from orbs.keyword.web import Web

def test_google_search():
    """Test Google search functionality"""
    
    # Open Google
    Web.open("https://www.google.com")
    
    # Type search query
    Web.set_text("name=q", "Orbs automation framework")
    
    # Submit search
    Web.press_enter("name=q")
    
    # Wait for results
    Web.wait_for_element("id=search", timeout=10)
    
    # Verify results are visible
    assert Web.is_visible("id=search"), "Search results not displayed"
    
    print("✅ Google search test passed")
```

### 4. Run Test

```bash
orbs run testcases/google_search.py --platform=chrome
```

---

## Browser Configuration

### Configuration File

Location: `settings/browser.properties`

```properties
# Browser selection
browser=chrome

# Headless mode (true/false)
headless=false

# Window size (widthxheight)
window_size=1920x1080

# Additional Arguments (comma-separated)
args=--disable-gpu,--no-sandbox

# WebDriver executable path (optional)
driver_path=/path/to/chromedriver
```

### Supported Browsers

| Browser | Platform Value | Requirements |
|---------|----------------|--------------|
| Chrome | `chrome` | ChromeDriver |
| Firefox | `firefox` | GeckoDriver |
| Edge | `edge` | EdgeDriver |
| Safari | `safari` | Built-in (macOS only) |

### Runtime Platform Override

```bash
# Run on Firefox
orbs run testsuites/smoke.yml --platform=firefox

# Run on Edge
orbs run testsuites/regression.yml --platform=edge
```

### Headless Execution

For CI/CD or background execution:

```properties
headless=true
```

Or via environment variable:

```bash
export HEADLESS=true
orbs run testsuites/regression.yml
```

---

## Locator Strategies

Orbs supports multiple locator strategies with a simple syntax:

### Syntax

```
strategy=value
```

### Supported Strategies

| Strategy | Syntax | Example |
|----------|--------|---------|
| ID | `id=element_id` | `id=submit-button` |
| CSS Selector | `css=.class-name` | `css=#login-form input[type='email']` |
| XPath | `xpath=//div[@id='test']` | `xpath=//button[text()='Submit']` |
| Name | `name=element_name` | `name=username` |
| Class Name | `class=class-name` | `class=btn-primary` |
| Tag Name | `tag=div` | `tag=input` |
| Link Text | `link=Click Here` | `link=Sign Up` |
| Partial Link | `partial_link=Click` | `partial_link=Learn More` |

### Default Strategy

If no strategy is specified, **ID** is assumed:

```python
Web.click("submit-button")  # Treated as id=submit-button
```

### Best Practices

**Priority order:**

1. **ID** - Fast, unique, stable
2. **CSS Selector** - Flexible, readable
3. **XPath** - Powerful but slower
4. **Name** - Good for form elements
5. **Link Text** - Good for links
6. **Class** - Avoid if not unique

**Examples:**

✅ Good:
```python
Web.click("id=login-btn")
Web.set_text("css=#email-field")
```

❌ Avoid:
```python
Web.click("xpath=/html/body/div[3]/div[2]/button[1]")  # Fragile
Web.click("class=btn")  # Not unique
```

---

## Web Keywords

### Navigation

#### `Web.open(url)`
Open a URL in the browser.

```python
Web.open("https://example.com")
```

#### `Web.refresh()`
Refresh the current page.

```python
Web.refresh()
```

#### `Web.back()`
Navigate to previous page.

```python
Web.back()
```

#### `Web.forward()`
Navigate to next page.

```python
Web.forward()
```

---

### Element Interaction

#### `Web.click(locator, timeout=10)`
Click an element.

```python
Web.click("id=submit-button")
Web.click("css=.login-btn", timeout=5)
```

#### `Web.double_click(locator, timeout=10)`
Double-click an element.

```python
Web.double_click("id=file-item")
```

#### `Web.set_text(locator, text, timeout=10, clear_first=True)`
Type text into an input field.

```python
Web.set_text("id=username", "admin")
Web.set_text("name=email", "test@example.com", clear_first=False)
```

#### `Web.clear(locator, timeout=10)`
Clear text from an input field.

```python
Web.clear("id=search-box")
```

#### `Web.press_enter(locator, timeout=10)`
Press Enter key on an element.

```python
Web.set_text("id=search", "automation")
Web.press_enter("id=search")
```

#### `Web.submit(locator, timeout=10)`
Submit a form.

```python
Web.submit("id=login-form")
```

---

### Dropdowns

#### `Web.select_by_text(locator, text, timeout=10)`
Select dropdown option by visible text.

```python
Web.select_by_text("id=country", "United States")
```

#### `Web.select_by_value(locator, value, timeout=10)`
Select dropdown option by value attribute.

```python
Web.select_by_value("id=country", "US")
```

#### `Web.select_by_index(locator, index, timeout=10)`
Select dropdown option by index (0-based).

```python
Web.select_by_index("id=country", 0)  # First option
```

---

### Checkboxes & Radio Buttons

#### `Web.check(locator, timeout=10)`
Check a checkbox (if not already checked).

```python
Web.check("id=terms-checkbox")
```

#### `Web.uncheck(locator, timeout=10)`
Uncheck a checkbox (if checked).

```python
Web.uncheck("id=newsletter-opt-in")
```

#### `Web.is_checked(locator, timeout=10) -> bool`
Check if checkbox/radio is selected.

```python
if Web.is_checked("id=remember-me"):
    print("Remember me is checked")
```

---

### Element State

#### `Web.is_visible(locator, timeout=10) -> bool`
Check if element is visible.

```python
if Web.is_visible("id=error-message"):
    print("Error message displayed")
```

#### `Web.is_enabled(locator, timeout=10) -> bool`
Check if element is enabled.

```python
if Web.is_enabled("id=submit-btn"):
    Web.click("id=submit-btn")
```

#### `Web.wait_for_element(locator, timeout=10)`
Wait for element to be present.

```python
Web.wait_for_element("css=.loading-spinner")
```

#### `Web.wait_for_visible(locator, timeout=10)`
Wait for element to be visible.

```python
Web.wait_for_visible("id=success-message", timeout=15)
```

#### `Web.wait_for_invisible(locator, timeout=10)`
Wait for element to become invisible.

```python
Web.wait_for_invisible("css=.loading-spinner", timeout=30)
```

---

### Element Properties

#### `Web.get_text(locator, timeout=10) -> str`
Get visible text from element.

```python
message = Web.get_text("id=notification")
assert message == "Login successful"
```

#### `Web.get_attribute(locator, attribute, timeout=10) -> str`
Get attribute value from element.

```python
href = Web.get_attribute("id=download-link", "href")
class_name = Web.get_attribute("id=submit-btn", "class")
```

#### `Web.get_value(locator, timeout=10) -> str`
Get value from input field.

```python
email = Web.get_value("id=email-field")
```

---

### Alerts

#### `Web.accept_alert()`
Accept browser alert.

```python
Web.click("id=delete-btn")
Web.accept_alert()
```

#### `Web.dismiss_alert()`
Dismiss browser alert.

```python
Web.dismiss_alert()
```

#### `Web.get_alert_text() -> str`
Get alert message text.

```python
alert_text = Web.get_alert_text()
assert "Are you sure?" in alert_text
```

---

### Windows & Frames

#### `Web.switch_to_frame(locator, timeout=10)`
Switch to iframe.

```python
Web.switch_to_frame("id=payment-iframe")
Web.set_text("id=card-number", "4111111111111111")
Web.switch_to_default()
```

#### `Web.switch_to_default()`
Switch back to main content.

```python
Web.switch_to_default()
```

#### `Web.switch_to_window(index)`
Switch to browser window by index.

```python
Web.switch_to_window(1)  # Switch to second window
```

---

### Scrolling

#### `Web.scroll_to_element(locator, timeout=10)`
Scroll element into view.

```python
Web.scroll_to_element("id=footer-section")
```

#### `Web.scroll_to_bottom()`
Scroll to bottom of page.

```python
Web.scroll_to_bottom()
```

---

### JavaScript Execution

#### `Web.execute_script(script, *args)`
Execute JavaScript code.

```python
Web.execute_script("window.scrollTo(0, 500)")
Web.execute_script("arguments[0].click()", element)
```

---

### Screenshots

#### `Web.take_screenshot(filepath)`
Capture screenshot.

```python
Web.take_screenshot("screenshots/login_page.png")
```

---

### Driver Control

#### `Web.close_browser()`
Close current browser window.

```python
Web.close_browser()
```

#### `Web.quit()`
Close all browser windows and quit driver.

```python
Web.quit()
```

---

## Writing Test Cases

### Python Test Case Example

```python
from orbs.keyword.web import Web

def test_user_login():
    """Test user login flow"""
    
    # Navigate to login page
    Web.open("https://app.example.com/login")
    
    # Enter credentials
    Web.set_text("id=email", "test@example.com")
    Web.set_text("id=password", "SecurePass123")
    
    # Submit form
    Web.click("id=login-button")
    
    # Wait for dashboard
    Web.wait_for_visible("id=dashboard", timeout=10)
    
    # Verify success
    welcome_msg = Web.get_text("css=.welcome-message")
    assert "Welcome back" in welcome_msg
    
    print("✅ Login test passed")

def test_user_logout():
    """Test user logout"""
    
    Web.click("id=user-menu")
    Web.click("link=Logout")
    
    # Verify redirect to login
    Web.wait_for_visible("id=login-button")
    
    print("✅ Logout test passed")
```

### Test Suite Example

`testsuites/login.yml`:

```yaml
name: Login Test Suite
description: End-to-end login tests

testcases:
  - path: testcases/login/test_user_login
    enable: true
  - path: testcases/login/test_user_logout
    enable: false
```

Run:

```bash
orbs run testsuites/login.yml
```

---

## BDD with Features

### Create Feature

```bash
orbs create-feature user_authentication
```

Edit `include/features/user_authentication.feature`:

```gherkin
Feature: User Authentication

  Scenario: Successful login with valid credentials
    Given I am on the login page
    When I enter email "test@example.com"
    And I enter password "SecurePass123"
    And I click the login button
    Then I should see the dashboard

  Scenario: Failed login with invalid credentials
    Given I am on the login page
    When I enter email "wrong@example.com"
    And I enter password "WrongPass"
    And I click the login button
    Then I should see error message "Invalid credentials"
```

### Generate Steps

```bash
orbs implement-feature user_authentication
```

Edit `include/steps/user_authentication_steps.py`:

```python
from behave import given, when, then
from orbs.keyword.web import Web

@given('I am on the login page')
def step_impl(context):
    Web.open("https://app.example.com/login")

@when('I enter email "{email}"')
def step_impl(context, email):
    Web.set_text("id=email", email)

@when('I enter password "{password}"')
def step_impl(context, password):
    Web.set_text("id=password", password)

@when('I click the login button')
def step_impl(context):
    Web.click("id=login-button")

@then('I should see the dashboard')
def step_impl(context):
    Web.wait_for_visible("id=dashboard", timeout=10)
    assert Web.is_visible("id=dashboard")

@then('I should see error message "{message}"')
def step_impl(context, message):
    error_text = Web.get_text("css=.error-message")
    assert message in error_text
```

### Run Feature

```bash
orbs run include/features/user_authentication.feature
```

---

## Best Practices

### 1. Use Page Object Pattern

Create reusable page classes:

```python
# pages/login_page.py
from orbs.keyword.web import Web

class LoginPage:
    URL = "https://app.example.com/login"
    
    # Locators
    EMAIL_FIELD = "id=email"
    PASSWORD_FIELD = "id=password"
    LOGIN_BUTTON = "id=login-button"
    ERROR_MESSAGE = "css=.error-message"
    
    @staticmethod
    def open():
        Web.open(LoginPage.URL)
    
    @staticmethod
    def login(email, password):
        Web.set_text(LoginPage.EMAIL_FIELD, email)
        Web.set_text(LoginPage.PASSWORD_FIELD, password)
        Web.click(LoginPage.LOGIN_BUTTON)
    
    @staticmethod
    def get_error_message():
        return Web.get_text(LoginPage.ERROR_MESSAGE)
```

Use in tests:

```python
from pages.login_page import LoginPage

def test_login():
    LoginPage.open()
    LoginPage.login("test@example.com", "password123")
    # assertions...
```

### 2. Explicit Waits

Always use timeouts for stability:

```python
Web.wait_for_visible("id=results", timeout=15)
Web.click("id=submit", timeout=10)
```

### 3. Meaningful Assertions

```python
# ❌ Not helpful
assert Web.is_visible("id=message")

# ✅ Clear failure message
message = Web.get_text("id=message")
assert message == "Success", f"Expected 'Success', got '{message}'"
```

### 4. Clean Up Resources

Use test fixtures or teardown:

```python
def test_example():
    try:
        Web.open("https://example.com")
        # test logic
    finally:
        Web.quit_browser()
```

### 5. Environment-Specific URLs

Use environment variables:

```python
from orbs.config import config
BASE_URL = config.get("BASE_URL", "https://staging.example.com")
Web.open(f"{BASE_URL}/login")
```

---

## Troubleshooting

### Element Not Found

**Symptom:** `NoSuchElementException`

**Solutions:**
* Increase timeout: `Web.click("id=btn", timeout=15)`
* Verify locator in browser DevTools
* Wait for element: `Web.wait_for_element("id=btn")`
* Check if element is in iframe

### Element Not Clickable

**Symptom:** `ElementClickInterceptedException`

**Solutions:**
* Scroll to element: `Web.scroll_to_element("id=btn")`
* Wait for overlay to disappear: `Web.wait_for_invisible("css=.loading")`
* Use JavaScript click: `Web.execute_script("arguments[0].click()", element)`

### Stale Element

**Symptom:** `StaleElementReferenceException`

**Solutions:**
* Orbs handles this automatically with retry logic
* Avoid storing element references
* Re-find element after page changes

### Browser Not Starting

**Symptom:** WebDriver errors

**Solutions:**
* Verify driver installation: `chromedriver --version`
* Update driver to match browser version
* Check `settings/browser.properties` configuration
* Try headless mode for CI environments

### Slow Tests

**Solutions:**
* Use headless mode: `headless=true`
* Reduce unnecessary waits
* Run in parallel (test suite collection level)
* Optimize locators (prefer ID, CSS over XPath)

---

## Next Steps

* [Mobile Testing Guide](mobile-testing.md)
* [API Testing Guide](api-testing.md)
* [Spy Tool Usage](spy.md)
* [Architecture Overview](architecture.md)
