# Defects — node `affected_symbols`, dispatch 3b

packet_hash=5b1e031b1111 plan=c98fb664a54f commit=4b30c3814ccd2b4cfd5ac4b18b2f177ba59355eb

Three filed: D1 (code — the two failing bullets), D2 (spec/format — why the delta
declared this node done anyway), D3 (packet — verify command).

D2 is the one I would bring to the dispatcher first. D1 is a real gap, but D2 is
the reason nobody would have known about it.

---

## D1 — `Row.callers_unknowable` is specified on the surface and absent from the code

**Filed against:** `done_when` bullets 5 and 6, and the surface contract line

> `analyzer.affected.Row.callers_unknowable`: set iff the old index records
> unresolved sites in the symbol's importer set — the symbol's own file, plus every
> file whose import table contains any binding whose resolved origin is the symbol's
> defining module (module imports, from-imports of any name in it, and re-export
> chains). […]  [authored]

**Evidence.** The attribute does not exist on `Row` in any code path:

```
  Row fields:            ['path', 'category', 'detail', 'callers', 'error']
  'callers_unknowable' in Row fields: False
```

`analyzer/affected.py:25-31` declares the five fields above. `:93-98` is the sole
consumer of `index["unresolved"]` and filters `u["reason"] == "parse_error"`,
discarding `getattr_call` and every other unresolved reason. No statement in
`:100-159` sets the field.

Both bullets were exercised against fixtures that satisfy every precondition they
name — a file doing `import mod` (so it is in the importer set) that also contains a
`getattr(mod, name)` site the old index flags `reason=getattr_call`:

```
  >> old index unresolved sites:
     file=other.py line=5 in=other.dynamic_user reason=getattr_call expr=getattr(mod, name)
  >> old index referenced_by for mod.target: []
  ROW path='mod.target' category='signature' detail='callers affected (0)'      <- bullet 5
  ROW path='mod.target' category='deleted' detail='no callers recorded'         <- bullet 6
```

Bullet 5 forbids "a bare zero" and the report emits `callers affected (0)`.
Bullet 6 requires the qualification and the report emits an unqualified
`no callers recorded`. In both cases the output is *indistinguishable* from the
genuinely-zero-callers case, which is precisely the confusion the field exists to
prevent. Full transcripts: `.harness/scratch/probe_out.txt` sections B5 and B6.

**What a fix would require.** Computing the surface's importer set needs, per file,
the import bindings and their *resolved origins*. The index does not carry that.
Established by calling `build_index` and printing the returned shape — not by
reading `analyzer/indexer.py`:

```
index top-level keys: ['commit', 'files', 'symbols', 'unresolved', 'version']
symbol record keys : ['body_hash', 'confidence', 'decor_hash', 'doc', 'end_line',
                      'file', 'kind', 'parent', 'path', 'referenced_by', 'sig_hash',
                      'signature', 'start_line']
unresolved keys    : ['expression', 'file', 'in_symbol', 'line', 'reason']
unresolved record  : {'file': 'other.py', 'line': 5, 'in_symbol': 'other.d',
                      'reason': 'getattr_call', 'expression': 'getattr(mod, n)(1)'}
```

Note the unresolved record names no target module — `mod` appears only as text
inside `expression`. So even deciding "is *this* unresolved site in symbol X's
importer set" requires the importing file's import table. The data is not in the
index by any route.

Two ways forward, and the choice is not mine to make:

- **Option A — inside my write scope.** Rebuild import tables in
  `compute_affected`: `gitio.read_files` at `old_sha`, `ast.parse` each file,
  `refs.ImportTable.from_module`, `modpath.module_path`, and `refs.Resolver.resolve_dotted`
  for the re-export chains. Every one of these is a packet-listed interface, so this
  is implementable without new utilities. **Cost:** a second full parse of every file
  at `old_rev`, on top of the parse `build_index` already performs internally, plus a
  second construction of import tables the indexer builds internally today. The suite
  carries a `tests/test_perf.py`, so parse cost is a tracked concern.
- **Option B — outside my write scope.** Have `build_index` expose per-file import
  bindings with resolved origins, and let `affected.py` look the importer set up.
  This edits `analyzer/indexer.py` (not my scope) and widens the index shape, which is
  itself a surface line in my packet (`analyzer.indexer.record(...)` and the
  `build_index` key list) — so it is a surface change, and one that touches the
  `symbol_table` node.

**Why I did not implement it.** The dispatch permits writing code when a bullet
fails for a code reason. This bullet fails because a specified feature was never
built, and closing it means choosing between a duplicated-parse implementation and a
cross-node index-shape change with a performance tradeoff — on a node whose delta was
declared empty and whose dispatch was labelled validation-only. Per the executor
identity that is a filing, not a judgement call I should make unilaterally.

