# Console Summary and Exit Codes

## Overview

ORBS now includes a console summary feature that displays test execution results in a formatted, easy-to-read output. The framework also provides proper exit codes for CI/CD integration.

## Console Summary Output

After test execution completes, ORBS displays a comprehensive summary:

```
==================================================
ORBS TEST EXECUTION SUMMARY
==================================================
Total Tests     : 12
Passed          : 10
Failed          : 2
Skipped         : 0
Retries         : 3
Duration        : 1m 24s
Environment     : UAT
Browser         : Chrome (headless)
Self-Healing    : Enabled
Retry           : Enabled (max 2)
==================================================
STATUS: FAILED
==================================================
```

## Features

### Color-Coded Output
- **Passed**: Green
- **Failed**: Red
- **Skipped**: Yellow
- **Overall Status**: Color-coded based on result

### Information Displayed
- **Total Tests**: Total number of test cases executed
- **Passed/Failed/Skipped**: Breakdown of test results
- **Retries**: Number of test retries performed
- **Duration**: Human-readable execution time (e.g., "1m 24s", "2h 15m 30s")
- **Environment**: Current test environment (dev, uat, staging, prod)
- **Browser**: Platform and mode (headless/headed)
- **Self-Healing**: Status of self-healing feature
- **Retry**: Retry configuration status

## Exit Codes for CI/CD

ORBS provides standard exit codes for integration with CI/CD pipelines:

- **Exit Code 0**: All tests passed
- **Exit Code 1**: One or more tests failed

### CI/CD Integration Examples

#### Jenkins Pipeline
```groovy
stage('Run Tests') {
    steps {
        script {
            def exitCode = sh(
                script: 'orbs run testsuites/regression.yml --env uat',
                returnStatus: true
            )
            if (exitCode != 0) {
                currentBuild.result = 'FAILURE'
                error("Tests failed with exit code ${exitCode}")
            }
        }
    }
}
```

#### GitHub Actions
```yaml
- name: Run ORBS Tests
  run: |
    orbs run testsuites/regression.yml --env uat
  continue-on-error: false

- name: Check Test Results
  if: failure()
  run: echo "Tests failed"
```

#### GitLab CI
```yaml
test:
  script:
    - orbs run testsuites/regression.yml --env uat
  allow_failure: false
  artifacts:
    when: always
    paths:
      - reports/
```

#### Azure Pipelines
```yaml
- task: CmdLine@2
  displayName: 'Run ORBS Tests'
  inputs:
    script: 'orbs run testsuites/regression.yml --env uat'
  continueOnError: false
```

## Configuration

The console summary automatically reflects your configuration from `settings/execution.properties`:

### Retry Configuration
```properties
retry_enabled=true
retry_max_attempts=2
```

### Self-Healing Configuration
```properties
self_healing_enabled=true
self_healing_max_attempts=5
```

### Browser Configuration
```properties
browser_headless=true
```

## Programmatic Access

The console summary functionality is available programmatically through the `ConsoleSummary` class:

```python
from orbs.console_summary import ConsoleSummary

# Generate summary from overview data
summary_text = ConsoleSummary.generate(overview_data)
print(summary_text)

# Get exit code for CI/CD
exit_code = ConsoleSummary.get_exit_code(overview_data)

# Print summary to console
ConsoleSummary.print_summary(overview_data)
```

## Implementation Details

### Retry Tracking
Retries are tracked at the test case level. Each time a test case is retried:
1. The retry counter is incremented
2. The driver is reset for a clean state
3. The test is re-executed
4. Screenshots can be captured (based on configuration)

### Exit Code Flow
1. Test execution starts with exit code 0
2. Tests run and results are collected
3. Report generator creates overview with pass/fail counts
4. Console summary displays results
5. Exit code is determined: 0 if all passed, 1 if any failed
6. Framework exits with appropriate code

## Benefits

### For Developers
- Quick visual feedback on test results
- Easy identification of test status
- Human-readable duration formatting

### For CI/CD
- Standard exit codes for pipeline integration
- Fail-fast behavior when tests fail
- Clear indication of test status

### For Reports
- Consistent summary format
- All key metrics in one place
- Color-coded for quick scanning

## Example Output Scenarios

### All Tests Pass
```
==================================================
ORBS TEST EXECUTION SUMMARY
==================================================
Total Tests     : 15
Passed          : 15
Failed          : 0
Skipped         : 0
Retries         : 0
Duration        : 2m 15s
Environment     : production
Browser         : Chrome (headless)
Self-Healing    : Enabled
Retry           : Disabled
==================================================
STATUS: PASSED
==================================================
```
Exit Code: 0

### Some Tests Fail
```
==================================================
ORBS TEST EXECUTION SUMMARY
==================================================
Total Tests     : 20
Passed          : 17
Failed          : 3
Skipped         : 0
Retries         : 5
Duration        : 5m 42s
Environment     : uat
Browser         : Firefox (headed)
Self-Healing    : Enabled
Retry           : Enabled (max 2)
==================================================
STATUS: FAILED
==================================================
```
Exit Code: 1

### With Skipped Tests
```
==================================================
ORBS TEST EXECUTION SUMMARY
==================================================
Total Tests     : 25
Passed          : 20
Failed          : 0
Skipped         : 5
Retries         : 0
Duration        : 3m 8s
Environment     : dev
Browser         : Chrome (headed)
Self-Healing    : Disabled
Retry           : Disabled
==================================================
STATUS: PASSED
==================================================
```
Exit Code: 0
