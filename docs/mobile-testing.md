# Mobile Testing with Orbs

Complete guide to Android mobile automation using Orbs and Appium.

---

## Table of Contents

* [Introduction](#introduction)
* [Prerequisites](#prerequisites)
* [Quick Start](#quick-start)
* [Configuration](#configuration)
* [Mobile Keywords](#mobile-keywords)
* [Writing Test Cases](#writing-test-cases)
* [Device Management](#device-management)
* [Best Practices](#best-practices)
* [Troubleshooting](#troubleshooting)

---

## Introduction

Orbs provides mobile automation capabilities through **Appium** integration, supporting Android devices and emulators. The framework handles:

* **Automatic Appium server management** - Starts server if not running
* **Device detection and selection** - Interactive device picker
* **Thread-safe execution** - Parallel mobile test support
* **Smart element waiting** - Automatic waits with retries
* **Unified API** - Similar to web automation for easy learning

---

## Prerequisites

### System Requirements

* **Operating System:** Windows, macOS, or Linux
* **Node.js:** v14+ (installed automatically via `orbs setup android`)
* **npm:** Latest version
* **Java JDK:** 8 or higher
* **Android SDK:** Android Studio or command-line tools

### Environment Variables

Add to system PATH:

**Windows:**
```
JAVA_HOME=C:\Program Files\Java\jdk-11.0.x
ANDROID_HOME=C:\Users\<username>\AppData\Local\Android\Sdk

PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\tools
```

**Mac/Linux:**
```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-11.jdk/Contents/Home
export ANDROID_HOME=~/Library/Android/sdk
export PATH=$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/tools:$PATH
```

---

## Quick Start

### 1. Setup Android Environment

```bash
orbs setup android
```

This command will:
* ✅ Install Node.js (if not present)
* ✅ Install Appium globally
* ✅ Install Appium UIAutomator2 driver
* ✅ Verify all installations

### 2. Initialize Project

```bash
orbs init mobile-automation
cd mobile-automation
```

### 3. Connect Device

Connect Android device via USB or start emulator:

```bash
# Check connected devices
adb devices

# Start emulator (if using AVD)
emulator -avd Pixel_4_API_30
```

### 4. Select Device

```bash
orbs select-device
```

Interactive menu:
```
? Select device: 
  emulator-5554
❯ R58M40ABCDE
  
✅ Updated deviceName=R58M40ABCDE in settings/appium.properties
```

### 5. Configure Appium

Edit `settings/appium.properties`:

```properties
# Device configuration
deviceName=R58M40ABCDE
platformName=Android
platformVersion=12.0

# App configuration
appPackage=com.example.app
appActivity=.MainActivity

# Or use app file path
# app=/path/to/app.apk

# Appium server
appium_url=http://localhost:4723/wd/hub

# Additional capabilities
automationName=UiAutomator2
noReset=true
fullReset=false
```

### 6. Create Test Case

```bash
orbs create-testcase android_login
```

Edit `testcases/android_login.py`:

```python
from orbs.keyword.mobile import Mobile

def test_android_login():
    """Test Android app login"""
    
    # Wait for app to load
    Mobile.wait_for_element("id=com.example.app:id/username", timeout=10)
    
    # Enter credentials
    Mobile.set_text("id=com.example.app:id/username", "testuser")
    Mobile.set_text("id=com.example.app:id/password", "password123")
    
    # Click login
    Mobile.tap("id=com.example.app:id/login_button")
    
    # Verify home screen
    Mobile.wait_for_element("id=com.example.app:id/home_screen", timeout=10)
    assert Mobile.element_visible("id=com.example.app:id/home_screen")
    
    print("✅ Android login test passed")
```

### 7. Run Test

```bash
orbs run testsuites/login.yml --platform=android
```

---

## Configuration

### Appium Properties

Location: `settings/appium.properties`

#### Basic Configuration

```properties
# Required
deviceName=emulator-5554
platformName=Android
platformVersion=11.0

# App identification (choose one)
appPackage=com.android.calculator2
appActivity=com.android.calculator2.Calculator

# Or use APK file
# app=/absolute/path/to/app.apk
```

#### Advanced Capabilities

```properties
# Automation engine
automationName=UiAutomator2

# Reset behavior
noReset=true          # Don't reset app state between sessions
fullReset=false       # Don't uninstall app

# Timeouts (milliseconds)
newCommandTimeout=300000

# Performance
skipServerInstallation=true
skipDeviceInitialization=false

# Logging
printPageSourceOnFindFailure=true
```

### Appium Server Configuration

```properties
# Server URL
appium_url=http://localhost:4723/wd/hub

# Or remote server
# appium_url=http://192.168.1.100:4723/wd/hub
```

### Platform Configuration

Location: `settings/platform.properties`

```properties
default_platform=android
```

---

## Mobile Keywords

### App Control

#### `Mobile.launch(id=None, activity=None, reset=False)`
Launch an application with optional package ID and activity.

```python
# Launch from config
Mobile.launch()

# Launch specific app
Mobile.launch("com.android.chrome", "com.google.android.apps.chrome.Main")

# Launch with reset
Mobile.launch("com.swaglabsmobileapp", ".MainActivity", reset=True)

# Keyword args
Mobile.launch(id="com.android.chrome", activity=".Main", reset=True)
```

#### `Mobile.launch_and_install(apk, id=None, activity=None, reset=False)`
Install APK and launch the application.

```python
# Install and launch
Mobile.launch_and_install("/apps/myapp.apk")

# Install with specific launch params
Mobile.launch_and_install(
    apk="/apps/chrome.apk",
    id="com.android.chrome",
    activity=".Main",
    reset=True
)
```

#### `Mobile.activate_app(bundle_id)`
Activate app by bundle ID.

```python
Mobile.activate_app("com.android.chrome")
```

#### `Mobile.terminate_app(bundle_id)`
Terminate app by bundle ID.

```python
Mobile.terminate_app("com.android.chrome")
```

---

### Element Interaction

#### `Mobile.tap(locator, timeout=10, retry_count=3)`
Tap on an element with retry logic.

```python
Mobile.tap("id=com.example.app:id/submit_button")
Mobile.tap("xpath=//android.widget.Button[@text='Login']")
```

#### `Mobile.set_text(locator, text, timeout=10, clear_first=True, retry_count=3)`
Enter text into an element with retry logic.

```python
Mobile.set_text("id=com.example.app:id/email", "test@example.com")
Mobile.set_text("xpath=//android.widget.EditText[@content-desc='Username']", "admin")
```

#### `Mobile.clear_text(locator, timeout=10)`
Clear text from an element.

```python
Mobile.clear_text("id=com.example.app:id/search_field")
```

#### `Mobile.long_press(locator, duration=1000, timeout=10)`
Long press on an element.

```python
Mobile.long_press("id=com.example.app:id/item", duration=2000)
```

---

### Element State

#### `Mobile.element_visible(locator, timeout=10) -> bool`
Check if element is visible.

```python
if Mobile.element_visible("id=com.example.app:id/error_message"):
    print("Error displayed")
```

#### `Mobile.element_exists(locator, timeout=10) -> bool`
Check if element exists.

```python
if Mobile.element_exists("id=com.example.app:id/submit"):
    Mobile.tap("id=com.example.app:id/submit")
```

#### `Mobile.wait_for_element(locator, timeout=10)`
Wait for element to be present.

```python
Mobile.wait_for_element("id=com.example.app:id/loading", timeout=30)
```

#### `Mobile.wait_for_visible(locator, timeout=10)`
Wait for element to be visible.

```python
Mobile.wait_for_visible("id=com.example.app:id/success_dialog")
```

---

### Element Properties

#### `Mobile.get_text(locator, timeout=10) -> str`
Get text from element.

```python
message = Mobile.get_text("id=com.example.app:id/notification")
assert message == "Upload successful"
```

#### `Mobile.get_attribute(locator, attribute, timeout=10) -> str`
Get attribute value.

```python
enabled = Mobile.get_attribute("id=com.example.app:id/btn", "enabled")
content_desc = Mobile.get_attribute("xpath=//android.widget.Button", "content-desc")
```

---

### Gestures

#### `Mobile.swipe(start_x, start_y, end_x, end_y, duration=1000)`
Swipe gesture from start to end coordinates.

```python
# Swipe right
Mobile.swipe(100, 500, 900, 500, duration=800)

# Swipe up (scroll)
Mobile.swipe(500, 1500, 500, 500, duration=600)
```

#### `Mobile.swipe_up(start_x=None, distance=500, duration=1000)`
Swipe up from bottom of screen.

```python
Mobile.swipe_up()
Mobile.swipe_up(distance=800)
```

#### `Mobile.swipe_down(start_x=None, distance=500, duration=1000)`
Swipe down from top of screen.

```python
Mobile.swipe_down()
Mobile.swipe_down(distance=800)
```

#### `Mobile.swipe_left(start_y=None, distance=300, duration=1000)`
Swipe left.

```python
Mobile.swipe_left()
```

#### `Mobile.swipe_right(start_y=None, distance=300, duration=1000)`
Swipe right.

```python
Mobile.swipe_right()
```

#### `Mobile.scroll_to_element(locator, max_scrolls=5, direction='up')`
Scroll until element is found.

```python
Mobile.scroll_to_element("id=com.example.app:id/settings")
Mobile.scroll_to_element("accessibility_id=Submit", direction="down")
```

---

### Device Interaction

#### `Mobile.back()`
Press Android back button.

```python
Mobile.back()
```

#### `Mobile.hide_keyboard()`
Hide on-screen keyboard.

```python
Mobile.hide_keyboard()
```

---

### Screen Capture

#### `Mobile.take_screenshot(filepath)`
Capture screenshot.

```python
Mobile.take_screenshot("screenshots/login_screen.png")
```

---

### Locator Strategies

Orbs supports multiple Android locator strategies:

| Strategy | Syntax | Example |
|----------|--------|---------|
| Resource ID | `id=resource-id` | `id=com.example.app:id/button` |
| XPath | `xpath=xpath-expression` | `xpath=//android.widget.Button[@text='Login']` |
| Accessibility ID | `accessibility_id=content-desc` | `accessibility_id=Submit Button` |
| Class Name | `class=class-name` | `class=android.widget.Button` |
| Android UIAutomator | `android_uiautomator=UiSelector` | `android_uiautomator=new UiSelector().text("Login")` |

**Examples:**

```python
# By resource ID (most stable)
Mobile.tap("id=com.android.calculator2:id/digit_5")

# By XPath
Mobile.tap("xpath=//android.widget.Button[@text='Calculate']")

# By content-desc (accessibility)
Mobile.tap("accessibility_id=Submit Form")

# By class
Mobile.tap("class=android.widget.EditText")

# By UIAutomator
Mobile.tap("android_uiautomator=new UiSelector().text('Login')")
```

---

## Writing Test Cases

### Python Test Case

```python
from orbs.keyword.mobile import Mobile

def test_calculator_addition():
    """Test calculator addition"""
    
    # Wait for app to load
    Mobile.wait_for_element("id=com.android.calculator2:id/digit_1", timeout=10)
    
    # Perform calculation: 5 + 3 = 8
    Mobile.tap("id=com.android.calculator2:id/digit_5")
    Mobile.tap("id=com.android.calculator2:id/op_add")
    Mobile.tap("id=com.android.calculator2:id/digit_3")
    Mobile.tap("id=com.android.calculator2:id/eq")
    
    # Verify result
    result = Mobile.get_text("id=com.android.calculator2:id/result")
    assert result == "8", f"Expected 8, got {result}"
    
    print("✅ Calculator test passed")

def test_form_submission():
    """Test form submission flow"""
    
    # Fill form
    Mobile.set_text("id=com.example.app:id/name", "John Doe")
    Mobile.set_text("id=com.example.app:id/email", "john@example.com")
    Mobile.hide_keyboard()
    
    # Scroll to submit button
    Mobile.scroll_to_element("id=com.example.app:id/submit")
    
    # Submit form
    Mobile.tap("id=com.example.app:id/submit")
    
    # Wait for confirmation
    Mobile.wait_for_visible("id=com.example.app:id/success_message", timeout=10)
    
    # Verify message
    message = Mobile.get_text("id=com.example.app:id/success_message")
    assert "submitted successfully" in message.lower()
    
    print("✅ Form submission test passed")
```

### Test Suite Example

`testsuites/mobile_regression.yml`:

```yaml
name: Mobile Regression Suite
description: Android app regression tests

testcases:
  - path: testcases/android_login/test_android_login
    enable: true
  - path: testcases/calculator/test_calculator_addition
    enable: true
  - path: testcases/forms/test_form_submission
    enable: false
```

Run:

```bash
orbs run testsuites/mobile_regression.yml --platform=android
```

---

## Device Management

### List Connected Devices

```bash
adb devices
```

Output:
```
List of devices attached
emulator-5554          device
R58M40ABCDE            device
```

### Select Device Interactively

```bash
orbs select-device
```

### Specify Device in Test Run

```bash
orbs run testsuites/mobile.yml --platform=android --deviceId=emulator-5554
```

### Multiple Device Testing

Run tests on different devices in parallel:

```bash
# Terminal 1
orbs run testsuites/suite1.yml --platform=android --deviceId=emulator-5554

# Terminal 2
orbs run testsuites/suite2.yml --platform=android --deviceId=R58M40ABCDE
```

---

## Best Practices

### 1. Use Resource IDs When Possible

✅ Stable:
```python
Mobile.tap("id=com.example.app:id/login_button")
```

❌ Fragile:
```python
Mobile.tap("xpath=/hierarchy/android.widget.FrameLayout[1]/android.widget.Button[3]")
```

### 2. Handle Keyboard

Always hide keyboard after text input:

```python
Mobile.set_text("id=email_field", "test@example.com")
Mobile.hide_keyboard()
```

### 3. Use Explicit Waits

```python
Mobile.wait_for_visible("id=success_message", timeout=15)
```

### 4. Page Object Pattern

```python
# pages/login_page.py
from orbs.keyword.mobile import Mobile

class LoginPage:
    USERNAME = "id=com.example.app:id/username"
    PASSWORD = "id=com.example.app:id/password"
    LOGIN_BTN = "id=com.example.app:id/login_button"
    
    @staticmethod
    def login(username, password):
        Mobile.set_text(LoginPage.USERNAME, username)
        Mobile.set_text(LoginPage.PASSWORD, password)
        Mobile.hide_keyboard()
        Mobile.tap(LoginPage.LOGIN_BTN)
```

### 5. Error Handling

```python
def test_with_retry():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            Mobile.tap("id=unstable_element")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 1}/{max_retries}")
            time.sleep(2)
```

### 6. Screenshot on Failure

```python
def test_login():
    try:
        Mobile.tap("id=login_button")
        # test logic
    except Exception as e:
        Mobile.take_screenshot("screenshots/failure.png")
        raise
```

---

## Troubleshooting

### Appium Server Not Starting

**Check installation:**
```bash
appium --version
```

**Reinstall:**
```bash
orbs setup android
```

**Start manually:**
```bash
appium --address 0.0.0.0 --port 4723
```

### ADB Not Found

**Verify PATH:**
```bash
adb version
```

**Add to PATH (Windows):**
```
C:\Users\<username>\AppData\Local\Android\Sdk\platform-tools
```

### Device Not Detected

**Check USB debugging:**
* Enable Developer Options on device
* Enable USB Debugging
* Accept debugging authorization prompt

**Verify connection:**
```bash
adb devices
```

**Restart ADB:**
```bash
adb kill-server
adb start-server
```

### Element Not Found

**Solutions:**
* Increase timeout
* Use Appium Inspector to verify locators
* Wait for app to load completely
* Check if element is in different activity

### Session Creation Failed

**Check capabilities:**
* Verify `appPackage` and `appActivity` are correct
* Ensure app is installed: `adb shell pm list packages | grep example`
* Check platform version matches device

**View logs:**
```bash
adb logcat
```

### Slow Test Execution

**Optimize:**
* Reduce unnecessary waits
* Use `noReset=true` to skip reinstall
* Disable animations on device
* Use faster emulator (x86 images with HAXM)

---

## Advanced Topics

### Device Information

```python
# Get screen size
size = Mobile.get_device_size()
print(f"Width: {size['width']}, Height: {size['height']}")

# Get/Set orientation
orientation = Mobile.get_orientation()  # PORTRAIT or LANDSCAPE
Mobile.set_orientation("LANDSCAPE")
```

### Driver Management

```python
# Check driver status
status = Mobile.get_driver_status()

# Reset driver between tests
Mobile.reset_driver()

# Quit session
Mobile.quit()
```

### Parallel Execution

Run multiple test suites in parallel using different devices:

```bash
# Use orchestration tool or CI/CD
pytest -n 2 --deviceId=emulator-5554,R58M40ABCDE
```

---

## Next Steps

* [Web Testing Guide](web-testing.md)
* [Spy Tool for Mobile](spy.md)
* [API Testing](api-testing.md)
* [Architecture Overview](architecture.md)
