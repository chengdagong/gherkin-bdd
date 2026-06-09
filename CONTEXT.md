# Gherkin BDD Plugin

A shared plugin that gives Codex and Claude Code one Gherkin BDD workflow and keeps a BDD rule present in each project it is installed into.

## Language

**Feature**:
A unit of user-facing application behaviour. Every feature is specified in a Gherkin `.feature` file, which is the source of truth for that behaviour.
_Avoid_: conflating it with the Gherkin `Feature:` keyword (that is syntax), or with a code module or implementation task.

**BDD rule**:
The project requirement that every feature has a matching `.feature` file, treated as the source of truth for its behaviour. Its canonical text is `BDD.md`.
_Avoid_: "the convention", "the policy", "BDD requirements".

**Host**:
An agent platform the plugin installs into — Claude Code or Codex. Each host reads its own instruction file and loads hooks in its own way.
_Avoid_: "platform", "client", "IDE", "editor".

**Instruction file**:
The project-root file a host reads for standing agent instructions: `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex.
_Avoid_: "config file", "rules file", "prompt file".

**Canonical instruction file**:
The one instruction file a given host actually reads — `CLAUDE.md` for the `claude` host, `AGENTS.md` for the `codex` host. The BDD rule must be present here for that host to see it.
_Avoid_: "default instruction file".
