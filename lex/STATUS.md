# lex — status at a glance

The bottom layer of the constitutional agent stack: a build system where an
agent is given a compiled, provable context and nothing else, walled in while
it works, and checked afterwards by something that never saw its output.

**Read `docs/lab-brief.md` and `harness/LOOP.md` first.** LOOP.md is the
standing state and standing law — it is the first read of every session and
the last write of every session. `docs/lex-v2.md` is the current ruling.

## What is real, and proven

| Thing | Where | State |
|---|---|---|
| Symbol indexer (the subject being built) | `analyzer/` | working; identity = path + sig_hash + body_hash |
| Spec compiler — E01–E08 block, W01–W07 print | `harness/speccc.py` | working |
| Plan/join — spec resolved against the real index, levels, packets | `harness/join.py` | working |
| Write + read fence (chmod, PreToolUse hook, diff gate) | `harness/fence.py` | working, role-aware |
| Dispatch — worktree, fence, packet, harvest, record | `harness/dispatch.py` | working |
| Three-probe sufficiency gate, byte-identical to archived gate.js | `harness/gate.py` | working; per-provider calibration mandatory |
| Autopilot — the conductor (P1) | `harness/autopilot.py` | **flown live**: single, parallel, full-plan walk |
| lex v1 — terminal operator, agent loop, confirm gate in code | `lex/` | working on Anthropic + xAI |
| Lex Lab — local read instrument | `lab/` | 1 of 7 views built (Runs) |

Tests: **456 passing**. Run `.venv/bin/python -m pytest -q`.

## The constitution, in four lines

1. **No self-ratification.** No agent closes a finding or approves its own
   work. In `lex/` this is code: `lex/confirm.py` has no bypass parameter.
2. **Autopilot did not weaken that** — the unit of ratification moved from
   per-action to per-run. A human authorises one compiled plan hash; drift is
   re-checked before every level and stops the run.
3. **Bookkeeping is subordinate to the wall.** No tracker, registry or record
   step may crash, skip or weaken a dispatch or its teardown.
4. **Production-shaped tests.** A structural test builds its subject through
   the real production path and asserts against what production emits.

## Where to look for evidence

- `harness/reports/001–016.md` — every round, verbatim, with a monotonic
  findings ledger. Nothing leaves the table.
- `docs/evidence/` — packets, dispatch records, harvests, gate verdicts,
  worker transcripts, autopilot journals.
- `docs/evidence/gate-port/parity.md` — how instrument continuity was proven.

## What is NOT done

- **The A/B is not run.** Whether a compiled packet beats letting an agent
  search is the question the architecture rests on, and it is unanswered.
- P2 offices (refuter, integrator, monarch, observers) — not built.
- P3 optimizer, P4 larp detector / office ablations — not built.
- Lab: Session, Law, Graph, Evals, Monarch views — not built.
- Doctrine-1 sweep: 10 tests in `tests/test_autopilot.py` still assert
  against hand-built shapes.
