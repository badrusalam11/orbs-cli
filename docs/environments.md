# Environment Configuration

Environment configuration allows you to manage different test configurations for various environments (development, UAT, staging, production).

## Overview

The environment system provides:
- **Multiple environment support**: default, dev, uat, staging, prod
- **YAML-based configuration**: Easy to read and maintain
- **Nested configuration**: Support for complex configuration structures
- **Environment variable substitution**: Secure handling of sensitive data
- **Dot notation access**: Simple API to retrieve nested values

## Directory Structure

```
your-project/
├── environments/
│   ├── default.yml    # Base configuration
│   ├── dev.yml        # Development environment
│   ├── uat.yml        # UAT environment
│   ├── staging.yml    # Staging environment
│   ├── prod.yml       # Production environment
│   └── README.md      # Environment documentation
```

## Configuration File Format

Environment files use YAML format:

```yaml
# dev.yml
url: "https://dev.example.com"
api_url: "https://api-dev.example.com"

username: "dev_user"
password: "dev_password"

api_timeout: 60
api_retry: 5

db_host: "dev-db.example.com"
db_port: 5432
db_name: "dev_db"

custom_config:
  feature_flag_1: true
  feature_flag_2: false
  max_retry: 5
  debug_mode: true
```

## Setting Active Environment

Set the `ORBS_ENV` environment variable to specify which configuration to use:

### Windows PowerShell
```powershell
$env:ORBS_ENV = "dev"
```

### Windows CMD
```cmd
set ORBS_ENV=dev
```

### Linux/Mac
```bash
export ORBS_ENV=dev
```

If `ORBS_ENV` is not set, the system will use `default.yml`.

## API Usage

### Basic Usage

```python
from orbs.config import config

# Get simple values
url = config.target("url")
username = config.target("username")
api_url = config.target("api_url")

# With default fallback
timeout = config.target("api_timeout", 30)
```

### Nested Values (Dot Notation)

```python
# Access nested configuration using dot notation
feature_flag = config.target("custom_config.feature_flag_1")
max_retry = config.target("custom_config.max_retry", 3)
debug_mode = config.target("custom_config.debug_mode", False)
```

### Complete Test Example

```python
from orbs.config import config
from orbs.keyword.web import WebKeyword

class TestLogin:
    def test_successful_login(self):
        web = WebKeyword()
        
        # Get configuration from active environment
        base_url = config.target("url")
        username = config.target("username")
        password = config.target("password")
        timeout = config.target("api_timeout", 30)
        
        # Use in test
        web.navigate_to(base_url)
        web.input_text("id=username", username)
        web.input_text("id=password", password)
        web.click("id=login-button")
        
        # Verify login
        web.verify_element_visible("id=dashboard")
```

### BDD/Behave Steps Example

```python
from behave import given, when, then
from orbs.config import config

@given('the user opens the application')
def step_open_app(context):
    url = config.target("url", "https://example.com")
    context.driver.get(url)

@when('the user logs in with default credentials')
def step_login(context):
    username = config.target("username", "test_user")
    password = config.target("password", "test_password")
    
    context.driver.find_element_by_id("username").send_keys(username)
    context.driver.find_element_by_id("password").send_keys(password)
    context.driver.find_element_by_id("login").click()
```

## Environment Variable Substitution

For sensitive data in production, use environment variable placeholders:

```yaml
# prod.yml
url: "https://example.com"
username: "${PROD_USERNAME}"
password: "${PROD_PASSWORD}"
api_key: "${API_KEY}"
```

Then set the actual values:

```bash
# Linux/Mac
export PROD_USERNAME=actual_username
export PROD_PASSWORD=actual_password
export API_KEY=your_api_key

# Windows PowerShell
$env:PROD_USERNAME = "actual_username"
$env:PROD_PASSWORD = "actual_password"
$env:API_KEY = "your_api_key"
```

## Running Tests with Different Environments

### Development
```bash
# Set environment
export ORBS_ENV=dev

# Run tests
orbs run testsuites/login.yml
# or
python main.py testsuites/login.yml
```

