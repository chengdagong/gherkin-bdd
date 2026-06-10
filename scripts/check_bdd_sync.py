#!/usr/bin/env python3
"""SessionStart hook: keep a reference to the BDD rule in project instructions.

This script is shared by Claude Code and Codex. Both coding agents invoke it as
a SessionStart hook with ``--coding-agent {claude|codex}`` and
``--bdd-ref <path>`` baked in by the installer, and pass a JSON payload on stdin
(with a ``cwd`` field).

It does NOT inline ``BDD.md``; ``BDD.md`` stays the single source of truth. It
keeps a short *reference* to it inside a managed region (marked by
``<!-- gherkin-bdd:rule:start -->`` / ``<!-- gherkin-bdd:rule:end -->``) in the
coding agent's canonical instruction file — ``CLAUDE.md`` for Claude,
``AGENTS.md`` for Codex. The reference differs by coding agent:

- Claude Code reads ``CLAUDE.md`` and expands ``@path`` imports into context, so
  the reference is an ``@<bdd-ref>`` import that auto-loads ``BDD.md``.
- Codex does not expand imports, so the reference is an imperative directive that
  requires the agent to read ``BDD.md``.

The script creates the canonical file if absent, refreshes the managed region when
present, is idempotent, and never blocks the session.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md")
CODING_AGENT_CANONICAL_FILE = {"claude": "CLAUDE.md", "codex": "AGENTS.md"}
MARKER_START = "<!-- gherkin-bdd:rule:start -->"
MARKER_END = "<!-- gherkin-bdd:rule:end -->"


def main() -> int:
    coding_agent, bdd_ref = parse_options()
    if not coding_agent or not bdd_ref:
        return 0

    project_dir = resolve_project_dir(read_payload())
    changed = sync_instructions(project_dir, coding_agent, bdd_ref)
    if changed:
        emit_notice(changed)
    return 0


def parse_options() -> tuple[str | None, str | None]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--coding-agent", choices=tuple(CODING_AGENT_CANONICAL_FILE))
    parser.add_argument("--bdd-ref")
    args, _ = parser.parse_known_args()
    return args.coding_agent, args.bdd_ref


def read_payload() -> dict:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def resolve_project_dir(payload: dict) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return Path(cwd).expanduser()
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.cwd()


def sync_instructions(project_dir: Path, coding_agent: str, bdd_ref: str) -> list[str]:
    """Keep the rule reference in the coding agent's canonical file. Returns changed names."""
    canonical = CODING_AGENT_CANONICAL_FILE[coding_agent]
    snippet = build_snippet(coding_agent, bdd_ref)
    existing = existing_instruction_files(project_dir)
    match = next((p for p in existing if p.name.lower() == canonical.lower()), None)
    target = match if match is not None else project_dir / canonical
    if ensure_region(target, snippet):
        return [target.name]
    return []


def build_snippet(coding_agent: str, bdd_ref: str) -> str:
    if coding_agent == "claude":
        return f"## BDD rule\n\n@{bdd_ref}"
    return (
        "## BDD rule (required)\n\n"
        f"Before adding or changing any user-facing functionality, you MUST read "
        f"`{bdd_ref}` and follow it. Every feature must have a matching `.feature` "
        "file, which is the source of truth for its behavior. Do not treat work as "
        "complete until the behavior matches that file."
    )


def existing_instruction_files(project_dir: Path) -> list[Path]:
    if not project_dir.exists():
        return []
    wanted = {name.lower() for name in INSTRUCTION_FILES}
    return sorted(
        (path for path in project_dir.iterdir() if path.is_file() and path.name.lower() in wanted),
        key=lambda path: path.name.lower(),
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def ensure_region(path: Path, snippet: str) -> bool:
    """Create, append, or refresh the managed region. True if the file changed."""
    original = read_text(path) if path.exists() else None
    updated = upsert_region(original, snippet)
    if original is not None and updated == original:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return True


def upsert_region(original: str | None, snippet: str) -> str:
    region = f"{MARKER_START}\n{snippet}\n{MARKER_END}"
    if not original:
        return region + "\n"
    if MARKER_START in original and MARKER_END in original:
        start = original.index(MARKER_START)
        end = original.index(MARKER_END) + len(MARKER_END)
        if start < end:
            return original[:start] + region + original[end:]
    separator = "\n\n" if original.strip() else ""
    return original.rstrip() + separator + region + "\n"


def emit_notice(changed: list[str]) -> None:
    names = ", ".join(changed)
    payload = {
        "continue": True,
        "systemMessage": f"Linked the BDD rule into {names}.",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                f"{names} now references the BDD rule in BDD.md. Every user-facing "
                "feature must have a matching Gherkin file as the source of truth "
                "for its behavior."
            ),
        },
    }
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
