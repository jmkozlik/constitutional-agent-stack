# LOOP — standing state (first read of every session, last write of every session)

**Updated:** 2026-08-07, session in flight (v0.4.1 execution). This header is
stale until the session's last write.

## Where the build is

- Analyzer v0: complete, 202 tests. The join (step 2): complete. Write-fence:
  shipped (fence.py + committed PreToolUse hook + diff gate).
- Spec format: v0.4.1 being applied (F10a reword, F10b as-built pin, F11
  provenance line, fence scratch section). Then gate, then step 3.
- W05 restructure (index_assembly node) ratified, sequenced AFTER step 3.
  The refs W05 prints until it lands. gitio._git consumption (F6) rides
  with it.

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
