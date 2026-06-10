"""Step definitions executing features/gherkin-to-html.feature.

The gherkin-to-html converter is a stdlib-only script shipped with the skill;
these steps drive it the way a user would — as a subprocess against a project
directory — and assert on the produced HTML.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from textwrap import dedent

import pytest
from pytest_bdd import given, scenarios, then, when

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "gherkin_to_html.py"
CLI_PATH = ROOT / "bin" / "bdd-bootstrap"
DEFAULT_OUT = "gherkin.html"
DEFAULT_OUT_REL = Path("docs") / DEFAULT_OUT

scenarios("../features/gherkin-to-html.feature")


def load_cli():
    loader = SourceFileLoader("bdd_bootstrap_cli_overview", str(CLI_PATH))
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


def write_feature(project: Path, relative: str, text: str) -> None:
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).lstrip("\n"), encoding="utf-8")


# --- Given --------------------------------------------------------------------


@given("一个在多个目录中都有 Gherkin 文件的项目")
def project_with_spread_features(project: Path) -> None:
    write_feature(
        project,
        "features/checkout.feature",
        """
        # language: zh-CN
        功能: 结账
          场景: 为购物车付款
            假如 购物车中有一件商品
            当 顾客付款
            那么 订单被创建
        """,
    )
    write_feature(
        project,
        "docs/specs/refunds.feature",
        """
        # language: zh-CN
        功能: 退款
          场景: 为已送达订单退款
            假如 一个已送达订单
            当 顾客申请退款
            那么 退款进入队列
        """,
    )


@given("一个 Gherkin 文件包含标签、背景、场景大纲和步骤数据的项目")
def project_with_rich_feature(project: Path) -> None:
    write_feature(
        project,
        "features/orders.feature",
        '''
        # language: zh-CN
        @billing
        功能: 订单管理
          顾客在购买后管理自己的订单。

          背景:
            假如 一个已登录顾客

          @smoke
          场景: 取消待处理订单
            假如 一个状态为 "pending" 的订单
            当 顾客取消该订单
            那么 订单显示为 "cancelled"
            而且 收据内容为:
              """
              订单已取消。
              退款已排队。
              """

          场景大纲: 按地区计算配送费
            假如 配送地址位于 <region>
            当 计算配送费
            那么 配送费为 <fee>

            例子:
              | region | fee |
              | EU     | 5   |
              | US     | 8   |

          场景: 列出订单商品
            假如 订单包含:
              | item   | qty |
              | 铅笔   | 2   |
        ''',
    )


@given("一个包含 Gherkin 文件的项目")
def project_with_one_feature(project: Path) -> None:
    write_feature(
        project,
        "features/login.feature",
        """
        # language: zh-CN
        功能: 用户登录
          场景: 使用有效凭据登录
            假如 一个注册用户
            当 用户登录
            那么 用户进入首页
        """,
    )


@given("一个依赖目录和隐藏目录中也包含 Gherkin 文件的项目")
def project_with_vendor_features(project: Path) -> None:
    write_feature(
        project,
        "features/real.feature",
        """
        # language: zh-CN
        功能: 真实行为
          场景: 计数
            假如 一些真实内容
        """,
    )
    for relative, name in (
        ("node_modules/pkg/specs/vendor.feature", "Vendor behavior"),
        (".venv/lib/site.feature", "Venv behavior"),
        (".hidden/h.feature", "Hidden behavior"),
    ):
        write_feature(
            project,
            relative,
            f"""
            # language: zh-CN
            功能: {name}
              场景: 隐藏内容
                假如 一些隐藏内容
            """,
        )


@given("一个没有 Gherkin 文件的项目")
def project_without_features(project: Path) -> None:
    pass


@given("一个包含无法解析文本的 Gherkin 文件的项目")
def project_with_broken_feature(project: Path) -> None:
    write_feature(
        project,
        "features/broken.feature",
        """
        这里有一个文件
        没有 Gherkin，只有普通文本
        """,
    )


@given("正在为某个 coding agent 安装 gherkin-bdd 的项目")
def blank_install_project(project: Path) -> None:
    pass


# --- When ---------------------------------------------------------------------


@when("用户将 gherkin 渲染为 HTML")
def render_gherkin(project: Path, ctx: dict) -> None:
    ctx["files_before"] = {p.relative_to(project) for p in project.rglob("*") if p.is_file()}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(project)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    match = re.search(r"Gherkin HTML: (.+)", result.stdout)
    assert match, result.stdout
    ctx["out"] = Path(match.group(1))
    ctx["html"] = ctx["out"].read_text(encoding="utf-8")


@when("技能已安装")
def install_claude(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(project)
    assert load_cli().main(["claude"]) == 0


# --- Then ---------------------------------------------------------------------


@then("单个 HTML 页面列出每个 Gherkin 文件及其来源文件")
def page_lists_all_features(ctx: dict) -> None:
    assert ctx["out"].exists()
    html = ctx["html"]
    for name, origin in (
        ("结账", "features/checkout.feature"),
        ("退款", "docs/specs/refunds.feature"),
    ):
        assert name in html
        assert origin in html


@then("页面提供到每个 Gherkin 文件的导航")
def page_has_navigation(ctx: dict) -> None:
    html = ctx["html"]
    targets = set(re.findall(r'href="#([^"]+)"', html))
    anchors = set(re.findall(r'id="([^"]+)"', html))
    assert len(targets) >= 2
    assert targets <= anchors, f"dangling links: {targets - anchors}"


@then("页面显示功能名称和叙述")
def page_shows_narrative(ctx: dict) -> None:
    assert "订单管理" in ctx["html"]
    assert "顾客在购买后管理自己的订单。" in ctx["html"]


@then("每个场景及其步骤按顺序出现")
def scenarios_in_order(ctx: dict) -> None:
    html = ctx["html"]
    ordered = (
        "取消待处理订单",
        "顾客取消该订单",
        "按地区计算配送费",
        "计算配送费",
        "列出订单商品",
    )
    positions = [html.index(text) for text in ordered]
    assert positions == sorted(positions)


@then("标签、背景步骤、examples 表格、步骤表格和 doc string 都保留在它们描述的对象旁边")
def structure_stays_attached(ctx: dict) -> None:
    html = ctx["html"]
    assert "@billing" in html
    assert html.index("@smoke") < html.index("取消待处理订单")
    assert "一个已登录顾客" in html
    assert html.index("按地区计算配送费") < html.index("EU")
    assert "铅笔" in html
    assert "退款已排队。" in html


@then("页面是单个自包含文件")
def single_file_output(project: Path, ctx: dict) -> None:
    added = {p.relative_to(project) for p in project.rglob("*") if p.is_file()} - ctx["files_before"]
    assert added == {ctx["out"].relative_to(project)}
    assert ctx["out"].name == DEFAULT_OUT


@then("页面默认写入 docs/gherkin.html")
def output_to_docs(project: Path, ctx: dict) -> None:
    assert ctx["out"] == project / DEFAULT_OUT_REL
    assert ctx["out"].parent.is_dir()


@then("中文界面会本地化 Gherkin 关键字")
def gherkin_keywords_localize(ctx: dict) -> None:
    html = ctx["html"]
    for keyword in ("功能", "场景", "假如", "当", "那么"):
        assert f'data-gherkin-keyword="{keyword}"' in html
    for translated in ('"功能": "Feature"', '"场景": "Scenario"', '"假如": "Given"', '"当": "When"', '"那么": "Then"'):
        assert translated in html
    for translated in ('Feature: "功能"', 'Scenario: "场景"', 'Given: "假如"', 'When: "当"', 'Then: "那么"'):
        assert translated in html


@then("页面不引用任何外部资源")
def no_external_resources(ctx: dict) -> None:
    html = ctx["html"]
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "@import" not in html


@then("只列出项目自己的 Gherkin 文件")
def vendor_features_excluded(ctx: dict) -> None:
    html = ctx["html"]
    assert "真实行为" in html
    for excluded in ("Vendor behavior", "Venv behavior", "Hidden behavior"):
        assert excluded not in html


@then("页面说明还没有 Gherkin 文件")
def empty_state(ctx: dict) -> None:
    assert "no gherkin files" in ctx["html"].lower()


@then("页面列出该文件、原始文本和解析警告")
def broken_file_shown(ctx: dict) -> None:
    html = ctx["html"]
    assert "features/broken.feature" in html
    assert "只有普通文本" in html
    assert "could not be parsed" in html


@then("gherkin-to-html 脚本被放入技能的 scripts 目录")
def converter_installed(project: Path) -> None:
    scripts = project / ".claude" / "skills" / "gherkin-bdd" / "scripts"
    assert (scripts / "gherkin_to_html.py").exists()
