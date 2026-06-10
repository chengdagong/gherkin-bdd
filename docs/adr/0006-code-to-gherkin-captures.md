# Code to Gherkin captures current behavior; it does not design new behavior

The code-to-gherkin skill backfills `.feature` coverage by reading the code and
recording what it does **today**, in product language. Capture, not design: the
skill must not invent behavior the code does not have, and must not "fix"
behavior while recording it.

Two consequences of treating backfill as capture were decided here:

**Characterization tests pass immediately.** Every backfilled scenario gets a
test (per `BDD.md`), but the red-green order does not apply: red-green verifies
*new* behavior, while a characterization test verifies that the scenario
describes reality — so it must pass against the current code on first run. A
failing characterization test indicts the scenario, not the code.

**Suspicious behavior becomes a question, never a silent spec.** When code
contradicts its own naming, comments, docs, or obvious user expectation, the
skill asks the user instead of writing the defective outcome into a scenario.
If the user rules it intended, it is captured like any other behavior. If the
user rules it a defect, the scenario records the *intended* behavior — its
failing test is the red of a future fix, making the mismatch visible instead of
enshrined. This is the backfill-time application of the BDD rule's "if code and
a `.feature` file disagree" clause.

## Consequences

- Backfill is re-runnable: the inventory step adds only what is still missing.
- A wave of backfilled scenarios may include `@todo` entries (tests that cannot
  be built yet); they follow the existing `@todo` debt rules in `BDD.md`.
- The skill ships with installs as a companion skill (one `SKILL.md`), like
  bdd-bootstrap — installation stays bdd-bootstrap's job, so converting a
  non-BDD project is the composition: bootstrap, then code-to-gherkin.
- Behavior in `features/code-to-gherkin.feature`; its scenarios are
  agent-observable (`@agent`) and run with the live suite.
