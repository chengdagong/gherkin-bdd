Feature: BDD rule sync
  The BDD rule is kept present in the host's canonical instruction file —
  CLAUDE.md for Claude Code, AGENTS.md for Codex — both when the plugin is
  installed and on every session start. One script does this in both places.

  Scenario: Claude session, no instruction files
    Given a Claude Code project with no CLAUDE.md or AGENTS.md
    When the BDD sync runs for the claude host
    Then a CLAUDE.md is created containing the BDD rule
    And no AGENTS.md is created

  Scenario: Codex session, no instruction files
    Given a Codex project with no CLAUDE.md or AGENTS.md
    When the BDD sync runs for the codex host
    Then an AGENTS.md is created containing the BDD rule
    And no CLAUDE.md is created

  Scenario: Host file missing while the other host's file exists
    Given a Claude Code project that has AGENTS.md but no CLAUDE.md
    When the BDD sync runs for the claude host
    Then CLAUDE.md is created with the BDD rule
    And the existing AGENTS.md is also kept in sync

  Scenario: The rule is already present
    Given a project whose canonical instruction file contains the BDD rule
    When the BDD sync runs
    Then the instruction files are left unchanged

  Scenario: Install runs the same sync
    Given a project being set up with the gherkin-bdd installer for a host
    When the plugin is installed
    Then the host's canonical instruction file carries the BDD rule
    And a session-start hook is registered to run the same sync script later
