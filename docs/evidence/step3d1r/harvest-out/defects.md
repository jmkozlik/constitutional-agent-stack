# Defects — 3d-1r · node index_assembly · role executor

Four filed. D-3d1r-1 is a hard blocker for a green suite and cannot be
fixed from inside this fence. D-3d1r-2 is an interpretive call I made and
am flagging so it can be cheaply overturned. D-3d1r-3 is genuine surface
underspecification I resolved with a stated reading. D-3d1r-4 is an
observation about the harness indexing its own dispatch scratch.

---

## D-3d1r-1 — building `import_origins` invalidates a test that asserts it is absent

**Filed against:** `tests/test_join.py::test_f20_callable_extension_absent_until_built_on_real_spec`
(outside my write scope — my scope is exactly `analyzer/indexer.py`).

**Evidence.** Suite was 241 passed before the edit, 240 passed / 1 failed
after; the failure is deterministic across repeated isolated runs.

```
$ .venv/bin/python -m pytest tests/test_join.py::test_f20_callable_extension_absent_until_built_on_real_spec -q
>       assert status == "absent"
E       AssertionError: assert 'present' == 'absent'
E         - absent
E         + present
tests/test_join.py:989: AssertionError
```

The test's own comment states the premise:

```python
def test_f20_callable_extension_absent_until_built_on_real_spec():
    # D1-B's import_origins is authored, inside index_assembly's own write
    # scope (analyzer/indexer.py), and NOT built -> absent, so the node
    # honestly reports outstanding work instead of validation-only.
```

It builds an index of `PROJECT_ROOT` (= this worktree, per
`tests/conftest.py:6`) and asserts the F20 delta reports `import_origins`
as `absent`, `delta["kind"] == "partial"`, and `import_origins` present in
`delta["outstanding"]`.

**The mechanism is fine; the fixture's premise is dead.** The delta now
correctly reports the callable as `present` and the node's delta as
`empty` — that is the mechanism working, and it is exactly what this
dispatch was sent to cause. The test picked the single outstanding item of
a live node as its "known-absent" canary, so it was always going to fail
the moment that node's dispatch succeeded.

**What a fix would require** (in `tests/test_join.py`, not mine to make):
re-point the canary at a surface entry that is authored-but-unbuilt and
expected to *stay* that way, or pin it to a synthetic spec/repo fixture
rather than the live `PROJECT_ROOT` so a real dispatch cannot invalidate
it. Retiring the assertion outright would lose an F20 demonstration, so
re-pointing is the better shape. Note the sibling
`test_f20_locked_demonstration_on_real_spec` still passes.

---

## D-3d1r-2 — the imports table is built from the import statements, not from `ImportTable`'s bindings

**Filed against:** my own implementation, and against this line of the
carried handoff:

> **Binding enumeration is still not declared surface.** If you need a
> public accessor on `analyzer/refs.py`, that is a spec change owned by
> `reference_map`: FILE it, do not reach across and do not re-derive
> imports by parsing.

I did neither of the two forbidden things — I did not touch `refs.py` and
I did not re-derive any *resolution*. But I did enumerate bindings by
walking the import statements in the ASTs `build_index` already holds,
rather than from `ImportTable`. Flagging it because that is close enough
to the prohibition that it deserves a ruling rather than my judgement.

**Why the FILE-a-spec-change branch does not apply: a public accessor on
`ImportTable` could not satisfy two of the done_when bullets.** This is
measured, not argued — `.harness/scratch/probe_before_out.txt`:

```
app/bare.py          source='import pkg.impl'
                     _bindings={'pkg': ('pkg',)}  has_star=False
app/starred.py       source='from pkg.star_src import *'
                     _bindings={}  has_star=True
...
== 3. the bullet-4 question ==
statement:        import pkg.impl
bound name:       pkg
resolve('pkg') ->  ('pkg',)
bullet 4 wants origin == module == 'pkg.impl'
ImportTable can supply 'pkg.impl'? False
```

`ImportTable.add` binds `top -> top` for a dotted `import a.b`, so `.impl`
is **discarded at construction** — bullet 4 asks for `pkg.impl` and no
accessor over `_bindings` can return what was never stored. Likewise a
star import stores *nothing* (`_bindings={}`, only a `has_star` bool), so
bullet 5's "module set to the source module" has no source to read. The
information exists only in the statement.

**What I did instead, and what it does not re-derive.** Resolution stays
in `refs` end to end: `ImportTable.base_of(stmt)` resolves relative
levels, `Resolver.is_module` decides module-ness, `Resolver.resolve_dotted`
chases re-exports, and the `unresolved_import_target` case is read off the
reference pass's *own* verdicts (matched by `(line, reason)`) rather than
re-deciding the star-poisoning condition. The statement supplies only the
binding — name, and the module it names — which the handoff's own
"Recording the binding is in scope; inventing one is not" appears to
permit.

