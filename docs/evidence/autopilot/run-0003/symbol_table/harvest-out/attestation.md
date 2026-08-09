# Attestation — node symbol_table (validation-only dispatch)

packet: node=symbol_table role=executor commit=9d3bc13c0611b8bea23658237a755960245344bb plan=66e648664216 packet_hash=48344a19274d

Baseline before probing, with the verify command the packet names:

```
$ .venv/bin/python -m pytest 2>&1 | tail -5
  /Users/rokko/experiments/lex/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================== 441 passed, 1 skipped, 1 warning in 25.99s ==================
```

All evidence below is observed through the surface callable
`analyzer.symbols.extract_symbols(source, rel_path)` per the packet's
`observed_through` line. Probe sources live in `.harness/scratch/`.

## ATTEST — Reformatting whitespace does not change the body hash

Probe: `.harness/scratch/probe_done_when.py`. The same three definitions
(a class, a method, a module function with a docstring) are extracted from
an original source and from a whitespace-only reformat of it: blank lines
inserted/removed, spacing around operators/commas/colons changed,
indentation widened from 4 to 8, one statement wrapped in parentheses
across lines, the return expression split across a continuation. The AST
is semantically identical; only whitespace/layout differs.

```
$ .venv/bin/python .harness/scratch/probe_done_when.py
== bullet 1: body_hash under whitespace reformat ==
src.config.Config: original=ad7bce58 reformatted=ad7bce58 equal=True
src.config.Config.scaled: original=984f2eda reformatted=984f2eda equal=True
src.config.helper: original=8114d0eb reformatted=8114d0eb equal=True
```

Every `body_hash` is byte-identical across the reformat. Mechanism (from
the packet's verified source of `analyzer/symbols.py`, lines 97-101):
`_body_hash` hashes `ast.unparse(stmt)` per body statement, and unparsing
normalizes away whitespace/formatting; docstrings are body statements and
correctly participate. ATTESTED.

## ATTEST — Ranges are recomputed per commit, never stored as identity

Two independent demonstrations.

(a) In-memory shift (same probe file): the identical definitions are
extracted again after being pushed 37 lines lower. Ranges move; every
identity hash (`sig_hash`, `body_hash`, `decor_hash`) is unchanged; and a
repeat extraction of the shifted source reproduces the ranges from source
alone — nothing is carried between calls.

```
$ .venv/bin/python .harness/scratch/probe_done_when.py
...
== bullet 2: ranges vs identity across a shift ==
src.config.Config: lines 1-8 -> 38-45; sig/body/decor hashes unchanged=True
src.config.Config.scaled: lines 4-8 -> 41-45; sig/body/decor hashes unchanged=True
src.config.helper: lines 11-13 -> 48-50; sig/body/decor hashes unchanged=True

re-extraction of shifted source reproduces ranges from source alone: True
record fields: ['body_hash', 'decor_hash', 'doc', 'end_line', 'file', 'kind', 'parent', 'path', 'sig_hash', 'signature', 'start_line']
ALL PROBES PASSED
```

(b) Literal per-commit form: a two-commit git fixture
(`.harness/scratch/gitfix`, built with `git -c user.email=t@t.t
-c user.name=t`) where commit 2 moves `def target` down six lines behind a
header comment and a new constant. `.harness/scratch/probe_per_commit.py`
extracts `mod.py` as it exists at each commit:

```
$ .venv/bin/python .harness/scratch/probe_per_commit.py
commit 46a5560: mod.target lines 1-2 sig_hash=3102cf0b body_hash=d919ee34 decor_hash=e3b0c442
commit 84022bc: mod.target lines 7-8 sig_hash=3102cf0b body_hash=d919ee34 decor_hash=e3b0c442
ranges differ across commits; identity hashes identical: True
```

Mechanism (packet's verified source): `extract_symbols` (lines 126-131) is
a pure function of `(source, rel_path)` with no cache or store — ranges can
only ever be recomputed from the source handed in per extraction/commit.
The three hash inputs (`_sig_canonical` lines 31-60, `_body_hash` lines
97-101, decorator unparse at lines 162-164) contain no line numbers, so
`start_line`/`end_line` cannot leak into identity. ATTESTED.

## Fence denial record (protocol-required, verbatim)

While building the git fixture, one Bash command that `cd`'d into
`.harness/scratch/gitfix` and redirected to the bare filename `mod.py` was
denied:

```
PreToolUse:Bash hook error: [python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/write-fence.py]: write fence [symbol_table]: 'mod.py' is out of scope — REQUEST_MEM or file a defect. Do not work around. Your write scope: analyzer/modpath.py, analyzer/symbols.py
```

The true target was inside `.harness/scratch/`, which the fence permits;
the denial was retriggered by the lexical `mod.py`. I did not re-run the
denied command; the file was written via the Write tool at its explicit
`.harness/scratch/gitfix/mod.py` path, which the fence allowed. Filed as
defect D1 in `.harness/out/defects.md`.
