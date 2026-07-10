# stack-tools

God-space machinery for the agent stack, built through the stack itself and
installed to `~/.claude/hooks/` by the promotion procedure (after canary).
Node builtins only; no dependencies. Everything resolves the vault via
`VAULT_ROOT` (default `~/vault`).

- `beacon.js` — health arithmetic. Reads ledger/telemetry/archive artifacts
  and computes the system-health report that reaches god mechanically.
  Agents see beacon OUTPUTS; the formulas live only here, in god-space.
- `beacon-alarm.js` — threshold watcher over beacon output: staleness,
  regressions, alarm records to `god/beacons/`.
- `graduation.js` — regency arithmetic: counts consecutive unvetoed monarch
  decisions per power class; any veto resets the class.
- `leak-linter.js` — metric-blindness enforcement. Scans a `proposed/`
  artifact for grading-machinery language (shadow-dimension terms,
  threshold/weight patterns) that must never leak to lower layers. Exit 2 on
  any hit; writes a flag to `god/beacons/leak-flags/`. First gate of every
  promotion.
- `retaliation-flag.js` — flags prunings that closely follow a target's
  adverse governance filings; a flagged pruning cannot proceed without
  monarch review.
- `compile.js` — the law→definition compiler. Regenerates law-embedded agent
  defs from vault law (core.md + role charter) injected into stored body
  templates (`templates/*.body.md`, roles mapped by `manifest.json`).
  Writes ONLY to a staging dir, gated by an independent SHA-256 hash file;
  never touches the live agents dir itself.

## Tests

`tests/` holds the gate fixtures the stack's own test-engineers wrote for
these tools (blind, from contract interface specs). Most take the tool path
as argv:

```
node tests/gate_t1-graduation_counting.js ./graduation.js
node tests/gate_t2-leak-linter_behaviors.js ./leak-linter.js
```

The beacon/beacon-alarm fixtures expect the tool colocated with the fixture
(worktree convention): copy `beacon.js` / `beacon-alarm.js` into `tests/`
first, then run the fixture with no argument. The `gate_t3-compiler_*`
fixtures exercise a live vault + agents dir and need a populated
`VAULT_ROOT` to run.
