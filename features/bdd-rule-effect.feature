Feature: BDD rule effect
  Installing the plugin must actually deliver the BDD rule into agent sessions:
  Claude Code auto-loads it through the CLAUDE.md import, Codex reads it when
  AGENTS.md directs it to, and a project's installed copy stays frozen until the
  installer is re-run.

  @agent
  Scenario: Claude Code auto-loads the rule through the import
    Given an installed Claude Code project whose rule copy contains a canary line
    When a headless Claude session is asked for the canary without tool access
    Then the canary line is returned

  @agent
  Scenario: Codex reads the rule the directive points at
    Given an installed Codex project whose rule copy contains a canary line
    When a headless Codex session is asked to report the canary from its required reading
    Then the canary line is returned

  @agent
  Scenario: A source update is invisible until re-install
    Given an installed Claude Code project whose rule copy contains a canary line
    And the source rule's canary has since changed
    When a headless Claude session is asked for the canary without tool access
    Then the original canary line is returned, not the updated one

  @agent
  Scenario: Re-installing delivers the updated rule
    Given an installed Claude Code project whose rule copy contains a canary line
    And the source rule's canary has since changed
    And the installer is re-run in the project
    When a headless Claude session is asked for the canary without tool access
    Then the updated canary line is returned
