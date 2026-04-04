# Object Repository (self-healing)

## Overview

The `find_test_obj()` keyword reads `WebElementEntity` JSON files from the project's object repository and returns a Selenium `WebElement`. It implements a self-healing strategy: if the primary locator fails, the framework will try alternative selectors and generated fallbacks derived from the element properties.

## File format

Object repository files follow the `WebElementEntity` JSON format. Example:

```json
{
  "name": "input_login-button",
  "description": "",
  "tag": "input",
  "elementGuidId": "uuid-xxx",
  "selectorCollection": {
    "XPATH": "//*[@id='login-button']",
    "CSS": "#login-button"
  },
  "selectorMethod": "XPATH",
  "webElementProperties": [
    {
      "name": "tag",
      "value": "input",
      "isSelected": true,
      "matchCondition": "equals",
      "type": "Main"
    },
    {
      "name": "id",
      "value": "login-button",
      "isSelected": false,
      "matchCondition": "equals",
      "type": "Main"
    }
  ]
}
```

## Usage

Recommended inline pattern (concise and readable):

```python
from orbs.keyword import Web
from orbs.keyword import find_test_obj

Web.open("https://example.com")
Web.set_text(find_test_obj("input_username.json"), "admin")
Web.set_text(find_test_obj("input_password.json"), "password123")
Web.click(find_test_obj("button_login.json"))
```

Supported path formats (the project normalizes paths):

- Forward slash (recommended, cross-platform): `button_login.json` (or `object_repository/button_login.json`)
- Double backslash (Windows): `object_repository\\button_login.json`
- Raw string with single backslash: `r"object_repository\button_login.json"`

Alternative usage patterns:

```python
# Assign to a variable for reuse
username = find_test_obj("input_username.json")
username.clear()
username.send_keys("admin")

# Direct method call
find_test_obj("button_login.json").click()
```

## Self-healing strategy

Locator priority used by the framework:

1. Primary locator from `selectorMethod` (e.g. XPATH)
2. Entries in `selectorCollection` (CSS, ID, etc.)
3. Generated locators derived from `webElementProperties` (id, name, CSS, various XPaths)

Generated fallback examples (not exhaustive):

- `id` and `name` attribute locators
- Tag-based XPaths: `//{tag}[@id='value']`, `//{tag}[@name='value']`, `//{tag}[@type='value']`
- Combined attribute XPaths: `//{tag}[@name='value' and @type='value']`
- CSS selectors: `{tag}#{id}`, `{tag}.{class}`, `{tag}[name='value']`

## Logging

When self-healing occurs, the framework logs which locator succeeded. Example:

```
[INFO] Finding element 'input_login-button' from object_repository/input_login-button.json (primary: xpath=//*[@id='login-button'], N alternatives)
[ACTION] Found 'input_login-button' using alternative locator (2/N): id=login-button
```

## From Spy to Object Repository

The built-in spy writes captured elements as `WebElementEntity` JSON files into your `object_repository` folder. Workflow:

1. Run the spy and capture an element.
2. Save the generated JSON as `object_repository/<element_name>.json`.
3. Use `find_test_obj("<element_name>.json")` in tests or inline with `Web` keywords.

This workflow produces maintainable element definitions and enables automatic fallback when locators change.

## Example

```python
from orbs.keyword import Web
from orbs.keyword import find_test_obj

def test_login():
    Web.open("https://www.saucedemo.com/")
    Web.set_text(find_test_obj("input_username.json"), "standard_user")
    Web.set_text(find_test_obj("input_password.json"), "secret_sauce")
    Web.click(find_test_obj("input_login-button.json"))
    Web.wait_for_element("css=.inventory_list")
    Web.close()
```

## Tips

1. Provide meaningful properties in JSON (id, name, class, text) — more properties improve fallback quality.
2. Populate `selectorCollection` with multiple selectors (XPath, CSS, ID) so the parser has reliable alternatives.
3. Choose a stable primary locator in `selectorMethod` to minimize fallbacks.

## Advanced: Inspect parsed JSON

```python
from orbs.keyword.locator import WebElementEntity
el = WebElementEntity("input_login-button.json")
print(el.name, el.tag)
print(el.get_primary_locator())
print(el.get_alternative_locators())
```

## Integration with existing code

You can mix object-repository references with classic locators:

```python
Web.click("id=old-style-locator")
Web.click(find_test_obj("new-element.json"))
```

## See Also

- [Configuration Documentation](../README.md)
- [CLI Reference](cli-reference.md)
- [Test Structure](architecture.md)