**One genuine reach-across to rule on:** I import `_scope_stmts` (a
private) from `analyzer.refs` into `analyzer/indexer.py`. It is listed in
my packet as an available interface. I chose it over writing my own
scope-level traversal deliberately: it is the same function
`ImportTable.from_module` uses, so the set of statements the imports table
sees is guaranteed identical to the set the import tables were built from.
Re-implementing it would have been the actual duplication. If this is
disallowed, the fix is a public re-export or a declared accessor on
`reference_map`, and it is a one-line change here.

---

## D-3d1r-3 — third unresolved flavour is unspecified: resolvable source module, unresolvable name, no star

**Filed against:** `harness/specs/analyzer.yaml`, the imports-table type
line. It rules two unresolvable cases:

- `star_import` → kind unresolved, origin null, module = source module
- `unresolved_import_target` → kind unresolved, origin and module null

A third case occurs constantly and is named by neither: `from pkg.impl
import CONSTANT`, where the source module is indexed and star-free but the
name is not an indexed definition. The reference pass deliberately stays
**silent** here (`analyzer/refs.py:757-770` — "this import is provably not
a def edge ... and stays silent"), so there is no unresolved site to key
off. Every stdlib import is also this case: `from pathlib import Path`.

**What I did:** kind `unresolved`, origin `null`, module = the stated base.
Reasoning, offered so a ruling has something to reject: the surface's own
justification for the star case — *"a stated source module is a fact, not
an invention"* — applies identically, and the base is trustworthy here in
a way it is not for `unresolved_import_target` (where the base star-imports,
which is precisely what makes it unreliable as the definer). Keeping the
module also keeps `import_origins` honest: the file really does import
from `pkg.impl`, and dropping it would under-set the importer set that
`callers_unknowable` consumes downstream.

**Consequence to be aware of:** stdlib and third-party modules now appear
as `module` values, so `import_origins(index, "pathlib")` answers
non-empty. Observed on the real repo:

```
{"kind": "unresolved", "module": "pathlib",     "name": "Path",        "origin": null}
{"kind": "unresolved", "module": "collections", "name": "defaultdict", "origin": null}
{"kind": "module",     "module": "json",        "name": "json",        "origin": "json"}
```

I read this as correct — they are real import bindings and the spec says
"every indexed file gets an entry list", not "in-repo imports only" — but
if the intent was repo-internal edges only, this is where to say so, and
the filter belongs in `_import_entries`.

**REQUEST_MEM (non-blocking):** is the third flavour's `module` the stated
base (as built), or null like `unresolved_import_target`? And should
out-of-repo modules be recorded at all?

---

## D-3d1r-4 — worktree indexing sweeps a dispatch's own `.harness/scratch/*.py` into the index

**Filed against:** `analyzer.indexer._worktree_files` (my write scope, but
the behaviour is pre-existing and deliberate, so I did not change it under
a done_when that does not name it).

`_worktree_files` uses `git ls-files --cached --others --exclude-standard`,
so untracked-but-unignored `.py` files are indexed. `.harness/` is
untracked and not ignored, so an executor's own scratch probes land in any
worktree index built during the dispatch:

```
import_origins(analyzer.refs) =
    .harness/scratch/probe_before.py      <-- my scratch, not repo source
    analyzer/indexer.py
    tests/test_refs.py
    tests/test_unresolved.py
```

Harmless for my attestation (bullet-1 evidence uses the `HEAD` commit path,
and the fixture probes use their own repo). But the harness builds
worktree indexes during `plan`/`packet`/`record`, so a live dispatch's
scratch can influence packet compilation for the next node. Worth a ruling
on whether `.harness/` should be ignored by the file walk or added to
`.gitignore`; either is outside what this dispatch was asked to decide.

---

## Read disclosure (read policy: disclose)

Out-of-packet reads, all read-only, no writes attempted outside scope:

- `analyzer/refs.py` lines 1-270 and 318-437, 726-830 — `ImportTable`,
  `Resolver`, `_scope_stmts`, and the walker's `_visit_Import` /
  `_visit_ImportFrom`. Directly load-bearing: D-3d1r-2's measurement and
  the `unresolved_import_target` condition in D-3d1r-3 both come from here.
- `harness/specs/analyzer.yaml` (grep only) — confirming the packet's
  surface text against its source.
- `docs/superpowers/plans/2026-08-08-v05-bundle.md` lines 1-80 — this is
  the one that changed the build. **V5 states the bullet-4 fixture
  explicitly**: "bare `import pkg.impl`, imported and never called, yields
  a module-kind entry whose `origin` and `module` are both `pkg.impl`."
  That is what settled `origin = pkg.impl` rather than `pkg`, which the
  packet's done_when phrase "the imported module" left open.
- `tests/test_join.py` lines 955-995 and `tests/conftest.py:6` — reading
  the failing test to file D-3d1r-1 accurately.
- `.venv` site-packages `.pth` contents — diagnosing why standalone probes
  imported the parent repo's `analyzer`.

No write outside the fence was attempted and no denial was recorded.
