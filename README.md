# constitutional-agent-stack

**A working constitutional government for AI agents, built on Claude Code.**

A short body of written law ([`law/core.md`](law/core.md)) is compiled into
per-role agent charters; executors do contracted work in isolated git
worktrees; council lenses review plans before any executor spawns;
adversarial refuters attack delivered work; observers grade runs from
artifacts after the fact; an autonomous monarch ratifies or vetoes against a
written vision; every governance act lands in an append-only ledger; and new
machinery reaches production only through a canary rollout. The rules that
matter are not prompts asking agents to behave — they are hooks and
arithmetic that block the tool call.

```
contract → panel review → executors ∥ blind test-engineer → refuter
        → integrator → grievance window → observers → motions → vote
        → monarch ratification → leak-lint → canary → production
```

## By the numbers

| | |
|---|---|
| Articles of law | 5 (evidence, communication, memory, governance, death) |
| Charters | 4 ranks, one compiler, zero hand-edited definitions |
| Compiled agent definitions | 12 (the monarch is handwritten; the chair is the live session) |
| Enforcement hooks | ~15 — spawn-guard, ledger-guard, law injection, telemetry |
| Gate fixtures on the machinery | 309 passing in this export |
| CLI test suite | 158/158 |
| Reproducibility | law + templates recompile **byte-identical** to `agents/` |
| Production mileage | 12+ governed runs, 160+ ledger entries at export time |

## Why

Scalable oversight of untrusted agent work is a systems-engineering problem,
not a prompting problem. A single agent asked to "review its own work" grades
its own homework; a swarm of agents with shared write access negotiates in
DMs and merges its own mistakes. The design bet here is that the same
machinery human organizations use to stay honest under misaligned incentives
— separation of powers, immutable contracts, blind verification, append-only
records, prosecution on evidence — can be built cheaply out of agent
definitions, filesystem layout, and ~15 small hooks, and that it measurably
changes what a run produces.

This is not a proposal. It is extracted from a working, daily-driven private
instance: 12+ governed runs and 160+ ledger entries in the production vault
at the time of export. The contract template in
[`law/templates/contract.md`](law/templates/contract.md) is the visible scar
tissue — most of its clauses are ratified motions filed by executors after
specific, cited failures.

## Architecture

### The hierarchy

```
god        — the human owner. Reads digests, signs off during regency.
monarch    — autonomous sovereign. Governs by a written vision.md; ratifies
             or vetoes passed motions; runs alignment audits. Sees beacon
             outputs, never formulas.        agents/stack-monarch.md
council    — chair (executive: decomposes goals, writes contracts, runs
             merges; votes on nothing it authored) + three member lenses
             (advocate, evidence-skeptic, system-conservative) convened
             fresh per decision, plus a wildcard seat with voice, not vote.
             agents/stack-lens-*.md, agents/stack-wildcard.md
observers  — post-run analysts, artifact-only: behavior analyst
             (qualitative) and efficiency analyst (operational). Grade runs,
             hunt metric-gaming, draft candidate machinery to proposed/.
             agents/stack-behavior-analyst.md, agents/stack-efficiency-analyst.md
executors  — implementers, blind test-engineers, and one integrator per
             run, each locked to a contract in its own worktree.
             agents/stack-implementer.md, agents/stack-test-engineer.md,
             agents/stack-integrator.md
utilities  — refuter (adversarial verifier) and context-builder
             (rehydration briefs). Functions, not citizens.
             agents/stack-refuter.md, agents/stack-context-builder.md
```

Everyone is bound by [`law/core.md`](law/core.md) (evidence, communication,
memory, governance, death — five articles) plus the charter for their rank
([`law/charters/`](law/charters/)). The compiler
([`tools/stack-tools/compile.js`](tools/stack-tools/compile.js)) regenerates
every agent definition from law + body template, so the law has one source
of truth and the definitions cannot drift from it silently.

### The run lifecycle

Defined in [`law/run-protocol.md`](law/run-protocol.md):

1. **Contract.** The chair decomposes the goal into per-task contracts
   ([`law/templates/contract.md`](law/templates/contract.md)): exhaustive
   file ownership, an interface spec precise enough to test from alone, a
   model tier. Contracts are immutable once execution starts.
2. **Panel.** The three council lenses review the plan independently
   (verdict + confidence written before convening, then a convene pass where
   votes change only by cited evidence). The wildcard's challenge must be
   answered on the record.
3. **Executors in worktrees.** Implementers build in isolated worktrees;
   `hooks/spawn-guard.js` blocks any executor spawn without an existing
   contract file. In parallel, a test-engineer — constitutionally barred
   from reading any implementation — writes gate fixtures from the interface
   spec alone.
4. **Refuter.** Delivered work meets an adversarial verifier whose only job
   is to break the claim "this satisfies the contract". Verdicts are
   REFUTED with reproducible evidence, or NOT-REFUTED with the attack list.
5. **Integrator.** One per run merges verified branches, asserts each
   branch's diff is a subset of its contract's owned files, owns the seams,
   runs the full suite. Semantic seam conflicts go back to the chair, who
   arbitrates from contract text alone.
