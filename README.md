Orbs 🚀



A lightweight, POM structured test automation framework for Python + Appium, including:

📦 Project scaffolding with orbs init

⟳ Test suite, test case, feature, and step generation using Jinja2 templating

▶️ Runner for executing feature (.feature), YAML suite, or .py test case files

🌐 REST API server (orbs serve) to list and schedule test suites

🔗 API client module (orbs.api_client) for programmatic integration

⚙️ Typer-powered CLI for all commands

🛡️ Hooks/listener system, dotenv support, jinja templating

🔧 Features

orbs setup — setup all mobile dependencies: node js, appium, uiAutomatior2

orbs init <project> — bootstrap a complete orbs project scaffold

orbs create-testsuite <name> — generate boilerplate YAML test suite & .py for its test suite hook

orbs create-testsuite-collection <name> — generate boilerplate YAML test suite collection

orbs create-testcase <name> — generate a .py test case stub

orbs create-listener <name> — generate a test listener

orbs create-feature <name> — generate a .feature file

orbs implement-feature <name> — autogenerate step definitions from your .feature

orbs run <target> — run one of .feature, .yml, or .py test scripts

orbs serve [--port <port>] — expose a REST API to list, run, and schedule test suites

orbs spy — interactive element inspector for web and mobile applications

🔍 Spy Functionality

The **spy** command provides an interactive element inspector similar to Katalon's Object Spy, allowing you to capture element locators easily for your test automation.

### Web Spy - Quick Start

The primary command for web element inspection:

```bash
# Basic web spy command (always include https://)
orbs spy --url=https://google.com --web

# Other examples
orbs spy --url=https://example.com --web
orbs spy --url=https://github.com --web
orbs spy --url=https://stackoverflow.com --web
```

**⚠️ Important:** Always include the full URL with `https://` protocol to avoid errors.

**Step-by-Step Usage:**

1. **Start the spy session:**
   ```bash
   orbs spy --url=https://google.com --web
   ```

2. **Browser opens automatically** - Chrome will launch and navigate to your specified URL

3. **Activate element selection** - Press `Ctrl+` ` (Ctrl + backtick key) in the browser

4. **Click any element** - Mouse over and click elements to capture their locators

5. **View captured data** - Locator information appears in your terminal console

6. **Stop the session** - Press `Ctrl+C` in the terminal to exit

**What Gets Captured:**
- Element tag name and attributes
- CSS selectors (ID, class, tag-based)
- XPath expressions (absolute and relative)
- Element text content
- All HTML attributes for precise targeting

### Mobile Spy

Start a mobile spy session to inspect elements on mobile applications:

```bash
# Start mobile spy (requires connected device)
orbs spy --mobile
```

**Prerequisites for Mobile Spy:**
- Connected Android device (via USB debugging)
- Appium server running (automatically started by orbs)
- Target application installed on device

**How to use Mobile Spy:**
1. Ensure your Android device is connected and USB debugging is enabled
2. Run the mobile spy command
3. Select your target device if multiple devices are connected
4. Navigate to your target mobile application
5. Use the spy interface to inspect elements
6. Press `Ctrl+C` to stop the spy session

**Mobile Spy Features:**
- Real-time device screen capture
- Element hierarchy inspection
- Android-specific locators (ID, XPath, UiSelector)
- Element properties and attributes
- Screenshot with element highlighting

### Integration with Test Creation

The spy functionality integrates seamlessly with orbs test creation:

```bash
# 1. Use spy to identify elements
orbs spy --web --url https://login.example.com

# 2. Create test case using discovered locators
orbs create-testcase login_test

# 3. Implement test using captured element information
# Edit testcases/login_test.py with your locators
```

### Example Usage in Test Code

After using spy to capture elements, you can use them in your test code:

```python
# Example usage of captured web elements
from selenium.webdriver.common.by import By
from orbs.browser_factory import BrowserFactory

def test_login():
    driver = BrowserFactory.create_driver()
    
    # Using captured locators from spy session
    username_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    
    username_field.send_keys("testuser")
    password_field.send_keys("password123")
    login_button.click()
```

```python
# Example usage of captured mobile elements
from appium.webdriver.common.mobileby import MobileBy
from orbs.mobile_factory import MobileFactory

def test_mobile_login():
    driver = MobileFactory.create_driver()
    
    # Using captured locators from mobile spy session
    username_field = driver.find_element(MobileBy.ID, "com.app:id/username")
    password_field = driver.find_element(MobileBy.ID, "com.app:id/password")
    login_button = driver.find_element(MobileBy.XPATH, "//android.widget.Button[@text='Login']")
    
    username_field.send_keys("testuser")
    password_field.send_keys("password123")
    login_button.click()
```

✅ Installation

pip install orbs

Or locally:

git clone https://github.com/badrusalam11/orbs.git
cd orbs
pip install -e .

🚀 Quick Start

1. Setup mobile project
orbs setup

2. Scaffold a new project

orbs init myproject
cd myproject

3. Create testsuite/feature/case

orbs create-testsuite login
orbs create-feature login
orbs implement-feature login

4. Add test logic in testcases/, steps/, etc.

5. Run tests

orbs run features/login.feature        # via behave
orbs run testsuites/login.yml         # via runner

after that, choose the mobile device, or set it directly in `deviceName` at settings/appium.properties

🌐 API Testing Example

You can use the same ApiClient to test any public free REST API, for example JSONPlaceholder:

from orbs.api_client import ApiClient

# initialize client for JSONPlaceholder
client = ApiClient(
    base_url="https://jsonplaceholder.typicode.com",
    default_headers={"Accept": "application/json"}
)

# GET a list of posts
response = client.get("/posts")
assert response.status_code == 200
posts = response.json()
assert isinstance(posts, list)
print(f"Retrieved {len(posts)} posts")

# GET a single post
response = client.get("/posts/1")
assert response.status_code == 200
post = response.json()
assert post.get("id") == 1
print(f"Post title: {post.get('title')}")

# POST a new post (will return a mock id)
new_post = {
    "title": "foo",
    "body": "bar",
    "userId": 1
}
response = client.post("/posts", json=new_post)
assert response.status_code == 201
created = response.json()
assert created.get("id") is not None
print(f"Created post ID: {created.get('id')}")

🛠️ Configuration

Use a .env in your project root to customize:

APP_PORT=5006
SERVER_URL=http://localhost:5006

💡 Why use orbs?

🧠 Inspired by Katalon, but for Python developers

🌟 Supports feature files + step generation + scheduling

🚀 Design for both CLI use and API integration

🧹 Expandable via listeners/hooks, Config, MobileFactory, etc.

🤝 Contributing

PRs are welcome! Please ensure:

Code is well-documented and follows PEP8

Templates & CLI updated accordingly

README.md and tests updated

Use Black, Flake8, isort (recommended)

📜 License

MIT — see LICENSE for details.

📨 Contact

Built & maintained by Muhamad Badru Salam — QA Automation Engineer (SDET)

Github: [badrusalam11](https://github.com/badrusalam11)

LinkedIn: [Muhamad Badru Salam](https://www.linkedin.com/in/muhamad-badru-salam-3bab2531b/)

Email: muhamadbadrusalam760@gmail.com