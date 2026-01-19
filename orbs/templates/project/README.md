# orbs
This is Orbs project sample scaffolding

# Run with shortcut
- Open file test_suite.yml or test_case.py
- Press `ctrl + F5`

# Run with command
- Open terminal
- Run: `python .\main.py testsuites\login.yml`

## Run with Specific Environment
```bash
# Option 1: Create .env file (Recommended)
# Create .env file with: ORBS_ENV=dev
orbs run testsuites/login.yml

# Option 2: Set ORBS_ENV in terminal
export ORBS_ENV=dev
orbs run testsuites/login.yml

# Option 3: Use --env argument
orbs run testsuites/login.yml --env=dev
orbs run testsuites/login.yml --env=uat
orbs run testsuites/login.yml --env=staging
orbs run testsuites/login.yml --env=prod
```

**Note:** If no environment is specified (no `.env`, no `ORBS_ENV`, no `--env`), you will be prompted to select an environment interactively.

# Environment Configuration
This project supports multiple environment configurations for flexible test execution across different environments.

## Available Environments
- `default` - Default configuration
- `dev` - Development environment
- `uat` - UAT environment
- `staging` - Staging environment
- `prod` - Production environment

## Set Environment

### Option 1: Create .env file (Recommended)
Create a `.env` file in your project root:
```bash
ORBS_ENV=dev
ORBS_DEBUG=true
```

### Option 2: Using environment variables
```bash
# Windows PowerShell
$env:ORBS_ENV = "dev"
$env:ORBS_DEBUG = "true"

# Linux/Mac
export ORBS_ENV=dev
export ORBS_DEBUG=true
```

**Note:** Configuration keys are case-insensitive. Both `ORBS_ENV` and `orbs_env` will work.

## Debug Mode
Enable debug mode for detailed logging:
```bash
ORBS_DEBUG=true
```

## Usage in Tests
```python
from orbs.config import config

# Get environment-specific values
url = config.target("url")
username = config.target("username")
api_url = config.target("api_url", "https://default.com")
```

See [docs](https://github.com/badrusalam11/orbs-cli/tree/main/docs) for detailed documentation.
