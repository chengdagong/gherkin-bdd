Feature: BDD rule sync
  BDD.md is the single source of truth for the rule. The plugin keeps a reference
  to it in the host's canonical instruction file — CLAUDE.md for Claude Code,
  AGENTS.md for Codex — both at install and on every session start. The reference
  lives in a managed region the plugin owns.

  Scenario: Claude gets an import reference
    Given a Claude Code project
    When the BDD sync runs for the claude host
    Then CLAUDE.md contains an @-import of BDD.md inside the managed region
    And no AGENTS.md is created

  Scenario: Codex gets a required-reading directive
    Given a Codex project
    When the BDD sync runs for the codex host
    Then AGENTS.md requires the agent to read BDD.md inside the managed region
    And no CLAUDE.md is created

  Scenario: Surrounding content is preserved
    Given a project whose CLAUDE.md already holds the user's own notes
    When the BDD sync runs for the claude host
    Then the managed region is added and the user's notes are left intact

  Scenario: A stale managed region is refreshed
    Given a project whose managed region holds outdated content
    When the BDD sync runs
    Then the managed region is rewritten from the current reference
    And it appears exactly once

  Scenario: The reference is already current
    Given a project whose managed region already holds the current reference
    When the BDD sync runs
    Then the instruction file is left unchanged

  Scenario: Install runs the same sync
    Given a project being set up with the gherkin-bdd installer for a host
    When the plugin is installed
    Then the host's canonical instruction file references BDD.md
    And a session-start hook is registered to run the same sync script later