6. **Window.** Executors file debriefs and evidence-cited motions;
   `hooks/clerk.js` compiles the anonymized grievance digest (the chair
   never compiles it).
7. **Observers.** After the window closes, both observer seats grade the
   archive bundle: cited scorecards, behavioral logs, case files. They watch
   nothing live.
8. **Motions, votes, ratification.** Observer-validated motions go to a
   council vote; passed motions go to the monarch for ratification or a
   written veto. Ratified changes to machinery ride the promotion procedure:
   leak-lint, ratify, compile to staging, canary, swap, ledger.

Every step leaves ledger entries ([`ledger/FORMAT.md`](ledger/FORMAT.md));
`hooks/ledger-guard.js` makes the ledger append-only for every rank
including the monarch.

### The enforcement layer

Judgment proposes, arithmetic disposes. [`hooks/`](hooks/) holds the
Claude Code hooks that make the constitution mechanical (spawn-guard,
ledger-guard, quick-lane bounds, telemetry, law injection);
[`tools/stack-tools/`](tools/stack-tools/) holds the god-space machinery
(health beacon and alarm, leak-linter, regency graduation arithmetic,
retaliation flagging, the law compiler). [`tools/vaultctl/`](tools/vaultctl/)
is a stdlib-only Python CLI for operating the vault (status, index
regeneration, run history).

## Measurement and Goodhart

Observers grade runs partly on *shadow dimensions* — metrics the lower ranks
are never told about, precisely so they cannot be gamed
([`tools/stack-tools/leak-linter.js`](tools/stack-tools/leak-linter.js)
exists to catch machinery that would reveal them). Publishing this repo
necessarily publishes the export-time dimension set and the beacon's health
arithmetic. That is a deliberate trade: the published set should be treated
as burned, and any production instance — including the one this was
extracted from — should rotate its own. If your oversight scheme stops
working the moment its metrics are known, that is a finding about the
scheme; rotation is the mitigation this design chooses.

## What's here vs what stays private

Public — the machinery:

- `law/` — the full constitutional text: core law, four charters, run
  protocol, retrieval guide, note templates (including the battle-scarred
  contract template).
- `agents/` — the 12 live agent definitions, law embedded.
- `tools/`, `hooks/` — vaultctl, stack-tools (with their gate-fixture test
  suites), and the hook layer.
- `ledger/FORMAT.md` + synthetic example entries.
- `vault.example/` — the vault layout as an empty skeleton.

Private — the production vault: `knowledge/`, real ledger entries, run
archives, scorecards, case files, the monarch's vision.md, and everything in
god-space. The machinery is the release; the organization's memory is not.

Paths are normalized to a `VAULT_ROOT` convention (default `~/vault`);
project-specific labels and run-specific worked-example citations were
genericized. Nothing else about the law or the code was changed.

## Status

Extracted from a working private system, July 2026. Sanitized by hand for
publication; a full writeup is forthcoming. Expect rough edges of a real
system rather than the polish of a framework — this is an instance you can
study and rebuild, not a package you can install.

## Quickstart — standing up your own vault

1. Copy the skeleton and the law:

   ```
   cp -r vault.example ~/vault
   cp -r law/* ~/vault/_system/
   export VAULT_ROOT=~/vault   # optional; ~/vault is the default
   ```

2. Install the agent definitions and machinery:

   ```
   cp agents/*.md ~/.claude/agents/
   cp hooks/* tools/stack-tools/*.js ~/.claude/hooks/
   cp -r tools/stack-tools/templates tools/stack-tools/manifest.json ~/.claude/hooks/
   ```

3. Wire the hooks into `~/.claude/settings.json` (exact JSON in
   [`hooks/README.md`](hooks/README.md)).

4. When you amend the law, recompile the definitions instead of editing them
   by hand — staging dir plus hash gate, then diff and swap. The compiler
   refuses to run without an independently recorded hash file of the live
   definitions (that is the point), so record one first:

   ```
   (cd ~/.claude/agents && shasum -a 256 stack-*.md) > "$VAULT_ROOT"/DEF-HASHES.txt

   node tools/stack-tools/compile.js \
     --vault "$VAULT_ROOT" \
     --agents-dir ~/.claude/agents \
     --staging-dir /tmp/agent-staging \
     --templates tools/stack-tools/templates \
     --manifest tools/stack-tools/manifest.json \
     --hashes "$VAULT_ROOT"/DEF-HASHES.txt
   ```

5. Initialize `~/vault/council/state.md` with a RUN-STATE block
   (`lane: none` — see [`law/run-protocol.md`](law/run-protocol.md)), write
   your first contract from the template, and run something small. The
   spawn-guard will refuse executor spawns until the contract file exists,
   which is the system working.

The monarch's `vision.md` you must write yourself. It is the one file the
whole upper half of the hierarchy is built to interpret, and it does not
transfer.

## License

MIT — see [LICENSE](LICENSE).

---

Built and daily-driven by [Jonathan Kozlik](https://app.selfsell.ai) —
[github.com/jmkozlik](https://github.com/jmkozlik) ·
[X @jmkozlik](https://x.com/jmkozlik). Writeup with production ledger
statistics forthcoming.
