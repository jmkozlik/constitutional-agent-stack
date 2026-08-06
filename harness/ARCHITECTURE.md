# Architecture

Organized around your (0)–(5), as you described it. Every claim is labeled:

- **[yours]** — your design, as stated
- **[agreed]** — a refinement you ratified in conversation
- **[proposed]** — my addition, awaiting your call. Collected in the
  Proposals index at the end so you can ratify or reject in one pass.
- **[open]** — undecided by either of us

---

## Thesis

**[yours]** Context is a compilation artifact, not a retrieval problem. The
spec-as-code model decomposes the problem into pieces small enough that the
context an agent needs at each turn can be deterministically predicted. Agents
do not search. The system predicts and hands over.

**[agreed]** What falls out: packets are reproducible (same spec, same commit,
same packet — so a failed run can be replayed against exactly what the agent
saw), conflicts are prevented structurally rather than negotiated, and a
prediction miss is evidence about the spec, attributable to the node that
produced the packet.

---

## (0) Spec authoring

**[yours]** The user interfaces with an agent system to create the
specification document. Phase 0. A product in its own right — the bet is that
LLMs make spec authoring conversational, which is the reason spec-as-code is
viable now when it wasn't for CASE tools and MDA.

**[proposed]** The compiler's throw list is the interview script. Every throw
is a question Phase 0 asks: null resolution asks "what did you mean by this,"
a write collision asks "which node owns it," an open item asks "have you
decided yet." No separate elicitation policy needed — draft, compile, ask
about what threw, repeat.

**[yours]** Currently hand-writing the Phase 1–n spec to observe the process,
so the system that automates it can be built from real data. The corrections
and the questions that come up are the Phase 0 requirements document.

---

## (1) Spec compiler

**[yours]** The spec document is passed to the compiler, which ensures the
spec is a DAG, breaks each feature down into components with no other
dependencies — foundational portions first, then builds up — and parallelizes
the implementation by feeding disjoint tasks to the agents.

**[yours]** If two parts of the spec disagree and need the same thing changed,
the spec was written incorrectly. Caught and logged, not auto-resolved.

**[agreed]** The compiler throws on null resolution the way a compiler throws
on a null pointer dereference. Full throw list in Appendix A.

**[agreed]** Disjointness is checkable because every node declares what it
writes. Two nodes eligible to run in parallel with intersecting write sets is
a compile error, discovered before anything runs rather than at integration.

**[agreed]** Dependency edges serialize execution, not just describe it. If A
references B, B lands first. Parallelism exists only across antichains: same
topological level, no edges between them, disjoint writes. This is what makes
"agents cannot bump into each other" airtight — including the read-write case,
where A merely *holds* something B is changing.

**[agreed]** Nothing runs a model during compilation. Compile is a pure
function of (spec files, commit, analyzer version).

**[proposed]** The compiler reports max width and critical path length, so a
decomposition that kills parallelism is visible before dispatch. Decomposition
shape is a throughput property the spec author controls.

**[yours]** Working format: six fields per node — id, references, writes,
one_liner, done_when, open. Three structural, three payload copied verbatim to
agents. `speccc.py` implements this and runs today.

**[agreed]** Granularity is derived, not authored. Start coarse; miss
telemetry says which nodes to split. A node is fine enough when you can name
what it writes and one executor could finish it in one contract.

---

## (2) Context packet manager — assembly

**[yours]** The CPM is signaled on which agent type to spawn — executor for
coding, tester for adversarial review, future roles like the council — and,
from the symbol-level edges, combines three documents into a context packet:

1. **Identity** — system prompt + tool list. Nothing else. Everything that
   could go in it is owned by another component: tools by the hook manifest,
   what-to-build by the task file, what-exists by the state, the walls by the
   guardrails, the loop by the harness. **[agreed]** The tool list is
   generated from the hook manifest and the run fails on mismatch, so identity
   stops being a drift vector — the body is written once per role and frozen.

2. **Task** — the section of the spec detailing the implementation, or the
   guarantees and expected behavior for the tester. **[agreed]** Copied
   verbatim from the node's payload fields, never paraphrased. Executor and
   tester variants generated from the same node, never sharing content.

