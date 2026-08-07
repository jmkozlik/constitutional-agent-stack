# LOOP — standing state (first read of every session, last write of every session)

**Updated:** 2026-08-07, session close after report 001.

## Where the build is

- Analyzer v0: complete, 204 tests. The join (step 2): complete. Write-fence:
  shipped, with the v0.4.1 scratch section (.harness/scratch).
- Spec format v0.4.1 applied at commit 4e5d495; gate run; **third STOP**:
  F12 (ratified Row.error iff-condition vs V6 parse-failure behavior) and
  F13 (F10b pin vs legitimate moved rows). Candidate one-line amendments in
  harness/reports/001.md. **Step 3 NOT dispatched** — staging is 4 commands
  once F12/F13 are ruled; dispatch protocol drafted in report `next`.
- W05 restructure (index_assembly node) ratified, sequenced AFTER step 3.
  The refs W05 prints until it lands. gitio._git consumption (F6) rides
  with it.
- Authoritative findings ledger: harness/reports/001.md (F1–F13).

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
