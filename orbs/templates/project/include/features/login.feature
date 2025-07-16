Feature: Login functionality
  @positive
  Scenario Outline: Successful login
    Given the user opens the login page
    When the user fill username <username> and password <password>
    Then the user should see the dashboard

Examples:
  | username | password           |
  | John Doe | ThisIsNotAPassword |