"""Shared fixtures and live (@agent) step definitions.

The @agent steps drive real headless host sessions (`claude -p`, `codex exec`).
They run on demand — `.venv/bin/pytest -m "agent and not todo"` — from a normal
terminal where both CLIs are installed and logged in. Each probe runs once and
must pass, per BDD.md. A missing CLI skips (environment gap, not a failure).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, then, when

ROOT = Path(__file__).resolve().parents[1]
MARKER_START = "<!-- gherkin-bdd:rule:start -->"

CANARY_V1 = "CANARY: zebra-quantum-42"
CANARY_V2 = "CANARY: heron-photon-77"
CANARY_PROBE = (
    "If your context contains a line starting with 'CANARY:', output exactly "
    "that line and nothing else; otherwise output NO-CANARY."
)
CODEX_PROBE = (
    "Your project instructions require reading a BDD rule file before any "
    "feature work. Read it as instructed, then output the line starting with "
    "'CANARY:' from it, exactly and nothing else."
)
CLAUDE_ALL_TOOLS = (
    "Bash",
    "Read",
    "Glob",
    "Grep",
    "Edit",
    "Write",
    "WebFetch",
    "WebSearch",
    "Task",
    "TodoWrite",
    "NotebookEdit",
)


@pytest.fixture
def live(tmp_path: Path) -> dict:
    """Mutable staging state shared between live steps of one scenario."""
    return {"tmp": tmp_path}


def require_cli(name: str) -> None:
    if shutil.which(name) is None:
        pytest.skip(f"{name} CLI not available")


def clean_env() -> dict:
    """Drop parent-session variables that break nested host CLIs."""
    env = os.environ.copy()
    for var in (
        "ANTHROPIC_BASE_URL",
        "CLAUDECODE",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDE_CODE_SESSION_ID",
        "CLAUDE_AGENT_SDK_VERSION",
        "BAGGAGE",
        "AI_AGENT",
    ):
        env.pop(var, None)
    return env


def run_claude(project: Path, prompt: str, *, mode: str) -> str:
    """mode: 'full' = skip permissions; 'readonly' = default -p gating (mutating
    tools are auto-denied, so asking is the agent's only move); 'none' = all
    tools disallowed (proves context auto-loading)."""
    require_cli("claude")
    command = ["claude", "-p", prompt]
    if mode == "full":
        command.append("--dangerously-skip-permissions")
    elif mode == "none":
        command += ["--disallowedTools", *CLAUDE_ALL_TOOLS]
    else:
        assert mode == "readonly", mode
    result = subprocess.run(
        command, cwd=project, env=clean_env(), capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0 and "401" in (result.stdout + result.stderr):
        pytest.fail(
            "claude CLI is not authenticated (401). Open a terminal, run `claude`, "
            "complete /login, then re-run the live suite.",
            pytrace=False,
        )
    assert result.returncode == 0, result.stderr
    return result.stdout


def run_codex(project: Path, prompt: str, *, writes: bool) -> str:
    require_cli("codex")
    command = ["codex", "exec", "--skip-git-repo-check"]
    if writes:
        # Codex's sandbox refuses writes to its own .codex/ config even in
        # workspace-write mode; interactively the user would approve that
        # write. Headless, full access stands in for that approval (the
        # project is a throwaway tmp dir).
        command += ["--sandbox", "danger-full-access"]
    command.append(prompt)
    result = subprocess.run(
        command, cwd=project, env=clean_env(), capture_output=True, text=True, timeout=900
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def make_source_copy(into: Path, canary: str | None = None) -> Path:
    """Copy the installer-relevant source tree so tests can mutate it freely."""
    source = into / "source"
    source.mkdir(parents=True)
    for entry in ("bin", "skills", "scripts"):
        shutil.copytree(ROOT / entry, source / entry)
    shutil.copy2(ROOT / "BDD.md", source / "BDD.md")
    if canary:
        with (source / "BDD.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n{canary}\n")
    return source


def bootstrap(source: Path, project: Path, host: str) -> None:
    result = subprocess.run(
        [sys.executable, str(source / "bin" / "bdd-bootstrap"), host],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- Given: effect probes -----------------------------------------------------


@given("an installed Claude Code project whose rule copy contains a canary line")
def installed_claude_project(live: dict) -> None:
    live["source"] = make_source_copy(live["tmp"], canary=CANARY_V1)
    live["project"] = live["tmp"] / "project"
    live["project"].mkdir()
    bootstrap(live["source"], live["project"], "claude")


@given("an installed Codex project whose rule copy contains a canary line")
def installed_codex_project(live: dict) -> None:
    live["source"] = make_source_copy(live["tmp"], canary=CANARY_V1)
    live["project"] = live["tmp"] / "project"
    live["project"].mkdir()
    bootstrap(live["source"], live["project"], "codex")


@given("the source rule's canary has since changed")
def source_canary_changed(live: dict) -> None:
    bdd = live["source"] / "BDD.md"
    bdd.write_text(bdd.read_text(encoding="utf-8").replace(CANARY_V1, CANARY_V2), encoding="utf-8")


@given("the installer is re-run in the project")
def reinstall(live: dict) -> None:
    bootstrap(live["source"], live["project"], "claude")


# --- Given: bootstrap-skill staging --------------------------------------------


def stage_source_as_project(live: dict, host: str) -> None:
    """The project IS a source copy, self-installed, with the host's sync
    artifacts removed so the skill invocation leaves an observable delta."""
    project = make_source_copy(live["tmp"])
    bootstrap(project, project, host)
    if host == "claude":
        (project / ".claude" / "settings.json").unlink()
        (project / "CLAUDE.md").unlink()
    else:
        (project / ".codex" / "hooks.json").unlink()
        (project / "AGENTS.md").unlink()
    live["host"] = host
    live["project"] = project


@given("a session running in Claude Code")
def claude_session(live: dict) -> None:
    stage_source_as_project(live, "claude")


@given("a session running in Codex")
def codex_session(live: dict) -> None:
    stage_source_as_project(live, "codex")


@given("the gherkin-bdd source repository is not present in the project")
def no_source_repo(live: dict) -> None:
    project = live["tmp"] / "project"
    project.mkdir()
    bootstrap(ROOT, project, "claude")
    (project / ".claude" / "settings.json").unlink()
    (project / "CLAUDE.md").unlink()
    live["host"] = "claude"
    live["project"] = project


# --- When -----------------------------------------------------------------------


@when("a headless Claude session is asked for the canary without tool access")
def probe_claude(live: dict) -> None:
    live["stdout"] = run_claude(live["project"], CANARY_PROBE, mode="none")


@when("a headless Codex session is asked to report the canary from its required reading")
def probe_codex(live: dict) -> None:
    live["stdout"] = run_codex(live["project"], CODEX_PROBE, writes=False)


@when("the user invokes the bdd-bootstrap skill without naming a host")
def invoke_skill(live: dict) -> None:
    if live["host"] == "claude":
        live["stdout"] = run_claude(live["project"], "/bdd-bootstrap", mode="full")
    else:
        live["stdout"] = run_codex(
            live["project"],
            "Invoke the bdd-bootstrap skill now. Do not ask for confirmation.",
            writes=True,
        )


@when("the user invokes the bdd-bootstrap skill naming the codex host")
def invoke_skill_naming_codex(live: dict) -> None:
    live["stdout"] = run_claude(live["project"], "/bdd-bootstrap codex", mode="full")


@when("the user invokes the bdd-bootstrap skill")
def invoke_skill_plain(live: dict) -> None:
    # Used by the no-source scenario: permissions stay gated so the agent
    # cannot self-serve (e.g. clone from GitHub) — asking is its only move.
    live["stdout"] = run_claude(live["project"], "/bdd-bootstrap", mode="readonly")


# --- Then -------------------------------------------------------------------------


@then("the canary line is returned")
def canary_returned(live: dict) -> None:
    assert CANARY_V1 in live["stdout"], live["stdout"]


@then("the original canary line is returned, not the updated one")
def original_canary_returned(live: dict) -> None:
    assert CANARY_V1 in live["stdout"], live["stdout"]
    assert CANARY_V2 not in live["stdout"], live["stdout"]


@then("the updated canary line is returned")
def updated_canary_returned(live: dict) -> None:
    assert CANARY_V2 in live["stdout"], live["stdout"]


@then("the installer runs for the claude host in the current project")
def claude_install_happened(live: dict) -> None:
    project = live["project"]
    settings_path = project / ".claude" / "settings.json"
    assert settings_path.exists(), f"installer did not run; session said:\n{live['stdout'][-2000:]}"
    command = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
        "hooks"
    ][0]["command"]
    assert "check_bdd_sync.py" in command
    assert MARKER_START in (project / "CLAUDE.md").read_text(encoding="utf-8")


@then("the installer runs for the codex host in the current project")
def codex_install_happened(live: dict) -> None:
    project = live["project"]
    hooks_path = project / ".codex" / "hooks.json"
    assert hooks_path.exists(), f"installer did not run; session said:\n{live['stdout'][-2000:]}"
    command = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
        "hooks"
    ][0]["command"]
    assert "check_bdd_sync.py" in command
    assert MARKER_START in (project / "AGENTS.md").read_text(encoding="utf-8")


@then("the user is asked where their gherkin-bdd clone lives or offered a fresh clone")
def asked_for_source(live: dict) -> None:
    project = live["project"]
    assert not (project / ".claude" / "settings.json").exists(), "installer ran without a source"
    output = live["stdout"].lower()
    assert any(token in output for token in ("clone", "github", "path")), live["stdout"]
