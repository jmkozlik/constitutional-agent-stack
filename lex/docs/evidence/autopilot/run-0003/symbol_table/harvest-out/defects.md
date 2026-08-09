# Defects — node symbol_table

No defects against the task node, the spec surface, or the done_when
bullets: both bullets attested with evidence (see attestation.md).

## D1 — write-fence false positive on scratch paths reached via `cd`

Filed against: the write-fence hook
(`"$CLAUDE_PROJECT_DIR"/.claude/hooks/write-fence.py`), i.e. harness
tooling — not the symbol_table node.

Evidence (verbatim denial): the command
`cd .harness/scratch/gitfix && ... printf '...' > mod.py && git ... commit`
was denied with:

```
PreToolUse:Bash hook error: [python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/write-fence.py]: write fence [symbol_table]: 'mod.py' is out of scope — REQUEST_MEM or file a defect. Do not work around. Your write scope: analyzer/modpath.py, analyzer/symbols.py
```

The redirect target resolved to
`.harness/scratch/gitfix/mod.py` — inside the always-permitted
`.harness/scratch/` area — but the fence judged the lexical token
`mod.py` without resolving it against the command's `cd`. Writing the
same file via the Write tool at its explicit `.harness/scratch/...` path
was allowed, confirming the path itself is in scope and the denial was a
false positive on relative-path resolution.

What a fix would require: the fence's Bash-command scan should resolve
write targets against the working directory in effect at the point of the
redirect (tracking `cd`/`git -C`-style context), or conservatively deny
only after normalizing candidate paths to absolute form. Out of my write
scope; no workaround attempted beyond using an explicit in-scope path.
