# Gherkin BDD

A shared skill that gives Codex and Claude Code one Gherkin BDD workflow and keeps a BDD rule referenced in each project it is installed into.

## Language

**Feature**:
A unit of user-facing application behaviour. Every feature is specified in a Gherkin `.feature` file, which is the source of truth for that behaviour.
_Avoid_: conflating it with the Gherkin `Feature:` keyword (that is syntax), or with a code module or implementation task.

**BDD rule**:
The project requirement that every feature has a matching `.feature` file, treated as the source of truth for its behaviour. Its canonical text is the tool's `BDD.md`, shipped with the skill and refreshed by re-installing; projects reference it and do not edit their installed copy.
_Avoid_: "the convention", "the policy", "BDD requirements".

**Host**:
An agent platform the plugin installs into — Claude Code or Codex. Each host reads its own instruction file and loads hooks in its own way.
_Avoid_: "platform", "client", "IDE", "editor".

**Instruction file**:
The project-root file a host reads for standing agent instructions: `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex.
_Avoid_: "config file", "rules file", "prompt file".

**Canonical instruction file**:
The one instruction file a given host actually reads — `CLAUDE.md` for the `claude` host, `AGENTS.md` for the `codex` host. The BDD rule must be reachable from here for that host to see it.
_Avoid_: "default instruction file".

**Rule reference**:
The pointer to `BDD.md` placed in a host's instruction file in place of the rule's full text. For Claude it is an `@`-import that auto-loads; for Codex it is a directive requiring the agent to read `BDD.md`.
_Avoid_: "the rule copy", "inlined rule".

**Bootstrap skill**:
The skill that runs the installer from inside an agent session, targeting the host the session runs in unless the user names one.
_Avoid_: conflating it with the installer CLI itself (`bin/bdd-bootstrap`).

**Agent scenario**:
A scenario verifiable only by observing agent behavior in a live session. Tagged `@agent` in the `.feature` file; its automated test drives a live agent session and runs on demand, outside the default test run.
_Avoid_: "manual scenario", "untestable scenario", "exempt scenario".

**Todo scenario**:
A scenario declared in a `.feature` file whose test cannot be built yet. Tagged `@todo` with an adjacent comment recording why and what unblocks it — tracked debt, never silently dropped.
_Avoid_: "pending scenario", "skipped scenario".

**Managed region**:
The block in an instruction file, delimited by `<!-- gherkin-bdd:rule:start -->` / `<!-- gherkin-bdd:rule:end -->` comments, that the sync owns and refreshes. Content inside it is overwritten on sync; the rule text itself changes upstream in the gherkin-bdd tool, not in the project.
_Avoid_: "the snippet", "the injected block".
