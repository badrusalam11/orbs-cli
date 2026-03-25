# Object Repository (self-healing)

## Overview

The `find_test_obj()` keyword reads `WebElementEntity` XML files from the project's object repository and returns a Selenium `WebElement`. It implements a self-healing strategy: if the primary locator fails, the framework will try alternative selectors and generated fallbacks derived from the element properties.

## File format

Object repository files follow the `WebElementEntity` XML format. Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<WebElementEntity>
  <description></description>
  <name>input_login-button</name>
  <tag>input</tag>
  <selectorCollection>
    <entry>
      <key>XPATH</key>
      <value>//*[@id="login-button"]</value>
    </entry>
    <entry>
      <key>CSS</key>
      <value>#login-button</value>
    </entry>
  </selectorCollection>
  <selectorMethod>XPATH</selectorMethod>
  <webElementProperties>
    <isSelected>true</isSelected>
    <name>tag</name>
    <value>input</value>
  </webElementProperties>
  <webElementProperties>
    <isSelected>false</isSelected>
    <name>id</name>
    <value>login-button</value>
  </webElementProperties>
</WebElementEntity>
```

## Usage

Recommended inline pattern (concise and readable):

```python
from orbs.keyword import web
from orbs.keyword import find_test_obj

web.open("https://example.com")
web.set_text(find_test_obj("input_username.xml"), "admin")
web.set_text(find_test_obj("input_password.xml"), "password123")
web.click(find_test_obj("button_login.xml"))
```

Supported path formats (the project normalizes paths):

- Forward slash (recommended, cross-platform): `button_login.xml` (or `object_repository/button_login.xml`)
- Double backslash (Windows): `object_repository\\button_login.xml`
- Raw string with single backslash: `r"object_repository\button_login.xml"`

Alternative usage patterns:

```python
# Assign to a variable for reuse
username = find_test_obj("input_username.xml")
username.clear()
username.send_keys("admin")

# Direct method call
find_test_obj("button_login.xml").click()
```

## Self-healing strategy

Locator priority used by the framework:

1. Primary locator from `<selectorMethod>` (e.g. XPATH)
2. Entries in `<selectorCollection>` (CSS, ID, etc.)
3. Generated locators derived from `<webElementProperties>` (id, name, CSS, various XPaths)

Generated fallback examples (not exhaustive):

- `id` and `name` attribute locators
- Tag-based XPaths: `//{tag}[@id='value']`, `//{tag}[@name='value']`, `//{tag}[@type='value']`
- Combined attribute XPaths: `//{tag}[@name='value' and @type='value']`
- CSS selectors: `{tag}#{id}`, `{tag}.{class}`, `{tag}[name='value']`

## Logging

When self-healing occurs, the framework logs which locator succeeded. Example:

```
[INFO] Finding element 'input_login-button' from object_repository/input_login-button.xml (primary: xpath=//*[@id="login-button"], N alternatives)
[ACTION] Found 'input_login-button' using alternative locator (2/N): id=login-button
```

## From Spy to Object Repository

The built-in spy writes captured elements as `WebElementEntity` XML files into your `object_repository` folder. Workflow:

1. Run the spy and capture an element.
2. Save the generated XML as `object_repository/<element_name>.xml`.
3. Use `find_test_obj("<element_name>.xml")` in tests or inline with `Web` keywords.

This workflow produces maintainable element definitions and enables automatic fallback when locators change.

## Example

```python
from orbs.keyword import web
from orbs.keyword import find_test_obj

def test_login():
    web.open("https://www.saucedemo.com/")
    web.set_text(find_test_obj("input_username.xml"), "standard_user")
    web.set_text(find_test_obj("input_password.xml"), "secret_sauce")
    web.click(find_test_obj("input_login-button.xml"))
    web.wait_for_element("css=.inventory_list")
    web.close()
```

## Tips

1. Provide meaningful properties in XML (id, name, class, text) — more properties improve fallback quality.
2. Populate `selectorCollection` with multiple selectors (XPath, CSS, ID) so the parser has reliable alternatives.
3. Choose a stable primary locator in `<selectorMethod>` to minimize fallbacks.

## Advanced: Inspect parsed XML

```python
from orbs.keyword.locator import WebElementEntity
el = WebElementEntity("input_login-button.xml")
print(el.name, el.tag)
print(el.get_primary_locator())
print(el.get_alternative_locators())
```

## Integration with existing code

You can mix object-repository references with classic locators:

```python
web.click("id=old-style-locator")
web.click(find_test_obj("new-element.xml"))
```

## See Also

- [Configuration Documentation](../README.md)
- [CLI Reference](cli-reference.md)
- [Test Structure](architecture.md)
