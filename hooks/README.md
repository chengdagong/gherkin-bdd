# Hooks

Optional Claude Code hooks can live here as `hooks.json`.

Add hooks only for commands that are safe to run automatically and easy for users to understand.

## Session-start BDD sync

This plugin ships one hook by default: a `SessionStart` sync that keeps `BDD.md`
present in the project's `CLAUDE.md` / `AGENTS.md`.

It is **not** loaded from this directory. `bin/bdd-bootstrap` registers it into
the host's own config at install time, because Claude Code loads hooks from
`.claude/settings.json` (or a registered plugin), not from a copied skill folder:

- Claude Code → merged into `<project>/.claude/settings.json`
- Codex → merged into `<project>/.codex/hooks.json`

Both entries call `scripts/check_bdd_sync.py`, which appends `BDD.md` to any
instruction file missing the rule (creating `CLAUDE.md` if none exists) and is
idempotent once the rule is present. See `scripts/check_bdd_sync.py` and
`features/bdd-sync-check.feature`.
