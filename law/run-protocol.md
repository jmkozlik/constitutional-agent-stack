---
type: law
labels: [governance, run, architecture]
status: live
---
# Run Protocol — how work is identified, tracked, and archived

## Run identity
- run-id: `r<NNN>-<slug>` for standard/mega, `rq<NNN>-<slug>` for quick lane
  (e.g. r001-oauth-login, rq003-fix-typo). NNN = next integer after the
  highest across executors/archive/ and the active RUN-STATE, counted
  separately per prefix. Slug ≤ 3 words.

## RUN-STATE block (machine-readable, in council/state.md)
Exactly one block; hooks parse it. Format:

    <!-- RUN-STATE
    run-id: r001-example
    lane: standard | quick | mega | none
    rationale: <one line — REQUIRED for quick and mega>
    project: </abs/path/to/repo>
    status: planning | executing | verifying | window | complete | none
    -->

`lane: none` between runs. The chair updates this at every stage transition.

## Paths per run
- Contracts: executors/contracts/<run-id>/<task-id>.md  (template: _system/templates/contract.md; IMMUTABLE once status: executing — amendments only via triage, ledgered)
- Heartbeats: executors/active/<agent-id>.md  (template: working-state.md)
- Archive bundle (post-run): executors/archive/<run-id>/
  - working-states (moved from active/), debrief-<n>.md files,
    verify-report-<task-id>.md files, digest.md (clerk output)
- Ledger: every run gets entries at start (NNNN-<run-id>-start.md: lane +
  rationale + contract list) and end (NNNN-<run-id>-complete.md: outcome +
  verify summary). Ledger numbering: next NNNN, zero-padded 4.

## Branches
- Executor worktrees auto-branch as worktree-agent-<id> (harness-managed).
- Integrator merges executor branches into `run/<run-id>`, runs full-system
  verify there, then merges run/<run-id> into the project's main per its
  conventions. Executor branches are deleted after merge.

## Spawn markers (hook-enforced)
Executor spawn prompts MUST contain these two lines:
    EXECUTOR-SPAWN run-id: <run-id>
    CONTRACT: $VAULT_ROOT/executors/contracts/<run-id>/<task-id>.md
The spawn-guard blocks executor spawns without an existing contract file.

## Substrate note (ledgered decision)
Phase 1 substrate: Agent tool + worktree isolation + SendMessage-by-id.
Standing teams (TeamCreate) adopted when live n↔n interface-question volume
demonstrably needs them — earn complexity, don't presume it.