### UAT
```bash
export ORBS_ENV=uat
orbs run testsuites/smoke_test.yml
```

### Production
```bash
export ORBS_ENV=prod
export PROD_USERNAME=actual_user
export PROD_PASSWORD=actual_pass
orbs run testsuites/critical_path.yml
```

### One-liner (Linux/Mac)
```bash
ORBS_ENV=dev orbs run testsuites/login.yml
```

### One-liner (Windows PowerShell)
```powershell
$env:ORBS_ENV = "dev"; orbs run testsuites/login.yml
```

## Best Practices

### 1. Use default.yml as Template
Keep all possible configuration keys in `default.yml` as a reference:

```yaml
# default.yml - Complete configuration template
url: "https://example.com"
api_url: "https://api.example.com"
username: "default_user"
password: "default_password"
# ... all other keys
```

### 2. Environment-Specific Overrides
Only override values that differ in each environment:

```yaml
# dev.yml - Only changed values
url: "https://dev.example.com"
api_url: "https://api-dev.example.com"
username: "dev_user"
# Other values will inherit from default.yml
```

### 3. Never Hardcode Sensitive Data
Use environment variables for production credentials:

```yaml
# ❌ BAD - Hardcoded credentials
username: "admin"
password: "super_secret_password"

# ✅ GOOD - Use environment variables
username: "${PROD_USERNAME}"
password: "${PROD_PASSWORD}"
```

### 4. Version Control
- ✅ Commit environment files to version control
- ❌ Never commit files with real credentials
- ✅ Use `.env` or environment variables for sensitive data

### 5. Documentation
Add comments in YAML files to explain configuration:

```yaml
# Base URL for the application under test
url: "https://example.com"

# API timeout in seconds (default: 30)
api_timeout: 30

# Maximum retry attempts for failed requests
api_retry: 3
```

### 6. Naming Convention
Use descriptive environment names:
- `default.yml` - Base configuration
- `dev.yml` - Development
- `uat.yml` - User Acceptance Testing
- `staging.yml` - Staging/Pre-production
- `prod.yml` - Production

## Integration with CI/CD

### GitHub Actions
```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, uat, staging]
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        env:
          ORBS_ENV: ${{ matrix.environment }}
        run: |
          orbs run testsuites/smoke_test.yml
```

### GitLab CI
```yaml
# .gitlab-ci.yml
test:dev:
  script:
    - export ORBS_ENV=dev
    - orbs run testsuites/regression.yml

test:uat:
  script:
    - export ORBS_ENV=uat
    - orbs run testsuites/regression.yml
```

### Jenkins
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                script {
                    def environments = ['dev', 'uat', 'staging']
                    environments.each { env ->
                        sh """
                            export ORBS_ENV=${env}
                            orbs run testsuites/smoke_test.yml
                        """
                    }
                }
            }
        }
    }
}
```

## Troubleshooting

### Environment not loading
**Problem**: Changes to environment files not reflecting

**Solution**: 
- Ensure `ORBS_ENV` is set correctly
- Check file name matches environment name exactly (case-sensitive)
- Verify YAML syntax is valid

### Environment variable not substituted
**Problem**: `${VAR_NAME}` appearing literally in config

**Solution**:
- Ensure environment variable is set before running tests
- Check variable name spelling matches exactly
- Verify variable is exported/set in current shell session

### Nested value not found
**Problem**: `config.target("custom.nested.value")` returns None

**Solution**:
- Check dot notation path is correct
- Verify key exists in YAML file
- Ensure proper indentation in YAML (use spaces, not tabs)

## Example Projects

See `demo_environment.py` in project template for interactive examples:

```bash
# Create new project
orbs init my-project
cd my-project

# Run environment demo
python demo_environment.py

# Try different environments
$env:ORBS_ENV = "dev"
python demo_environment.py
```

## See Also

- [Configuration Documentation](../README.md)
- [CLI Reference](cli-reference.md)
- [Test Structure](architecture.md)
