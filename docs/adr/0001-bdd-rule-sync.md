# BDD rule sync: reference BDD.md from the host's instruction file, via one script

`BDD.md` is the single source of truth for the BDD rule. Rather than copy its text
into each project, we inject a short *reference* to it into the host's canonical
instruction file (`CLAUDE.md` for Claude, `AGENTS.md` for Codex), inside a managed
region marked by HTML comments. One script, `scripts/check_bdd_sync.py`, owns this:
the installer runs it once (as a subprocess, fed the same payload a hook sends) and
a `SessionStart` hook runs the same script on every start/resume. It takes `--host`
and `--bdd-ref` and refreshes the managed region idempotently.

The reference is host-specific because the hosts differ: Claude Code expands
`@path` imports into context, so we write `@<bdd-ref>` and `BDD.md` loads
automatically; Codex does not expand imports, so we write an imperative directive
that requires the agent to read `BDD.md`.

## Considered options

- Inline `BDD.md`'s full text into the instruction file — rejected: it duplicates
  the rule and drifts from `BDD.md`; a reference keeps a single source of truth.
- Remind instead of sync — rejected: the reference should be guaranteed present.
- Duplicate the sync logic in the installer and the hook — rejected: one script,
  one implementation.
- Detect the host at runtime — rejected as fragile; host and path are known at
  install time and baked into the command.
