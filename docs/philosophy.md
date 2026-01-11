# Orbs Philosophy & Concepts

## Introduction

Orbs is built on a set of core principles that guide its design, implementation, and evolution. These principles ensure that automation scales with your team's maturity without requiring framework migration or test rewrites.

---

## Core Principles

### 1. Tests are Software, Not Scripts

**What it means:**

Automation code should be designed, structured, reviewed, and evolved like production code — not copied scripts glued together over time.

**Why it matters:**

* Test automation is a software development discipline
* Poor structure leads to unmaintainable test suites
* Copy-paste approaches create technical debt that compounds over time
* Teams should apply the same engineering standards to tests as they do to production code

**How Orbs supports this:**

* Enforced project structure from day one
* Separation of concerns: test cases, test suites, features, steps
* Template-based generation for consistency
* Support for listeners and hooks for extensibility
* Version control friendly structure

---

### 2. Explicit is Better Than Implicit

**What it means:**

If something runs, it should be obvious:
* What is executed
* From where
* With which configuration

No silent defaults. No hidden behavior.

**Why it matters:**

* Debugging mysterious test failures wastes time
* Team members should understand execution flow without digging through framework internals
* Configuration should be discoverable and documented
* Surprises in automation lead to loss of trust

**How Orbs supports this:**

* Clear command syntax: `orbs run testsuites/login.yml`
* Explicit platform selection: `orbs run --platform=android`
* Configuration in readable files: `settings/*.properties` and `.env`
* Transparent template system
* CLI commands that describe what they do

---

### 3. Structure Before Scale

**What it means:**

Orbs enforces structure early so teams don't pay technical debt later. Scaling automation should feel predictable, not painful.

**Why it matters:**

* Unstructured test suites become unmaintainable at scale
* Retrofitting structure into existing chaos is expensive
* Teams should focus on writing tests, not organizing them
* Good structure enables parallel execution, selective runs, and clear reporting

**How Orbs supports this:**

* Scaffolding with `orbs init` creates proper structure immediately
* Predefined directories: `testcases/`, `testsuites/`, `features/`, `steps/`, `listeners/`
* Naming conventions and templates
* YAML-based test suite definitions for clarity
* Separation of test logic from execution configuration

---

### 4. One Core, Many Interfaces

**What it means:**

The same execution engine can be accessed via:
* CLI (`orbs run`)
* REST API (`orbs serve`)
* Orbs Studio (GUI) - planned

Different entry points, same behavior.

**Why it matters:**

* Teams have different preferences and workflows
* Junior engineers may prefer GUI, seniors prefer CLI
* CI/CD requires programmatic access
* Consistency across interfaces ensures reliable execution
* One implementation = easier maintenance

**How Orbs supports this:**

* Core execution engine in `orbs.runner`
* CLI wrapper via Typer
* REST API server for remote execution
* All interfaces use the same underlying runner
* Configuration is interface-agnostic

---

### 5. Tooling Should Assist, Not Hide Reality

**What it means:**

Generators, runners, and spy tools exist to accelerate work — not to obscure how automation actually works.

**Why it matters:**

* Engineers should understand what they're running
* Black-box tools create dependency and knowledge gaps
* Generated code should be readable and modifiable
* Tooling should teach, not replace learning

**How Orbs supports this:**

* Templates are Jinja2 files you can inspect and modify
* Generated code is standard Python/YAML
* Spy tools capture elements but don't hide locators
* CLI commands are transparent
* Source code is accessible and documented

---

## Maturity Levels

Orbs supports teams at different automation maturity levels:

### Level 1: Beginners

**Who:** Junior QA engineers, manual testers learning automation

**Tools:**
* Visual spy tools for element capture
* Template generators for boilerplate
* YAML-based test suite definitions
* Keyword-driven approach

**Example workflow:**
```bash
orbs init myproject
orbs spy --web --url=https://app.example.com
orbs create-feature login
orbs implement-feature login
orbs run features/login.feature
```

---

### Level 2: Intermediate

**Who:** Automation engineers comfortable with code

**Tools:**
* Direct Python test case development
* Custom listeners for reporting
* Environment-specific configuration
* API testing integration

**Example workflow:**
```bash
orbs create-testcase checkout_flow
# Edit testcases/checkout_flow.py directly
orbs create-testsuite regression
# Edit testsuites/regression.yml to include tests
orbs run testsuites/regression.yml --platform=chrome
```

---

### Level 3: Advanced

**Who:** Senior SDETs, framework developers

**Tools:**
* Custom keywords and extensions
* API-driven execution
* Docker-based parallel execution
* CI/CD pipeline integration
* Custom listeners for metrics/reporting

**Example workflow:**
```bash
# Start API server
orbs serve --port=5006

# Trigger via REST API
curl -X POST http://localhost:5006/run \
  -H "Content-Type: application/json" \
  -d '{"target": "testsuites/regression.yml", "platform": "chrome"}'

# Check status
curl http://localhost:5006/status
```

---

## Key Concepts

### Test Case

A **test case** is a single, focused test scenario written in Python.

**Location:** `testcases/`

**Example:**
```python
def test_login_valid_credentials():
    # Test logic here
    pass
```

**When to use:**
* Unit-level test scenarios
* Reusable test building blocks
* Code-first test development

---

### Test Suite

A **test suite** is a collection of test cases with execution configuration.

**Location:** `testsuites/`

**Format:** YAML + Python

**Example (login.yml):**
```yaml
test_cases:
  - path: testcases\login.py
    enabled: true
```

**When to use:**
* Grouping related test cases
* Environment-specific test runs
* Regression suites

---

### Feature

A **feature** is a BDD-style specification using Gherkin syntax.

**Location:** `include/features/`

**Example (login.feature):**
```gherkin
Feature: User Login
  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should see the dashboard
```

**When to use:**
* Behavior-driven development
* Business-readable test specs
* Collaboration with non-technical stakeholders

---

### Steps

**Steps** are the implementation of Gherkin scenarios using Behave.

**Location:** `include/steps/`

**Example:**
```python
from behave import given, when, then

@given('I am on the login page')
def step_impl(context):
    context.driver.get("https://app.example.com/login")
```

**When to use:**
* Implementing BDD features
* Reusable step definitions

---

### Listeners

**Listeners** are hooks that execute at specific points in the test lifecycle.

**Location:** `listeners/`

**Use cases:**
* Custom reporting
* Screenshot capture on failure
* Metrics collection
* Integration with third-party tools

---

### Configuration

Configuration is explicit and layered:

1. **Environment variables** (`.env`)
2. **Property files** (`settings/*.properties`)
3. **Command-line arguments**

**Priority:** CLI args > Environment vars > Property files

---

## Design Philosophy Summary

| Principle | What it prevents | What it enables |
|-----------|------------------|-----------------|
| Tests are software | Copy-paste chaos | Maintainable automation |
| Explicit over implicit | Mystery failures | Clear debugging |
| Structure before scale | Technical debt | Predictable growth |
| One core, many interfaces | Vendor lock-in | Flexible workflows |
| Tooling assists | Black-box dependency | Learning & ownership |

---

## Next Steps

* [CLI Reference](cli-reference.md) - Learn all available commands
* [Web Testing](web-testing.md) - Web automation guide
* [Mobile Testing](mobile-testing.md) - Android testing guide
* [Architecture](architecture.md) - Technical architecture overview
