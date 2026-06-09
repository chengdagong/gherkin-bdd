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

Install this plugin into the current project for both Claude Code and Codex:

```bash
bin/bdd-bootstrap
```

Default install targets:

- Claude Code: `.claude/skills/gherkin-bdd`
- Claude Code session hook: `.claude/settings.json`
- Codex plugin source: `.agents/plugins/plugins/gherkin-bdd`
- Codex project marketplace: `.agents/plugins/marketplace.json`
- Codex session hook: `.codex/hooks.json`

Claude Code files are copied into `.claude/skills/gherkin-bdd`, which makes the project plugin self-contained and easier to commit with the project.

Codex plugin files use symbolic links back to this repository, so changes to shared files such as `skills/gherkin-bdd/SKILL.md` take effect without copying files again.

`BDD.md` defines the project rule that every application feature should have a `.feature` file, and that Gherkin feature file is the source of truth for app behavior.

During install, `bdd-bootstrap` checks the target project root for `CLAUDE.md` and `AGENTS.md` files. The check is case-insensitive, so `claude.md` and `agents.md` are handled too. If either file exists and does not already contain the full `BDD.md` content, the content is appended to the end of that file. If either file is missing, the CLI asks whether to create it with the `BDD.md` content.

`bdd-bootstrap` also registers a `SessionStart` hook for each host so that every session keeps this sync up to date automatically. The hook runs `scripts/check_bdd_sync.py` whenever Claude Code or Codex starts (or resumes) a session in the project. If `BDD.md` is missing from `CLAUDE.md` / `AGENTS.md`, the hook appends it; if neither file exists, it creates `CLAUDE.md` with the rule. The sync is idempotent — once the rule is present the hook leaves the files untouched. The hook entry is merged into the host config (`.claude/settings.json` for Claude Code, `.codex/hooks.json` for Codex) without disturbing existing hooks, and re-running the installer is idempotent.

Claude Code only loads hooks from `settings.json` (or a registered plugin), not from a copied skill directory, which is why the hook lives in `.claude/settings.json` rather than the installed skill folder.

This CLI only supports project-level installation. It does not write to `~/.claude`, `~/.agents`, or any other user-level plugin location.

Useful options:

```bash
bin/bdd-bootstrap show-paths
bin/bdd-bootstrap --project-dir /path/to/project
bin/bdd-bootstrap --target claude
bin/bdd-bootstrap --target codex
bin/bdd-bootstrap --force
bin/bdd-bootstrap --dry-run
bin/bdd-bootstrap --create-missing-instructions yes
bin/bdd-bootstrap --create-missing-instructions no
```

For Claude Code, restart the session or run:

```text
/reload-plugins
```

For Codex, refresh local plugins after the project marketplace entry is written.

## Suggested Next Files

- `agents/`: optional Claude Code subagents for feature review or step-definition planning.
- `hooks/hooks.json`: optional Claude Code hooks. Add only when an automatic command is really needed.
- `.mcp.json`: optional MCP server config for shared tools.
- `scripts/`: helper scripts used by skills, hooks, or MCP servers.
- `examples/`: sample feature files and review outputs.

## Compatibility Notes

Keep host-specific metadata in the matching manifest. The shared `skills/` directory should stay portable and avoid assumptions about one host's tool names.

Codex validation is stricter about manifest fields, so do not copy Claude-only fields into `.codex-plugin/plugin.json` unless Codex supports them.
