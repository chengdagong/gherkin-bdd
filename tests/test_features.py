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
scenarios("../features/code-to-gherkin.feature")


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


@given("一个 Claude Code 项目")
@given("一个 Codex 项目")
@given("正在为某个 host 安装 gherkin-bdd 的项目")
def blank_project(project: Path) -> None:
    pass


@given("一个 CLAUDE.md 中已有用户笔记的项目")
def project_with_notes(project: Path) -> None:
    (project / "CLAUDE.md").write_text("# My project\n\nSome notes.\n", encoding="utf-8")


@given("一个受管区域内容已过期的项目")
def project_with_stale_region(project: Path) -> None:
    stale = f"# Project\n\n{MARKER_START}\nOLD STALE\n{MARKER_END}\n"
    (project / "CLAUDE.md").write_text(stale, encoding="utf-8")


@given("一个受管区域已经包含当前引用的项目")
def project_with_current_region(project: Path, ctx: dict) -> None:
    run_sync(project, "claude", CLAUDE_REF)
    ctx["before"] = (project / "CLAUDE.md").read_text(encoding="utf-8")


# --- When -------------------------------------------------------------------


@when(parsers.parse("为 {host} host 运行 BDD 同步"))
def sync_for_host(project: Path, ctx: dict, host: str) -> None:
    bdd_ref = CLAUDE_REF if host == "claude" else CODEX_REF
    ctx["stdout"] = run_sync(project, host, bdd_ref)


@when("运行 BDD 同步")
def sync_default(project: Path, ctx: dict) -> None:
    ctx["stdout"] = run_sync(project, "claude", CLAUDE_REF)


@when("技能已安装")
@when("技能再次安装")
def install_claude(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project)
    assert load_cli().main(["claude"]) == 0


# --- Then: sync -------------------------------------------------------------


@then("CLAUDE.md 的受管区域包含对 BDD.md 的 @ 导入")
def claude_has_import(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("AGENTS.md 在受管区域中要求 agent 读取 BDD.md")
def agents_has_directive(project: Path) -> None:
    text = (project / "AGENTS.md").read_text(encoding="utf-8")
    region = managed_region(text)
    assert "MUST read" in region
    assert CODEX_REF in region


@then("没有创建 AGENTS.md")
def no_agents_md(project: Path) -> None:
    assert not (project / "AGENTS.md").exists()


@then("没有创建 CLAUDE.md")
def no_claude_md(project: Path) -> None:
    assert not (project / "CLAUDE.md").exists()


@then("受管区域被加入且用户笔记保持不变")
def notes_intact(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert "# My project" in text
    assert "Some notes." in text
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("受管区域被当前引用重写")
def region_refreshed(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert "OLD STALE" not in text
    assert "# Project" in text
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("它只出现一次")
def region_appears_once(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1


@then("指令文件保持不变")
def file_unchanged(project: Path, ctx: dict) -> None:
    assert ctx["stdout"].strip() == ""
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == ctx["before"]


# --- Then: install ----------------------------------------------------------


@then("技能、BDD 规则和技能脚本被放入 host 的项目技能目录")
def skill_layout(project: Path) -> None:
    skill_dir = project / ".claude" / "skills" / "gherkin-bdd"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "BDD.md").exists()
    assert (skill_dir / "scripts" / "check_bdd_sync.py").exists()
    assert (skill_dir / "scripts" / "gherkin_to_html.py").exists()
    assert sorted(p.name for p in skill_dir.iterdir()) == ["BDD.md", "SKILL.md", "scripts"]
    assert sorted(p.name for p in (skill_dir / "scripts").iterdir()) == [
        "check_bdd_sync.py",
        "gherkin_to_html.py",
    ]


@then("项目中没有新增其他内容")
def nothing_else(project: Path) -> None:
    assert sorted(p.name for p in project.iterdir()) == [".claude", "CLAUDE.md"]
    skills = project / ".claude" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == [
        "bdd-bootstrap",
        "code-to-gherkin",
        "gherkin-bdd",
    ]


@then("host 的规范指令文件引用 BDD.md")
def canonical_references_rule(project: Path) -> None:
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"@{CLAUDE_REF}" in managed_region(text)


@then("注册了一个稍后运行同一同步脚本的 session-start hook")
def hook_registered(project: Path) -> None:
    settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "check_bdd_sync.py" in command
    assert "--host claude" in command
    assert f'--bdd-ref "{CLAUDE_REF}"' in command


@then("只存在一个 session-start hook 条目和一个受管区域")
def install_idempotent(project: Path) -> None:
    settings = json.loads((project / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings["hooks"]["SessionStart"]) == 1
    text = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START) == 1


@then("bdd-bootstrap 技能与 gherkin-bdd 技能安装在同一级目录")
def bootstrap_skill_installed(project: Path) -> None:
    bootstrap_dir = project / ".claude" / "skills" / "bdd-bootstrap"
    assert (bootstrap_dir / "SKILL.md").exists()
    assert [p.name for p in bootstrap_dir.iterdir()] == ["SKILL.md"]


@then("code-to-gherkin 技能与 gherkin-bdd 技能安装在同一级目录")
def code_to_gherkin_skill_installed(project: Path) -> None:
    skill_dir = project / ".claude" / "skills" / "code-to-gherkin"
    assert (skill_dir / "SKILL.md").exists()
    assert [p.name for p in skill_dir.iterdir()] == ["SKILL.md"]


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
    assert (tmp_path / ".agents" / "skills" / "code-to-gherkin" / "SKILL.md").exists()
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "--host codex" in command
    assert f'--bdd-ref "{CODEX_REF}"' in command
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "MUST read" in text
