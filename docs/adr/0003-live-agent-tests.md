# Live agent tests: @agent routes to a live suite, single-run, @todo records debt

Scenarios verifiable only by observing agent behavior get automated tests like any
other scenario: their steps drive headless coding-agent sessions (`claude -p`,
`codex exec`) against throwaway installed projects. The `@agent` tag only routes
them out of the default pytest run because they cost real model calls;
`pytest -m "agent and not todo"` executes them on demand. Probes assert binary
outcomes — a canary line appended to the installed `BDD.md` must (or must not)
surface in the session's answer — with tool access disabled for Claude (proving
the `@import` auto-loads the rule) and enabled for Codex (proving the directive
makes it actually read the file). Each probe runs once and must pass; there are
no retries and no pass-rate thresholds. A scenario whose test cannot be built yet
carries `@todo` plus an adjacent comment (why + what unblocks it), enforced by a
meta-test in the default suite that fails on undocumented debt.

## Considered options

- N-of-M pass thresholds or auto-retry for LLM nondeterminism — rejected: start
  strict single-run and revisit only if flakiness actually materializes.
- Treating `@agent` scenarios as exempt from automation — rejected: agent-in-the-
  loop automation is still automation; an exemption would let coverage rot
  silently. The tag changes where a test runs, not whether it exists.
- Deleting the un-stageable "coding agent cannot be determined" scenario —
  rejected: a new coding agent may make it stageable; it stays as recorded
  `@todo` debt instead.

## Consequences

- The live suite needs both coding-agent CLIs installed and logged in; a missing CLI
  skips. The CLI and the desktop app keep separate credentials — a 401 from
  `claude -p` means the CLI's stored login is stale (`claude` → `/login` fixes
  it). The harness strips inherited coding-agent-app env vars, so it can run even from
  inside a coding-agent session.
- Codex's sandbox refuses writes to its own `.codex/` config even in
  workspace-write mode; the live steps run codex with full access as a stand-in
  for the approval an interactive user would grant. The bootstrap skill documents
  this limitation.