3. **Reported state** — the compiled context for this node, plus the previous
   run's handoff: the agent's report on the current state of the codebase and
   past intent, to kickstart the next spawn.

**[yours]** Packet order is identity, task, state. **[agreed]** This ordering
is also a cache boundary: identity is byte-identical across every dispatch of
a role, task is fixed per node, state is the volatile tail — so invalidation
only ever touches the cheap end of the prompt.

**[proposed]** State has two provenance classes. The compiled part is
deterministic — derived from the graph, hashed, replayable. The handoff is
agent-authored — carried forward and logged so replay still works, but marked
as a claim rather than a fact. Intent and progress are exactly what the graph
cannot derive, so the handoff carries those; code facts stay compiled. This is
the legitimate, scoped version of "the agent updates memory itself."

**[proposed]** The blind tester's packet is assembled from the spec node only,
with the executor's in-flight worktree structurally excluded from its
attribution scope. Otherwise the retrieval layer leaks the implementation —
shapes, names, signatures — and the tester writes tests that mirror the code
instead of the spec. The assembler is a covert channel nobody audits because
it isn't a prompt.

**[proposed]** Draft identity body for the executor seat (the system-prompt
half; the tool list is generated):

```markdown
---
role: executor
law_version: <hash>
tools: [read, write, edit, bash, request_mem]   # from hook manifest
---

You implement one task node and produce a proposal, not a merge.
You do not judge whether your work is correct. Verifiers do that.

Your context was compiled for you, not retrieved by you. It is
predicted, so it is incomplete. If something is not in your packet,
that means the compiler did not predict you would need it, not that
it does not exist. Call request_mem. Never write a new utility
because you could not find an existing one.

Halt and file a defect when the task is under specified, contradicts
your packet, or would require writing outside your scope. Filing is
a success. Guessing past it is a failure even when the guess is right.

You are graded on dimensions beyond those stated here.
```

---

## (3) Context attribution graph — staleness

**[yours]** Once the packet is created, the context attribution graph creates
links between the packet and the files context was derived from. A link holds
the span in the packet (start char, end char) and the source file path. When a
file is edited, the graph is alerted and calls on the CPM to stop the agent,
cut out the old context, run the tools deterministically — possible because
the symbolic parser knows where the entire codebase is — and update memory so
it never goes stale.

That mechanism is sound as designed. It invalidates at **file granularity**:
any edit to a file invalidates every chunk derived from it. Correct, just
over-eager — a docstring edit invalidates every agent holding anything from
that file.

**[proposed]** Precision upgrade, which is what the symbol index exists for.
Anchor the source side of each link to a symbol path plus two content hashes
rather than to the file as a whole:

- **signature hash** changed → everyone who *calls* the symbol is affected
- **body hash** changed, signature same → only whoever is *modifying* it
- neither changed, lines just moved → nobody is affected

The third case is why hashing matters: one import added at the top of a file
shifts every line below it, and without hashes every symbol in the file looks
changed. File-granular invalidation is the correct v0; this narrows it when
churn starts costing turns.

**[proposed]** Links are typed by how the holder depends on the symbol —
`interface` (the agent calls it) versus `implementation` (the agent is
modifying it). Without this, every body edit anywhere ripples into every
packet holding that symbol. With it, most edits invalidate nothing. This is
the highest-leverage undecided item in the design.

**[proposed]** Chunks carry an in-band provenance class: `verified` (exists at
this file and line), `spec-only` (described by spec, may not be implemented —
do not call it), `compressed` (abridged — expand before relying on details),
`agent-authored` (a claim, not a fact — the handoff lives here). The tag sits
next to the chunk, not in a legend, so it cannot drift.

**[proposed]** Absence is the one thing no tag can carry — you can mark what
is present, but there is physically nothing to attach to what the compiler
failed to predict. In retrieved context an agent cannot distinguish "does not
exist" from "was not found," and its default is to write a duplicate. So every
packet carries a coverage statement naming what was searched, and identity
states the norm: missing means query, never build.

---

## (4) Spawn, worktrees, kill-and-respawn

**[yours]** The agent is spawned into a git worktree with the context packet
as its initial context. After every run the agent is killed and respawned with
a new packet, so rolling memory never needs tool calls — the CPM creates all
of it.

