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
from textwrap import dedent

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


@given("已安装的 Claude Code 项目，它的规则副本包含一行 canary")
def installed_claude_project(live: dict) -> None:
    live["source"] = make_source_copy(live["tmp"], canary=CANARY_V1)
    live["project"] = live["tmp"] / "project"
    live["project"].mkdir()
    bootstrap(live["source"], live["project"], "claude")


@given("已安装的 Codex 项目，它的规则副本包含一行 canary")
def installed_codex_project(live: dict) -> None:
    live["source"] = make_source_copy(live["tmp"], canary=CANARY_V1)
    live["project"] = live["tmp"] / "project"
    live["project"].mkdir()
    bootstrap(live["source"], live["project"], "codex")


@given("源规则中的 canary 已经改变")
def source_canary_changed(live: dict) -> None:
    bdd = live["source"] / "BDD.md"
    bdd.write_text(bdd.read_text(encoding="utf-8").replace(CANARY_V1, CANARY_V2), encoding="utf-8")


@given("在项目中重新运行安装器")
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


@given("一个运行在 Claude Code 中的会话")
def claude_session(live: dict) -> None:
    stage_source_as_project(live, "claude")


@given("一个运行在 Codex 中的会话")
def codex_session(live: dict) -> None:
    stage_source_as_project(live, "codex")


@given("当前项目中找不到 gherkin-bdd 源仓库")
def no_source_repo(live: dict) -> None:
    project = live["tmp"] / "project"
    project.mkdir()
    bootstrap(ROOT, project, "claude")
    (project / ".claude" / "settings.json").unlink()
    (project / "CLAUDE.md").unlink()
    live["host"] = "claude"
    live["project"] = project


# --- When -----------------------------------------------------------------------


@when("无工具权限的 headless Claude 会话被询问 canary")
def probe_claude(live: dict) -> None:
    live["stdout"] = run_claude(live["project"], CANARY_PROBE, mode="none")


@when("headless Codex 会话被要求从必读规则中报告 canary")
def probe_codex(live: dict) -> None:
    live["stdout"] = run_codex(live["project"], CODEX_PROBE, writes=False)


@when("用户调用 bdd-bootstrap 技能但没有指定 host")
def invoke_skill(live: dict) -> None:
    if live["host"] == "claude":
        live["stdout"] = run_claude(live["project"], "/bdd-bootstrap", mode="full")
    else:
        live["stdout"] = run_codex(
            live["project"],
            "Invoke the bdd-bootstrap skill now. Do not ask for confirmation.",
            writes=True,
        )


@when("用户调用 bdd-bootstrap 技能并指定 codex host")
def invoke_skill_naming_codex(live: dict) -> None:
    live["stdout"] = run_claude(live["project"], "/bdd-bootstrap codex", mode="full")


@when("用户调用 bdd-bootstrap 技能")
def invoke_skill_plain(live: dict) -> None:
    # Used by the no-source scenario: permissions stay gated so the agent
    # cannot self-serve (e.g. clone from GitHub) — asking is its only move.
    live["stdout"] = run_claude(live["project"], "/bdd-bootstrap", mode="readonly")


# --- Then -------------------------------------------------------------------------


@then("返回 canary 行")
def canary_returned(live: dict) -> None:
    assert CANARY_V1 in live["stdout"], live["stdout"]


@then("返回原始 canary 行，而不是更新后的 canary 行")
def original_canary_returned(live: dict) -> None:
    assert CANARY_V1 in live["stdout"], live["stdout"]
    assert CANARY_V2 not in live["stdout"], live["stdout"]


@then("返回更新后的 canary 行")
def updated_canary_returned(live: dict) -> None:
    assert CANARY_V2 in live["stdout"], live["stdout"]


@then("安装器为当前项目运行 claude host 安装")
def claude_install_happened(live: dict) -> None:
    project = live["project"]
    settings_path = project / ".claude" / "settings.json"
    assert settings_path.exists(), f"installer did not run; session said:\n{live['stdout'][-2000:]}"
    command = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
        "hooks"
    ][0]["command"]
    assert "check_bdd_sync.py" in command
    assert MARKER_START in (project / "CLAUDE.md").read_text(encoding="utf-8")


@then("安装器为当前项目运行 codex host 安装")
def codex_install_happened(live: dict) -> None:
    project = live["project"]
    hooks_path = project / ".codex" / "hooks.json"
    assert hooks_path.exists(), f"installer did not run; session said:\n{live['stdout'][-2000:]}"
    command = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0][
        "hooks"
    ][0]["command"]
    assert "check_bdd_sync.py" in command
    assert MARKER_START in (project / "AGENTS.md").read_text(encoding="utf-8")


@then("用户被询问 gherkin-bdd clone 的位置，或收到重新 clone 的建议")
def asked_for_source(live: dict) -> None:
    project = live["project"]
    assert not (project / ".claude" / "settings.json").exists(), "installer ran without a source"
    output = live["stdout"].lower()
    assert any(token in output for token in ("clone", "github", "path")), live["stdout"]


# --- code-to-gherkin: staging ---------------------------------------------------

