# harness v0

The execution layer under the constitutional agent stack. Compiles a spec into a
task graph, then runs coding agents whose context is **compiled and handed to
them** rather than searched for.

This repo is at step one of that: the analyzer.

## Files

| file | what it is |
|---|---|
| `CLAUDE.md` | Standing rules. Claude Code reads this automatically every session — the hand-written identity document of this build. |
| `PROMPTS.md` | The five session prompts, in compiled plan order. You paste these — they are the task files. |
| `BRIEF-analyzer.md` | The self-contained work order for the v0 analyzer. The source of truth on conflict. |
| `specs/analyzer.yaml` | The same work, expressed in the spec format the harness will eventually compile. |
| `speccc.py` | Spec compiler front end. Validates, resolves, detects cycles, levels, checks write collisions. |

## Hand it to Claude Code

1. Copy this folder into your stack repo as `harness/`.
2. Open Claude Code **inside** `harness/` so `CLAUDE.md` loads
   automatically.
3. Paste Session 1 from `PROMPTS.md`. When it lands, continue in
   order — sessions 2 and 3 can run as parallel worktrees.
4. Log every question the agent asks you: a question is a gap in the
   brief, and gaps in the brief are Phase 0 data.

## Try it

```bash
python3 speccc.py specs/
```

Compiles the analyzer spec, prints the parallelism plan, surfaces open decisions
as warnings. Break something to see it throw — delete a referenced `id`, or give
two nodes on the same level the same `writes` entry.

## Build order

1. **Analyzer** — index a repo, map references, flag what can't be resolved,
   turn a diff into affected symbols. This is `BRIEF-analyzer.md`. Mostly stdlib.
2. **The join** — resolve a spec node's `writes` against the symbol table,
   compute levels and collisions, assemble one context packet. Read the packet
   yourself and ask whether you could do the task with only that.
3. **Proof** — one node, one worktree, one agent, one compiled packet, no search
   tool at all. If it completes, the thesis holds. If it can't, the `request_mem`
   log says exactly what was missing.

Everything past step 3 is scaling: parallel dispatch, invalidation on write,
ratification barriers, the amendment loop.

## Spec format

Six fields per node, three of which the compiler reads.

```yaml
- id:          symbol_table          # structural: identity
  references:  [other_node_id]       # structural: edges
  writes:      [path/to/code]        # structural: collision + packet assembly
  one_liner:   What it does.         # payload: copied to the agent
  done_when:                         # payload: compiled into the tester contract
    - How you know it works.
  open:                              # payload: surfaces as a compiler warning
    - What you haven't decided.
```

`references` are spec node ids. `writes` are code paths, resolved by the analyzer
against the codebase at a commit. Two namespaces, joined by the analyzer.

Nothing runs a model during compilation. Same spec plus same commit gives the
same plan every time.

## Deliberately not built yet

SCIP emission, tree-sitter, any language but Python, value-level dataflow, packet
budget policy, ratification barriers, `reaches` declarations for dynamic dispatch.
Each is real and each is later.
