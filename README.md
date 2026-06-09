# Gherkin BDD Plugin

This repository is a shared plugin skeleton for Codex and Claude Code.

It keeps the reusable workflow in `skills/`, then gives each host its own manifest:

- Codex: `.codex-plugin/plugin.json`
- Claude Code: `.claude-plugin/plugin.json`
- BDD project rules: `BDD.md`

The shared skill lives at `skills/gherkin-bdd/SKILL.md`.

## Use In Codex

Install or package this directory as a Codex plugin source. The Codex manifest points to the shared `skills/` directory and keeps host-specific UI metadata in `.codex-plugin/plugin.json`.

For local validation:

```bash
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

## Use In Claude Code

For local development, load the plugin directly:

```bash
claude --plugin-dir .
```

Then run the namespaced skill:

```text
/gherkin-bdd:gherkin-bdd
```

After changing plugin components, run this inside Claude Code:

```text
/reload-plugins
```

## Install With CLI

Install this plugin into the **current directory**, one host at a time:

```bash
bin/bdd-bootstrap claude   # Claude Code
bin/bdd-bootstrap codex    # Codex
```

The single positional argument (`claude` or `codex`) is required. The plugin source is the repository that ships `bin/bdd-bootstrap`; the install target is your current working directory — so `cd` into the project you want to set up, then run the command. Re-running is idempotent.

Install targets:

- Claude Code: `.claude/skills/gherkin-bdd` (copied) + a `SessionStart` hook in `.claude/settings.json`
- Codex: `.agents/plugins/plugins/gherkin-bdd` (symlinked) + a marketplace entry in `.agents/plugins/marketplace.json` + a `SessionStart` hook in `.codex/hooks.json`

Claude Code files are copied, which makes the install self-contained and easy to commit with the project. Codex files are symbolic links back to this repository, so edits to shared files such as `skills/gherkin-bdd/SKILL.md` take effect without re-installing.

`BDD.md` defines the project rule that every application feature should have a `.feature` file, and that Gherkin feature file is the source of truth for app behavior.

### BDD rule sync

The plugin keeps the `BDD.md` rule present in the host's instruction file — `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex — both at install time and on every session start. A single script, `scripts/check_bdd_sync.py`, does this:

- The installer runs it once (feeding it the same JSON payload a hook would), so the rule is in place immediately after install.
- A `SessionStart` hook runs the **same** script on every session start/resume, so the rule stays in sync over time.

The script creates the host's canonical instruction file if it is missing, appends the rule to any existing instruction file that lacks it, and does nothing once the rule is present (idempotent). It never blocks the session. Claude Code only loads hooks from `settings.json` (or a registered plugin), not from a copied skill directory, which is why the hook lives in `.claude/settings.json`.

This CLI only supports project-level installation. It does not write to `~/.claude`, `~/.agents`, or any other user-level location.

For Claude Code, restart the session or run `/reload-plugins`. For Codex, refresh local plugins after the marketplace entry is written.

## Suggested Next Files

- `agents/`: optional Claude Code subagents for feature review or step-definition planning.
- `hooks/hooks.json`: optional Claude Code hooks. Add only when an automatic command is really needed.
- `.mcp.json`: optional MCP server config for shared tools.
- `scripts/`: helper scripts used by skills, hooks, or MCP servers.
- `examples/`: sample feature files and review outputs.

## Compatibility Notes

Keep host-specific metadata in the matching manifest. The shared `skills/` directory should stay portable and avoid assumptions about one host's tool names.

Codex validation is stricter about manifest fields, so do not copy Claude-only fields into `.codex-plugin/plugin.json` unless Codex supports them.
