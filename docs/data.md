# Data Test Loader

Environment-aware CSV data loader with filtering and querying capabilities for test automation.

---

## Table of Contents

* [Introduction](#introduction)
* [Quick Start](#quick-start)  
* [Environment Resolution](#environment-resolution)
* [API Reference](#api-reference)
* [Filtering and Querying](#filtering-and-querying)
* [Method Chaining](#method-chaining)
* [Best Practices](#best-practices)
* [Examples](#examples)
* [Troubleshooting](#troubleshooting)

---

## Introduction

The Orbs data loader provides a lightweight CSV fixture system for test automation with:

* **Environment-aware path resolution** - Automatic file lookup across multiple data directories
* **Fluent querying API** - Method chaining for readable data access
* **Exact-match filtering** - String-based filtering for deterministic test data
* **Read-only design** - Prevents accidental data modification during tests
* **Type safety** - Full Python type hints for better IDE support

The system follows a "no mini-ORM" philosophy - it's designed for simple CSV test fixtures, not complex data relationships.

---

## Quick Start

```python
from orbs.data import load_data

# Load and query test data
users = load_data("users.csv")
admin = users.where(role="admin").first()

# Get exactly one matching row (error if 0 or >1 matches)
valid_user = load_data("auth/credentials.csv").one(scenario="valid")

# Multiple conditions
test_data = load_data("test-cases.csv").where(
    status="active", 
    environment="staging"
).all()
```

---

## Environment Resolution

Files are resolved in priority order:

1. `data.local/<path>` - **Highest priority** (local overrides, git-ignored)
2. `data/<ENV>/<path>` - Environment-specific data (uses `ORBS_ENV` config)  
3. `data/<path>` - Default fallback

This allows environment-specific test data while maintaining local overrides for development.

### Example Structure

```
project/
├── data/                    # Default data
│   ├── users.csv
│   └── auth/
│       └── tokens.csv
├── data.local/              # Local overrides (git-ignored)
│   └── users.csv            # Uses this in development
└── data/
    ├── staging/             # Staging environment
    │   └── users.csv
    └── production/          # Production environment
        └── auth/
            └── tokens.csv
```

---

## API Reference

### `load_data(path: str) -> CSVData`

Load CSV data with environment-aware path resolution.

**Parameters:**
- `path` - Relative path to CSV file (e.g. `"users.csv"`, `"auth/tokens.csv"`)

**Returns:** `CSVData` instance for querying

**Raises:** `FileNotFoundError` if file not found in any data directory

---

### CSVData Methods

#### `.all() -> list[dict]`

Get all rows as list of dictionaries.

```python
all_users = load_data("users.csv").all()
```

#### `.first() -> dict | None`

Get first row, regardless of count. Returns `None` if empty.

```python  
first_user = load_data("users.csv").first()
```

#### `.one(**conditions) -> dict`

Get exactly one row. **Raises `ValueError`** if 0 or >1 rows match.

```python
# Must have exactly 1 user with id="123" 
user = load_data("users.csv").one(id="123")

# Or from filtered results
admin = load_data("users.csv").where(role="admin").one()
```

#### `.where(**conditions) -> CSVData`

Filter by exact column matches. Returns new `CSVData` for chaining.

```python
# Single condition
active_users = load_data("users.csv").where(status="active")

# Multiple conditions  
data = load_data("test-cases.csv").where(
    environment="staging",
    scenario="valid"
)
```

#### `.random() -> dict | None`

Get random row. Returns `None` if empty.

```python
random_user = load_data("users.csv").where(role="admin").random()
```

---

## Filtering and Querying

### Exact String Matching

All filtering uses exact string comparison:

```python
# These are different:
data.where(age="25")    # String "25"
data.where(age=25)      # Number 25 -> converted to "25"
```

### Multiple Conditions

Use multiple keyword arguments for AND conditions:

```python
# All conditions must match
results = load_data("users.csv").where(
    department="IT",
    role="admin", 
    status="active"
)
```

### Empty Results

Methods handle empty results gracefully:

```python
data = load_data("users.csv").where(role="nonexistent")

data.all()     # Returns []
data.first()   # Returns None  
data.random()  # Returns None
data.one()     # Raises ValueError: No data found
```

---

## Method Chaining

The fluent API allows readable data access:

```python
# Chain filtering and selection
admin = (load_data("users.csv")
         .where(department="IT") 
         .where(role="admin")
         .first())

# More concise with multiple conditions
admin = load_data("users.csv").where(
    department="IT", 
    role="admin"
).first()

# Get exactly one result
config = load_data("app-config.csv").where(env="prod").one()
```

---

## Best Practices

### File Organization

```
data/
├── users.csv              # User accounts
├── auth/
│   ├── credentials.csv    # Login test data
│   └── tokens.csv         # API tokens
└── test-cases/
    ├── login.csv          # Login scenarios
    └── checkout.csv       # E-commerce flows
```

### CSV Structure

Keep CSV files simple with clear column names:

```csv
id,username,role,status,scenario
1,admin,administrator,active,valid_login
2,user1,user,active,standard_user
3,locked,user,locked,account_locked
```

### Error Handling

Use `.one()` when you expect exactly one result:

```python
try:
    admin = load_data("users.csv").one(role="admin")
except ValueError as e:
    print(f"Expected exactly 1 admin user: {e}")
```

### Environment-Specific Data

Use environment directories for different test data:

```python
# Uses staging/users.csv in staging environment
# Falls back to data/users.csv in other environments
users = load_data("users.csv")
```

---

## Examples

### Login Test Data

```python
# auth/credentials.csv
# username,password,expected_result,scenario
# admin,secret123,success,valid_admin
# user1,password,success,valid_user
# baduser,wrongpwd,failure,invalid_credentials

from orbs.data import load_data

# Get valid admin credentials
admin_creds = load_data("auth/credentials.csv").one(scenario="valid_admin")
username = admin_creds["username"]  # "admin"
password = admin_creds["password"]  # "secret123"

# Get all failure scenarios
failures = load_data("auth/credentials.csv").where(expected_result="failure").all()
```

### Test Configuration

```python
# config/environments.csv  
# name,base_url,timeout,database_url
# local,http://localhost:3000,30,sqlite:///local.db
# staging,https://staging.example.com,60,postgres://staging-db
# prod,https://example.com,90,postgres://prod-db

config = load_data("config/environments.csv").one(name="staging")
base_url = config["base_url"]    # "https://staging.example.com"
timeout = int(config["timeout"]) # 60
```

### User Management

```python
# users.csv
# id,name,email,department,role,status
# 1,John Doe,john@company.com,Engineering,developer,active
# 2,Jane Smith,jane@company.com,Engineering,admin,active  
# 3,Bob Wilson,bob@company.com,Marketing,user,inactive

# Get all active engineering users
engineers = load_data("users.csv").where(
    department="Engineering",
    status="active" 
).all()

# Get engineering admin (must be exactly 1)
eng_admin = load_data("users.csv").where(
    department="Engineering",
    role="admin"
).one()

# Random test user
test_user = load_data("users.csv").where(status="active").random()
```

---

## Troubleshooting

### FileNotFoundError

**Problem:** `FileNotFoundError: CSV not found. Tried: data.local/users.csv, data/users.csv`

**Solution:** 
- Check file path spelling and case sensitivity
- Ensure CSV file exists in one of the data directories
- Verify working directory is project root

### ValueError: Multiple rows found

**Problem:** `.one()` found multiple matching rows

**Solution:**
- Add more specific filter conditions
- Use `.first()` if you want any matching row  
- Use `.where().all()` to inspect all matches

### ValueError: No data found

**Problem:** `.one()` or `.where()` found no matching rows

**Solution:**
- Check filter conditions for typos
- Verify CSV data contains expected values
- Use `.all()` to inspect available data

### Column Not Found

**Problem:** Filtering on non-existent column returns empty results

**Solution:**
- Check CSV header names for typos
- Ensure column exists in the CSV file
- Verify CSV format (proper headers, encoding)

### Environment Data Not Loading

**Problem:** Expected environment-specific data not loading

**Solution:**
- Check `ORBS_ENV` configuration value
- Verify directory structure: `data/<ENV>/file.csv`
- Ensure file exists in environment directory