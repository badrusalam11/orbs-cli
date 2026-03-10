Feature: Search functionality
  @positive
  Scenario Outline: Successful search
    Given the user opens the search page
    When the user searches for <keyword>
    Then the user should see results

Examples:
  | keyword          |
  | orbs automation  |