**Do not accept a partial fix.** Handling only the symbol's own file plus direct
module/from-imports, and dropping re-export chains, is materially cheaper and would
pass a naive test. It would also under-set `callers_unknowable` — reporting "no
unresolved sites detected" for a symbol reached through a package facade. An
under-set `callers_unknowable` is worse than an absent one: absent is a known gap,
under-set is a false assurance, and the surface line explicitly says an unset value
"is not a completeness guarantee".

---

## D2 — `delta-exempt` on authored lines hides never-implemented surface fields

**Filed against:** the delta block's contract line

> `analyzer.affected.Row.callers_unknowable`: … [authored]: authored (contract —
> tester-verified, delta-exempt)

and its conclusion `=> empty delta — validation-only dispatch`.

**The defect.** The delta compiler marks every `[authored]` surface line
`delta-exempt` on the grounds that authored contract lines are verified by the
tester rather than by presence-checking. That reasoning holds for lines making
*behavioral* claims. It does not hold for lines making *structural* ones. This line
names an attribute on a named type — presence-checkable by exactly the mechanism the
compiler already applied one line earlier in the same packet:

```
- analyzer.affected.Row(path: str, category: str, detail: str, callers: list = ...,
    error: bool = False)  [seeded]: present                        <- checked
- analyzer.affected.Row.callers_unknowable: …  [authored]: authored (contract —
    tester-verified, delta-exempt)                                 <- not checked
```

Same type, two adjacent lines, one presence-checked and one exempted — and the
exempted one is the one that does not exist. The exemption is doing the opposite of
its intent: it is load-bearing precisely where the surface is newest and least
likely to be implemented.

**Consequence, which is the part that matters.** The delta summed to `empty` and the
dispatch was labelled validation-only, i.e. the node was presented as complete. Two
of six `done_when` bullets are in fact unimplemented. Had the done_when attestation
not been a required deliverable, this dispatch would have returned a clean bill of
health for a node missing a specified field. The delta is currently a proxy for
completeness that cannot see the gaps most likely to exist.

**What a fix would require** (spec/format change, outside my write scope): split
`[authored]` lines by claim type rather than exempting them wholesale.

- A line of the form `<Type>.<attr>` or `<module>.<callable>(…)`, where the Type or
  module is itself declared in the surface, makes a structural claim and should
  participate in the delta as a presence check. `Row.callers_unknowable` is caught by
  this rule.
- A line describing behavior, ordering, or an `iff` condition (e.g. the
  `Row.error` and `AffectedReport` compilation lines) is genuinely tester-verified and
  should stay exempt.

Cheap and sufficient here: for each authored line whose subject is `<DeclaredType>.<name>`,
check the attribute exists on the constructed type.

**The proposed check, run against this packet** (`.harness/scratch/d2_check_demo.txt`).
Nine authored lines; six are attribute-on-declared-type shape; the check flags exactly
one, with no false positives on the other five:

```
authored line                                  shape          delta verdict
------------------------------------------------------------------------------
analyzer.affected.compute_affected             other          behavioral -> exempt
analyzer.affected.Row.category                 attr-on-type   present
analyzer.affected.Row.path                     attr-on-type   present
analyzer.affected.Row.callers                  attr-on-type   present
analyzer.affected.AffectedReport               other          behavioral -> exempt
analyzer.affected.Row.callers_unknowable       attr-on-type   *** ABSENT ***
analyzer.indexer.record                        other          behavioral -> exempt
analyzer.affected.Row.error                    attr-on-type   present
analyzer.affected.AffectedReport.has_error     attr-on-type   present
------------------------------------------------------------------------------
structural authored lines that would FAIL the check: ['analyzer.affected.Row.callers_unknowable']
=> delta would be NON-EMPTY; dispatch would not be labelled validation-only.
```

The rule is discriminating rather than merely conservative: it does not simply
un-exempt everything authored. Five authored attribute lines pass, three genuinely
behavioral lines stay exempt, and the single unimplemented field is isolated.

---

## D3 — the packet's verify command does not run under the ambient interpreter

**Filed against:** the Coverage line `verify with: python -m pytest`.

**Evidence** (`.harness/scratch/verify_ambient.txt`, `.harness/scratch/verify_venv.txt`):

```
$ python --version
Python 3.13.13
$ python -m pytest
ERROR tests/test_fence.py
ERROR tests/test_join.py
ERROR tests/test_speccc.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in 0.07s
```

The three collection errors are all `ModuleNotFoundError: No module named 'yaml'`.
The worktree's own virtualenv resolves it:

```
$ ./.venv/bin/python -m pytest
============================= 208 passed in 13.19s =============================
```

**Severity: low, but not zero.** The command as written fails on a clean dispatch,
and its failure mode is a red herring — three errors in `test_fence` / `test_join` /
`test_speccc`, none related to this node, which an executor could plausibly report as
a broken baseline or start debugging. I resolved it by probing for a virtualenv
directory (an environment check, not a repository read) and proceeding.

**What a fix would require** (packet/compiler change, outside my write scope): the
Coverage line should name the interpreter the verify command assumes — e.g.
`verify with: .venv/bin/python -m pytest` — or the dispatcher should activate the
environment before handing the worktree over.
