---
name: gherkin-bdd
description: Use when writing, reviewing, refactoring, or implementing Gherkin BDD features, scenarios, acceptance criteria, step definitions, or Cucumber-style test plans.
---

# Gherkin BDD

Use this workflow when the user wants behavior written as Gherkin, wants existing scenarios reviewed, or wants implementation work guided by BDD acceptance criteria.

## Working Rules

- Keep business behavior separate from UI mechanics, test helper details, mocks, and implementation names.
- Prefer concrete examples over abstract descriptions.
- Write scenarios that a domain expert can read without knowing the codebase.
- Use `Rule` only when it clarifies a policy or invariant shared by multiple scenarios.
- Keep `Background` short. Put only facts that are true for every scenario in the feature.
- Avoid scenario outlines unless the examples table genuinely reduces repetition.
- When changing an existing feature, preserve the domain vocabulary already used in nearby scenarios.
- If a behavior change would make old data or old scenarios incompatible, ask whether to delete old data, migrate it, or support both versions.

## Drafting Flow

1. Identify the actor, the business goal, and the observable outcome.
2. Name the `Feature` after the capability, not the implementation.
3. Add one happy-path scenario before edge cases.
4. Add failure, permission, or boundary scenarios only when they affect product behavior.
5. Check each step for testability:
   - `Given` describes existing state.
   - `When` describes one user or system action.
   - `Then` describes visible, persisted, or externally observable result.
6. If implementation is requested, map scenarios to step definitions after the feature text is stable.

## Review Checklist

- The feature title names a user-facing capability.
- Scenario names describe outcomes.
- Steps avoid hidden assertions like "the system should be correct".
- Steps do not depend on timing unless timing is part of the behavior.
- Each scenario can fail for one clear product reason.
- Examples use realistic values, but avoid real private data.
- The wording leaves room for different UI implementations unless the UI detail is the behavior.

## Output Shape

When drafting a feature, prefer this structure:

```gherkin
Feature: <capability>
  <short business description when useful>

  Scenario: <observable outcome>
    Given <relevant starting state>
    When <actor does one thing>
    Then <observable result>
```

When reviewing a feature, return:

- Behavior gaps
- Ambiguous wording
- Scenarios to add or remove
- Step definition notes, if implementation is in scope

Use `$ARGUMENTS` as the user's requested feature, scenario, or review target when this skill is invoked as a Claude Code slash command.
