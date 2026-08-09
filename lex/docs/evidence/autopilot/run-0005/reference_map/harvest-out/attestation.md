# Attestation — node reference_map (validation-only dispatch)

Empty delta: every seeded surface callable/type is present at
c734ce52451af00181b7264d81573c4029096964. No code was written; this
dispatch validates the existing `analyzer/refs.py` against done_when.

Baseline — declared verify command:

```
$ .venv/bin/python -m pytest
================== 449 passed, 1 skipped, 1 warning in 25.37s ==================
```

Refs-focused subset:

```
$ .venv/bin/python -m pytest tests/test_refs.py tests/test_unresolved.py -q
59 passed in 0.02s
```

Targeted evidence below comes from a scratch probe run entirely through
the surface (`ImportTable.from_module` → `Resolver` → `collect_references`):
`.harness/scratch/validate_done_when.py`. The fixture defines
`src.config.load_settings` and calls it from module level, a function
body, and a method body in `src/app.py`, plus an opaque-receiver
`worker.load()` whose terminal name matches `src.config.Loader.load`.

## ATTEST — Given a symbol, returns every caller with file, line, and enclosing symbol.

```
$ .venv/bin/python .harness/scratch/validate_done_when.py
bullet 1 — call sites of src.config.load_settings:
  file=src/app.py line=3 in_symbol=src.app
  file=src/app.py line=9 in_symbol=src.app.boot
  file=src/app.py line=18 in_symbol=src.app.App.start
  PASS: all three call sites present, each with file/line/in_symbol
```

All three callers of `src.config.load_settings` (module level, inside a
function, inside a method) are returned, each record carrying `file`,
`line`, and `in_symbol`. The probe asserts every call record has all
three keys.

## ATTEST — Call site arguments are recorded as written, never traced to their origin.

```
bullet 2 — args recorded at each call site:
  line 3: args=["'app.toml'"]
  line 9: args=['p', 'strict=flag']
  line 18: args=['compute_path()', 'strict=not False']
  PASS: args are verbatim source text; 'p' not traced to compute_path()
```

At line 9 the argument `p` was assigned from `compute_path()` and `flag`
from a literal `True` two lines earlier in the same scope; the record
keeps the names as written (`p`, `strict=flag`) — the probe asserts no
recorded arg contains the traced origin (`compute_path` / `True`).
Expressions (`compute_path()`, `strict=not False`) are kept verbatim too.

## ATTEST — Ambiguous matches are recorded as ambiguous rather than dropped.

```
bullet 3 — worker.load() (opaque receiver, terminal matches Loader.load):
  record={'file': 'src/app.py', 'line': 22, 'in_symbol': 'src.app.poke', 'kind': 'call', 'args': [], 'ambiguous': True, 'note': 'attribute name match; receiver not statically resolvable'}
  PASS: recorded with ambiguous=True and a human-readable note
```

`worker.load()` on an opaque parameter cannot be resolved exactly; the
reference is emitted against the terminal-name match
`src.config.Loader.load` with `ambiguous: True` and a human-readable
`note`, not silently dropped.

Probe exit status: 0 (`all done_when probes passed`).

Fence: no tracked file was modified (`git status --porcelain` shows only
the pre-existing untracked `.venv`). Writes were limited to
`.harness/scratch/` and `.harness/out/`.
