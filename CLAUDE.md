# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single-source, dual-host **plugin skeleton** that ships a Gherkin BDD workflow to both Codex and Claude Code. The reusable workflow is authored once; each host gets its own manifest pointing at the same shared content. A Python CLI (`bin/bdd-bootstrap`) installs that content into other projects.

This is plugin *source*, not an application. There is no build step and no third-party dependencies — the CLI is stdlib-only Python 3.

## Commands

```bash
# Run the full test suite (11 tests, all stdlib unittest)
python3 -m unittest discover -s tests

# Run a single test
python3 -m unittest tests.test_install_cli.InstallCliTest.test_claude_install_copies_tree_and_registers_hook

# Install into the CURRENT directory for one host (cd into the target project first)
bin/bdd-bootstrap claude
bin/bdd-bootstrap codex
```

Loading this plugin in Claude Code during development:

```bash
claude --plugin-dir .          # then run /gherkin-bdd:gherkin-bdd
```

After editing any plugin component, run `/reload-plugins` inside the Claude Code session.

## Architecture

**Single source, two manifests.** The workflow lives once in `skills/gherkin-bdd/SKILL.md`. Both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` point their `skills` field at `./skills/`. Keep host-specific UI fields in the matching manifest only — Codex validation is stricter and rejects Claude-only fields, so do not cross-pollinate the two manifests, and keep everything under `skills/` portable (no assumptions about one host's tool names).

**`SHARED_ENTRIES` is the install contract.** The tuple in [bin/bdd-bootstrap](bin/bdd-bootstrap) (`skills`, `docs`, `examples`, `scripts`, `hooks`, `README.md`, `BDD.md`) is the exact set of top-level entries the installer copies/symlinks. Adding a new shared folder (e.g. populating the currently-empty `agents/`) has **no effect until its name is added to `SHARED_ENTRIES`** — this is the main cross-file coupling to remember.

**Install modes differ per host by design** (see `install_claude` vs `install_codex`):
- **Claude → copy** into `<project>/.claude/skills/gherkin-bdd`. Self-contained, so it can be committed with the target project.
- **Codex → symlink** into `<project>/.agents/plugins/plugins/gherkin-bdd`, plus a registered entry in `<project>/.agents/plugins/marketplace.json`. Symlinks mean edits to shared source take effect without re-installing.

**`BDD.md` is rule and payload, kept in sync by one script.** The rule: every user-facing feature must have a matching `.feature` file (Gherkin), treated as the source of truth for behavior. That rule must live in the host's **canonical instruction file** — `CLAUDE.md` for Claude, `AGENTS.md` for Codex. A single script, `scripts/check_bdd_sync.py`, owns syncing it and runs in two places:
- **Install time** — `install_claude` / `install_codex` invoke the script as a subprocess (`run_bdd_sync`), feeding it the same JSON payload a SessionStart hook would. Install-time and session-time sync therefore share one implementation; the installer never re-implements the file editing.
- **Session start** — the installer registers a `SessionStart` hook (Claude → `.claude/settings.json` with `${CLAUDE_PROJECT_DIR}`; Codex → `.codex/hooks.json` with an absolute path + `statusMessage`) that runs the same script on every start/resume. Both hosts share one hook schema (`hooks.SessionStart[].hooks[].command`).

The script takes `--host {claude|codex}` (baked into both the hook command and the install-time call), locates `BDD.md` relative to its own install dir (works for both the Claude copy and the Codex symlink), and reads the project root from stdin `cwd`. It ensures the host's canonical file carries the rule (creating it if absent), appends the rule to any *other* existing instruction file that lacks it, never creates the other host's file, and is idempotent + non-blocking. Claude does **not** load hooks from a copied skill dir, so the hook must live in `settings.json`. Behavior is specified in [features/bdd-sync-check.feature](features/bdd-sync-check.feature).

**Project-level only.** The CLI never writes to `~/.claude`, `~/.agents`, or any user-level location.

## Working in the CLI

`bin/bdd-bootstrap` has no `.py` extension and is loaded in tests via `SourceFileLoader`. It takes one required positional, `host` (`claude` or `codex`) — no flags, no subcommands. The plugin **source** is the script's own repo (`SOURCE = Path(__file__).resolve().parent.parent`) and the install **target** is `Path.cwd()`, so you run it from inside the project you're setting up. Re-running is idempotent: it removes and re-lays the tree, re-merges the hook entry, and the shared sync script no-ops once the rule is present. `main(argv)` returns an int; tests drive it by `chdir`-ing into a temp project.

## Conventions

- `SKILL.md` frontmatter (`name`, `description`) drives skill discovery; `$ARGUMENTS` in the skill body is the Claude Code slash-command argument hook.
- Do not place `README.md` (or any plain markdown) directly under `agents/` — Claude Code treats markdown files there as agent definitions.
- `.claude/skills/gherkin-bdd/` in this repo is a **copy-mode self-install** (the plugin dogfooded into its own project). Because it is a copy, it does not update when you edit `skills/...`; refresh it by running `bin/bdd-bootstrap claude` again. Edit the top-level source, not this copy.

## Agent skills

### Issue tracker

Issues and PRDs live in the `chengdagong/gherkin-bdd` GitHub Issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, each mapped to a label of the same name (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root, created lazily. See `docs/agents/domain.md`.
