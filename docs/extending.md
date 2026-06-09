# Extending The Plugin

This skeleton starts with one shared skill and two host manifests.

Add optional components only when there is a real repeated workflow:

- `agents/`: Claude Code agent Markdown files with YAML frontmatter.
- `hooks/hooks.json`: Claude Code event hooks.
- `.mcp.json`: MCP server configuration shared by Codex and Claude Code when both hosts support the same server.
- `scripts/`: helper scripts used by skills, hooks, or MCP servers.
- `examples/`: sample feature files and review outputs.

Avoid putting README files directly under `agents/`, because Claude Code treats Markdown files there as agent definitions.
