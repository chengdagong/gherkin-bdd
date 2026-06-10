---
name: code-to-gherkin
description: Use when converting a non-BDD project to BDD, backfilling Gherkin coverage from existing code, or recording user-facing behavior that no Gherkin file describes yet. Works whether the project has partial Gherkin coverage or none at all.
---

# Code to Gherkin

Read the project's code, find user-facing behavior that no `.feature` file
describes yet, and record it as Gherkin scenarios. Converting a project that
has never used BDD and topping up a partially covered one are the same job:
cover the gap.

## The Capture Rule

Backfilled scenarios record what the code does **today**, in product language.
You are a scribe, not a designer: do not invent behavior the code does not
have, and do not "fix" behavior while recording it.

The one exception is suspicion. When behavior looks like a defect — the code
contradicts its own naming, comments, docs, or obvious user expectation — do
not spec it. Ask the user whether it is intended:

- **Intended** → record it as a scenario like any other.
- **A defect** → record the *intended* behavior as the scenario. Its test will
  fail against the current code; that failure is the red of a future fix, and
  the mismatch is now visible instead of enshrined.

## Workflow

1. **Inventory the existing coverage.** Find every Gherkin file and list
   the behaviors it describes. No Gherkin files is simply an empty inventory.
2. **Survey the code for user-facing behavior.** Walk the entry points: CLI
   commands and flags, HTTP routes, UI pages and actions, public APIs,
   scheduled jobs, emitted files and messages. Use existing tests and docs as
   evidence of intent. Collect *behaviors* — what a user can do and observe —
   not functions.
3. **List the gaps.** Behavior present in the code but absent from the
   inventory, grouped by capability. Agree scope with the user when a
   conversation is possible; otherwise cover every gap found.
4. **Write the Gherkin files.** Follow the gherkin-bdd skill's working rules:
   name features after capabilities, describe observable outcomes, keep
   implementation names out of the text. When a capability already has a
   Gherkin file, extend that file in its own vocabulary — never describe the
   same behavior twice.
5. **Bind characterization tests.** Every backfilled scenario gets a test in
   the project's agreed test framework (none agreed — ask, per the BDD rule).
   These tests must **pass immediately**: they verify that the scenario
   describes reality, so a failing one means the scenario is wrong — rewrite
   the scenario, not the code. Red-green order is for *new* behavior; capture
   is not new behavior. A scenario whose test cannot be built yet is tagged
   `@todo` with an adjacent `# TODO:` comment, per the BDD rule.
6. **Leave the project BDD-driven.** If the BDD rule is not installed (no
   gherkin-bdd managed region in the project instructions), run the
   bdd-bootstrap skill. From here on, new behavior follows the normal
   feature-first, red-green workflow.

Re-running the skill is safe: the inventory step makes it add only what is
still missing.

Use `$ARGUMENTS` to narrow the survey (a subsystem, directory, or capability)
when provided; otherwise survey the whole project.
