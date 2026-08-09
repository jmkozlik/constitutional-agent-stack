# Wrap map — harness × constitutional-agent-stack

Based on an actual review of github.com/jmkozlik/constitutional-agent-stack
(README, law/templates/contract.md, ledger/FORMAT.md). Categories: what the
harness reuses as-is, what it generates into, what it absorbs, what it
upgrades from law to physics, and what is genuinely new. Items marked
**verify** need a look at a file I didn't pull.

---

## The headline finding

**The contract template is already a hand-authored spec node.** Field by
field:

| contract.md today | spec node field |
|---|---|
| Goal | `one_liner` |
| Files owned (exhaustive — touching anything else is a violation) | `writes` |
| Dependencies (task-ids or "none") | `references` |
| Interface spec (precise enough to test from alone) | `done_when` |
| Model tier (sonnet \| opus) | `model:` — **add this field to the spec format** |

The chair has been hand-compiling spec nodes into contracts for 12+ runs.
The harness doesn't replace the contract — it makes the contract a compiler
output. `task.compile` = fill `law/templates/contract.md` from the node.
Contracts stay immutable, keep their run-ids, keep satisfying spawn-guard.
Nothing downstream of the contract (panel, refuter, integrator, ledger
citations) needs to know anything changed.

This also means the system was never missing a spec format. It was missing
the automation of the chair's decomposition step — which is exactly what the
spec compiler + distribution pipeline are.

---

## The second finding: the motion clauses migrate to the compiler

Nearly every battle-scar clause in the contract template is an obligation on
**the chair at contract-writing time**, not on the executor:

- m-w1b: a "do NOT 500" assertion MUST enumerate the violating inputs; the
  chair MUST grep the handler for every call that raises on malformed input
- motion 0070: every enumerated outcome branch MUST have a discriminating
  fixture; the chair MUST list branches and confirm coverage
- m-w2-aria-role: a getByRole fixture MUST pin the ARIA role, or the blind
  tester and implementer diverge and burn a retry rung
- m-w3c: a background loop spec MUST state resource lifetime relative to the
  sleep
- orphan sweep: any enumerated removal list MUST close with the
  grep-confirmed-zero-uses clause

These are spec-authoring rules that accreted as law because there was no
compiler to hold them. Under the harness they become compiler checks and
Phase 0 interview questions:

| today (clause in the template) | tomorrow (mechanical home) |
|---|---|
| error-class assertion without enumerated vectors is a contract defect | W-class warning: `done_when` asserts an error boundary, no violating inputs listed → Phase 0 asks for them |
| enumerated branch without a fixture is a returnable gate defect | compile check: every `done_when` branch maps to a tester fixture |
| unpinned ARIA role on a role query | interface-completeness check on the spec node |
| chair MUST grep for raise-on-malformed / streaming hazards | analyzer query, run at compile — the grep the chair does by hand is a caller-map lookup |

This is the amendment loop retargeting, per your own routing rule: today a
ratified motion amends the contract *template* (prompt-adjacent law); under
the harness the same motion amends the *compiler* (mechanical law). The
loop's output gets stronger without the loop changing.

---

## Reused as-is

- **The entire governance top half.** Monarch, council lenses, wildcard,
  observers, panel protocol, grievance window, motions, ratification,
  leak-lint, canary. The harness sits below all of it.
- **Worktree isolation + spawn-guard.** Already per-contract. The
  scheduler's dispatch just creates worktrees and contract files in the
  order the graph dictates; spawn-guard keeps enforcing existence.
- **The law→charter compiler** (`tools/stack-tools/compile.js`). Staging
  dir, independent hash gate, byte-identical recompile — this is exactly
  the discipline identity compilation needs, and it already exists with
  `templates/` + `manifest.json`. `identity.compile` emits **into** this
  pipeline, not beside it. The law-injection hook is already the identity
  delivery mechanism.
- **The ledger + ledger-guard.** Append-only at the tool layer for every
  rank. See migration notes for how telemetry lands without flooding it.
- **Refuter and integrator seats**, unchanged. The integrator's
  diff-subset-of-owned-files assertion is the same check as E05, applied
  at merge time — belt and suspenders, keep both.

## Generated-into

- **Contracts** — from spec nodes, per the headline finding.
- **Guardrails.** The pattern "hook reads a per-run file and blocks the
  tool call" already exists (spawn-guard reads the contract). Write-set
  fencing is the same pattern pointed at the owned-files list.
  **verify:** whether a write-fence hook exists today or only spawn-guard —
  hooks/README.md has the wiring.
- **Panel input.** The lenses currently review hand-written plans. Under
  the harness they review the compile output: the plan, max width, critical
  path, W01 open items, low-confidence serializations. The shape report is
  the panel packet.

## Absorbed

- **Context-builder → CPM.** The utility seat currently writes rehydration
  briefs — judgment-assembled context. The CPM replaces routine briefs with
  compiled packets; the seat survives as the privileged resolver for
  misses past layer 2. Function, not citizen, either way.
- **`.stack-state.md` → the handoff.** The protocol-scaffolding clause
  already defines a worktree-local, never-merged, harvested-from-disk
  working-state note. That *is* the reported-state handoff, in production
  today. The CPM formalizes it: harvest at kill, carry into the next
  spawn's state section tagged agent-authored. The contract clause that
  keeps it out of git stays exactly as written.

## Upgraded from law to physics

- **The blind tester's bar.** Today it is constitutional — the charter bars
  reading any implementation, and the contract's interface spec is the sole
  shared surface (the ARIA clause exists precisely because that seam is the
  only place implementer and tester can coordinate). Under the harness the
  bar becomes structural: the tester's packet is assembled from the spec
  node with the executor worktree excluded from attribution scope. The
  stack's own doctrine — rules as hooks and arithmetic, not prompts asking
  agents to behave — applied to context itself.
  **verify:** whether any read-guard hook backs the charter bar today, or
  it is charter-text only.

## New, no current counterpart

Symbol index and attribution graph · context packets · kill-and-respawn
scheduling driven by graph levels · miss-depth telemetry · the eval layer.

---

## Migration notes

**Ledger volume.** Entries are one file each, globally monotonic 4-digit
numbering, controlled-vocabulary labels from law/retrieval-guide.md, and the
format's own rule is that every claim cites artifacts. Two consequences:

1. Miss telemetry and invalidation events are high-frequency and do NOT
   become ledger entries. They land as **run artifacts** (miss log, packet
   hashes, invalidation log) cited from the already-mandatory run start and
   completion entries. Packet hash per contract goes in the run-start entry
   next to the contract list.
2. New labels (packet, miss, eval) require amending the controlled
   vocabulary — which is a law amendment riding the promotion procedure.
   The harness's arrival is itself a governed change. That is correct and
   worth saying out loud at the demo.

**Chair shrinks, doesn't die.** Decomposition and dispatch automate; the
chair keeps goal-level judgment, seam arbitration from contract text, and
authorship of nothing it votes on. The role's clause in law barely changes.

**Proof run rides the existing lifecycle.** The single-node proof (one
compiled packet, one worktree, no search tool) should run **inside** the
stack's run protocol: generated contract satisfies spawn-guard, blind
tester and refuter run normally, ledger entries file normally. The first
harness run being indistinguishable from a governed run — except that the
contract was compiled and the executor never searched — is the whole
demonstration.

**Spec format amendments out of this review:** add `model:` (from Model
tier); keep task-ids/run-ids flowing through so ledger citations resolve;
`done_when` inherits the interface-spec bar — precise enough to test from
alone.
