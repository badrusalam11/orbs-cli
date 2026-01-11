# Orbs CLI Reference

Complete reference for all Orbs command-line interface commands.

---

## Table of Contents

* [Installation](#installation)
* [Global Options](#global-options)
* [Commands](#commands)
  * [setup android](#setup-android)
  * [init](#init)
  * [create-testsuite](#create-testsuite)
  * [create-testcase](#create-testcase)
  * [create-feature](#create-feature)
  * [create-step](#create-step)
  * [create-listener](#create-listener)
  * [implement-feature](#implement-feature)
  * [run](#run)
  * [select-device](#select-device)
  * [select-platform](#select-platform)
  * [spy](#spy)
  * [serve](#serve)

---

## Installation

```bash
pip install orbs
```

Verify installation:

```bash
orbs --help
```

---

## Global Options

All Orbs commands support standard Typer options:

```bash
--help          Show help message and exit
--version       Show version number
```

---

## Commands

### setup android

**Description:**  
Install required dependencies for Android mobile testing (Node.js, npm, Appium, Appium UIAutomator2 driver).

**Usage:**
```bash
orbs setup android
```

**What it does:**

1. Checks if Node.js and npm are installed
2. If not found, automatically downloads and installs Node.js (Windows) or uses package manager (Linux/Mac)
3. Installs Appium globally via npm
4. Installs Appium UIAutomator2 driver
5. Verifies all installations

**Platform support:**
* ✅ Windows (automatic MSI installer)
* ✅ macOS (via Homebrew if available)
* ✅ Linux (via apt if available)

**Example output:**
```
✅ npm detected
⬇️ Installing appium...
✅ appium installed
⬇️ Installing appium-uiautomator2-driver...
✅ appium-uiautomator2-driver installed
✅ All mobile dependencies are ready
```

**Notes:**
* Requires internet connection
* May require administrator/sudo privileges
* Only needs to be run once per machine

---

### init

**Description:**  
Initialize a new Orbs project with proper directory structure and template files.

**Usage:**
```bash
orbs init <project_name>

# Or initialize in current directory
orbs init .
```

**Arguments:**
* `project_name` - Name of the project (creates a new folder) or `.` for current directory

**Example:**
```bash
orbs init my-automation-project
cd my-automation-project
```

**Generated structure:**
```
my-automation-project/
├── include/
│   ├── environment.py
│   ├── features/
│   └── steps/
├── listeners/
├── settings/
│   ├── browser.properties
│   ├── mobile.properties
│   ├── platform.properties
│   └── server.properties
├── testcases/
│   └── login.py
├── testsuites/
│   ├── login.py
│   └── login.yml
├── testsuite_collections/
├── __init__.py
├── Dockerfile
├── main.py
├── pytest.ini
├── README.md
└── requirements.txt
```

**Notes:**
* Will not overwrite existing folders
* Creates a ready-to-run project with sample login test
* Includes Docker configuration for containerized execution

---

### create-testsuite

**Description:**  
Generate a new test suite with YAML configuration and Python runner files.

**Usage:**
```bash
orbs create-testsuite <name>
```

**Arguments:**
* `name` - Name of the test suite

**Example:**
```bash
orbs create-testsuite regression
```

**Generated files:**
* `testsuites/regression.yml` - Test suite configuration
* `testsuites/regression.py` - Python runner (optional)

**regression.yml template:**
```yaml
name: regression
description: Test suite for regression

testcases: []

platform: chrome
```

**When to use:**
* Grouping related test cases
* Creating environment-specific test runs
* Organizing regression, smoke, or integration suites

---

### create-testcase

**Description:**  
Generate a new test case Python file.

**Usage:**
```bash
orbs create-testcase <name>
```

**Arguments:**
* `name` - Name of the test case

**Example:**
```bash
orbs create-testcase checkout_flow
```

**Generated file:**
* `testcases/checkout_flow.py`

**Template:**
```python
def test_checkout_flow():
    """
    Test case: checkout_flow
    """
    # TODO: Implement test logic
    pass
```

**Context-aware:**
* If run from `testcases/` subdirectory, creates file there
* Otherwise creates in `testcases/` at project root

---

### create-feature

**Description:**  
Generate a new BDD feature file using Gherkin syntax.

**Usage:**
```bash
orbs create-feature <name>
```

**Arguments:**
* `name` - Name of the feature

**Example:**
```bash
orbs create-feature user_registration
```

**Generated file:**
* `include/features/user_registration.feature`

**Template:**
```gherkin
Feature: user_registration

  Scenario: user_registration scenario
    Given a precondition
    When an action occurs
    Then verify the outcome
```

**Next steps:**
1. Edit the feature file with your actual scenarios
2. Run `orbs implement-feature user_registration` to generate step definitions

---

### create-step

**Description:**  
Generate a new step definition file for BDD tests.

**Usage:**
```bash
orbs create-step <name>
```

**Arguments:**
* `name` - Name of the step file

**Example:**
```bash
orbs create-step authentication
```

**Generated file:**
* `include/steps/authentication.py`

**Template:**
```python
from behave import given, when, then

# Add your step definitions here
```

---

### create-listener

**Description:**  
Generate a new test listener for hooks and custom reporting.

**Usage:**
```bash
orbs create-listener <name>
```

**Arguments:**
* `name` - Name of the listener

**Example:**
```bash
orbs create-listener screenshot_on_failure
```

**Generated file:**
* `listeners/screenshot_on_failure.py`

**Use cases:**
* Custom reporting
* Screenshot capture
* Performance metrics
* Integration with third-party tools

---

### implement-feature

**Description:**  
Generate step definition boilerplate from an existing feature file.

**Usage:**
```bash
orbs implement-feature <name>
```

**Arguments:**
* `name` - Name of the feature (without .feature extension)

**Example:**
```bash
orbs create-feature login
# Edit include/features/login.feature
orbs implement-feature login
```

**What it does:**
1. Reads `include/features/<name>.feature`
2. Extracts all Given/When/Then/And steps
3. Generates step definition functions in `include/steps/<name>_steps.py`
4. Handles parameterized steps with `<param>` → `{param}` conversion

**Example feature:**
```gherkin
Feature: Login
  Scenario: Valid login
    Given I navigate to <url>
    When I enter username "<user>" and password "<pass>"
    Then I should see "<message>"
```

**Generated steps:**
```python
from behave import given, when, then

@given('I navigate to {url}')
def step_impl(context, url):
    pass

@when('I enter username "{user}" and password "{pass}"')
def step_impl(context, user, pass):
    pass

@then('I should see "{message}"')
def step_impl(context, message):
    pass
```

---

### run

**Description:**  
Execute test suites, test cases, or feature files.

**Usage:**
```bash
orbs run <target> [options]
```

**Arguments:**
* `target` - Path to test suite (.yml), test case (.py), or feature file (.feature)

**Options:**
* `--env <path>`, `-e <path>` - Load environment variables from custom .env file
* `--platform <name>`, `-p <name>` - Override platform (android, chrome, firefox, edge, safari)
* `--deviceId <id>` - Specify device ID for mobile testing

**Examples:**

Run a test suite:
```bash
orbs run testsuites/regression.yml
```

Run a specific test case:
```bash
orbs run testcases/login.py
```

Run a feature file:
```bash
orbs run include/features/checkout.feature
```

Run with custom environment:
```bash
orbs run testsuites/smoke.yml --env=.env.staging
```

Run on specific platform:
```bash
orbs run testsuites/login.yml --platform=firefox
```

Run on specific Android device:
```bash
orbs run testsuites/mobile.yml --platform=android --deviceId=emulator-5554
```

**Valid platforms:**
* **Mobile:** `android`
* **Web:** `chrome`, `firefox`, `edge`, `safari`

**Notes:**
* Platform can also be set in test suite YAML or settings/platform.properties
* CLI argument takes highest priority
* Environment file loading is optional

---

### select-device

**Description:**  
List connected Android devices and select one to update `settings/appium.properties`.

**Usage:**
```bash
orbs select-device
```

**What it does:**
1. Runs `adb devices` to list connected devices
2. Presents interactive selection menu
3. Updates `deviceName` in `settings/appium.properties`

**Example:**
```bash
orbs select-device
```

**Output:**
```
? Select device: 
  emulator-5554
❯ R58M40ABCDE
  
✅ Updated deviceName=R58M40ABCDE in settings/appium.properties
```

**Requirements:**
* ADB (Android Debug Bridge) must be in PATH
* At least one Android device/emulator connected

---

### select-platform

**Description:**  
Interactively select default platform and save to configuration.

**Usage:**
```bash
orbs select-platform
```

**What it does:**
1. Shows list of available platforms (mobile + web)
2. Saves selection to `settings/platform.properties`

**Example:**
```bash
orbs select-platform
```

**Output:**
```
? Select platform: 
  android
❯ chrome
  firefox
  edge
  
✅ Selected platform 'chrome' saved to settings/platform.properties
```

---

### spy

**Description:**  
Launch interactive element spy for web or mobile testing.

**Usage:**
```bash
# Web spy
orbs spy --web --url=<url>

# Mobile spy (Android)
orbs spy --mobile
```

**Options:**
* `--web` - Launch web spy mode
* `--mobile` - Launch mobile spy mode
* `--url <url>` - Target URL for web spy (required for --web)

**Examples:**

Web spy:
```bash
orbs spy --web --url=https://google.com
```

Mobile spy:
```bash
orbs spy --mobile
```

**Features:**
* Inspect elements interactively
* Capture locators (CSS, XPath, ID)
* Generate test code snippets
* Real-time element highlighting

**Keyboard shortcuts (Web):**
* `Ctrl + ` ` - Capture element under cursor
* `Ctrl + C` - Stop spy session

**See:** [Spy Documentation](spy.md) for detailed usage

---

### serve

**Description:**  
Start Orbs REST API server for remote test execution.

**Usage:**
```bash
orbs serve [--port <port>]
```

**Options:**
* `--port <port>` - Custom port number (default: 5006)

**Example:**
```bash
orbs serve --port 8080
```

**API Endpoints:**

**GET /testsuites** - List all available test suites
```bash
curl http://localhost:5006/testsuites
```

**POST /run** - Execute a test
```bash
curl -X POST http://localhost:5006/run \
  -H "Content-Type: application/json" \
  -d '{
    "target": "testsuites/regression.yml",
    "platform": "chrome"
  }'
```

**GET /status** - Check execution status
```bash
curl http://localhost:5006/status
```

**Use cases:**
* CI/CD integration
* Remote test execution
* Test orchestration
* Integration with custom dashboards

---

## Command Cheat Sheet

| Task | Command |
|------|---------|
| Setup Android environment | `orbs setup android` |
| Create new project | `orbs init myproject` |
| Create test suite | `orbs create-testsuite smoke` |
| Create test case | `orbs create-testcase login` |
| Create BDD feature | `orbs create-feature checkout` |
| Generate step definitions | `orbs implement-feature checkout` |
| Run test suite | `orbs run testsuites/smoke.yml` |
| Run on Firefox | `orbs run testsuites/smoke.yml --platform=firefox` |
| Select Android device | `orbs select-device` |
| Select default platform | `orbs select-platform` |
| Web element spy | `orbs spy --web --url=https://app.com` |
| Mobile element spy | `orbs spy --mobile` |
| Start API server | `orbs serve` |

---

## Best Practices

### 1. Project Initialization
Always start with `orbs init` to ensure proper structure

### 2. Naming Conventions
* Use snake_case for file names: `user_login.py`
* Use descriptive names: `checkout_flow` not `test1`

### 3. Platform Configuration
Set default platform in `settings/platform.properties` to avoid repeating `--platform` flag

### 4. Environment Management
Use separate `.env` files for different environments:
* `.env.dev`
* `.env.staging`
* `.env.production`

### 5. Mobile Testing
Run `orbs select-device` before mobile test execution to ensure correct device is targeted

---

## Troubleshooting

### Command not found

```bash
# Ensure orbs is installed
pip install orbs

# Or install in development mode
pip install -e .
```

### Appium not starting

```bash
# Verify installation
appium --version

# Reinstall if needed
orbs setup android
```

### ADB not found

Add Android SDK platform-tools to PATH:

**Windows:**
```
C:\Users\<username>\AppData\Local\Android\Sdk\platform-tools
```

**Mac/Linux:**
```bash
export PATH=$PATH:~/Library/Android/sdk/platform-tools
```

---

## Next Steps

* [Philosophy & Concepts](philosophy.md)
* [Web Testing Guide](web-testing.md)
* [Mobile Testing Guide](mobile-testing.md)
* [Spy Tool Usage](spy.md)
