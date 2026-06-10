Feature: Bootstrap skill
  A user can set up the current project from inside an agent session by invoking
  the bdd-bootstrap skill. The skill works out which host the session is running
  in and runs the installer with the matching host argument.

  @agent
  Scenario: Invoked from Claude Code
    Given a session running in Claude Code
    When the user invokes the bdd-bootstrap skill without naming a host
    Then the installer runs for the claude host in the current project

  @agent
  Scenario: Invoked from Codex
    Given a session running in Codex
    When the user invokes the bdd-bootstrap skill without naming a host
    Then the installer runs for the codex host in the current project

  @agent
  Scenario: The user names a host explicitly
    Given a session running in Claude Code
    When the user invokes the bdd-bootstrap skill naming the codex host
    Then the installer runs for the codex host in the current project

  @agent
  Scenario: The host cannot be determined
    Given a session whose host cannot be identified
    When the user invokes the bdd-bootstrap skill without naming a host
    Then the user is asked which host to install for instead of guessing

  @agent
  Scenario: The installer source is not available locally
    Given the gherkin-bdd source repository is not present in the project
    When the user invokes the bdd-bootstrap skill
    Then the user is asked where their gherkin-bdd clone lives or offered a fresh clone

  Scenario: The bootstrap skill ships with installs
    Given a project being set up with the gherkin-bdd installer for a host
    When the skill is installed
    Then the bdd-bootstrap skill is placed alongside the gherkin-bdd skill
