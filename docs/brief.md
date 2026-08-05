# Brief: analyzer v0

**Audience:** a coding agent implementing this from scratch.
**Deliverable:** a CLI that indexes a Python repo and answers three questions.
**Out of scope:** everything not listed under Scope. Read Non-goals before starting.

---

## Why this exists

This is the bottom layer of an agent harness. The harness compiles a spec into a
graph of tasks, runs coding agents in parallel worktrees, and hands each agent a
context packet built from the codebase instead of letting the agent search for
context. Nothing above can be built until something can answer, for any symbol in
a repo:

1. Where is it defined, and what is its signature?
2. Who references it?
3. When a diff lands, which symbols changed, and how?

That is this deliverable. No agents, no spec, no packets.

---

## Scope

### 1. Symbol table

Walk a Python repo at a given commit and emit a record per definition.

```json
{
  "path": "src.config.load_settings",
  "kind": "function",
  "file": "src/config.py",
  "start_line": 40,
  "end_line": 58,
  "signature": "(path: str, strict: bool = False) -> dict[str, str]",
  "sig_hash": "7c2e91a4",
  "body_hash": "91ab3f02",
  "parent": "src.config"
}
```

- Cover `FunctionDef`, `AsyncFunctionDef`, `ClassDef`. Methods get the dotted path
  through their class: `src.config.Loader.load`.
- `start_line` / `end_line` come from `ast` node attributes and span the whole
  definition including decorators.
- `sig_hash` covers the name, parameter names, parameter annotations, defaults
  presence, and return annotation. Nothing else.
- `body_hash` covers the body only, with comments and blank lines stripped and
  whitespace normalized, so reformatting does not change it.
- Ranges are **derived per commit and never used as identity**. Identity is
  `path` + `sig_hash` + `body_hash`.

### 2. Reference map

A second pass recording, for every symbol, the sites that reference it.

```json
{
  "path": "src.config.load_settings",
  "referenced_by": [
    {"file": "src/app.py", "line": 12, "in_symbol": "src.app.boot",
     "args": ["'./conf.yml'", "True"]},
    {"file": "src/cli.py", "line": 44, "in_symbol": "src.cli.main",
     "args": ["path"]}
  ]
}
```

- Match `Name` and `Attribute` nodes against the symbol table.
- Record call arguments **as written at the call site** — literals as literals,
  variable names as names. Do not attempt to trace where a variable came from.
  Value-level dataflow is explicitly out of scope.
- Accuracy here will be imperfect on shadowing, aliasing, and star imports. That
  is expected and handled by part 3.

### 3. Unresolved sites

Every call site whose target cannot be determined statically.

```json
{
  "file": "src/router.py",
  "line": 18,
  "in_symbol": "src.router.dispatch",
  "reason": "subscript_call",
  "expression": "HANDLERS[name](payload)"
}
```

Detect at minimum:

| reason | shape |
|---|---|
| `subscript_call` | `TABLE[key](...)` |
| `getattr_call` | `getattr(obj, name)(...)` |
| `attribute_of_call` | `factory()(...)` |
| `star_import` | `from x import *` anywhere in the file |
| `dynamic_attribute` | `setattr` / `__getattr__` definitions |

Any symbol defined in a file containing an unresolved site is marked
`confidence: "low"` in the symbol table. Consumers of this index treat low
confidence as "assume there is an edge to everything here."

This is the most important part of the deliverable. A missed reference that is
**flagged** is safe. A missed reference that is **silently absent** is the one
failure mode this whole layer exists to prevent. When in doubt, flag it.

### 4. Diff to affected symbols

Given two commits, report which symbols were affected and how.

```
$ analyzer affected HEAD~1 HEAD
src.config.load_settings    signature   callers affected (2)
src.config.Loader.parse     body        owner only
src.config.DEFAULTS         moved       no effect
```

Method:

1. `git diff --unified=0 <old> <new>` and parse the `@@` headers for changed
   line ranges per file.
2. Intersect those ranges against the symbol table **for the old commit** and
   **for the new commit**. Union the matches.
3. For each matched symbol, compare hashes across the two indexes:
   - `sig_hash` differs → `signature`, and everyone in `referenced_by` is affected
   - `body_hash` differs, `sig_hash` same → `body`, only the owner is affected
   - neither differs → `moved`, nobody is affected
   - present in old, absent in new → `deleted`, and this is an error if
     `referenced_by` is non-empty
   - absent in old, present in new → `added`

The `moved` case matters. An import added at the top of a file shifts every line
below it, and without hash comparison every symbol in that file looks changed.

---

## CLI

```
analyzer index <repo> [--commit REV] [-o index.json]
analyzer symbol <path> [--index index.json]
analyzer affected <old-rev> <new-rev> [--repo .]
analyzer unresolved [--index index.json]
```

`index` is the only one that must be fast. Assume it runs on every dispatch.

---

## Acceptance criteria

- Indexing the same commit twice produces byte-identical output.
- Given a symbol path, returns its definition, signature, and every caller.
- Adding an import at the top of a file reports every symbol in that file as
  `moved`, and nothing as changed.
- Changing only a function body reports `body` for that function and does not
  report its callers as affected.
- Changing a parameter list reports `signature` and names every call site.
- A file containing `HANDLERS[name](payload)` produces an unresolved-site record
  and marks symbols in that file low confidence.
- Deleting a symbol that has recorded callers is reported as an error, not a
  silent success.
- Runs on a 20k-line repo in under 10 seconds.

---

## Non-goals

Do not build any of these. They are later phases and building them now will make
the wrong thing hard to change:

- Value-level or interprocedural dataflow. Call-site arguments as written only.
- Any language other than Python.
- SCIP emission. The index format is internal JSON for now.
- tree-sitter. Use the `ast` stdlib module.
- Type inference. Use annotations where present; leave absent annotations absent.
- A daemon, a server, a database, or a cache layer.
- Anything touching agents, specs, packets, or worktrees.

---

## Notes for the implementer

- `ast` gives `end_lineno` on all definition nodes. `decorator_list` entries
  carry their own line numbers; the definition range should start at the first
  decorator.
- Normalize the body before hashing by unparsing the AST rather than by
  manipulating source text. `ast.unparse` on the body nodes gives a canonical
  form for free and drops comments automatically.
- Reference matching is a scoping problem. A local variable named `load_settings`
  is not the module-level function. Getting this fully right is hard; getting it
  conservatively wrong is fine — prefer over-reporting a reference to missing one,
  and note the ambiguity in the record.
- Where the design says "flag it," never substitute a guess.

---

## Open questions

Leave these as `TODO` comments where they come up rather than deciding:

- Should nested functions get their own symbol entries, or fold into the parent?
- Should module-level constants be indexed as symbols?
- What is the identity of a symbol that is renamed — follow it via the diff, or
  treat it as a delete plus an add?
