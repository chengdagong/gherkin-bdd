# Install plain project-level skills; no plugin packaging

Both Claude Code (`.claude/skills/`) and Codex (`.agents/skills/`) natively discover
project-level skills committed into a repository. The installer therefore copies the
skill (`SKILL.md` + `BDD.md` + the sync script) straight into those directories and
registers the SessionStart hook in the host's own config. The former plugin
packaging — `.claude-plugin/` and `.codex-plugin/` manifests plus a Codex
`marketplace.json` registration — was removed: for project-level installs it added
moving parts without adding capability.

Evidence: the Codex skills documentation
(https://developers.openai.com/codex/skills) lists `$REPO_ROOT/.agents/skills` as
an official scan location and describes plugins as a separate, optional layer for
distributing skills "beyond a single repo" — direct skill folders work locally.
Claude Code likewise discovers `.claude/skills/` project skills natively.

## Considered options

- Keep the dual manifests and Codex marketplace registration — rejected: only the
  dev-mode `claude --plugin-dir .` loader and a hypothetical marketplace
  distribution used them; the per-project install path never did (Claude installs
  bypassed plugin machinery entirely, copying into `.claude/skills/`).

## Consequences

- The Claude skill is invoked as `/gherkin-bdd` (no plugin namespace).
- If marketplace distribution is wanted later, manifests can be reintroduced
  alongside the same shared skill source without changing the installer's contract.
