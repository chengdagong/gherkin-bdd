Feature: BDD rule sync on session start
  When an agent starts working in a project that uses this plugin, the BDD rule
  is kept in sync into the project instruction files automatically.

  Scenario: An instruction file is missing the BDD rule
    Given a project whose CLAUDE.md does not contain the BDD rule
    When an agent session starts
    Then the BDD rule is appended to CLAUDE.md

  Scenario: Instruction files already contain the BDD rule
    Given a project whose CLAUDE.md contains the BDD rule
    When an agent session starts
    Then CLAUDE.md is left unchanged

  Scenario: No instruction files exist
    Given a project with no CLAUDE.md or AGENTS.md
    When an agent session starts
    Then a CLAUDE.md is created containing the BDD rule

  Scenario: Installing the plugin registers the sync
    Given a project being set up with the gherkin-bdd installer
    When the plugin is installed for Claude Code and Codex
    Then a session-start sync is registered for each host without replacing existing hooks
