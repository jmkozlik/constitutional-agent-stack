# Handoff — 3d-1r · node index_assembly · role executor

packet: node=index_assembly role=executor
commit=f146eb16d654cc25fdba3858ea6b393cc833b188
plan=66e648664216 packet_hash=c8242f97dc1c dispatch_id=3d-1r

State is split into **verified** (a command produced it, and the command
is named) and **interpretive** (my reading, which may be wrong). This
dispatch completed — nothing is half-built — so the main value here is the
reasoning behind three judgement calls, and one blocker only a
wider-scoped agent can clear.

---

## Where the dispatch ended

All five done_when bullets ATTEST. The single outstanding delta item
`analyzer.indexer.import_origins` is built; the node's delta is `empty`.
One tracked file changed: `analyzer/indexer.py`. Four defects filed.

The one thing needing action outside this fence: **D-3d1r-1**. The suite
is 240 passed / 1 failed, and the failure is
`tests/test_join.py::test_f20_callable_extension_absent_until_built_on_real_spec`,
which asserts `import_origins` is *absent*. Building it is what this
dispatch was for. The test needs re-pointing at a canary that will stay
unbuilt; it is outside my write scope.

## Verified — commands were run, output is on disk

- **Suite 241 passed before any edit** (`suite_baseline.txt`), **240
  passed / 1 failed after** (`suite_after.txt`), failure deterministic
  across two isolated re-runs.
- **`pytest` imports the worktree's `analyzer`, not the parent repo's.**
  Worth knowing: the venv has an editable `.pth` holding
  `/Users/rokko/experiments/lex`, so a **standalone script** run from
  `.harness/scratch/` imports the *parent repo* and will silently test the
  wrong code. Run probes with `PYTHONPATH=.`. I lost a cycle to this.
- **Byte-identity holds across three independent processes** on the real
  repo @HEAD, identical sha256 (`real_run{1,2,3}.json`). The fixture probe
  also asserts the `imports` key is present in the compared bytes, so the
  check cannot pass vacuously.
- **`ImportTable` structurally cannot supply done_when bullets 4 and 5.**
  `probe_before_out.txt`: `import pkg.impl` yields `_bindings={'pkg':
  ('pkg',)}` — the `.impl` is discarded at construction — and
  `from x import *` yields `_bindings={}` with only a `has_star` bool.
  This is the fact that drove the whole implementation shape (D-3d1r-2).
- **`files == imports.keys()`** on the real 30-file repo and on the
  fixture, including parse-failing files (empty list) .
- **Commit-path and worktree-path `imports` are identical** on the fixture.
- **The node delta is now `kind: empty`, `outstanding: []`**
  (`delta_after.txt`).
- **A dispatch's own `.harness/scratch/*.py` gets indexed** in worktree
  mode (D-3d1r-4). Not a regression, but it surprised me.

## Interpretive — my reading, may be wrong; each is a filed defect

1. **Enumerating bindings from the import statements** rather than from
   `ImportTable`. I judged this permitted by "Recording the binding is in
   scope" and *required* by the measurement above, since the prohibition's
   own remedy (a public accessor on refs) cannot return discarded data.
   All resolution still comes from refs. Filed as D-3d1r-2 with the
   evidence, so it can be overturned cheaply if the reading is wrong.
2. **Importing `_scope_stmts` (private) from `analyzer.refs`.** Chosen so
   the statement set matches `ImportTable.from_module`'s exactly; writing
   my own traversal would have been the real duplication. One-line change
   if disallowed. Also D-3d1r-2.
3. **The third unresolved flavour** — resolvable star-free source module,
   unresolvable name (`from pkg.impl import CONSTANT`, and every stdlib
   `from` import) — is ruled by neither surface case. I kept the stated
   base as `module`, extending the star case's own "a stated source module
   is a fact" rationale. Consequence: `import_origins(index, "pathlib")`
   answers non-empty. D-3d1r-3, with a non-blocking REQUEST_MEM.

## Things a resumer should not re-litigate

- **`origin` for a bare `import pkg.impl` is `pkg.impl`, not `pkg`.** Not
  my inference — `docs/superpowers/plans/2026-08-08-v05-bundle.md` V5
  states the fixture verbatim. The packet's own phrase "the imported
  module" is ambiguous on its own; V5 disambiguates it.
- **`name` is the bound name** (`pkg` for `import pkg.impl`, `pi` for
  `... as pi`, `"*"` for a star). This is why the ruled sort key is
  `(name, origin)` and not `name` alone: `import pkg.impl` and
  `import pkg.other` bind the same name and differ only in origin.
- **`app/viastar.py` is absent from `import_origins("pkg.star_src")` on
  purpose.** It is the `unresolved_import_target` case whose `module` the
  surface rules null. I wrote the probe expecting it to be present, was
  wrong, and left an explicit assertion of the exclusion in the probe so
  the next reader does not repeat the mistake.

## Sequencing note for 3d-2 (`affected_symbols`)

`callers_unknowable` consumes the importer set. Two properties of what I
built that its fixtures will feel directly:

- A file reaching a symbol through a re-export facade is attributed to the
  **defining** module, not the facade (`app/facade.py` → `pkg.impl`), so
  facade modules do *not* collect importers they merely forward.
- `unresolved_import_target` files carry `module: null` and therefore
  appear in **no** importer set. If a 3t fixture expects a star-poisoned
  importer to be visible to `callers_unknowable`, it will fail for a spec
  reason (the ruling), not an implementation one — same trap the previous
  handoff flagged, one level down.

## Scratch inventory

`mkfixture.py` (13-file fixture, one per import shape) · `probe_before.py`
+ `_out.txt` (the ImportTable finding) · `probe_after.py` + `_out.txt`
(all bullets, exit 0) · `suite_baseline.txt` · `suite_after.txt` ·
`real_run{1,2,3}.json` · `real_imports_sample.txt` ·
`real_origins_check.txt` · `delta_after.txt`.

Rebuild the fixture with:
`PYTHONPATH=. .venv/bin/python .harness/scratch/mkfixture.py .harness/scratch/repo`
then `PYTHONPATH=. .venv/bin/python .harness/scratch/probe_after.py .harness/scratch/repo`
(exit 0 = all bullets hold).
