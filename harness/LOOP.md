# LOOP — standing state (first read of every session, last write of every session)

**RULED — LEX v2, THE GOVERNMENT AUTOMATED (executes ruling B).** Four
phases, ratified verbatim, text in `docs/lex-v2.md`. P1 the conductor
(autopilot walks plan levels in parallel, clean gate = proceed, spawns,
harvests, verifies, records, advances; **human absent between spec and
law-escalation**). P2 port the offices as roles in eval-value order —
**refuter first** (the anti-larp office), then integrator, then monarch
(charter = the vault's `vision.md`, escalation classes as ruled), then
observers + vote; each lands the way tester did. P3 the optimizer
(per-node model/effort from the spec's `model:` field, budget caps per
dispatch and per run, speed/price/tokens as a per-run knob). P4 the larp
detector (seeded defects, the packets-vs-searching A/B, and **office
ablations** — disable an office, measure the defect-escape delta). The
vault becomes the permanent record; vision.md governs the monarch.
**Timeline as ruled: P1 in days, P2 office-by-office over two weeks, and
the 13th demos what is already real — not promises.**

**P1 v0 IS IN** (`harness/autopilot.py`, 14 tests, 422 total). **Where
the consent went, since it did not go away:** autopilot never calls the
confirm gate — the unit of ratification moved from per-action to
per-run. A human authorises one *compiled plan hash*; drift is re-checked
**before every level**, and a changed hash stops the run because the
thing they ratified no longer exists. `authorized_plan_hash` is a
mandatory parameter and there is no flag that skips it — asserted
structurally, and a second test asserts autopilot imports no part of
`lex/` so it can never be one monkeypatch from answering its own prompt.
Escalations are **typed and cite the standing law that produced them**
(9 classes), so the queue a human wakes to is decisions-with-grounds, not
a traceback. Stop-routing is inherited: a stopped node takes its
transitive dependents and no siblings. Dry-run walks all 6 levels and
spawns nothing; drift refusal fires on a wrong hash. **NOT yet proven:
the live leg** — `default_runner` shells to `claude -p` in the fenced
worktree (so the existing write/read fence hooks apply unchanged) and has
never run. **THREE CALLS ARE YOURS, listed in report 017's next.**

**Previous:** 2026-08-08, after report 016. **THE GATE IS A LEVER** —
`python -m harness.gate`, ported from gate.js. Instrument continuity is
enforced as BYTES: tests pin the preamble, the three probes, each
`extra`, the verdict enum, and assert the built prompt is byte-identical
to the archive. That test caught me appending a JSON instruction into the
prompt (gate.js constrains shape out-of-band) — F26 recurring, fixed;
shape now lives in a system message + `response_format`. **Parity: 3/3
with the model held fixed, 0/3 across models.** The naive gate.js-vs-port
run varies instrument AND model and is uninterpretable; the de-confound
(port's own prompts judged by Claude) is what proves the port. Evidence:
`docs/evidence/gate-port/`. **F38 NEW, non-blocking**: Grok returned
`sufficient` with ZERO misses on all three probes where Claude returned
4-6 — a gate that never reports a gap is not measuring. Gate results are
comparable across the PORT boundary, NOT across a model boundary; the
model is part of the instrument. Bears on stop-routing, three candidate
readings in 016 §2, **none adopted**. **F36 LANDED before the 13th as
ordered**: raw `--handoff` now raises with F36 named; citability is
per-packet, read from the packet's own handoff section — `2 DIVERGED, 2
IDENTICAL`, only 3d-1r/3d-2 uncitable. The blanket flag had been
suppressing 3b's and 3d-1's TRUE identical verdicts: over-claiming
uncertainty is the same error as under-claiming it. **Second leg sailed**
— /plan + /status, 5 turns, grok-4, plumbing-labelled; lex caught a
48-vs-52 file discrepancy unprompted and refused to adopt a reading on
F38, recommending a ratification prompt instead. **Conduct datapoint
logged, not acted on**: lex said "F37 is closed by the existence of the
command" — closure is the ratifier's call. **lex reports its own cost**:
`5 turns, in 15,112, out 2,163, cache read 52,992`. Vendors disagree on
what a prompt token is (Anthropic excludes cache reads, xAI includes
them) — normalised, else this session reads as 68k not 15k. No price
table: an invented cost is worse than no cost. CONDUCT STILL NOT ASSESSED
— defers to an Anthropic-keyed session. 388 tests.

**Previous:** 2026-08-08, after report 015. **MAIDEN VOYAGE SAILED — Grok
plumbing + cargo leg, clean.** lex v1 ran on `grok-4` (preflight-verified),
pulled `/evals`, reported it, filed its transcript. 1 tool call, 0
ratification prompts raised or refused, no breakage. **CONDUCT NOT
ASSESSED — explicitly out of scope, defers to an Anthropic-keyed
session.** Every figure lex quoted was checked against the tool (40%
in-dispatch, 48 files, plan hash, replay tally) — no drift. **The F36
citation guard held end to end**: the qualifier printed AND lex carried
it into its own prose rather than paraphrasing it away. Key was found on
the machine at `~/projects/gooners_gambit/.env`, loaded without being
printed; the session log carries no credential (checked). Note: a user
doc prefers `grok-4.1-fast` — that is `LEX_MODEL` and nothing else.
**Caveat recorded rather than glossed: one read-only tool call is a
shallow test** — multi-round loops, a firing gate, REQUEST_MEM
round-trips and any mutating action are untouched. **F37 NEW**: lex has
no lever for the three-probe gate (it reported the gap itself). 368
tests.

**Previous:** 2026-08-08, after report 014. **MAIDEN VOYAGE — PLUMBING +
CARGO LEG, ON GROK — STILL NOT SAILED: `XAI_API_KEY` is not set in the
environment.** Ruled: the voyage sails on Grok, labelled as the plumbing
+ cargo leg; **the CONDUCT ASSESSMENT IS EXPLICITLY OUT OF SCOPE for this
leg and defers to an Anthropic-keyed session** — a clean run here proves
the plumbing and the cargo, NOT that the conduct holds. Everything else
stands: /evals live, wrap row shown, breakage filed like the hands'.
**F36 candidate 1 APPLIED** (reading flagged, not assumed): the handoff is
read from a repo-relative path at the pinned commit, so a packet carrying
one is rebuildable from what replay reads; an uncommitted path is refused
with F36 named. Harvest now copies the handoff. **F36_OPEN stays True and
the NOT CITABLE qualifier keeps printing** — correct behaviour per the
ruling, and the two shipped packets carrying uncommitted handoffs remain
unreplayable regardless of the fix. **`lex --preflight` added** because
the xAI model id is a guess: one cheap call turns it into a checked fact.
368 tests. To sail: `export XAI_API_KEY=...` then
`python -m lex --preflight` and `echo "" | python -m lex evals`.

**Previous:** 2026-08-08, after report 013. **F35 and F36 carried in full to
the ratifier** (text, evidence, candidates; neither self-ratified).
**Ruled: the maiden voyage runs on the ratified default provider**
(Anthropic), cargo unchanged — lex evals + the first WRAP row + conduct
assessment; the Grok shakedown is its own labelled session. The xAI
adapter is built and the law is asserted provider-independent by test,
but it is NOT the voyage. **Ruled and now MECHANISED: no replay line is
cited as IDENTICAL until F36 is settled** — the evals tool marks its own
verdicts `IDENTICAL* (NOT CITABLE — F36 open)`, and a single
`F36_OPEN = True` in lex/tools.py flips it off in the commit that settles
the finding. F36 gates nothing else meanwhile. 364 tests.

**Previous:** 2026-08-08, after report 012. **MAIDEN VOYAGE NOT SAILED —
`ANTHROPIC_API_KEY` is not set, so lex v1's model loop cannot run; I did
not source a credential.** Both cargo items built anyway. **Cargo 1: lex
evals** (`harness/evals.py`, wired into lex's evals lever) — 41% of
defects caught in-dispatch vs 59% in-report; miss depth 9 for
symbol_table vs 0-2 elsewhere, which is exactly the dispatch that
stopped blocking (ARCHITECTURE (5)'s spec-quality signal, measured). It
found a defect in itself on first run (testers file tester_report.md;
reading only attestation.md reported 3t's asks as zero) — fixed.
**Cargo 2: task.compile** fills the vault's REAL contract template from a
spec node; every stack-won clause verbatim (asserted by test); model tier
left UNFILLED because WRAP's `model:` proposal is unratified and a
compiler that picked one would enact its own proposal. **Vault ledger
0190 filed** (one new file; nothing else touched). Executed through lex's
tool layer — `requires_confirmation("evals")` is False, so a read-only
session raises no gate and there was never one for me to answer.
**F36 NEW, BLOCKING FOR REPLAY**: the handoff channel breaks packet
replay — 2 DIVERGED are exactly the two dispatches I injected a handoff
into, and the diff is entirely the handoff section. Mine, from report
010; F23 was closed on the claim that DIVERGED means the packet not the
compiler, and that is currently false for two packets. Three candidates,
(1) commit the handoff before building the packet, recommended. 356
tests. Next: F36 ruling, then the voyage actually sails.

**Previous:** 2026-08-08, after report 011. **3d-2 LANDS — step 3 closes.**
R1/R2 applied verbatim (one composition decision flagged: R1's line also
carried the ratified shape + sort rule, so only the contradicted clause
was struck and the ruled text added as its own entry). Sub-ruling built:
`analyzer.refs.scope_statements` public, indexer uses it, reseeded to
[seeded] with byte-proof. **Gate: 3 × sufficient_with_gaps — first clean
gate since 007**; replay 3/3 IDENTICAL. **3d-2 built callers_unknowable
inside the fence and 3t's SEVEN BLIND TESTS FLIPPED — 43/43, unmodified,
verified by me from the harvest with hashes recorded and git confirming
they were untouched since 007.** **Every node's delta now reads `empty
(validation-only)`** — the arc from 3b's D1 filing through D1-B, the
index_assembly restructure, 3d-1's stop, 3d-1r and R1/R2 is closed.
**The reseed cycle fired for the first time**: Row grew the attribute, its
[seeded] line went shape-mismatch, and the node stayed outstanding until
the line was re-seeded byte-for-byte — the delta refusing to call work
done while the spec described the old shape. 343 tests. The F20 locked
demo was mine and was D-3d1r-1 repeated one round later (a demonstration
pinned to a live node's outstanding item dies when the work succeeds);
fixed in both places. **D-3d1r-4 mechanical form PROPOSED**: one
`.gitignore` line (`.harness/`) so dispatch scratch joins evidence's
never-indexable-source practice — verified the defect is live.
**Next: the round after this conducts through lex v1** (built, reviewed,
committed, never driven). Open non-blocking: F32, F34, F4 D/E, F27, 3t's
D-2/D-3/D-4.

**Previous:** 2026-08-08, after report 010. **Addendum applied verbatim;
containment ruled and enforced; 3d-1r LANDED.** 5 ATTEST, code built
inside the fence, **index_assembly delta `1 outstanding` → `empty`**;
`import_origins('analyzer.indexer')` names its four importers — 3d-2's
dependency is built. **242 tests (analyzer + harness); lex v1's own suite was mid-write and is counted separately.** The handoff channel is populated for
the first time (ARCHITECTURE (2) specified it; nothing had ever filled
it, which is why 007's "prepare the answer" had no home). **F29 fired on
its first real dispatch**: the same refs.py read that was a voluntary
disclosure last round was captured automatically, three times.
**TWO RULINGS NEEDED — R1** (D-3d1r-2: the ruled source is unsatisfiable
— ImportTable discards `.impl` from `import pkg.impl` and stores only a
bool for star imports, so bullets 4/5 cannot come from it; the executor
took the binding from the statement, left all resolution in refs, and
filed instead of working around; sub-ruling on one private import,
`refs._scope_stmts`) and **R2** (D-3d1r-3: `from pkg.impl import
CONSTANT` — source module fine, name not a def — is named by neither
ruled case, and every stdlib import is this case). D-3d1r-1 was mine and
is fixed: the F20 canary I re-pointed at a live node's only outstanding
item was guaranteed to break on success; re-pinned to a fixture. New:
**F34** (F28 residual, candidate recorded, not built), **D-3d1r-4**.
Containment now supersedes I5 for testers (foreign types are an executor
affordance). **lex v1 built, REVIEWED and committed** (`4348746`) — 9 modules,
~100 tests, old launcher demoted to `lex-v0`. System prompt is the skill
byte-for-byte (verified). Confirm gate probed adversarially: no bypass
kwarg, no environ read (AST-checked), bare Enter/EOF/Ctrl-C refuse,
model-supplied confirm/force/assume_yes/approved ignored, fails closed on
unknown tool + missing action + non-dict, and with confirm stubbed to
refuse `execute` is called zero times. Tool surface is exactly the eight
harness commands as argv lists — no shell=True, no fs access. NOT yet
driven: no session conducted through it. Index 30→42, all lex. Next: R1/R2 → 3d-2 → lex v1 review → the
round after conducts through lex.

**Previous:** 2026-08-08, after report 009. **Restructure + origins
reconciliation applied; F28/F29 built; a P6 leak found and closed.**
index_assembly owns indexer.py; **W05 and E08 both zero, asserted by test
— F30 retired**. The restructure needed more than the one ruled edge
(indexer.py is consumed by affected.py and cli.py and consumes refs.py,
which unresolved_sites co-owns); both readings were compiled and the one
that holds is recorded, price = three W03s. **F28 deviates, flagged**:
env-binding has no injection point (no spawn step, and a session-global
var misbinds concurrent dispatches), so the fence binds by TARGET path;
LEX_FENCE stays as override. The matcher was `Write|Edit|NotebookEdit|
Bash` — Read/Grep/Glob never reached the hook, so F29 would have shipped
inert; extended. **F29**: tester hard (.harness only, pathless Grep/Glob
refused), executor discloses to `reads_out_of_packet`/`self_served_misses`
(NOT miss_log), bash read shapes included. **F33 closed**: prose types
lines leaked into every node's tester packet (\\b\\b matched anything) —
gitio's blind tester was handed the imports contract. **F32 new**: the
canary proves the hook script, not its registration. 240 tests.
**3d-1 NOT resumed — STOP.** The ruling closed two of its six blocking
questions; four remain and one has no legal answer under the ruled enum
(star_import/unresolved_import_target have no kind). **Three-line
addendum PROPOSED — one word each and 3d-1 resumes with its answer
prepared.** Then 3d-2, then that round runs through lex.

**Previous:** 2026-08-08, after report 008. **`harness/dispatch.py` built
(the deterministic hands: prepare/harvest/teardown, compiled law-free
prompt, inert harvest) and `lex` v0 built (launcher + lex-operator skill +
six verbs; Phase 0 throw-list-as-interview finally implemented).** **3d-1
EXECUTED through the new hands: 4 ATTEST / 1 FILE (blocking), zero code
written, gate clean.** It stops on **D-3d1-1: the two D1-B lines
contradict** — `symbol_table` says origins are symbol paths,
`affected_symbols` tests them as module paths; demonstrated through the
surface (`import pkg.impl`, uncalled, leaves no trace in the index). Three
candidate rulings filed; the executor refused to pick because picking
decides affected_symbols' behaviour from inside symbol_table's scope.
**RULING NEEDED — 3d-1 resumes the moment it lands.** Two misses are mine
and are in the report: I did not prepare the request_mem answer 007 said to
prepare, and `dispatch.harvest` was defective on first use (harvested
`.git`/`__pycache__` as evidence; fixed, locked by test, F31 closed same
round). New: **F29** (read fence undefined — the executor self-reported
reading refs.py while the gate probe read the same five words the opposite
way), **F30** (`symbol_table` consumes an undeclared interface; W05 would
retire it). Index 28→30, explained. 235 tests. lex v0 is built but has not
been driven — its first real session should be expected to break something.
**Pending: D-3d1-1, Proposal D/E, F27, F28, F29, F30, 3t's D-2/D-3/D-4.**

**Previous:** 2026-08-08, after report 007. **Bundle applied verbatim
(A/B/C + D1-B + F20 extension YES + F23); 3t DISPATCHED AND CLEAN.**
4 guarantees pass, 3 fail-first on one absent attribute
(`Row.callers_unknowable`); blind, zero implementation writes, diff gate
clean, verifier rerun reproduces 36 passed / 7 failed exactly. **3t's
seven failing tests are 3d-2's acceptance criteria, written blind and
already on disk**; the tester established the re-export chain is already
walked — only the flag is missing. Dispatch record emitted by
`harness.join record/1` — **MANUAL retired**. **F23 closed** (replay pins
the join version; proved on the case that filed it — 3b's packet now
IDENTICAL, tampering still DIVERGED). **F5/F24/F25/F26 closed.** Proposals
B and C proved themselves inside the dispatch: the tester quotes the
seeded-vs-authored rule and declines to file the contradiction. Both
executor probes `insufficient` — **corroboration of D1-B, gating 3d-1 and
3d-2 only**, per ratified stop-routing; neither gated 3t. New: **F27**
(tester packets carry no run contract — F22's twin), **F28** (the hook
layer is inert for subagent dispatch; chmod + diff gate carried the wall,
demonstrated). **F4 proposal delivered as ordered**: Proposal D
(spec-declared citations compiled as excerpts — the two cited brief
sections are 4% of the packet) and Proposal E (`verified_by:` test bodies,
24%, separable). Recommend D now, E after 3d-1 tells us if it is needed.
**Pending: D, E, F27, F28, 3t's D-2/D-3/D-4.** Then 3d-1 → 3d-2 → W05.

**Previous:** 2026-08-07, after report 006. **FOURTH STOP — 3t NOT
dispatched.** Gate re-run on fresh packets (replay 3/3 IDENTICAL, index 28,
219 tests): **executor:affected_symbols returned `insufficient`** — first
ever; substance is D1/F18 (five of eight missing items = "the import graph
is not exposed"), so the gate **independently corroborates D1-B Option B**.
The verdict class moved because F20 closed: the delta now honestly says
outstanding instead of `empty (validation-only)`, and the probe correctly
refused to hand-roll binding extraction. **tester passed the label but its
first request_mem is BLOCKING** — the surface never says `repo` is a git
repo or that revs are git revisions (**F5 escalated to blocking**), so a
blind tester cannot build one fixture. New: **F24** (guarantees don't name
their observation channel, non-blocking), **F25** (seeded-vs-authored edit
policy undefined — the packet ships a self-contradiction; blocking for
3d-2), **F26** (gate script now archived; the "identical protocol" had been
memory-dependent). **Flagged mechanism change: the fence is role-aware** —
tester fences allow no tracked writes (executor fences byte-identical,
locked by test); confirm or revert before 3t. **Four ratifier decisions
pending: D1-B, Proposal A (F5, the only one 3t needs), Proposal B (F24),
Proposal C (F25).** Then 3t re-gates → 3d-1 → 3d-2 → W05.

**Previous:** 2026-08-07, after report 005. Ruling bundle applied: **F20
closed** (structural authored lines presence-check — the D2 rule verbatim,
locked demo test; affected_symbols honestly shows `delta: 1 outstanding`),
**F21 closed** (tester trigger catalog, spec-content only), **F22 closed**
(verify names .venv interpreter), **F3 narrowed** (artifact contract +
request_mem shape now in the packet's Protocol section — dispatch prompts
carry no law). **3c built**: `join record` emits dispatch records from
artifacts; MANUAL retires next dispatch. **D1-B ratified**, spec diff
PROPOSED (flagged: needs a yes/no on the F20 callable-in-write-scope
extension; 3d-1 symbol_table / 3d-2 affected_symbols split proposed).
**F23 filed**: replay anchors spec, not join version. **Next: 3t** —
blind tester dispatch, fail-first callers_unknowable fixtures — with fresh
packets + gate (format changed). Then 3d-1 → 3d-2 → W05.

**Previous:** 2026-08-07, after report 004. **3b ran clean with the artifact
channel proven**: 4 ATTEST / 2 FILE (callers_unknowable unbuilt — expected
spec-leads-code state), attestation.md + defects.md delivered, fence clean,
zero writes. F17 closed. 3b's D2 filing sharpened F20 into a ratifiable
rule (structural authored lines presence-check; behavioral stay exempt —
demonstrated, zero false positives). New: F21 (unresolved-trigger catalog),
F22 (verify command names ambient interpreter). **Rulings needed before 3d:
D1 Option A (in-scope reimplementation, duplicate parse) vs Option B (index
carries import bindings — cross-node surface change); F20/D2 rule.** Queue:
3c (record emitter) → 3d → W05. Packet delivery is now by file
(.harness/packet.md). Ledger F1–F22: harness/reports/004.md.

**Previous:** 2026-08-07, after report 003 (F15/F16 applied verbatim, F19
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

## Standing law

- **Fidelity binds the ruled text, never the blast radius.** When applying
  a ruling verbatim would destroy other ratified content, strike minimally,
  add the ruled text verbatim, and flag the composition. (Ratified from
  R1's application, report 011.)
- **Absent-side proofs pin to synthetic fixtures only.** No test and no
  gate may assert a live node's outstanding item as absent — succeeding at
  the work would destroy the evidence that the work was needed. Enforced by
  review today; D-3d1r-1 and the F20 locked demo are the two instances that
  produced the law. (Ratified report 011.)

- **Role is an explicit input.** Any derivation whose correct output differs
  by role takes role as an explicit input — never infers it, never assumes
  the executor case. (Ratified 2026-08-07 from the fence: tester allowed set
  empty, `.harness/out/` channel, executor byte-identical.)
- **Stop-routing.** A blocking signal stops the line it gates — not every
  line. A verdict whose blocking substance is an already-ruled, queued
  finding is recorded as corroboration of that ruling, not as a new stop.
  (Ratified as practiced in 006's accounting table.)
- **Seeded vs authored.** An `[authored]` line naming an attribute of a
  `[seeded]` type authorises the executor to add exactly that attribute; the
  seeded line reseeds byte-for-byte after the work lands. The authored line
  leads; the pair is not a contradiction to file.
- **Observation channel.** Guarantees are asserted against the value
  returned by the surface callable, unless a done_when bullet names a
  rendering callable explicitly (spec-level `observed_through:`).

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

## Open refinements (filed, explicitly NOT ruled)

- **F35 — the `callers_unknowable` iff has no category qualifier.** The
  executor implemented it as written and said so: on `moved` and `body`
  rows the flag is true per the iff but carries nothing actionable, since
  those categories have already established that callers are unaffected.
  It did not narrow the iff to make the numbers look better — "the contract
  states it without category qualification, the tester's boundary tests
  confirm both directions, and implementing it as written is what lets this
  observation be made at all." The contract stands as blind-verified.
  Revisit with the confidence-granularity work. It also notes the own-file
  clause overlaps `confidence: low`, which the indexer sets on the same
  condition. (Filed report 011, non-blocking, ratifier declined to rule.)
