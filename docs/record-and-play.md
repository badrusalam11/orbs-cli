# Record & Play (Recorder)

---

## Table of Contents

- [Introduction](#introduction)
- [Quick Start (Web)](#quick-start-web)
- [How Recording Works](#how-recording-works)
- [What Gets Recorded](#what-gets-recorded)
- [Generated Test Case Format](#generated-test-case-format)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [See Also](#see-also)

---

## Introduction

The Recorder captures user interactions in a browser session and converts them into a runnable Python test. Use it to rapidly prototype tests, reproduce flows, or generate a starting point for maintainable test code.

This guide explains the web recorder (desktop browser). Mobile recording may be listed as coming soon in the CLI.

---

## Quick Start (Web)

Start a recording session from the CLI:

```bash
orbs record --web --url=https://example.com --testcase=login_test
```

Interactive mode (choose defaults and stop manually):

```bash
orbs record --web --url=example.com
```

During a recording session:

- A browser window will open and the recorder injects listeners.
- Interact with the page normally (clicks, typing, navigation).
- Use the page "Stop Recording" button or press Ctrl+C in terminal to stop.
- The recorder will parse captured actions and generate a Python test file in the output directory.

After generation the CLI prints a recommended command to run the generated test, for example:

```
python output_dir/login_test.py
```

---

## How Recording Works

- A small JavaScript listener is injected into the page. It intercepts user events (click, input, change, navigation, keypress) and logs structured action objects to the browser console.
- The Python runner polls the browser console (and reads a window-exposed array) to retrieve actions and timestamps.
- Actions are deduplicated and optimized (short repeated events consolidated, recorder UI interactions ignored).
- Finally, the runner converts optimized actions into Python code using `orbs.keyword.web` primitives and writes a test file.

---

## What Gets Recorded

Typical action types captured by the recorder:

- `page_load` / `navigation` — page URLs and navigations
- `click` — mouse clicks on elements
- `input` — typing into input fields (password values are obfuscated)
- `change` — select or input change events
- `keypress` — special keys like Enter, Tab

Each action contains a timestamp and a target descriptor (element id, tag, or generated selector). The recorder attempts to capture multiple locator strategies where possible.

---

## Generated Test Case Format

The recorder generates a plain Python script containing a `run()` function. Example structure:

```python
#!/usr/bin/env python3
"""
Generated test case: login_test
Created by Orbs Recorder on 2026-02-22 12:34:56
"""

from orbs.keyword.web import Web


def run():
    """Generated test case for login_test"""

    # Setup
    Web.open("https://example.com")

    # Recorded interactions
    Web.click("css=#login")
    Web.set_text("css=input[name=\"username\"]", "user")
    Web.set_text("css=input[name=\"password\"]", "***PASSWORD***")

    # Cleanup
    Web.close()
```

Run the generated test with the printed command, for example:

```
python path/to/login_test.py
```

Note: the generated test is a starting point — adapt locators, add assertions, and refactor into page objects as needed.

---

## Examples

Record a simple login flow and run it:

```bash
# Record
orbs record --web --url=https://www.saucedemo.com --testcase=sauce_login

# After recording completes, run the generated test
python output_dir/sauce_login.py
```

Programmatic example (advanced):

```python
from orbs.record.web import WebRecordRunner

runner = WebRecordRunner(url="https://example.com", testcase_name="my_test")
runner.start()
# Interact with browser
# Stop recording from CLI or page UI
```

---

## Best Practices

- Start recordings from a clean browser state to reduce noise (cached data, popups).
- Use meaningful `--testcase` names so generated files are easy to find.
- Review and replace unstable locators (auto-generated XPaths) with stable selectors (ID, semantic CSS) before committing.
- Remove or mask sensitive input values; recorder obfuscates password fields by default but always verify.
- Convert long flows into smaller, focused tests to keep generated scripts maintainable.

---

## Troubleshooting

- No actions captured: ensure the recorder injected listeners (CLI prints injection success) and the browser did not block scripts or disable console access.
- Duplicate actions: dynamic pages can emit many events — use the generated test as a base and remove duplicates manually.
- Elements not found when running generated test: page timing and dynamic content may require `Web.wait_for_element()` or explicit waits.
- Recording UI interfering: the recorder ignores clicks against its own UI, but verify selectors if you see unexpected interactions.

---

## See Also

- [Spy Tool Usage Guide](spy.md)
- [Object Repository (self-healing)](object-repository.md)
- [CLI Reference](cli-reference.md)
