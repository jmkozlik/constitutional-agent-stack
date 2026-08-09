# Defects — 3d-1 · node symbol_table · role executor

packet: node=symbol_table role=executor commit=c7c6f7e0535cdc5de579cfadbd436af5860bc924
plan=c98fb664a54f packet_hash=6624a3b2aef7 dispatch_id=3d-1

Three filed. **D-3d1-1 is blocking** and is why done_when bullet 5 is FILED
rather than built. D-3d1-2 and D-3d1-3 are non-blocking and are filed against
the spec/protocol, not against any code.

---

## D-3d1-1 — BLOCKING — the spec's two `origins` lines contradict each other

**Filed against:** `harness/specs/analyzer.yaml`, the interaction of two
[authored] lines —

- `symbol_table.surface.types`: *"the index adds a top-level imports table —
  {file: [{name: str, origins: [dotted origins as resolved by the reference
  layer, re-export chase included]}]} — taken from the Resolver's output at
  build time, never recomputed downstream"* (yaml:49-52)
- `affected_symbols.surface.types`, `Row.callers_unknowable`: *"every file
  whose import table contains any binding whose **resolved origin is the
  symbol's defining module** (module imports, from-imports of any name in it,
  and re-export chains)"* (yaml:113)

**What it is.** The reference layer resolves to indexed **symbol** paths. The
consumer tests origins against a defining **module**. Those are different
namespaces, and the index contains no module records at all, so under the
literal `symbol_table` reading the equality the consumer performs can never
hold — and the "module imports" case its own line names explicitly resolves
to nothing.

**Evidence** (surface-only — `build_index`'s returned value, no
implementation internals read). Probe:
`.harness/scratch/probe_origin_contradiction.py`, output
`.harness/scratch/probe_origins_out.txt`:

```
files indexed: ['app/lazy.py', 'app/via_facade.py', 'pkg/__init__.py', 'pkg/impl.py']
top-level index keys: ['commit', 'files', 'symbols', 'unresolved', 'version']
every symbol path in the index: ['app.via_facade.go', 'pkg.impl.helper']
module paths present as symbol records: []

(a) app/lazy.py contains exactly `import pkg.impl` and uses nothing.
    reference records naming app/lazy.py : []
    unresolved sites naming app/lazy.py  : []

(b) app/via_facade.py reaches pkg.impl.helper only through the facade.
    call edge resolved to pkg.impl.helper <- app/via_facade.py:1 in app.via_facade
    call edge resolved to pkg.impl.helper <- app/via_facade.py:5 in app.via_facade.go
```

(b) shows the re-export chase already works for a **called** name — that
machinery is sound. (a) shows the gap: an **imported-but-uncalled** module
binding leaves no trace anywhere in the returned index, which is exactly the
edge the imports table exists to carry.

**What a fix would require.** A ruling on one line of spec, then the
implementation is small and lands wholly inside this node's write scope. The
three candidate rulings, with what each costs:

1. **Origins are symbol paths** (literal `symbol_table` reading). Cheapest to
   emit — it is the Resolver's output unmodified. Requires amending
   `affected_symbols` so the consumer derives a module from a symbol path
   (strip the terminal component), and requires an answer for bare module
   imports, which yield no symbol at all. Under this ruling the
   `callers_unknowable` bullet *"module imports"* cannot be satisfied without
   a further change.
2. **Origins are module paths.** Satisfies the consumer directly and covers
   bare `import pkg.impl`. Costs the finer resolution: `from pkg import
   helper` and `from pkg import Widget` become indistinguishable, both
   reporting origin `pkg.impl`.
3. **Both, in one list** (or one entry carrying two fields). Loses nothing
   and lets the consumer match on either, at the cost of a wider entry shape
   than the spec line currently writes — so the spec line changes either way.

My reading, offered as a claim and not acted on: (3) is what the two lines
*jointly* describe, and (2) is the minimum that makes the declared consumer's
own done_when bullet true. I did not pick. Picking would decide
`affected_symbols`' behaviour from inside `symbol_table`'s write scope, which
is 3d-2's contract, not mine.

