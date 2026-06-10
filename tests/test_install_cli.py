from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "bin" / "bdd-bootstrap"
CHECK_SCRIPT = ROOT / "scripts" / "check_bdd_sync.py"
MARKER_START = "<!-- gherkin-bdd:rule:start -->"
CLAUDE_REF = ".claude/skills/gherkin-bdd/BDD.md"
CODEX_REF = ".agents/plugins/plugins/gherkin-bdd/BDD.md"


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
        self._old_cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self._old_cwd)
        self.tmp.cleanup()

    # --- install: claude ---------------------------------------------------

    def test_claude_install_copies_tree_and_registers_hook(self) -> None:
        self.assertEqual(self.cli.main(["claude"]), 0)

        plugin = self.root / ".claude" / "skills" / "gherkin-bdd"
        self.assertTrue((plugin / ".claude-plugin" / "plugin.json").exists())
        self.assertTrue((plugin / "skills" / "gherkin-bdd" / "SKILL.md").exists())
        self.assertTrue((plugin / "BDD.md").exists())
        self.assertFalse((plugin / "skills").is_symlink())

        settings = json.loads((self.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("check_bdd_sync.py", command)
        self.assertIn("--host claude", command)
        self.assertIn("--bdd-ref", command)
        self.assertIn("${CLAUDE_PROJECT_DIR}", command)

    def test_claude_install_writes_import_reference(self) -> None:
        self.assertEqual(self.cli.main(["claude"]), 0)
        text = (self.root / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(MARKER_START, text)
        self.assertIn(f"@{CLAUDE_REF}", text)
        self.assertFalse((self.root / "AGENTS.md").exists())

    # --- install: codex ----------------------------------------------------

    def test_codex_install_copies_tree_and_registers_hook(self) -> None:
        self.assertEqual(self.cli.main(["codex"]), 0)

        plugin = self.root / ".agents" / "plugins" / "plugins" / "gherkin-bdd"
        self.assertTrue((plugin / ".codex-plugin" / "plugin.json").exists())
        self.assertTrue((plugin / "skills" / "gherkin-bdd" / "SKILL.md").exists())
        self.assertTrue((plugin / "BDD.md").exists())
        self.assertFalse((plugin / "skills").is_symlink())
        self.assertFalse((plugin / "BDD.md").is_symlink())

        marketplace = json.loads(
            (self.root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["plugins"][0]["name"], "gherkin-bdd")
        self.assertEqual(marketplace["plugins"][0]["source"]["path"], "./plugins/gherkin-bdd")

        hooks = json.loads((self.root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("--host codex", command)
        self.assertIn("--bdd-ref", command)

    def test_codex_install_writes_required_reading_directive(self) -> None:
        self.assertEqual(self.cli.main(["codex"]), 0)
        text = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(MARKER_START, text)
        self.assertIn("MUST read", text)
        self.assertIn(CODEX_REF, text)
        self.assertFalse((self.root / "CLAUDE.md").exists())

    # --- install: shared behavior ------------------------------------------

    def test_install_is_idempotent(self) -> None:
        self.assertEqual(self.cli.main(["claude"]), 0)
        self.assertEqual(self.cli.main(["claude"]), 0)

        plugin = self.root / ".claude" / "skills" / "gherkin-bdd"
        self.assertTrue((plugin / "skills" / "gherkin-bdd" / "SKILL.md").exists())
        settings = json.loads((self.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8").count(MARKER_START), 1)

    def test_invalid_host_exits(self) -> None:
        with self.assertRaises(SystemExit):
            self.cli.main(["github"])

    # --- check script: reference sync --------------------------------------

    def _run_check(self, project_dir: Path, host: str, bdd_ref: str) -> str:
        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT), "--host", host, "--bdd-ref", bdd_ref],
            input=json.dumps(
                {"cwd": str(project_dir), "hook_event_name": "SessionStart", "source": "startup"}
            ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_check_claude_writes_import(self) -> None:
        project = self.root / "project"
        project.mkdir()

        payload = json.loads(self._run_check(project, "claude", CLAUDE_REF))
        self.assertEqual(payload["hookSpecificOutput"]["hookEventName"], "SessionStart")
        text = (project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(f"@{CLAUDE_REF}", text)
        self.assertIn(MARKER_START, text)
        self.assertFalse((project / "AGENTS.md").exists())

    def test_check_codex_writes_directive(self) -> None:
        project = self.root / "project"
        project.mkdir()

        self._run_check(project, "codex", CODEX_REF)
        text = (project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("MUST read", text)
        self.assertIn(CODEX_REF, text)
        self.assertFalse((project / "CLAUDE.md").exists())

    def test_check_preserves_surrounding_content(self) -> None:
        project = self.root / "project"
        project.mkdir()
        (project / "CLAUDE.md").write_text("# My project\n\nSome notes.\n", encoding="utf-8")

        self._run_check(project, "claude", CLAUDE_REF)
        text = (project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("# My project", text)
        self.assertIn("Some notes.", text)
        self.assertIn(f"@{CLAUDE_REF}", text)

    def test_check_idempotent_on_second_run(self) -> None:
        project = self.root / "project"
        project.mkdir()

        first = self._run_check(project, "claude", CLAUDE_REF)
        self.assertNotEqual(first.strip(), "")
        before = (project / "CLAUDE.md").read_text(encoding="utf-8")

        second = self._run_check(project, "claude", CLAUDE_REF)
        self.assertEqual(second.strip(), "")
        self.assertEqual((project / "CLAUDE.md").read_text(encoding="utf-8"), before)
        self.assertEqual(before.count(MARKER_START), 1)

    def test_check_refreshes_managed_region(self) -> None:
        project = self.root / "project"
        project.mkdir()
        stale = f"# Project\n\n{MARKER_START}\nOLD STALE\n<!-- gherkin-bdd:rule:end -->\n"
        (project / "CLAUDE.md").write_text(stale, encoding="utf-8")

        self._run_check(project, "claude", CLAUDE_REF)
        text = (project / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(f"@{CLAUDE_REF}", text)
        self.assertNotIn("OLD STALE", text)
        self.assertIn("# Project", text)
        self.assertEqual(text.count(MARKER_START), 1)


if __name__ == "__main__":
    unittest.main()
