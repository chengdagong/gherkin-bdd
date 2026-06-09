from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "bin" / "bdd-bootstrap"
CHECK_SCRIPT = ROOT / "scripts" / "check_bdd_sync.py"


def load_cli():
    loader = SourceFileLoader("bdd_bootstrap_cli", str(CLI_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load CLI module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class InstallCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cli = load_cli()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_installs_claude_copy_and_codex_symlink_targets(self) -> None:
        project_dir = self.root / "project"

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        claude_plugin = project_dir / ".claude" / "skills" / "gherkin-bdd"
        marketplace = project_dir / ".agents" / "plugins" / "marketplace.json"
        codex_plugin = marketplace.parent / "plugins" / "gherkin-bdd"

        self.assertTrue((claude_plugin / ".claude-plugin" / "plugin.json").exists())
        self.assertTrue((claude_plugin / "skills" / "gherkin-bdd" / "SKILL.md").exists())
        self.assertTrue((claude_plugin / "BDD.md").exists())
        self.assertFalse((claude_plugin / ".claude-plugin").is_symlink())
        self.assertFalse((claude_plugin / "skills").is_symlink())
        self.assertTrue((codex_plugin / ".codex-plugin").is_symlink())
        self.assertTrue((codex_plugin / "skills").is_symlink())
        self.assertTrue((codex_plugin / "BDD.md").is_symlink())

        payload = json.loads(marketplace.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "project")
        self.assertEqual(payload["plugins"][0]["name"], "gherkin-bdd")
        self.assertEqual(payload["plugins"][0]["source"]["path"], "./plugins/gherkin-bdd")

    def test_target_claude_only_copies_shared_files(self) -> None:
        project_dir = self.root / "project"

        exit_code = self.cli.main(
            [
                "--target",
                "claude",
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        claude_dir = project_dir / ".claude" / "skills"
        skill = claude_dir / "gherkin-bdd" / "skills" / "gherkin-bdd" / "SKILL.md"
        self.assertTrue(skill.exists())
        self.assertFalse((claude_dir / "gherkin-bdd" / "skills").is_symlink())

    def test_appends_bdd_md_to_existing_project_instruction_files(self) -> None:
        project_dir = self.root / "project"
        project_dir.mkdir()
        claude_md = project_dir / "CLAUDE.md"
        agents_md = project_dir / "agents.md"
        claude_md.write_text("# Claude\n", encoding="utf-8")
        agents_md.write_text("# Agents\n", encoding="utf-8")

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        bdd_content = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()
        self.assertIn(bdd_content, claude_md.read_text(encoding="utf-8"))
        self.assertIn(bdd_content, agents_md.read_text(encoding="utf-8"))

        self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--force",
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(claude_md.read_text(encoding="utf-8").count(bdd_content), 1)
        self.assertEqual(agents_md.read_text(encoding="utf-8").count(bdd_content), 1)

    def test_does_not_create_missing_project_instruction_files(self) -> None:
        project_dir = self.root / "project"

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertFalse((project_dir / "CLAUDE.md").exists())
        self.assertFalse((project_dir / "AGENTS.md").exists())

    def test_creates_missing_project_instruction_files_when_enabled(self) -> None:
        project_dir = self.root / "project"

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "yes",
            ]
        )

        self.assertEqual(exit_code, 0)
        bdd_content = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()
        self.assertEqual((project_dir / "CLAUDE.md").read_text(encoding="utf-8").strip(), bdd_content)
        self.assertEqual((project_dir / "AGENTS.md").read_text(encoding="utf-8").strip(), bdd_content)

    def test_asks_before_creating_missing_project_instruction_files(self) -> None:
        project_dir = self.root / "project"
        answers = iter(["y", "n"])

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
            ],
            input_func=lambda _prompt: next(answers),
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue((project_dir / "CLAUDE.md").exists())
        self.assertFalse((project_dir / "AGENTS.md").exists())

    def test_registers_session_start_hook_for_both_hosts(self) -> None:
        project_dir = self.root / "project"

        exit_code = self.cli.main(
            [
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        claude_settings = json.loads((project_dir / ".claude" / "settings.json").read_text(encoding="utf-8"))
        claude_hook = claude_settings["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertIn("check_bdd_sync.py", claude_hook["command"])
        self.assertIn("${CLAUDE_PROJECT_DIR}", claude_hook["command"])

        codex_hooks = json.loads((project_dir / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        codex_hook = codex_hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertIn("check_bdd_sync.py", codex_hook["command"])
        self.assertIn(".agents/plugins/plugins/gherkin-bdd", codex_hook["command"])

    def test_session_start_hook_is_idempotent(self) -> None:
        project_dir = self.root / "project"
        base_args = [
            "--source",
            str(ROOT),
            "--project-dir",
            str(project_dir),
            "--create-missing-instructions",
            "no",
        ]

        self.cli.main(base_args)
        self.cli.main(base_args + ["--force"])

        claude_settings = json.loads((project_dir / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(claude_settings["hooks"]["SessionStart"]), 1)
        codex_hooks = json.loads((project_dir / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(codex_hooks["hooks"]["SessionStart"]), 1)

    def test_session_hook_preserves_existing_settings(self) -> None:
        project_dir = self.root / "project"
        (project_dir / ".claude").mkdir(parents=True)
        (project_dir / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {"matcher": "startup", "hooks": [{"type": "command", "command": "echo other"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )

        exit_code = self.cli.main(
            [
                "--target",
                "claude",
                "--source",
                str(ROOT),
                "--project-dir",
                str(project_dir),
                "--create-missing-instructions",
                "no",
            ]
        )

        self.assertEqual(exit_code, 0)
        settings = json.loads((project_dir / ".claude" / "settings.json").read_text(encoding="utf-8"))
        commands = [
            hook["command"]
            for entry in settings["hooks"]["SessionStart"]
            for hook in entry["hooks"]
        ]
        self.assertIn("echo other", commands)
        self.assertTrue(any("check_bdd_sync.py" in command for command in commands))

    def _run_check(self, project_dir: Path) -> str:
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT)],
            input=json.dumps(
                {"cwd": str(project_dir), "hook_event_name": "SessionStart", "source": "startup"}
            ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_check_script_appends_rule_into_existing_file(self) -> None:
        project_dir = self.root / "project"
        project_dir.mkdir()
        (project_dir / "CLAUDE.md").write_text("# Project\n", encoding="utf-8")
        bdd_content = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()

        payload = json.loads(self._run_check(project_dir))
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("CLAUDE.md", payload["hookSpecificOutput"]["additionalContext"])
        self.assertIn(bdd_content, (project_dir / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_check_script_is_idempotent_when_rule_present(self) -> None:
        project_dir = self.root / "project"
        project_dir.mkdir()
        bdd_content = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()
        (project_dir / "CLAUDE.md").write_text("# Project\n\n" + bdd_content + "\n", encoding="utf-8")

        self.assertEqual(self._run_check(project_dir).strip(), "")
        self.assertEqual(
            (project_dir / "CLAUDE.md").read_text(encoding="utf-8").count(bdd_content), 1
        )

    def test_check_script_creates_claude_md_when_none_exist(self) -> None:
        project_dir = self.root / "project"
        project_dir.mkdir()
        bdd_content = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()

        payload = json.loads(self._run_check(project_dir))
        self.assertIn("CLAUDE.md", payload["hookSpecificOutput"]["additionalContext"])
        self.assertEqual((project_dir / "CLAUDE.md").read_text(encoding="utf-8").strip(), bdd_content)


if __name__ == "__main__":
    unittest.main()
