# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A single-source, dual-host **plugin skeleton** that ships a Gherkin BDD workflow to both Codex and Claude Code. The reusable workflow is authored once; each host gets its own manifest pointing at the same shared content. A Python CLI (`bin/bdd-bootstrap`) installs that content into other projects.

This is plugin *source*, not an application. There is no build step and no third-party dependencies — the CLI is stdlib-only Python 3.

## Commands

```bash
# Run the full test suite (6 tests, all stdlib unittest)
python3 -m unittest discover -s tests

# Run a single test
python3 -m unittest tests.test_install_cli.InstallCliTest.test_appends_bdd_md_to_existing_project_instruction_files

# Inspect what an install would do, without writing anything
bin/bdd-bootstrap --dry-run
bin/bdd-bootstrap show-paths

# Install into a project (defaults: source=., project-dir=., both hosts)
bin/bdd-bootstrap --project-dir /path/to/project
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

**`BDD.md` is both rule and payload.** Its content is appended into the target project's `CLAUDE.md` / `AGENTS.md` (case-insensitive name match) idempotently — skipped if the content is already present — and the installer offers to create those files if missing (`--create-missing-instructions ask|yes|no`). The rule itself: every user-facing feature must have a matching `.feature` file (Gherkin), treated as the source of truth for behavior.

**Session-start sync.** The installer also registers a `SessionStart` hook per host that runs `scripts/check_bdd_sync.py` on every session start/resume. The script locates `BDD.md` relative to its own install dir (`<install>/scripts/..` works for both the Claude copy and the Codex symlink), reads the project root from the hook's stdin `cwd`, and **edits files in place**: it appends `BDD.md` to any `CLAUDE.md`/`AGENTS.md` missing the rule, or creates `CLAUDE.md` when neither exists. The sync is idempotent — once the rule is present nothing is rewritten. Hook entries are merged idempotently: Claude → `.claude/settings.json` (uses `${CLAUDE_PROJECT_DIR}`), Codex → `.codex/hooks.json` (absolute path + `statusMessage`). Both hosts share one hook schema (`hooks.SessionStart[].hooks[].command`). Claude does **not** load hooks from a copied skill dir, so the hook must live in `settings.json`, not the installed skill folder. Behavior is specified in [features/bdd-sync-check.feature](features/bdd-sync-check.feature).

**Project-level only.** The CLI never writes to `~/.claude`, `~/.agents`, or any user-level location.

## Working in the CLI

`bin/bdd-bootstrap` has no `.py` extension and is loaded in tests via `SourceFileLoader`. `main(argv, input_func=input)` takes both the arg list and the interactive-prompt function as parameters so tests can drive it directly — preserve these seams when changing argument parsing or the create-missing-files prompt. Argument handling is slightly unusual: `show-paths` is the only real subcommand; any other invocation is parsed as install flags with `command="run"`.

## Conventions

- `SKILL.md` frontmatter (`name`, `description`) drives skill discovery; `$ARGUMENTS` in the skill body is the Claude Code slash-command argument hook.
- Do not place `README.md` (or any plain markdown) directly under `agents/` — Claude Code treats markdown files there as agent definitions.
- `.claude/skills/gherkin-bdd/` in this repo is a **copy-mode self-install** (the plugin dogfooded into its own project). Because it is a copy, it does not update when you edit `skills/...`; refresh it with `bin/bdd-bootstrap --target claude --force`. Edit the top-level source, not this copy.
