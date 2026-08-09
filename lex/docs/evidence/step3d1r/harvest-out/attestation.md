# Attestation — 3d-1r · node index_assembly · role executor

packet: node=index_assembly role=executor
commit=f146eb16d654cc25fdba3858ea6b393cc833b188
plan=66e648664216 packet_hash=c8242f97dc1c dispatch_id=3d-1r

All five done_when bullets are **ATTEST**. The outstanding delta item
(`analyzer.indexer.import_origins`) is built and the node's delta is now
`empty`. One pre-existing test outside my write scope fails **as a direct
consequence of building it** — filed as D-3d1r-1, not worked around.

Interpreter: `/Users/rokko/experiments/lex/.venv/bin/python`.
Standalone probes run with `PYTHONPATH=.` because the venv carries an
editable `.pth` pointing at the parent repo; under `pytest` the worktree
already wins (verified below), so the suite numbers are the worktree's.

---

## Evidence index

| file | what it is |
| --- | --- |
| `.harness/scratch/mkfixture.py` | fixture builder — one file per import shape |
| `.harness/scratch/probe_before.py` / `_out.txt` | pre-change probe (the ImportTable finding) |
| `.harness/scratch/probe_after.py` / `_out.txt` | all five bullets, exit 0 |
| `.harness/scratch/suite_baseline.txt` | 241 passed, before any edit |
| `.harness/scratch/suite_after.txt` | 240 passed, 1 failed, after |
| `.harness/scratch/real_run{1,2,3}.json` | three independent process runs @HEAD |
| `.harness/scratch/delta_after.txt` | node delta = empty |

---

## Pre-flight: the worktree is what is under test

```
$ /Users/rokko/experiments/lex/.venv/bin/python -m pytest .harness/scratch/_where_test.py -q -s
PYTEST SEES: /private/tmp/.../dispatches/3d-1r/analyzer/__init__.py
1 passed in 0.00s
```

The temporary file was deleted after the check.

---

## 1. ATTEST — "Indexing the same commit twice produces byte identical output."

Three *independent processes* serialize the real repo at HEAD; identical
sha256. Cross-process is the stronger claim — it rules out within-process
dict-identity accidents, which matters because this dispatch adds a new
top-level key holding nested dicts and lists.

```
$ for i in 1 2 3; do PYTHONPATH=. python -c "...serialize(build_index(Path('.').resolve(), 'HEAD'))" > real_run$i.json; done
$ shasum -a 256 .harness/scratch/real_run*.json
24b7e725de4a467c841579de6ca825c872d46491ad1cdbf0d6a5d7c958522523  .harness/scratch/real_run1.json
24b7e725de4a467c841579de6ca825c872d46491ad1cdbf0d6a5d7c958522523  .harness/scratch/real_run2.json
24b7e725de4a467c841579de6ca825c872d46491ad1cdbf0d6a5d7c958522523  .harness/scratch/real_run3.json
$ diff .harness/scratch/real_run1.json .harness/scratch/real_run3.json && echo IDENTICAL
IDENTICAL
```

And on the fixture, through the surface, for both the commit and the
working-tree paths — with a positive control that the new key is actually
in the bytes being compared (so the check cannot pass vacuously):

```
[PASS] commit index serializes identically twice
        want: True
        got:  True
[PASS] the imports key is actually present in that output
        want: True
        got:  True
[PASS] worktree index serializes identically twice
        want: True
        got:  True
```

Determinism is structural, not incidental: files are emitted over
`sorted(files)`, and `_sorted_entries` deduplicates then sorts on
`(name, origin)` with `kind`/`module` as total-order tiebreakers and
`None` collapsed to `""` so the sort cannot raise on null origins.

## 2. ATTEST — "The emitted index maps every symbol path to at least one record carrying its definition location and signature."

```
[PASS] symbol paths present
        want: True
        got:  True
[PASS] records missing file/start_line/signature
        want: []
        got:  []
```

Every record carries a non-empty `file`, a non-null `start_line` and a
`signature` key. This bullet is re-attested under index_assembly per V2
(it is a claim about the index); the change in this dispatch does not
touch record assembly, and the check is run against the post-change code.

## 3. ATTEST — "build_index exposes each file's import bindings with resolved origins, re-export chains included, and import_origins answers from them."

The re-export case is the load-bearing one. `app/facade.py` contains only
`from pkg import helper`; `helper` is *defined* in `pkg/impl.py` and merely
re-exported by `pkg/__init__.py`. The origin chases through to the
definition, and `module` is the defining module, not the facade:

```
[PASS] re-export chain resolved to the defining symbol
        want: [{'name': 'helper', 'kind': 'symbol', 'origin': 'pkg.impl.helper', 'module': 'pkg.impl'}]
        got:  [{'name': 'helper', 'kind': 'symbol', 'origin': 'pkg.impl.helper', 'module': 'pkg.impl'}]
[PASS] direct symbol import resolved
        want: [{'name': 'widget', 'kind': 'symbol', 'origin': 'pkg.impl.widget', 'module': 'pkg.impl'}]
        got:  [{'name': 'widget', 'kind': 'symbol', 'origin': 'pkg.impl.widget', 'module': 'pkg.impl'}]
[PASS] import_origins names the re-export importer too
        want: ['app/alias.py', 'app/bare.py', 'app/constant.py', 'app/direct.py', 'app/facade.py', 'app/submod.py', 'pkg/__init__.py', 'pkg/star_src.py']
        got:  ['app/alias.py', 'app/bare.py', 'app/constant.py', 'app/direct.py', 'app/facade.py', 'app/submod.py', 'pkg/__init__.py', 'pkg/star_src.py']
[PASS] import_origins is empty for an unknown module
        want: []
        got:  []
[PASS] import_origins is empty for a pre-imports index
        want: []
        got:  []
```