TIPCALC_PY = dedent(
    '''
    """Split a restaurant bill evenly."""
    import sys


    def _fmt_currency_v2(amount):
        return f"${amount:.2f}"


    def split_bill(total, people):
        return total / people


    def main():
        total, people = float(sys.argv[1]), int(sys.argv[2])
        print(f"Each person pays {_fmt_currency_v2(split_bill(total, people))}")


    if __name__ == "__main__":
        main()
    '''
).lstrip()

GREETER_PY = dedent(
    '''
    """Greet or bid farewell to someone by name."""
    import sys


    def main():
        action, name = sys.argv[1], sys.argv[2]
        if action == "greet":
            print(f"Hello, {name}!")
        elif action == "farewell":
            print(f"Goodbye, {name}.")


    if __name__ == "__main__":
        main()
    '''
).lstrip()

GREETING_FEATURE = dedent(
    """
    Feature: Greeting
      Scenario: Greet someone by name
        Given the name "Ada"
        When the user asks for a greeting
        Then "Hello, Ada!" is printed
    """
).lstrip()

DISCOUNT_PY = dedent(
    '''
    """Checkout pricing: every order gets the advertised 10% discount."""
    import sys


    def discounted_total(total):
        # apply the 10% discount
        return round(total * 1.10, 2)


    def main():
        print(f"Total after discount: {discounted_total(float(sys.argv[1]))}")


    if __name__ == "__main__":
        main()
    '''
).lstrip()


def stage_code_project(live: dict, files: dict[str, str]) -> None:
    """A bootstrapped Claude project holding application code to backfill."""
    project = live["tmp"] / "project"
    project.mkdir()
    bootstrap(ROOT, project, "claude")
    for relative, text in files.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    live["host"] = "claude"
    live["project"] = project


def project_feature_texts(project: Path) -> dict[str, str]:
    """All Gherkin files in the project, outside install directories."""
    return {
        path.relative_to(project).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(project.rglob("*.feature"))
        if not any(part in (".claude", ".agents") for part in path.parts)
    }


# --- code-to-gherkin: steps -------------------------------------------------------


@given("一个有可运行代码但没有 Gherkin 文件的项目")
def code_project_uncovered(live: dict) -> None:
    stage_code_project(live, {"tipcalc.py": TIPCALC_PY})


@given("一个部分行为已经由 Gherkin 文件描述的项目")
def code_project_partially_covered(live: dict) -> None:
    stage_code_project(
        live,
        {"greeter.py": GREETER_PY, "features/greeting.feature": GREETING_FEATURE},
    )


@given("一个代码中包含疑似缺陷的项目")
def code_project_with_defect(live: dict) -> None:
    stage_code_project(live, {"discount.py": DISCOUNT_PY})


@when("用户调用 code-to-gherkin 技能")
def invoke_code_to_gherkin(live: dict) -> None:
    live["stdout"] = run_claude(live["project"], "/code-to-gherkin", mode="full")


@then("描述代码用户可见行为的 Gherkin 文件被创建")
def behavior_recorded(live: dict) -> None:
    texts = project_feature_texts(live["project"])
    assert texts, f"no Gherkin files created; session said:\n{live['stdout'][-2000:]}"
    combined = "\n".join(texts.values()).lower()
    assert "bill" in combined or "split" in combined, combined


@then("未覆盖的行为获得场景")
def uncovered_behavior_gains_scenarios(live: dict) -> None:
    combined = "\n".join(project_feature_texts(live["project"]).values()).lower()
    assert "farewell" in combined or "goodbye" in combined, combined


@then("已覆盖的行为不会被描述两次")
def covered_behavior_not_duplicated(live: dict) -> None:
    combined = "\n".join(project_feature_texts(live["project"]).values())
    assert combined.count("Greet someone by name") == 1, combined


@then("新场景描述用户可以观察到的结果")
def scenarios_describe_observables(live: dict) -> None:
    texts = project_feature_texts(live["project"])
    assert texts, f"no Gherkin files created; session said:\n{live['stdout'][-2000:]}"
    combined = "\n".join(texts.values())
    assert "Scenario:" in combined and "Then" in combined, combined
    assert "pay" in combined.lower() or "$" in combined, combined


@then("内部代码名不会出现在 Gherkin 文件中")
def internal_names_stay_out(live: dict) -> None:
    combined = "\n".join(project_feature_texts(live["project"]).values())
    for name in ("_fmt_currency_v2", "split_bill"):
        assert name not in combined, f"implementation name {name!r} leaked:\n{combined}"


@then("用户会被询问该行为是否符合预期")
def asked_about_defect(live: dict) -> None:
    output = live["stdout"].lower()
    assert "discount" in output, live["stdout"][-2000:]
    assert any(
        token in output for token in ("intended", "intentional", "bug", "defect", "expect", "?")
    ), live["stdout"][-2000:]


@then("没有场景把缺陷结果记录成预期行为")
def defect_not_specified(live: dict) -> None:
    combined = "\n".join(project_feature_texts(live["project"]).values())
    assert "110" not in combined, f"the defective outcome was specced:\n{combined}"
