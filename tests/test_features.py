"""Step definitions executing the Gherkin specs in features/.

Scenarios tagged @agent are excluded via pytest.ini (`-m "not agent"`); they are
verified agent-in-the-loop instead, per BDD.md.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "bin" / "bdd-bootstrap"
CHECK_SCRIPT = ROOT / "scripts" / "check_bdd_sync.py"
MARKER_START = "<!-- gherkin-bdd:rule:start -->"
MARKER_END = "<!-- gherkin-bdd:rule:end -->"
CLAUDE_REF = ".claude/skills/gherkin-bdd/BDD.md"
CODEX_REF = ".agents/skills/gherkin-bdd/BDD.md"

scenarios("../features/bdd-sync-check.feature")
scenarios("../features/bdd-bootstrap-skill.feature")


def load_cli():
    loader = SourceFileLoader("bdd_bootstrap_cli", str(CLI_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load CLI module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    directory = tmp_path / "project"
    directory.mkdir()
    return directory


@pytest.fixture
def ctx() -> dict:
    """Mutable state shared between steps of one scenario."""
    return {}


def run_sync(project: Path, host: str, bdd_ref: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), "--host", host, "--bdd-ref", bdd_ref],
        input=json.dumps(
            {"cwd": str(project), "hook_event_name": "SessionStart", "source": "startup"}
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def managed_region(text: str) -> str:
    assert MARKER_START in text and MARKER_END in text
    return text[text.index(MARKER_START) : text.index(MARKER_END)]


# --- Given ------------------------------------------------------------------


@given("a Claude Code project")
@given("a Codex project")
@given("a project being set up with the gherkin-bdd installer for a host")
def blank_project(project: Path) -> None:
    pass


@given("a project whose CLAUDE.md already holds the user's own notes")
def project_with_notes(project: Path) -> None:
    (project / "CLAUDE.md").write_text("# My project\n\nSome notes.\n", encoding="utf-8")


@given("a project whose managed region holds outdated content")
def project_with_stale_region(project: Path) -> None:
    stale = f"# Project\n\n{MARKER_START}\nOLD STALE\n{MARKER_END}\n"
    (project / "CLAUDE.md").write_text(stale, encoding="utf-8")


@given("a project whose managed region already holds the current reference")
def project_with_current_region(project: Path, ctx: dict) -> None:
    run_sync(project, "claude", CLAUDE_REF)
    ctx["before"] = (project / "CLAUDE.md").read_text(encoding="utf-8")


# --- When -------------------------------------------------------------------


@when(parsers.parse("the BDD sync runs for the {host} host"))
def sync_for_host(project: Path, ctx: dict, host: str) -> None:
    bdd_ref = CLAUDE_REF if host == "claude" else CODEX_REF
    ctx["stdout"] = run_sync(project, host, bdd_ref)


@when("the BDD sync runs")
def sync_default(project: Path, ctx: dict) -> None:
    ctx["stdout"] = run_sync(project, "claude", CLAUDE_REF)


@when("the skill is installed")
@when("the skill is installed again")
def install_claude(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project)
    assert load_cli().main(["claude"]) == 0


# --- Then: sync -------------------------------------------------------------


@then("CLAUDE.md contains an @-import of BDD.md inside the managed region")
def claude_has_import(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("AGENTS.md requires the agent to read BDD.md inside the managed region")
def agents_has_directive(project: Path) -> None:
    text = (project / "AGENTS.md").read_text(encoding="utf-8")
    region = managed_region(text)
    assert "MUST read" in region
    assert CODEX_REF in region


@then("no AGENTS.md is created")
def no_agents_md(project: Path) -> None:
    assert not (project / "AGENTS.md").exists()


@then("no CLAUDE.md is created")
def no_claude_md(project: Path) -> None:
    assert not (project / "CLAUDE.md").exists()


@then("the managed region is added and the user's notes are left intact")
def notes_intact(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# My project" in text
    assert "Some notes." in text
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("the managed region is rewritten from the current reference")
def region_refreshed(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert "OLD STALE" not in text
    assert "# Project" in text
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("it appears exactly once")
def region_appears_once(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1


@then("the instruction file is left unchanged")
def file_unchanged(project: Path, ctx: dict) -> None:
    assert ctx["stdout"].strip() == ""
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == ctx["before"]


# --- Then: install ----------------------------------------------------------


@then("the skill, the BDD rule, and the sync script are placed in the host's project skills directory")
def skill_layout(project: Path) -> None:
    skill_dir = project / ".claude" / "skills" / "gherkin-bdd"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "BDD.md").exists()
    assert (skill_dir / "scripts" / "check_bdd_sync.py").exists()
    assert sorted(p.name for p in skill_dir.iterdir()) == ["BDD.md", "SKILL.md", "scripts"]


@then("nothing else is added to the project")
def nothing_else(project: Path) -> None:
    assert sorted(p.name for p in project.iterdir()) == [".claude", "CLAUDE.md"]
    skills = project / ".claude" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["bdd-bootstrap", "gherkin-bdd"]


@then("the host's canonical instruction file references BDD.md")
def canonical_references_rule(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("a session-start hook is registered to run the same sync script later")
def hook_registered(project: Path) -> None:
    settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "check_bdd_sync.py" in command
    assert "--host claude" in command
    assert f'--bdd-ref "{CLAUDE_REF}"' in command


@then("only one session-start hook entry and one managed region exist")
def install_idempotent(project: Path) -> None:
    settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings["hooks"]["SessionStart"]) == 1
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1


@then("the bdd-bootstrap skill is placed alongside the gherkin-bdd skill")
def bootstrap_skill_installed(project: Path) -> None:
    bootstrap_dir = project / ".claude" / "skills" / "bdd-bootstrap"
    assert (bootstrap_dir / "SKILL.md").exists()
    assert [p.name for p in bootstrap_dir.iterdir()] == ["SKILL.md"]


# --- Spec hygiene -------------------------------------------------------------


def test_every_todo_scenario_records_its_debt() -> None:
    """@todo scenarios must carry an adjacent '# TODO' comment (why + unblock)."""
    offenders = []
    for feature in sorted((ROOT / "features").glob("*.feature")):
        lines = feature.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("@") or "@todo" not in stripped.split():
                continue
            cursor = index - 1
            while cursor >= 0 and lines[cursor].strip().startswith("@"):
                cursor -= 1
            comment_block = []
            while cursor >= 0 and lines[cursor].strip().startswith("#"):
                comment_block.append(lines[cursor])
                cursor -= 1
            if not any("TODO" in comment for comment in comment_block):
                offenders.append(f"{feature.name}:{index + 1}")
    assert not offenders, (
        "@todo scenarios missing an adjacent '# TODO' comment recording why the "
        f"test cannot be built yet and what unblocks it: {offenders}"
    )


# --- Regression guards not tied to a scenario --------------------------------


def test_invalid_host_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        load_cli().main(["github"])


def test_codex_install_targets_codex_locations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_cli().main(["codex"]) == 0
    assert (tmp_path / ".agents" / "skills" / "gherkin-bdd" / "SKILL.md").exists()
    assert (tmp_path / ".agents" / "skills" / "bdd-bootstrap" / "SKILL.md").exists()
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "--host codex" in command
    assert f'--bdd-ref "{CODEX_REF}"' in command
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "MUST read" in text
