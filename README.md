# Gherkin BDD

**English** | [中文](README.zh-CN.md)

A shared Gherkin BDD skill for Codex and Claude Code, plus a sync mechanism that keeps every installed project pointed at one BDD rule: each application feature is specified by a `.feature` file, and that Gherkin file is the source of truth for app behavior.

What ships:

- `skills/gherkin-bdd/SKILL.md` — the Gherkin BDD workflow (drafting, reviewing, and implementing behavior specs)
- `skills/bdd-bootstrap/SKILL.md` — a skill that runs the installer for whichever host the session is running in
- `BDD.md` — the BDD rule text, the single source of truth
- `scripts/check_bdd_sync.py` — keeps a reference to the rule in each host's instruction file
- `bin/bdd-bootstrap` — the per-project installer

There is no plugin packaging: both hosts discover project-level skills natively, so the installer just lays files down and registers one hook.

## Install

Install into the **current directory**, one host at a time:

```bash
bin/bdd-bootstrap claude   # Claude Code
bin/bdd-bootstrap codex    # Codex
```

The single positional argument (`claude` or `codex`) is required. The source is the repository that ships `bin/bdd-bootstrap`; the install target is your current working directory — so `cd` into the project you want to set up, then run the command. Re-running is idempotent.

What gets installed — and nothing else:

|  | Claude Code | Codex |
|---|---|---|
| Skills (`gherkin-bdd`, `bdd-bootstrap`) | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| `SessionStart` hook | `.claude/settings.json` | `.codex/hooks.json` |
| Rule reference (managed region) | `CLAUDE.md` | `AGENTS.md` |

The install is a self-contained copy — **commit the installed files with your project**. That way collaborators get the skill, the session hook, and the file the `CLAUDE.md` import points at without running the installer themselves. If you gitignore the install directory instead, the `@`-import in `CLAUDE.md` dangles (harmlessly — the rule is just not auto-loaded) until each clone runs the installer once. To pick up changes made in this repository (including `BDD.md`), re-run the installer in the project.

The CLI only supports project-level installation. It does not write to `~/.claude`, `~/.codex`, `~/.agents`, or any other user-level location.

## BDD rule sync

`BDD.md` is the single source of truth for the rule. Instead of copying its text into your project, the sync injects a short **reference** to it into the host's canonical instruction file — `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex — inside a managed region marked by HTML comments. The reference is host-specific:

- **Claude Code** expands `@path` imports, so the reference is `@<path-to-BDD.md>` and `BDD.md` is loaded into context automatically.
- **Codex** does not expand imports, so the reference is an imperative directive requiring the agent to read `BDD.md`.

A single script, `scripts/check_bdd_sync.py`, owns this. The installer runs it once (feeding it the same JSON payload a hook would), and a `SessionStart` hook runs the **same** script on every session start/resume. It creates the canonical file if absent, refreshes the managed region, and does nothing once the reference is current (idempotent). It never blocks the session. Claude Code only loads hooks from `settings.json`, not from a skill directory, which is why the hook lives in `.claude/settings.json`.

## Using the skills

In Claude Code, run `/gherkin-bdd` (or just describe Gherkin work — the skill description triggers it). Codex lists project skills automatically and loads the skill when a task matches. After re-installing, restart the session (Claude Code: or run `/reload-plugins`).

`/bdd-bootstrap` re-runs the installer for the current project from inside a session: it detects whether it is running in Claude Code or Codex and passes the matching host argument. Name a host explicitly (`/bdd-bootstrap codex`) to install for the other host.

## Developing this repo

This repository dogfoods its own skill but gitignores the install artifacts (`.claude/`), so after a fresh clone run `bin/bdd-bootstrap claude` once. Until then the `@`-import at the end of `CLAUDE.md` dangles and the BDD rule is not auto-loaded.

The `.feature` files under `features/` are the executable test suite (pytest-bdd). Set up and run:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

Scenarios tagged `@agent` are excluded from automation and verified with an agent in the loop instead.
