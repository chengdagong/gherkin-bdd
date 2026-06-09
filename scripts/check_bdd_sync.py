#!/usr/bin/env python3
"""SessionStart hook: keep the BDD rule synced into project instructions.

This script is shared by Claude Code and Codex. Both hosts invoke it as a
SessionStart hook, passing a JSON payload on stdin (with a ``cwd`` field). When
the project's ``CLAUDE.md`` / ``AGENTS.md`` do not yet contain the ``BDD.md``
rule, the script appends it; when neither file exists, it creates ``CLAUDE.md``
with the rule. It edits files in place, idempotently, and never blocks the
session.

``BDD.md`` is located relative to this script's install directory
(``<install>/scripts/check_bdd_sync.py`` -> ``<install>/BDD.md``), so it works
for both the copied Claude install and the symlinked Codex install.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md")
DEFAULT_INSTRUCTION_FILE = "CLAUDE.md"


def main() -> int:
    bdd_content = read_bdd_content()
    if not bdd_content:
        return 0

    project_dir = resolve_project_dir(read_payload())
    changed = sync_instructions(project_dir, bdd_content)
    if changed:
        emit_notice(changed)
    return 0


def read_bdd_content() -> str:
    bdd_path = Path(__file__).resolve().parent.parent / "BDD.md"
    if not bdd_path.exists():
        return ""
    return bdd_path.read_text(encoding="utf-8").strip()


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


def sync_instructions(project_dir: Path, bdd_content: str) -> list[str]:
    """Append the rule where missing. Returns the names of changed files."""
    existing = existing_instruction_files(project_dir)
    if existing:
        changed = []
        for path in existing:
            if bdd_content not in read_text(path):
                append_rule(path, bdd_content)
                changed.append(path.name)
        return changed

    target = project_dir / DEFAULT_INSTRUCTION_FILE
    create_rule_file(target, bdd_content)
    return [target.name]


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


def append_rule(path: Path, bdd_content: str) -> None:
    existing = read_text(path)
    separator = "\n\n" if existing.strip() else ""
    path.write_text(existing.rstrip() + separator + bdd_content + "\n", encoding="utf-8")


def create_rule_file(path: Path, bdd_content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bdd_content + "\n", encoding="utf-8")


def emit_notice(changed: list[str]) -> None:
    names = ", ".join(changed)
    payload = {
        "continue": True,
        "systemMessage": f"Synced the BDD rule into {names}.",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                f"The BDD rule from BDD.md was added to {names} to keep project "
                "instructions in sync. Per the BDD rule, every user-facing feature "
                "needs a matching .feature file as the source of truth for behavior."
            ),
        },
    }
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