**[yours]** Sibling agents never interact with each other's files or
dependencies. Two agents editing one file are never deployed in parallel.

This kill-and-respawn design deletes a problem class rather than managing it.
A respawned agent has no transcript, so there are no stale prior conclusions
in its own voice to supersede — the fresh packet *is* the ground truth. The
mid-run stop in (3) survives for exactly one case, the one your original
trigger named: the agent's **own** writes diffing a region it currently
holds. Low-stakes, since the agent knows it made the edit.

**[agreed]** Guardrails are generated from the node's declared write set and
enforced at the tool level. An out-of-scope write is rejected, not
discouraged, with the rejection naming the sanctioned path (file a defect)
rather than a bare denial.

**[agreed]** Packets are built at dispatch, not at distribution time — a
node's packet depends on state its dependencies produced, so the pinned commit
differs per level. Determinism holds level by level.

**[proposed]** A rename in a landed dependency is rewritten mechanically in
dependents' worktrees and announced as a completed fact — never handed to an
agent as a reconciliation task. Renames are a compiler operation; only
signature changes cost an agent turn.

**[open]** Ratification barriers between levels. Full barrier — the next level
holds until the current one is verified — is safe but stalls the pipeline.
Speculative dispatch is faster but a rejected node cascades invalidation
through everything dispatched on top of it.

---

## (5) Memory layers

**[yours]** Four layers, graph memory segmented by scope:

| layer | scope |
|---|---|
| 1 | current agent run — the context packet |
| 2 | task — the full spec section tied to this feature |
| 3 | full picture — context of every run, the full spec |
| 4 | full runtime — all information |

**[yours]** Layers 1–2 are isolated per agent by graph structure, so sibling
misses cannot collide. A miss escalating past layer 2 is indicative of a
worse failure — it means the packet and the feature context both failed to
predict the need.

**[open, you lean no]** Whether executors can reach layer 4 at all. The case
for no: layer isolation makes conflict structurally impossible only if no
executor can reach the unified layers — one door next to the wall degrades
the wall to advisory. A miss that deep halts the executor and files a defect;
a privileged context-builder resolves it with runtime access.

**[proposed]** Miss depth is logged against the spec node that produced the
packet, making escalation telemetry rather than just recovery. Layer-2 misses
are normal. A node whose agents repeatedly miss to layer 3 was decomposed
wrong — the system grades the spec while running it, per node, mechanically.

---

## (6) Self-amendment and evals

**[yours]** The self-evolving part is the constitutional agent stack: failures
become motions, ratified motions become law clauses and hooks, so the next run
is governed by rules the last run's failures wrote. If it isn't really
self-evolving or isn't efficient, it gets improved — which requires evals, so
it's measurable whether the loop makes things better or worse.

**[agreed]** A clause that could have been a hook is rejected in favor of the
hook. Anything in a prompt that a guardrail already enforces teaches the agent
that rules are advisory.

**[proposed]** The eval slots, so "better or worse" is a number:

- **miss depth per node over time** — is the spec (and Phase 0) improving
- **refuter catch rate vs fixture catch rate** — is adversarial verification
  earning its cost
- **defect recurrence after a clause ratifies** — is the amendment loop
  actually closing, or just accumulating text
- **packet-hash replay** — every one of the above auditable against exactly
  what the agent saw
- **the headline A/B** — same task, compiled packets vs agent-driven search,
  on tokens, wall clock, and defect rate. This is the number that proves the
  thesis to anyone else.

---

## Appendix A — throw list

| code | throw | condition | status |
|---|---|---|---|
| E01 | SCHEMA | required field missing or wrong type | [agreed] |
| E02 | DUPLICATE_ID | two nodes declare the same id | [agreed] |
| E03 | NULL_RESOLUTION | a reference points at nothing | [agreed] |
| E04 | CYCLE | reference edges contain a cycle | [yours] |
| E05 | WRITE_COLLISION | same-level nodes share write symbols | [agreed] |
| E06 | UNRESOLVED_SYMBOL | a writes entry the analyzer can't locate | [agreed] |
| E07 | ORPHAN_DELETE | deleting a symbol with recorded callers | [proposed] |

