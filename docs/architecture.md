# Orbs Architecture Overview

Technical architecture and design patterns of the Orbs automation framework.

---

## Table of Contents

* [High-Level Architecture](#high-level-architecture)
* [Core Components](#core-components)
* [Execution Flow](#execution-flow)
* [Thread Safety](#thread-safety)
* [Extension Points](#extension-points)
* [Project Structure](#project-structure)
* [Technology Stack](#technology-stack)
* [Design Patterns](#design-patterns)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Interfaces                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│     CLI      │  REST API    │  Spy Tools   │  Studio (TBD)  │
│  (Typer)     │  (FastAPI)   │  (Selenium)  │                │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
                         │
                    ┌────▼────┐
                    │  Runner │  ◄── Orchestrates execution
                    └────┬────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
  ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
  │   Web   │      │ Mobile  │      │   API   │
  │ Keyword │      │ Keyword │      │ Client  │
  └────┬────┘      └────┬────┘      └────┬────┘
       │                 │                 │
  ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
  │ Browser │      │ Appium  │      │ Requests│
  │ Factory │      │ Factory │      │ Session │
  └─────────┘      └─────────┘      └─────────┘
       │                 │                 │
  ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
  │Selenium │      │ Appium  │      │  HTTP   │
  │WebDriver│      │ Driver  │      │ Client  │
  └─────────┘      └─────────┘      └─────────┘
```

### Key Characteristics

* **Layered Architecture** - Clear separation of concerns
* **Plugin-based Extensions** - Listeners, keywords, factories
* **Thread-safe Design** - Parallel execution support
* **Multi-interface** - CLI, API, GUI access to same core
* **Configuration-driven** - YAML, properties, environment variables

---

## Core Components

### 1. Runner (`orbs.runner`)

**Purpose:** Central execution orchestrator

**Responsibilities:**
* Load test suites, cases, or features
* Determine execution mode (pytest, behave, direct)
* Manage test lifecycle
* Coordinate listeners
* Handle platform configuration

**Key Functions:**
```python
def run(target: str, platform: str = None, device_id: str = None):
    """Main entry point for test execution"""
    # 1. Parse target (suite/case/feature)
    # 2. Load configuration
    # 3. Initialize listeners
    # 4. Execute tests
    # 5. Generate reports
```

### 2. Browser Factory (`orbs.browser_factory`)

**Purpose:** Create and configure WebDriver instances

**Responsibilities:**
* Platform detection (chrome, firefox, edge, safari)
* Driver configuration from properties
* Headless mode support
* Custom options injection

**Key Functions:**
```python
def create_driver(platform: str = None) -> WebDriver:
    """Create configured browser instance"""
    # Read settings/browser.properties
    # Apply platform-specific options
    # Return initialized driver
```

### 3. Mobile Factory (`orbs.mobile_factory`)

**Purpose:** Create and configure Appium driver instances

**Responsibilities:**
* Load capabilities from settings/appium.properties
* Start Appium server if needed
* Device detection and selection
* Driver initialization

**Key Functions:**
```python
def create_driver(device_id: str = None) -> WebDriver:
    """Create configured mobile driver"""
    # Load appium.properties
    # Ensure Appium server is running
    # Initialize with capabilities
```

### 4. Thread Context (`orbs.thread_context`)

**Purpose:** Thread-local storage for driver instances and state

**Why:**
* Enables parallel test execution
* Each thread gets isolated driver
* Prevents cross-thread interference

**Implementation:**
```python
import threading

_context = threading.local()

def get_context(key: str):
    """Get thread-local value"""
    return getattr(_context, key, None)

def set_context(key: str, value):
    """Set thread-local value"""
    setattr(_context, key, value)
```

### 5. Web Keywords (`orbs.keyword.web`)

**Purpose:** High-level Selenium operations

**Responsibilities:**
* Element location and interaction
* Smart waiting and retries
* Multi-strategy locator support
* Common web operations

**Design:**
* Class methods (no instantiation needed)
* Automatic driver retrieval from thread context
* Built-in error handling

### 6. Mobile Keywords (`orbs.keyword.mobile`)

**Purpose:** High-level Appium operations

**Similar to Web Keywords but for mobile:**
* Touch gestures
* Device interactions
* Mobile-specific locators

### 7. API Client (`orbs.api_client`)

**Purpose:** HTTP request handling with logging

**Features:**
* Session-based requests
* Automatic request/response recording
* Thread-safe logging

### 8. Listener Manager (`orbs.listener_manager`)

**Purpose:** Load and execute test hooks

**Responsibilities:**
* Discover listener modules
* Execute hooks at lifecycle events
* Handle errors gracefully

**Lifecycle Events:**
* `before_suite`
* `before_test`
* `after_test`
* `after_suite`
* `on_failure`

### 9. Configuration (`orbs.config`)

**Purpose:** Centralized configuration management

**Sources (priority order):**
1. Command-line arguments
2. Environment variables
3. Property files (settings/*.properties)
4. Defaults

**Example:**
```python
from orbs.config import config

platform = config.get("platform", "chrome")
headless = config.get("headless", False)
```

### 10. Template Engine (`orbs.utils`)

**Purpose:** Generate boilerplate code from Jinja2 templates

**Used by:**
* `orbs create-testsuite`
* `orbs create-testcase`
* `orbs create-feature`
* `orbs implement-feature`

**Location:** `orbs/templates/jinja/`

---

## Execution Flow

### Web Test Execution

```
┌─────────────────┐
│ orbs run test.py│
└────────┬────────┘
         │
    ┌────▼────────────────────┐
    │ Runner.run(target)      │
    └────────┬────────────────┘
             │
    ┌────────▼───────────────┐
    │ Load configuration     │
    │ (platform, settings)   │
    └────────┬───────────────┘
             │
    ┌────────▼────────────────┐
    │ Initialize listeners    │
    │ (listeners/*.py)        │
    └────────┬────────────────┘
             │
    ┌────────▼─────────────────┐
    │ Execute: before_suite()  │
    └────────┬─────────────────┘
             │
    ┌────────▼──────────────────┐
    │ Run test function         │
    │   ├─ Web.open(url)        │
    │   ├─ Create driver        │
    │   │   (BrowserFactory)    │
    │   ├─ Store in thread ctx  │
    │   ├─ Web.click(...)       │
    │   └─ Assertions           │
    └────────┬──────────────────┘
             │
    ┌────────▼─────────────────┐
    │ Execute: after_test()    │
    └────────┬─────────────────┘
             │
    ┌────────▼──────────────────┐
    │ Close driver              │
    └────────┬──────────────────┘
             │
    ┌────────▼─────────────────┐
    │ Execute: after_suite()   │
    └────────┬─────────────────┘
             │
    ┌────────▼──────────────────┐
    │ Generate report           │
    └───────────────────────────┘
```

### BDD Feature Execution

```
┌───────────────────────────┐
│ orbs run login.feature    │
└──────────┬────────────────┘
           │
    ┌──────▼──────────────┐
    │ Runner detects .feature│
    └──────┬──────────────┘
           │
    ┌──────▼───────────────┐
    │ Call behave runner   │
    │ with feature path    │
    └──────┬───────────────┘
           │
    ┌──────▼────────────────┐
    │ Behave loads:         │
    │  - features/*.feature │
    │  - steps/*.py         │
    │  - environment.py     │
    └──────┬────────────────┘
           │
    ┌──────▼─────────────────┐
    │ before_scenario()      │
    │  (environment.py)      │
    └──────┬─────────────────┘
           │
    ┌──────▼──────────────────┐
    │ Execute scenario steps  │
    │  @given, @when, @then   │
    └──────┬──────────────────┘
           │
    ┌──────▼─────────────────┐
    │ after_scenario()       │
    │  (cleanup)             │
    └────────────────────────┘
```

---

## Thread Safety

### Problem

Multiple tests running in parallel need isolated driver instances:

```python
# Thread 1: Test on Chrome
# Thread 2: Test on Firefox
# Both running simultaneously
```

If drivers are global, they interfere with each other.

### Solution: Thread-Local Storage

Each thread gets its own driver:

```python
# orbs/thread_context.py
import threading

_context = threading.local()

def set_context(key, value):
    setattr(_context, key, value)

def get_context(key):
    return getattr(_context, key, None)
```

Usage:

```python
# Thread 1
set_context('web_driver', chrome_driver)

# Thread 2
set_context('web_driver', firefox_driver)

# Each thread retrieves its own driver
my_driver = get_context('web_driver')
```

### Web Keyword Implementation

```python
class Web:
    @classmethod
    def _get_driver(cls):
        """Get thread-local driver"""
        driver = get_context('web_driver')
        if driver is None:
            driver = BrowserFactory.create_driver()
            set_context('web_driver', driver)
        return driver
    
    @classmethod
    def click(cls, locator):
        driver = cls._get_driver()  # Thread-safe
        # ...
```

### Benefits

* ✅ Parallel execution support
* ✅ No race conditions
* ✅ Isolated test environments
* ✅ Scalable to any number of threads

---

## Extension Points

Orbs is designed for extensibility without modifying core code.

### 1. Custom Keywords

Create custom keyword libraries:

```python
# keywords/custom_web.py
from orbs.keyword.web import Web

class CustomWeb(Web):
    @classmethod
    def login(cls, username, password):
        """Custom login keyword"""
        cls.type_text("id=username", username)
        cls.type_text("id=password", password)
        cls.click("id=login-btn")
```

Use in tests:

```python
from keywords.custom_web import CustomWeb

def test_login():
    CustomWeb.login("admin", "password")
```

### 2. Listeners

Create test lifecycle hooks:

```python
# listeners/screenshot_listener.py

def before_test(context):
    """Called before each test"""
    print(f"Starting test: {context.test_name}")

def after_test(context):
    """Called after each test"""
    if context.failed:
        # Take screenshot on failure
        from orbs.keyword.web import Web
        Web.take_screenshot(f"failures/{context.test_name}.png")

def on_failure(context, error):
    """Called when test fails"""
    print(f"Test failed with error: {error}")
```

Listeners are auto-discovered from `listeners/` directory.

### 3. Custom Factories

Override driver creation:

```python
# factories/custom_browser.py
from selenium import webdriver
from orbs.browser_factory import BrowserFactory

class CustomBrowserFactory(BrowserFactory):
    @staticmethod
    def create_driver(platform=None):
        """Custom driver with proxy"""
        options = webdriver.ChromeOptions()
        options.add_argument('--proxy-server=http://proxy:8080')
        return webdriver.Chrome(options=options)
```

### 4. Custom Reporters

Generate custom test reports:

```python
# listeners/custom_reporter.py

_results = []

def after_test(context):
    _results.append({
        'name': context.test_name,
        'status': 'PASS' if not context.failed else 'FAIL',
        'duration': context.duration
    })

def after_suite(context):
    # Generate HTML report
    with open('custom_report.html', 'w') as f:
        f.write('<html><body>')
        for result in _results:
            f.write(f"<div>{result}</div>")
        f.write('</body></html>')
```

---

## Project Structure

### Framework Structure

```
orbs/
├── __init__.py               # Package initialization
├── cli.py                    # Typer CLI commands
├── runner.py                 # Test execution orchestrator
├── config.py                 # Configuration management
├── browser_factory.py        # Web driver creation
├── mobile_factory.py         # Mobile driver creation
├── api_client.py             # HTTP client
├── thread_context.py         # Thread-local storage
├── listener_manager.py       # Hook execution
├── report_generator.py       # Report creation
├── utils.py                  # Utilities (templates, etc.)
├── keyword/
│   ├── web.py                # Web keywords
│   ├── mobile.py             # Mobile keywords
│   └── locator.py            # Locator utilities
├── spy/
│   ├── base.py               # Base spy class
│   ├── web.py                # Web spy implementation
│   ├── mobile.py             # Mobile spy implementation
│   └── js/
│       └── web_spy_listener.js  # Browser injection script
└── templates/
    ├── jinja/                # Code generation templates
    │   ├── testcases/
    │   ├── testsuites/
    │   ├── features/
    │   └── steps/
    └── project/              # Project scaffold template
        ├── __init__.py
        ├── main.py
        ├── settings/
        ├── testcases/
        ├── testsuites/
        └── include/
```

### User Project Structure

```
myproject/
├── __init__.py               # Project root marker
├── main.py                   # Entry point (optional)
├── .env                      # Environment variables
├── pytest.ini                # Pytest configuration
├── settings/                 # Configuration files
│   ├── browser.properties
│   ├── mobile.properties
│   ├── appium.properties
│   ├── platform.properties
│   └── server.properties
├── testcases/                # Individual test cases
│   ├── login.py
│   └── checkout.py
├── testsuites/               # Test suite definitions
│   ├── smoke.yml
│   ├── regression.yml
│   └── regression.py
├── testsuite_collections/    # Suite collections
│   └── nightly.yml
├── listeners/                # Custom hooks
│   └── screenshot_on_failure.py
├── include/                  # BDD resources
│   ├── environment.py        # Behave hooks
│   ├── features/
│   │   └── login.feature
│   └── steps/
│       └── login_steps.py
├── object_repository/        # Spy-captured elements
│   ├── LoginButton.xml
│   └── SearchBox.xml
└── reports/                  # Generated reports (gitignored)
    └── test_report.html
```

---

## Technology Stack

### Core Dependencies

| Library | Purpose |
|---------|---------|
| **Selenium** | Web browser automation |
| **Appium** | Mobile app automation |
| **Requests** | HTTP client for API testing |
| **Behave** | BDD framework (Gherkin) |
| **Pytest** | Test runner and assertions |
| **Typer** | CLI framework |
| **FastAPI** | REST API server |
| **Jinja2** | Template engine |
| **InquirerPy** | Interactive prompts |
| **python-dotenv** | Environment variable management |

### Optional Dependencies

| Library | Purpose |
|---------|---------|
| **Allure** | Advanced reporting |
| **Requests-mock** | API mocking |
| **Docker** | Containerized execution |

---

## Design Patterns

### 1. Factory Pattern

**BrowserFactory** and **MobileFactory** create drivers:

```python
# Encapsulates driver creation logic
driver = BrowserFactory.create_driver(platform="chrome")
```

**Benefits:**
* Centralized configuration
* Easy to extend with new platforms
* Testable in isolation

### 2. Singleton (Thread-Local)

**Thread context** ensures one driver per thread:

```python
# First call creates driver
driver1 = Web._get_driver()

# Subsequent calls return same instance
driver2 = Web._get_driver()

assert driver1 is driver2  # Same instance
```

### 3. Template Method

**Runner** defines test execution template:

```python
def run(target):
    load_config()
    initialize_listeners()
    execute_before_hooks()
    run_tests()
    execute_after_hooks()
    generate_report()
```

Subclasses override specific steps.

### 4. Strategy Pattern

**Locator strategies** are selected dynamically:

```python
# User specifies strategy
Web.click("id=button")
Web.click("css=.submit")
Web.click("xpath=//button")

# Framework selects appropriate locator
```

### 5. Observer Pattern

**Listeners** observe test lifecycle events:

```python
# Framework notifies listeners
listener_manager.notify('before_test', context)
listener_manager.notify('after_test', context)
```

### 6. Facade Pattern

**Web/Mobile keywords** provide simple interface to complex operations:

```python
# Simple API
Web.click("id=button")

# Hides complexity:
# - Driver retrieval
# - Element waiting
# - Error handling
# - Retry logic
```

---

## Performance Considerations

### 1. Lazy Driver Initialization

Drivers are created only when first needed:

```python
def _get_driver(cls):
    driver = get_context('web_driver')
    if driver is None:  # Create only if needed
        driver = BrowserFactory.create_driver()
        set_context('web_driver', driver)
    return driver
```

### 2. Connection Pooling

API client uses `requests.Session` for connection reuse:

```python
self.session = requests.Session()  # Reuses connections
```

### 3. Parallel Execution

Thread-local storage enables parallel tests:

```bash
pytest -n 4  # Run 4 tests in parallel
```

### 4. Smart Waiting

Explicit waits instead of sleep:

```python
# ❌ Slow
time.sleep(5)

# ✅ Fast
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "element"))
)
```

---

## Security Considerations

### 1. Credential Management

Never hardcode credentials:

```python
# ✅ Good
username = os.getenv("TEST_USERNAME")

# ❌ Bad
username = "admin"
```

### 2. SSL Verification

API client verifies SSL by default:

```python
# Default: verify=True
response = api.get("/endpoint")

# Only disable for local development
api.session.verify = False  # Not recommended
```

### 3. Input Validation

Validate user inputs in CLI:

```python
if platform not in VALID_PLATFORMS:
    raise ValueError(f"Invalid platform: {platform}")
```

---

## Future Enhancements

### Planned Features

* **Orbs Studio** - GUI for test creation and execution
* **iOS Support** - Appium integration for iOS
* **Distributed Execution** - Selenium Grid integration
* **AI-Powered Healing** - Self-healing locators
* **Visual Testing** - Screenshot comparison
* **Performance Testing** - Load testing integration

---

## Next Steps

* [Philosophy & Concepts](philosophy.md) - Framework principles
* [CLI Reference](cli-reference.md) - Command documentation
* [Web Testing](web-testing.md) - Web automation guide
* [Mobile Testing](mobile-testing.md) - Mobile automation guide
