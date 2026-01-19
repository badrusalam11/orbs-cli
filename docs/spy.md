# Spy Tool Usage Guide

Interactive element inspection and locator capture for web and mobile testing.

---

## Table of Contents

* [Introduction](#introduction)
* [Web Spy](#web-spy)
* [Mobile Spy](#mobile-spy)
* [Captured Element Format](#captured-element-format)
* [Using Captured Elements](#using-captured-elements)
* [Best Practices](#best-practices)
* [Troubleshooting](#troubleshooting)

---

## Introduction

The **Orbs Spy** is an interactive tool for inspecting and capturing element locators from web pages and mobile apps. It helps you:

* **Inspect elements** interactively without writing code
* **Capture multiple locator strategies** (ID, XPath, CSS, etc.)
* **Generate test-ready code snippets** automatically
* **Build object repositories** for reusable elements
* **Speed up test development** by avoiding manual locator creation

---

## Web Spy

### Starting Web Spy

```bash
orbs spy --web --url=https://example.com
```

**With protocol auto-detection:**
```bash
# Automatically adds https://
orbs spy --web --url=google.com
```

### How It Works

1. **Launches Chrome browser** with spy listeners injected
2. **Navigate and interact** with the page normally
3. **Press `Ctrl + ` `** (backtick) while hovering over any element
4. **Element details are captured** and saved automatically
5. **Press `Ctrl + C`** in terminal to stop spy session

### Capturing Elements

#### Step-by-Step

1. **Start spy session:**
   ```bash
   orbs spy --web --url=https://google.com
   ```

2. **Browser opens** with the target URL

3. **Hover over element** you want to capture (e.g., search box)

4. **Press `Ctrl + ` `** (backtick key, usually below ESC)

5. **Console shows capture:**
   ```
   [SPY] Element captured: input[name='q']
   [SPY] Saved to: object_repository/SearchBox.xml
   ```

6. **Repeat for more elements**

7. **Stop when done:**
   Press `Ctrl + C` in the terminal

### Captured Locator Strategies

The spy automatically captures multiple locator strategies:

* **ID** - Element's id attribute
* **Name** - Element's name attribute
* **CSS Selector** - Generated CSS selector
* **XPath** - Generated XPath expression
* **Class Name** - Element's class attribute
* **Tag Name** - HTML tag
* **Link Text** - For `<a>` elements
* **Attributes** - All element attributes

### Example Captured Element

After capturing Google's search box, you get:

```xml
<!-- object_repository/SearchBox.xml -->
<WebElementEntity>
  <name>SearchBox</name>
  <tag>input</tag>
  <selectorCollection>
    <entry>
      <key>ID</key>
      <value>APjFqb</value>
    </entry>
    <entry>
      <key>NAME</key>
      <value>q</value>
    </entry>
    <entry>
      <key>CSS</key>
      <value>input[name='q']</value>
    </entry>
    <entry>
      <key>XPATH</key>
      <value>//input[@name='q']</value>
    </entry>
    <entry>
      <key>CLASS</key>
      <value>gLFyf</value>
    </entry>
  </selectorCollection>
  <attributes>
    <name>q</name>
    <type>text</type>
    <autocomplete>off</autocomplete>
    <title>Search</title>
  </attributes>
</WebElementEntity>
```

### Dynamic Page Handling

The spy **automatically re-injects listeners** when:

* You navigate to a new page
* Page content is dynamically updated
* Listeners are removed by JavaScript

This ensures continuous capture across single-page apps (SPAs) and multi-page workflows.

### Configuration

Default output directory: `object_repository/`

To change output location:

```python
from orbs.spy.web import WebSpyRunner

spy = WebSpyRunner(
    url="https://example.com",
    output_dir="custom_elements"
)
spy.start()
```

---

## Mobile Spy

### Starting Mobile Spy

```bash
orbs spy --mobile
```

### Prerequisites

1. **Appium installed:**
   ```bash
   orbs setup android
   ```

2. **Device connected:**
   ```bash
   adb devices
   ```

3. **Device selected:**
   ```bash
   orbs select-device
   ```

4. **App configured** in `settings/appium.properties`

### How It Works

1. **Launches Appium session** with your app
2. **Displays app on screen** (or emulator)
3. **Interactive element inspection** (implementation-specific)
4. **Captures locator strategies** for Android elements
5. **Saves to object repository**

### Captured Mobile Locators

For Android elements:

* **Resource ID** - `com.example.app:id/element_id`
* **XPath** - Generated XPath
* **Accessibility ID** - Content description
* **Class Name** - Android widget class
* **Text** - Visible text
* **UIAutomator** - UiSelector expression

### Example Mobile Element

```xml
<!-- object_repository/LoginButton.xml -->
<MobileElementEntity>
  <name>LoginButton</name>
  <platform>Android</platform>
  <selectorCollection>
    <entry>
      <key>RESOURCE_ID</key>
      <value>com.example.app:id/login_button</value>
    </entry>
    <entry>
      <key>XPATH</key>
      <value>//android.widget.Button[@text='Login']</value>
    </entry>
    <entry>
      <key>ACCESSIBILITY_ID</key>
      <value>Login Button</value>
    </entry>
    <entry>
      <key>CLASS</key>
      <value>android.widget.Button</value>
    </entry>
    <entry>
      <key>TEXT</key>
      <value>Login</value>
    </entry>
  </selectorCollection>
</MobileElementEntity>
```

---

## Captured Element Format

### XML Structure

```xml
<WebElementEntity>
  <name>ElementName</name>
  <tag>html_tag</tag>
  <selectorCollection>
    <entry>
      <key>STRATEGY_NAME</key>
      <value>locator_value</value>
    </entry>
    <!-- More strategies... -->
  </selectorCollection>
  <attributes>
    <attribute_name>attribute_value</attribute_name>
  </attributes>
</WebElementEntity>
```

### Loading Captured Elements

Create a helper to parse XML:

```python
import xml.etree.ElementTree as ET

def load_element(name):
    """Load element from object repository"""
    path = f"object_repository/{name}.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    
    selectors = {}
    for entry in root.find("selectorCollection").findall("entry"):
        key = entry.find("key").text
        value = entry.find("value").text
        selectors[key] = value
    
    return selectors

# Usage
login_btn = load_element("LoginButton")
print(login_btn["CSS"])  # Get CSS selector
print(login_btn["XPATH"])  # Get XPath
```

---

## Using Captured Elements

### Direct Usage in Tests

After capturing elements, use them in your tests:

```python
from orbs.keyword.web import Web

def test_google_search():
    """Test using spy-captured elements"""
    
    Web.open("https://google.com")
    
    # Use captured locators
    Web.type_text("name=q", "Orbs automation")
    Web.press_enter("name=q")
    
    # Verify results
    Web.wait_for_element("id=search", timeout=10)
```

### Object Repository Pattern

Create a page object using captured elements:

```python
# pages/google_page.py
class GooglePage:
    # Locators from spy capture
    SEARCH_BOX = "name=q"
    SEARCH_BUTTON = "css=input[value='Google Search']"
    RESULTS_DIV = "id=search"
    
    @staticmethod
    def search(query):
        from orbs.keyword.web import Web
        Web.type_text(GooglePage.SEARCH_BOX, query)
        Web.press_enter(GooglePage.SEARCH_BOX)
    
    @staticmethod
    def wait_for_results():
        from orbs.keyword.web import Web
        Web.wait_for_element(GooglePage.RESULTS_DIV, timeout=10)
```

Use in test:

```python
from pages.google_page import GooglePage

def test_search():
    GooglePage.search("automation framework")
    GooglePage.wait_for_results()
```

### Centralized Element Repository

```python
# repositories/elements.py
class Elements:
    """Central element repository"""
    
    # Login page
    LOGIN_EMAIL = "id=email"
    LOGIN_PASSWORD = "id=password"
    LOGIN_BUTTON = "id=login-btn"
    
    # Dashboard
    DASHBOARD_WELCOME = "css=.welcome-message"
    DASHBOARD_MENU = "id=main-menu"
    
    # Forms
    FORM_NAME = "name=fullname"
    FORM_SUBMIT = "css=button[type='submit']"
```

---

## Best Practices

### 1. Name Elements Descriptively

✅ Good:
```
LoginButton.xml
SearchInputField.xml
UserProfileDropdown.xml
```

❌ Avoid:
```
Element1.xml
Button.xml
Input.xml
```

### 2. Prefer Stable Locators

From spy results, choose in this order:

1. **ID** (most stable)
2. **Name** (good for forms)
3. **CSS Selector** (flexible, readable)
4. **XPath** (powerful but fragile)
5. **Class** (avoid if not unique)

### 3. Organize by Page/Module

```
object_repository/
├── login/
│   ├── EmailField.xml
│   ├── PasswordField.xml
│   └── LoginButton.xml
├── dashboard/
│   ├── WelcomeMessage.xml
│   └── UserMenu.xml
└── forms/
    └── SubmitButton.xml
```

### 4. Verify Captured Locators

Always test captured locators in your automation:

```python
def verify_locator():
    Web.open("https://example.com")
    
    # Test each strategy
    assert Web.is_visible("id=login-btn")
    assert Web.is_visible("css=.login-button")
    
    print("✅ Locators verified")
```

### 5. Update When UI Changes

When UI updates:

1. Re-capture affected elements
2. Update your object repository
3. Re-run tests to verify

### 6. Document Custom Attributes

Add notes to captured XML:

```xml
<WebElementEntity>
  <name>SubmitButton</name>
  <!-- Note: This button is disabled until form is valid -->
  <selectorCollection>
    ...
  </selectorCollection>
</WebElementEntity>
```

---

## Troubleshooting

### Web Spy Not Capturing

**Symptom:** Pressing `Ctrl + ` ` does nothing

**Solutions:**
* Check browser console for JavaScript errors
* Ensure page has fully loaded
* Try refreshing the page
* Check if browser blocked script injection
* Verify Chrome version compatibility

### Listeners Not Working After Navigation

**Symptom:** Capture works on first page but not after clicking links

**Solutions:**
* Spy should auto-reinject listeners (check console)
* If not working, restart spy session
* For SPAs, ensure listeners are re-injected after route changes

### Mobile Spy Not Starting

**Symptom:** `orbs spy --mobile` fails

**Solutions:**
* Verify Appium installation: `appium --version`
* Check device connection: `adb devices`
* Verify `settings/appium.properties` configuration
* Ensure app is installed on device
* Check Appium logs for errors

### Element Not Found in XML

**Symptom:** Captured XML missing expected attributes

**Solutions:**
* Element may have been dynamically generated
* Try re-capturing with element fully loaded
* Check browser DevTools to verify attributes exist
* Some attributes may be set by JavaScript after page load

### Output Directory Not Created

**Symptom:** `object_repository/` folder missing

**Solutions:**
* Ensure write permissions in current directory
* Manually create directory: `mkdir object_repository`
* Check disk space
* Verify path in spy configuration

---

## Advanced Usage

### Custom Element Naming

Automatically rename captured elements:

```python
from orbs.spy.web import WebSpyRunner

class CustomSpyRunner(WebSpyRunner):
    def save_element(self, element_data):
        # Custom naming logic
        tag = element_data.get('tag')
        name = element_data.get('name', 'Unknown')
        
        filename = f"{tag}_{name}.xml"
        # Save logic...
```

### Batch Element Capture

Capture multiple elements in sequence:

```python
# Create a list of elements to capture
elements_to_capture = [
    "Login email field",
    "Login password field",
    "Login submit button",
    "Remember me checkbox"
]

# Start spy and capture each one
# (Manual process - hover and press Ctrl+` for each)
```

### Integration with CI/CD

Spy is primarily for local development. For CI/CD:

1. **Capture elements locally** during test development
2. **Commit object repository** to version control
3. **Use captured locators** in automated tests
4. **Re-capture when UI changes**

---

## Next Steps

* [Web Testing Guide](web-testing.md) - Use captured elements in web tests
* [Mobile Testing Guide](mobile-testing.md) - Use captured elements in mobile tests
* [CLI Reference](cli-reference.md) - All spy command options
* [Best Practices](philosophy.md) - Framework philosophy and patterns