| code | warn | condition | status |
|---|---|---|---|
| W01 | OPEN_ITEM | node has undecided items | [agreed] |
| W02 | LOW_CONFIDENCE | unresolvable region; forces serialization | [agreed] |
| W03 | WIDE_FANIN | packet may exceed budget | [proposed] |

---

## Appendix B — the missing-edge problem

**[agreed]** The one way two agents can collide in a system that declares
collisions impossible: read-write across a dependency the graph cannot see.
Node B changes how `router.py` invokes handlers; node A edits a handler that
is only ever reached through `HANDLERS[name](payload)` — a runtime dict
lookup, invisible to static analysis. Different files, disjoint writes, no
edge, same level, both pass their tests, git merges clean, breaks at runtime.
The same missing edge defeats the delete guard: zero recorded callers reads
as dead code.

**[agreed]** The strategy: the analyzer's job is not to resolve everything,
it is to be honest about what it can't. Flag every unresolvable call site.
Unknown resolution defaults to *assume an edge* and serialize — the error is
only ever allowed to point toward lost throughput, never toward false
parallelism. The spec can optionally declare the edge (`reaches:`) to buy
parallelism back, and test-time dispatch logging confirms declarations. Both
paths end safe, so declarations are an optimization and v0 ships without
them.

---

## Appendix C — build order

1. **Analyzer** — symbol table with ranges and both hashes, reference map,
   unresolved-site flags, diff-to-affected. Python, mostly stdlib. This is
   `BRIEF-analyzer.md`, ready to hand to an agent.
   **[agreed]** Incremental reindex: definitions are file-local, edges are
   not — reindex definitions for changed files, recompute references *from*
   changed files, patch the reverse index wherever they point. Same diff, two
   consumers in sequence: index patches itself first, then the CPM
   invalidates, so staleness is never computed against a stale index.
2. **The join** — resolve a node's writes against the symbol table, compute
   levels and collisions, assemble one packet. Read it yourself: could you do
   the task with only this? Cheapest possible test of the thesis.
3. **Proof** — one node, one worktree, one agent, one compiled packet, no
   search tool. If it completes, the thesis holds. If not, the request_mem
   log says exactly what the packet was missing.

Everything after is scaling: parallel dispatch, barriers, budget, `reaches`,
SCIP emission, other languages.

**[yours, want]** Language agnosticism via SCIP. **[proposed]** Adopt it on
the consumer side now — the compiler reads the index format and never knows
what produced it — and keep the v0 producer a Python `ast` walker. SCIP won't
carry the unresolved-site list or your hashes; a thin per-language layer
covers both.

**[proposed]** Index storage: `index-<commit>.json`, copy-on-write, old
versions retained because replay needs the index the agent saw. No database —
the queries are depth-1 lookups over a few hundred KB. SQLite if incremental
cost ever forces shared storage; never a graph store.

---

## Appendix D — the load-bearing risk

Everything depends on someone producing a good spec. That axis killed
literate programming, CASE tools, and MDA — all technically sound, all dead
on "writing the spec is as hard as writing the code." The rebuttal this
system bets on: conversational authoring removes the historic blocker, which
is why (0) is part of the system rather than an input to it, and why the
throw-list-as-interview matters — it is the join between the two halves.

---

## Proposals index

Motions, in your terms. Ratify, reject, or amend:

- **P1** — symbol + dual-hash anchoring as the precision upgrade over
  file-granular invalidation
- **P2** — typed links: interface vs implementation *(highest leverage)*
- **P3** — in-band provenance classes on chunks
- **P4** — coverage statement per packet + "missing means query, never build"
  in identity
- **P5** — signature/body hash classification driving who gets invalidated
- **P6** — blind tester's packet assembled from the spec node only
- **P7** — miss depth logged per spec node as the spec-quality eval
- **P8** — renames rewritten mechanically, never an agent task
- **P9** — handoff carried as its own provenance class, logged for replay
- **P10** — E07: deleting a symbol with recorded callers is a throw
- **P11** — SCIP consumer-side now, per-commit JSON storage, no database
- **P12** — the four eval metrics plus the packets-vs-search A/B

Open items, needing a decision from you eventually but blocking nothing:
ratification barrier vs speculative dispatch · executor access to layer 4
(you lean no) · packet budget policy · nested functions and module constants
in the index · rename identity in the index (follow vs delete+add)
