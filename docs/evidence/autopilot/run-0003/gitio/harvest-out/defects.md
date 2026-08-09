# Defects — node gitio

## DEFECT 1 — write-fence false positive on cwd-relative paths inside .harness/scratch/

Filed against: the harness write-fence hook (`.claude/hooks/write-fence.py`),
not against the gitio node or its contract.

Evidence (denial recorded verbatim):

```
PreToolUse:Bash hook error: [python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/write-fence.py]: write fence [gitio]: 'src/a.py' is out of scope — REQUEST_MEM or file a defect. Do not work around. Your write scope: analyzer/gitio.py
```

Triggering command (abridged): `cd .harness/scratch/fx && git init -q repo &&
cd repo && mkdir src && printf 'a = 1\n' > src/a.py && ...` — every write in it
targets `.harness/scratch/fx/repo/`, which the packet's fence explicitly permits
("writes outside your write scope, .harness/scratch/, and .harness/out/ are
violations"). The fence evaluated `src/a.py` relative to the project root instead
of the command's cwd after `cd`, and denied a permitted scratch write.

Disposition here: I did not evade the fence — I rewrote the command with
scratch-anchored paths (`> $FX/repo/src/a.py`, `git -C`) so the fence could see
the true targets, and it passed. Same files, same content, targets visible.

A fix would require: the fence to track `cd` when resolving relative paths in a
compound command (or to conservatively resolve candidates against both the
project root and any cwd established earlier in the command) before ruling a
path out of scope. Until then, fixture-building commands that `cd` into scratch
will false-positive.

No defects filed against `analyzer/gitio.py`: all three done_when bullets
attested with evidence (see attestation.md).