**Not the blocker** (measured, so it can be struck from the list): whether a
new top-level `imports` key is tolerated by the out-of-scope consumers. It
is — full suite 234 passed both without and with an injected key, with a
control proving the injection reached the test modules. Evidence in
attestation.md §5.

---

## D-3d1-2 — non-blocking — `symbol_table` depends on an interface with no spec path

**Filed against:** `harness/specs/analyzer.yaml` — node ownership, not code.

**What it is.** `symbol_table`'s authored contract requires taking the imports
table *"from the Resolver's output at build time"*. `analyzer.refs.Resolver`
is owned by `reference_map`, and my packet renders every refs symbol as
`[UNDECLARED — owned by reference_map, no spec path; spec-quality signal]`
with `confidence low` and a bare constructor signature. A node cannot be
required to consume an interface that the spec never declares: the packet
compiler correctly cannot carry an API it has no declaration for, so the
executor is left with a done_when bullet whose named mechanism is invisible.

**Evidence.** `.harness/packet.md:604-611` (the UNDECLARED block), against
`.harness/packet.md:66` (the requirement to take the table from the
Resolver's output). The same gap was predicted verbatim by the pre-dispatch
gate probe and shipped unchanged — `harness/reports/007.md:208-216` (verdict
**insufficient**, first missing line: *"analyzer.refs.Resolver's public API
for import resolution — the packet gives only the constructor"*), and
`harness/reports/007.md:753-754` ("Its probe named exactly what it needs; that
list is the request_mem answer to prepare"). The answer was not prepared: my
packet's `## State — handoff` section reads `(none for this dispatch)`.

**What a fix would require.** Either declare the consumed surface in
`reference_map` (the resolution entry point and the binding-enumeration
accessor, so the join can compile it into consumers' packets), or move the
imports-table ownership to the `index_assembly` node that W05 already has
ratified for exactly this restructure. The second is already on the roadmap;
the first is the smaller change if 3d-1 is to be resumed before W05 lands.

---

## D-3d1-3 — non-blocking — the read fence is undefined, and I hit it

**Filed against:** the Protocol section of the executor packet
(`.harness/packet.md:25-45`), self-reported.

**What it is.** The packet defines the **write** fence exactly — an
enumerated `allowed` set in `fence.json`, enforced by a PreToolUse hook, with
a stated response on denial. It defines no **read** fence. The only
read-related words in the whole packet are *"never read around it"*, five
words inside the request_mem paragraph. That is a rule about substituting
reading for asking, and it does not say which files are out of bounds.

**Evidence, self-reported.** Early in this dispatch, before writing anything
and before recognising the question, I read `analyzer/refs.py` lines 1-270 to
learn the Resolver's resolution API — a file outside my write scope, though
one my own `analyzer/indexer.py` already imports from, and one the packet
lists under "Interfaces you consume". The pre-dispatch gate probe for this
same node reasoned the other way from the same words: *"The charter forbids
reading around a packet miss, so I cannot open analyzer/refs.py"*
(`harness/reports/007.md:234`). Two runs of the same role, opposite readings,
same sentence — that is the defect.

**What it did and did not change.** It settled the *mechanical* API question
(how one would obtain resolutions). It settled **none** of the semantic
questions in D-3d1-1 or in the blocking request_mem lines, because those are
contract questions that no source file answers. I did not implement from it,
and D-3d1-1's evidence is deliberately built from `build_index`'s returned
value alone, so the filing stands independent of the read.

**What a fix would require.** One sentence in the Protocol section, stating
the read rule and its scope — candidates: (a) read anything tracked at the
pinned commit, since the packet is a *predicted* subset and re-reading is how
an executor checks the compiler; (b) read only what the packet carries, with
the write scope's own files exempt, making request_mem the sole channel for
anything else; (c) (a) but with mandatory disclosure of every out-of-packet
read in the attestation. This is F3's remaining "read-fence" item
(`harness/reports/005.md`, findings ledger), now with a concrete instance.
