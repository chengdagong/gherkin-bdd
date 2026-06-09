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
BDD_CONTENT = (ROOT / "BDD.md").read_text(encoding="utf-8").strip()


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
        self.assertIn("${CLAUDE_PROJECT_DIR}", command)

    # --- install: codex ----------------------------------------------------

    def test_codex_install_symlinks_tree_and_registers_hook(self) -> None:
        self.assertEqual(self.cli.main(["codex"]), 0)

        plugin = self.root / ".agents" / "plugins" / "plugins" / "gherkin-bdd"
        self.assertTrue((plugin / ".codex-plugin").is_symlink())
        self.assertTrue((plugin / "skills").is_symlink())
        self.assertTrue((plugin / "BDD.md").is_symlink())

        marketplace = json.loads(
            (self.root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["plugins"][0]["name"], "gherkin-bdd")
        self.assertEqual(marketplace["plugins"][0]["source"]["path"], "./plugins/gherkin-bdd")

        hooks = json.loads((self.root / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("check_bdd_sync.py", command)
        self.assertIn("--host codex", command)
        self.assertIn(".agents/plugins/plugins/gherkin-bdd", command)

    # --- install: shared behavior ------------------------------------------

    def test_install_is_idempotent(self) -> None:
        self.assertEqual(self.cli.main(["claude"]), 0)
        self.assertEqual(self.cli.main(["claude"]), 0)

        plugin = self.root / ".claude" / "skills" / "gherkin-bdd"
        self.assertTrue((plugin / "skills" / "gherkin-bdd" / "SKILL.md").exists())
        settings = json.loads((self.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(len(settings["hooks"]["SessionStart"]), 1)

    def test_install_claude_syncs_claude_md_via_check_script(self) -> None:
        self.assertEqual(self.cli.main(["claude"]), 0)
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8").strip(), BDD_CONTENT)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_install_codex_syncs_agents_md_via_check_script(self) -> None:
        self.assertEqual(self.cli.main(["codex"]), 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8").strip(), BDD_CONTENT)
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_invalid_host_exits(self) -> None:
        with self.assertRaises(SystemExit):
            self.cli.main(["github"])

    # --- check script: host-aware sync -------------------------------------

    def _run_check(self, project_dir: Path, host: str | None) -> str:
        command = [sys.executable, str(CHECK_SCRIPT)]
        if host:
            command += ["--host", host]
        result = subprocess.run(
            command,
            input=json.dumps(
                {"cwd": str(project_dir), "hook_event_name": "SessionStart", "source": "startup"}
            ),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_check_claude_creates_claude_md(self) -> None:
        project = self.root / "project"
        project.mkdir()

        payload = json.loads(self._run_check(project, host="claude"))
        self.assertIn("CLAUDE.md", payload["hookSpecificOutput"]["additionalContext"])
        self.assertEqual((project / "CLAUDE.md").read_text(encoding="utf-8").strip(), BDD_CONTENT)
        self.assertFalse((project / "AGENTS.md").exists())

    def test_check_codex_creates_agents_md(self) -> None:
        project = self.root / "project"
        project.mkdir()

        self._run_check(project, host="codex")
        self.assertEqual((project / "AGENTS.md").read_text(encoding="utf-8").strip(), BDD_CONTENT)
        self.assertFalse((project / "CLAUDE.md").exists())

    def test_check_claude_creates_canonical_and_syncs_existing(self) -> None:
        project = self.root / "project"
        project.mkdir()
        (project / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")

        self._run_check(project, host="claude")
        self.assertIn(BDD_CONTENT, (project / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn(BDD_CONTENT, (project / "AGENTS.md").read_text(encoding="utf-8"))

    def test_check_idempotent_when_rule_present(self) -> None:
        project = self.root / "project"
        project.mkdir()
        (project / "CLAUDE.md").write_text("# Project\n\n" + BDD_CONTENT + "\n", encoding="utf-8")

        self.assertEqual(self._run_check(project, host="claude").strip(), "")
        self.assertEqual((project / "CLAUDE.md").read_text(encoding="utf-8").count(BDD_CONTENT), 1)

    def test_check_fallback_creates_claude_md_without_host(self) -> None:
        project = self.root / "project"
        project.mkdir()

        self._run_check(project, host=None)
        self.assertEqual((project / "CLAUDE.md").read_text(encoding="utf-8").strip(), BDD_CONTENT)


if __name__ == "__main__":
    unittest.main()
