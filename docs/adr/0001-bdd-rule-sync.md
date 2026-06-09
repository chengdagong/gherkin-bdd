# BDD rule sync: one script, run at install and on every session start

The BDD rule must stay present in each host's canonical instruction file
(`CLAUDE.md` for Claude, `AGENTS.md` for Codex). We sync it with a single script,
`scripts/check_bdd_sync.py`, which the installer runs once (as a subprocess, fed
the same stdin payload a hook sends) and a `SessionStart` hook runs on every
start/resume. The script auto-fixes (creates/appends the rule) rather than only
warning, and takes `--host` so it edits the file the host actually reads.

## Considered options

- Duplicate the sync logic inside the installer and the hook separately — rejected:
  two implementations to keep in step.
- Remind instead of auto-fix — rejected: the rule should be guaranteed present, not
  merely flagged.
- Detect the host at runtime from the hook payload — rejected as fragile; the host is
  known at install time and baked into the command as `--host`.
