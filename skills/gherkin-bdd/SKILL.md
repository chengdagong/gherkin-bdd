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
- Follow the project's existing Gherkin language. If no Gherkin files exist yet,
  use the user's session language; for Simplified Chinese, include
  `# language: zh-CN` and localized keywords such as `功能`, `场景`, `假如`,
  `当`, and `那么`.

## Drafting Flow

1. Identify the actor, the business goal, and the observable outcome.
2. Name the `Feature` / `功能` after the capability, not the implementation.
3. Add one happy-path scenario before edge cases.
4. Add failure, permission, or boundary scenarios only when they affect product behavior.
5. Check each step for testability:
   - `Given` / `假如` describes existing state.
   - `When` / `当` describes one user or system action.
   - `Then` / `那么` describes visible, persisted, or externally observable result.
6. If implementation is requested, map scenarios to step definitions after the feature text is stable.

## Review Checklist

- The feature title names a user-facing capability.
- Scenario names describe outcomes.
- Steps avoid hidden assertions like "the system should be correct".
- Steps do not depend on timing unless timing is part of the behavior.
- Each scenario can fail for one clear product reason.
- Examples use realistic values, but avoid real private data.
- The wording leaves room for different UI implementations unless the UI detail is the behavior.

## Gherkin to HTML

When the user wants to read the project's Gherkin files as one easy-to-read,
searchable page, run the converter shipped in this skill's `scripts/` directory:

```
python3 <this-skill-dir>/scripts/gherkin_to_html.py --project-dir .
```

It writes `docs/gherkin.html` by default, creating `docs/` when needed
(override with `--out`) — a single self-contained Gherkin Reader page rendering
every `.feature` file in the project as it is, ready to open in a browser with
no server and no network. It uses Gherkin file tabs, scenario counts, collapsible
scenarios, Given/When/Then phase spacing, search/filtering, local theme
switching, and Chinese/English UI labels plus displayed Gherkin keywords.
It currently supports English Gherkin files and Simplified Chinese files that
declare `# language: zh-CN`; other localized Gherkin languages are outside the
current support scope. Display language can localize keywords without rewriting
the source files. It scans all project-owned Gherkin files, not just `features/`;
dependency and hidden directories are skipped. A file that does not parse as
Gherkin is still listed, as plain text with a parse warning.

## Output Shape

When drafting a feature, prefer this structure:

```gherkin
# language: zh-CN
功能: <capability>
  <short business description when useful>

  场景: <observable outcome>
    假如 <relevant starting state>
    当 <actor does one thing>
    那么 <observable result>
```

When reviewing a feature, return:

- Behavior gaps
- Ambiguous wording
- Scenarios to add or remove
- Step definition notes, if implementation is in scope

Use `$ARGUMENTS` as the user's requested feature, scenario, or review target when this skill is invoked as a Claude Code slash command.