`import_origins` reads `index.get("imports")` and matches the `module`
field only — it never rebuilds anything, which is what makes the
legacy-index case fall out as `[]` rather than a `KeyError`.

On the real repo, the answers are sensible rather than merely well-typed:

```
import_origins(analyzer.modpath) = ['analyzer/indexer.py', 'analyzer/symbols.py',
                                    'tests/test_modpath.py', 'tests/test_refs.py',
                                    'tests/test_unresolved.py']
import_origins(nope.nope)        = []
```

## 4. ATTEST — "A bare module import that is never called yields a module-kind imports entry whose origin and module are both the imported module."

`app/bare.py` is exactly `import pkg.impl` and nothing else.

```
[PASS] app/bare.py entry
        want: [{'name': 'pkg', 'kind': 'module', 'origin': 'pkg.impl', 'module': 'pkg.impl'}]
        got:  [{'name': 'pkg', 'kind': 'module', 'origin': 'pkg.impl', 'module': 'pkg.impl'}]
[PASS] app/bare.py cites no symbol (import is never called)
        want: []
        got:  []
[PASS] so the trace exists only via imports
        want: 1
        got:  1
```

The middle check is what gives the bullet its teeth: no `referenced_by`
site anywhere in the index cites `app/bare.py`, so before this dispatch
the file left **no trace at all** — the predecessor's finding, now closed.
`name` is `pkg` (what the statement actually binds) while `origin` and
`module` are `pkg.impl` (what it names). Keeping both is why the sort key
is `(name, origin)`: `import pkg.impl` and `import pkg.other` bind the
same name and are separated only by origin.

## 5. ATTEST — "A star-importing file lands in the source module's importer set — its imports entry carries kind unresolved with module set to the source module, so import_origins names it."

```
[PASS] app/starred.py entry
        want: [{'name': '*', 'kind': 'unresolved', 'origin': None, 'module': 'pkg.star_src'}]
        got:  [{'name': '*', 'kind': 'unresolved', 'origin': None, 'module': 'pkg.star_src'}]
[PASS] import_origins names the star importer
        want: ['app/starred.py']
        got:  ['app/starred.py']
[PASS] unresolved_import_target importer is excluded by the ruling
        want: False
        got:  False
```

`name` is `"*"` — the alias the AST literally carries, so the entry
records what is written rather than inventing a binding name for
something that binds no single name.

The third check is a correction I owe the record. I first wrote this probe
expecting `app/viastar.py` (which also imports *from* `pkg.star_src`) to
appear in the importer set, and it failed. The code was right and my
expectation was wrong: `app/viastar.py` is the `unresolved_import_target`
case, whose `module` the surface rules **null**, so it is deliberately
excluded. I changed the probe to the ruled behaviour and added an explicit
assertion of the exclusion so it stays visible rather than accidental.

## Surface conformance (beyond the bullets, same probe)

```
[PASS] every indexed file has an entry list        want: True   got: True
[PASS] a file importing nothing gets []            want: []     got: []
[PASS] a file that fails to parse gets []          want: []     got: []
[PASS] ...alongside its parse_error site           want: ['parse_error']  got: ['parse_error']
[PASS] unresolved_import_target: origin AND module null
        want: [{'name': 'hidden_thing', 'kind': 'unresolved', 'origin': None, 'module': None}]
        got:  [{'name': 'hidden_thing', 'kind': 'unresolved', 'origin': None, 'module': None}]
[PASS] from-import of a submodule is module-kind    -> origin=module='pkg.impl'
[PASS] aliased module import keeps the full module path -> {'name': 'pi', ..., 'origin': 'pkg.impl'}
[PASS] commit vs worktree imports identical         want: True   got: True
```

`files == imports.keys()` also holds on the real 30-file repo:

```
files indexed: 30  imports keys: 30
files == imports keys: True
```

## Delta

The one outstanding item is closed:

```
$ python -c "...join.compute_delta(plan, index, resolved, 'index_assembly', repo=root)"
kind: empty
outstanding: []
  present   analyzer.indexer.build_index(repo: str | Path, commit: str | None) ->
  present   analyzer.indexer.serialize(index: dict) -> str  [seeded]
  present   analyzer.indexer.load_index(path: str | Path) -> dict  [seeded]
  present   analyzer.indexer.import_origins(index: dict, module: str) -> list[str]
```

## Suite

Before (unmodified worktree):

```
$ .venv/bin/python -m pytest -q
241 passed in 19.98s
```

After:

```
$ .venv/bin/python -m pytest -q
FAILED tests/test_join.py::test_f20_callable_extension_absent_until_built_on_real_spec
1 failed, 240 passed in 20.06s
```

The single failure is deterministic (reproduced twice in isolation) and is
**caused by this dispatch succeeding** — the test asserts `import_origins`
is `absent`. It lives in `tests/test_join.py`, outside my write scope.
Filed as D-3d1r-1; not worked around.

## Fence

```
$ git status --short
 M analyzer/indexer.py
?? .harness/
```

One tracked file modified, and it is the only entry in my write scope.
`.harness/` is my deliverables + scratch directory. No write was denied.
