# Gherkin BDD

A shared skill that gives Codex and Claude Code one Gherkin BDD workflow and keeps a BDD rule referenced in each project it is installed into.

## Language

**Feature**:
A unit of user-facing application behaviour. Every feature is specified in a Gherkin `.feature` file, which is the source of truth for that behaviour.
_Avoid_: conflating it with the Gherkin `Feature:` keyword (that is syntax), or with a code module or implementation task.

**Gherkin file**:
A `.feature` source file that contains one Gherkin feature specification. It is the file-level artifact agents read, update, test against, and render into HTML.
_Avoid_: "feature file" when the sentence is about the file rather than the user-facing behaviour.

**BDD rule**:
The project requirement that every feature has a matching `.feature` file, treated as the source of truth for its behaviour. Its canonical text is the tool's `BDD.md`, shipped with the skill and refreshed by re-installing; projects reference it and do not edit their installed copy.
_Avoid_: "the convention", "the policy", "BDD requirements".

**Coding agent**:
An agent product the installer targets — currently Claude Code or Codex. Each coding agent reads its own instruction file and loads hooks in its own way.
_Avoid_: "host", "platform", "client", "IDE", "editor".

**Instruction file**:
The project-root file a coding agent reads for standing agent instructions: `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex.
_Avoid_: "config file", "rules file", "prompt file".

**Canonical instruction file**:
The one instruction file a given coding agent actually reads — `CLAUDE.md` for the `claude` coding agent, `AGENTS.md` for the `codex` coding agent. The BDD rule must be reachable from here for that coding agent to see it.
_Avoid_: "default instruction file".

**Rule reference**:
The pointer to `BDD.md` placed in a coding agent's instruction file in place of the rule's full text. For Claude it is an `@`-import that auto-loads; for Codex it is a directive requiring the agent to read `BDD.md`.
_Avoid_: "the rule copy", "inlined rule".

**Bootstrap skill**:
The skill that runs the installer from inside an agent session, targeting the coding agent the session runs in unless the user names one.
_Avoid_: conflating it with the installer CLI itself (`bin/bdd-bootstrap`).

**Code to Gherkin**:
The capability of reading a project's code and recording user-facing behavior that no Gherkin file describes yet as Gherkin scenarios — capture of what the code does today, not design of what it should do. Works identically with partial or zero existing coverage, and is re-runnable.
_Avoid_: "migration" or "conversion" (it is incremental, not one-shot), "reverse engineering".

**Characterization test**:
The test bound to a backfilled scenario. It must pass against the current code on first run, because it verifies that the scenario describes reality — a failure indicts the scenario, not the code. Red-green order applies only to new behavior.
_Avoid_: "regression test", "golden test".

**Agent scenario**:
A scenario verifiable only by observing agent behavior in a live session. Tagged `@agent` in the `.feature` file; its automated test drives a live agent session and runs on demand, outside the default test run.
_Avoid_: "manual scenario", "untestable scenario", "exempt scenario".

**Todo scenario**:
A scenario declared in a `.feature` file whose test cannot be built yet. Tagged `@todo` with an adjacent comment recording why and what unblocks it — tracked debt, never silently dropped.
_Avoid_: "pending scenario", "skipped scenario".

**Gherkin to HTML**:
The capability and command flow that renders every Gherkin file in a project — as it is, nothing summarized or left out — into one self-contained HTML page. Produced on demand by the `gherkin_to_html.py` script that ships with the skill; never served, never fetched from the network.
_Avoid_: "overview" or "summary" (the content is presented verbatim), "the report", "the docs site", "living documentation server", using it as the page title.

**Gherkin Reader**:
The generated HTML page experience produced by Gherkin to HTML. It is the human-facing reading surface for a project's Gherkin files, usually opened from `docs/gherkin.html`.
_Avoid_: using it to name the conversion capability or script.

**Managed region**:
The block in an instruction file, delimited by `<!-- gherkin-bdd:rule:start -->` / `<!-- gherkin-bdd:rule:end -->` comments, that the sync owns and refreshes. Content inside it is overwritten on sync; the rule text itself changes upstream in the gherkin-bdd tool, not in the project.
_Avoid_: "the snippet", "the injected block".
