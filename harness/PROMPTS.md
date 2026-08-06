# Session prompts — paste one per Claude Code session, in order

Level 0 is session 1. Sessions 2 and 3 are level 1 — they only depend on
session 1, so you can run them as two parallel worktrees if you want to
feel the parallelism by hand. Session 4 needs 1–3. Session 5 needs all.

---

## Session 1 — symbol_table

```
Read harness/BRIEF-analyzer.md end to end before writing anything.

Implement Part 1 only: the symbol table (analyzer/index.py).

1. Write pytest tests from the Acceptance criteria that apply to
   Part 1, plus the record-format example in the brief.
2. Implement until green.
3. Prove determinism: index this repo twice at HEAD and diff the
   two outputs. Show me the diff (it must be empty).
4. Show me the full index entry for one real symbol from this repo
   so I can check it by eye.
```

## Session 2 — reference_map (level 1, can parallel session 3)

```
Read harness/BRIEF-analyzer.md end to end before writing anything.
Part 1 (analyzer/index.py) is done — read it before you start.

Implement Part 2 only: the reference map (analyzer/references.py).

1. Tests from the Part 2 acceptance criteria first.
2. Record call-site arguments as written. Never trace where a
   variable came from — that is out of scope by design.
3. Where a match is ambiguous (shadowing, aliasing), record it as
   ambiguous. Prefer over-reporting a reference to missing one.
4. Show me every recorded caller of one real function in this repo,
   including at least one method call, so I can verify by eye.
```

## Session 3 — unresolved_sites (level 1, can parallel session 2)

```
Read harness/BRIEF-analyzer.md end to end before writing anything.
Part 1 (analyzer/index.py) is done — read it before you start.

Implement Part 3 only: unresolved sites (analyzer/unresolved.py).

1. Tests first, from the Part 3 table of shapes and its acceptance
   criteria. Include a test fixture file containing a registry
   pattern: HANDLERS[name](payload) plus a @register decorator.
2. Every shape in the table produces a record — a silent skip on
   any of them is the one failure this layer exists to prevent.
3. Symbols in a file with an unresolved site get confidence: low.
4. Show me the unresolved records and the low-confidence marks for
   the fixture file, then run it on this repo and show what it flags.
```

## Session 4 — affected_symbols

```
Read harness/BRIEF-analyzer.md end to end before writing anything.
Parts 1–3 are done — read analyzer/ before you start.

Implement Part 4 only: diff to affected symbols (analyzer/affected.py).

1. Build a scratch git repo fixture in the tests and construct each
   acceptance scenario as real commits:
   - import added at top of file → every symbol reports moved
   - body-only change → owner affected, callers not
   - parameter added → signature, every call site named
   - symbol deleted while callers exist → error, not success
2. Parse git diff --unified=0 hunks; intersect against the old AND
   new index; classify by comparing sig_hash and body_hash.
3. Show me the tool's output for each of the four scenarios.
```

## Session 5 — analyzer_cli

```
Read harness/BRIEF-analyzer.md end to end before writing anything.
Parts 1–4 are done — read analyzer/ before you start.

Implement the CLI (analyzer/cli.py) exactly as specified in the
brief's CLI section: index, symbol, affected, unresolved.

1. Every subcommand except index works from a saved index file
   without re-indexing.
2. Time `analyzer index` on this repo and report it. The budget is
   10 seconds on 20k lines.
3. Show me one real invocation of each subcommand and its output.
```
