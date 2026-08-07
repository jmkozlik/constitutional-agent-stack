# LOOP — standing state (first read of every session, last write of every session)

**Updated:** 2026-08-07, after report 003 (F15/F16 applied verbatim, F19
replay checker built and closed, F18 spec diff PROPOSED — awaiting
ratification, incl. the importer-set definition pin). New standing
protocols: ratification fidelity (ruled-text vs applied-diff side by side;
mismatch stops regardless of blocking class) and harvested code stored
inert (.py.txt — evidence is never indexable source). Replay is `python -m
harness.join replay <node> --commit C --shipped F` (IDENTICAL 0 / DIVERGED
1 / CHECK-ERROR 2, commit-anchored). Ledger F1–F19: harness/reports/003.md.
Queue: 3b → 3c → F18 ratification → 3d → W05 restructure.

**Previous:** 2026-08-07, session close after report 002.

## Where the build is

- **STEP 3a HAS RUN AND IS CLEAN**: one node (affected_symbols), one
  worktree at e667744, one compiled packet (68437893ac8d), no search,
  inside the fence. 4/4 done_when ATTEST, zero code written, no fence
  events, diff gate clean, one non-blocking REQUEST_MEM. The thesis held
  for a validation-only dispatch. Full evidence: harness/reports/002.md +
  docs/evidence/step3a/.
- Stop rule amended (blocking-only stops); packet replay is a standing
  tuple line (6/6 IDENTICAL this round). F12/F13 ruled and applied.
- Open for ruling: **F18** (unresolved reference edges never reach the
  affected report — the executor's own finding), F15/F16 rewords optional.
- Queue: **3b** (re-dispatch with .harness/out/ attestation.md + defects.md
  required verbatim — closes F17), **3c** (dispatch-record emitter, retires
  the MANUAL label), then the ratified W05 restructure (index_assembly;
  retires F6).
- Authoritative findings ledger: harness/reports/002.md (F1–F18).

## Protocol (ratified 2026-08-07)

- Reports to the ratifier: `harness/reports/NNN.md`, committed. Sections:
  state, evidence, flags, findings ledger, next. Verbatim transcripts only.
  Key tuple up top (commit, spec plan hash, dispatch plan hash, packet
  hashes, fence hash). Probe verdicts quoted in full. Findings ledger is
  monotonic; nothing leaves the table.
- Gate: identical three-probe protocol (executor:symbol_table,
  executor:affected_symbols, tester:affected_symbols; packet-only, no
  tools). Stop rule: anything new that is not F3/F4 stops the line.

## Findings ledger pointer

Authoritative table lives in the latest report under harness/reports/.

## Next

See the `next` section of the latest report.
