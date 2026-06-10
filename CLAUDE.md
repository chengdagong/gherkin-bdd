# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A shared **Gherkin BDD skill + per-project installer** for Codex and Claude Code. The workflow is authored once in `skills/gherkin-bdd/SKILL.md`; `bin/bdd-bootstrap` copies it (with `BDD.md` and the sync script) into a target project's host-native skills directory and registers a SessionStart hook. There is **no plugin packaging** — both hosts discover project-level skills natively (decision in [docs/adr/0002-no-plugin-packaging.md](docs/adr/0002-no-plugin-packaging.md)).

This is tool source, not an application. There is no build step; the shipped code is stdlib-only Python 3, and the test suite (dev-only) uses pytest + pytest-bdd.

## Commands

```bash
# One-time test setup
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

# Run the executable Gherkin specs (features/*.feature via pytest-bdd)
.venv/bin/pytest

# Run a single scenario (-k matches the generated test name)
.venv/bin/pytest -k stale_managed_region

# Install into the CURRENT directory for one host (cd into the target project first)
bin/bdd-bootstrap claude
bin/bdd-bootstrap codex
```

## Architecture

**The install contract is three skills + one hook.** `install_skill` copies exactly `SKILL.md`, `BDD.md`, `scripts/check_bdd_sync.py`, and `scripts/gherkin_to_html.py` into `<skills-dir>/gherkin-bdd/`; `install_companion_skill` copies one `SKILL.md` each into `<skills-dir>/bdd-bootstrap/` (the in-session skill that re-runs the installer for the detected host) and `<skills-dir>/code-to-gherkin/` (backfills `.feature` coverage from existing code — capture semantics in [docs/adr/0006-code-to-gherkin-captures.md](docs/adr/0006-code-to-gherkin-captures.md)); nothing else ships. `HOST_SKILL_DIRS` / `HOST_HOOK_FILES` in [bin/bdd-bootstrap](bin/bdd-bootstrap) map each host to its skills directory (Claude → `.claude/skills`, Codex → `.agents/skills`) and hook config (Claude → `.claude/settings.json`, Codex → `.codex/hooks.json`). Adding a new shipped file means adding an explicit `copy_path` call.

**`BDD.md` stays the single source of truth; instruction files only reference it.** A single script, `scripts/check_bdd_sync.py`, injects a short reference to `BDD.md` into the host's **canonical instruction file** (`CLAUDE.md` for Claude, `AGENTS.md` for Codex), inside a managed region marked by `<!-- gherkin-bdd:rule:start/end -->`. The reference is host-specific: Claude gets an `@<bdd-ref>` import (auto-loaded into context); Codex, which has no import mechanism, gets an imperative "you MUST read it" directive. The script runs in two places:
- **Install time** — the installer invokes the script as a subprocess (`run_bdd_sync`), feeding it the same JSON payload a SessionStart hook would. Install-time and session-time sync share one implementation.
- **Session start** — the installer registers a `SessionStart` hook (Claude with `${CLAUDE_PROJECT_DIR}`; Codex with an absolute path + `statusMessage`) running the same script on every start/resume. Both hosts share one hook schema (`hooks.SessionStart[].hooks[].command`).

The script takes `--host {claude|codex}` and `--bdd-ref <path>` (both baked into the hook command and the install-time call). It creates the canonical file if absent, refreshes the managed region, and is idempotent + non-blocking. Claude does **not** load hooks from a skill dir, so the hook must live in `settings.json`. Decision recorded in [docs/adr/0001-bdd-rule-sync.md](docs/adr/0001-bdd-rule-sync.md); behavior in [features/bdd-sync-check.feature](features/bdd-sync-check.feature).

**The gherkin HTML page is a generated artifact, not source.** `scripts/gherkin_to_html.py` (stdlib-only, shipped with the skill) scans the project for `.feature` files — skipping hidden and dependency directories — and renders them, as they are, into one self-contained HTML page (`gherkin.html` by default, gitignored here). It parses English Gherkin line-by-line; a file that does not parse is still listed as plain text with a parse warning. Behavior in [features/gherkin-to-html.feature](features/gherkin-to-html.feature).

**Project-level only.** The CLI never writes to `~/.claude`, `~/.codex`, `~/.agents`, or any user-level location.

**Testing: pytest-bdd (user-chosen per the BDD.md workflow).** The `.feature` files under `features/` are the executable specs; [tests/test_features.py](tests/test_features.py) binds them via `scenarios()` + step definitions, and pytest-bdd fails on unbound steps, which enforces the scenario↔test trace. Scenarios tagged `@agent` bind to steps that drive a **live host session** ([tests/conftest.py](tests/conftest.py): canary probes via `claude -p` / `codex exec`); they are deselected from the default run and executed on demand with `.venv/bin/pytest -m "agent and not todo"` because they cost real model calls — the harness sanitizes inherited host-app env vars, so it runs from anywhere — including inside a Claude Code session — as long as the `claude` CLI's own login is fresh. The CLI and the desktop app keep **separate credentials**: a 401 from `claude -p` means the CLI's stored login is stale; run `claude` → `/login` once in a terminal to fix it. Single-run, no retries. The tag changes where a test runs, not whether it exists. Scenarios tagged `@todo` have no test yet and must carry an adjacent `# TODO:` comment (why + unblock condition) — a meta-test in the default suite fails on undocumented `@todo` debt. Policy in [docs/adr/0003-live-agent-tests.md](docs/adr/0003-live-agent-tests.md).

## Working in the CLI

`bin/bdd-bootstrap` has no `.py` extension and is loaded in tests via `SourceFileLoader`. It takes one required positional, `host` (`claude` or `codex`) — no flags, no subcommands. The **source** is the script's own repo (`SOURCE = Path(__file__).resolve().parent.parent`) and the install **target** is `Path.cwd()`, so you run it from inside the project you're setting up. Re-running is idempotent: it removes and re-lays the skill directory, re-merges the hook entry, and the sync script no-ops once the reference is current. `main(argv)` returns an int; tests drive it by `chdir`-ing into a temp project.

## Conventions

- `SKILL.md` frontmatter (`name`, `description`) drives skill discovery on both hosts; `$ARGUMENTS` in the skill body is the Claude Code slash-command argument hook. Keep `SKILL.md` portable — no assumptions about one host's tool names.
- `.claude/skills/gherkin-bdd/` in this repo is a **self-install** (the skill dogfooded into its own project). It is a copy, so it does not update when you edit `skills/...`; refresh it by running `bin/bdd-bootstrap claude` again. Edit the top-level source, not this copy. `.claude/` is gitignored here, so after a fresh clone run `bin/bdd-bootstrap claude` once — until then the `@`-import at the end of this file dangles and the BDD rule is not auto-loaded.

## Agent skills

### Issue tracker

Issues and PRDs live in the `chengdagong/gherkin-bdd` GitHub Issues, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles, each mapped to a label of the same name (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root, created lazily. See `docs/agents/domain.md`.

<!-- gherkin-bdd:rule:start -->
## BDD rule

@.claude/skills/gherkin-bdd/BDD.md
<!-- gherkin-bdd:rule:end -->
