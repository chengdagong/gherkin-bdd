---
name: bdd-bootstrap
description: Set up or refresh the Gherkin BDD skill and BDD-rule sync in the current project. Use when the user wants to install gherkin-bdd, bootstrap BDD, re-install or refresh the BDD setup, or runs /bdd-bootstrap.
---

# BDD Bootstrap

Run the `bdd-bootstrap` installer for the coding agent this session is running in. The
installer lays the Gherkin BDD skill into the project's skills directory and
registers a session-start hook that keeps the BDD rule referenced from the
project's instruction file. It is idempotent — re-running refreshes the install
in place.

## Steps

1. **Pick the coding agent argument.**
   - If the user named a coding agent when invoking the skill (`claude` or `codex` —
     `$ARGUMENTS` when run as a Claude Code slash command), use that.
   - Otherwise use the environment you are running in: pass `claude` if you are
     Claude Code, `codex` if you are Codex. As a shell-level cross-check, the
     environment variable `CLAUDECODE=1` indicates Claude Code.
   - If you cannot tell which coding agent you are running in, ask the user instead of
     guessing.

2. **Locate the installer.** It is `bin/bdd-bootstrap` in the gherkin-bdd
   source repository:
   - If the current project contains `bin/bdd-bootstrap` together with
     `skills/gherkin-bdd/SKILL.md`, you are inside the source repository — use
     it directly.
   - Otherwise ask the user where their clone of `gherkin-bdd` lives, or offer
     to clone `https://github.com/chengdagong/gherkin-bdd` to a location they
     choose. Cloning and installing need the user's consent: if you are running
     non-interactively and cannot ask, report that the source repository is
     needed and stop — do not clone or install on your own.

3. **Run it from the project root.** The installer installs into the current
   working directory:

   ```bash
   cd <project-root> && <source-repo>/bin/bdd-bootstrap <coding-agent>
   ```

4. **Report the result.** Tell the user where the skills landed, where the
   session hook was registered, and that the instruction file now references
   `BDD.md`. Remind them to restart the session (or reload skills) so newly
   installed skills are discovered, and to commit the installed files with the
   project.

Note for Codex sessions: the sandbox may refuse writes to `.codex/hooks.json`
(Codex protects its own config). If that write is blocked and cannot be
approved, report it and tell the user to run `bin/bdd-bootstrap codex` from a
regular terminal to finish hook registration.
