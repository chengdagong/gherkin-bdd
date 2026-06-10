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

Both entries call `scripts/check_bdd_sync.py --host <host> --bdd-ref <path>`. The
script keeps a reference to `BDD.md` in the host's canonical instruction file — an
`@`-import in `CLAUDE.md` for Claude, an imperative "must read" directive in
`AGENTS.md` for Codex — inside a managed region it owns and refreshes. The
installer runs the same script once at install time, so install-time and
session-time sync share one implementation. See `scripts/check_bdd_sync.py` and
`features/bdd-sync-check.feature`.
