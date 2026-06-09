Feature: User login
  Registered users need to sign in before accessing private workspace pages.

  Scenario: Registered user signs in with valid credentials
    Given a registered user exists with email "alex@example.com"
    When the user signs in with the correct password
    Then the user lands on the workspace home page

  Scenario: User signs in with a wrong password
    Given a registered user exists with email "alex@example.com"
    When the user signs in with an incorrect password
    Then the user sees an authentication error
    And the user remains signed out
