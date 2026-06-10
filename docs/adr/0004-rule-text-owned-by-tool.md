# The BDD rule text is owned by the tool, not the project

`BDD.md` ships with the skill, and the managed-region reference points at the
installed copy. Projects do not edit their copy; rule-text changes happen in this
repository and reach a project when the installer is re-run there.

We considered the opposite (issue #2): seed `BDD.md` into the project root and
reference that instead — a root file is tracked, so the import would never dangle
on fresh clones, and the rule would become a project-owned policy document.
Rejected: the rule is coupled to the tool — its text is expected to reference the
tool's own skills and workflow — so its evolution must stay synchronized with the
skill that interprets it. Project-local ownership would fork the text and cut
projects off from upstream improvements.

## Consequences

- The fresh-clone dangle keeps its documented mitigations: target projects commit
  the installed files; this repo runs `bin/bdd-bootstrap claude` once after
  cloning.
- Re-install refreshes the rule copy — verified live by the
  "Re-installing delivers the updated rule" scenario in
  `features/bdd-rule-effect.feature`.
- A project needing extra standing instructions writes them in its own
  instruction files outside the managed region, not inside `BDD.md`.
