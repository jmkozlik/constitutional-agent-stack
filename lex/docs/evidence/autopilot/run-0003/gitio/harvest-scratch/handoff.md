# Handoff — node gitio (validation-only dispatch)

packet: node=gitio role=executor commit=9d3bc13c0611b8bea23658237a755960245344bb plan=66e648664216 packet_hash=1df844bc2c8a

## Status: COMPLETE. All three done_when bullets ATTESTED; deliverables written.

## Verified facts (command output on record in .harness/out/attestation.md)

- Empty delta confirmed in practice: `analyzer/gitio.py` was never edited; git
  status of the worktree shows no source changes.
- Packet verify command `.venv/bin/python -m pytest`: 441 passed, 1 skipped.
- `tests/test_gitio.py`: 7 passed.
- Bullet 1: `list_py_files`/`read_files` answer correctly against a bare clone
  (no checkout exists) and return committed bytes when the worktree disagrees
  with the queried rev. Probe: `.harness/scratch/fx/probe.py`.
- Bullet 2: a git-confirmed R100 rename (`src/b.py`→`src/c.py`) comes back as
  `'src/b.py': ([(1,1)], [])` + `'src/c.py': ([], [(1,1)])` — delete plus add.
- Bullet 3: bad revs / nonexistent dir raise `GitError` naming the failed git
  command for every callable; `read_files` on a missing path raises
  `GitError("object <rev>:<path> not found")`.
- One write-fence denial occurred (recorded verbatim in defects.md, DEFECT 1):
  the fence resolved `src/a.py` against the project root despite a `cd` into
  `.harness/scratch/`. Resolved by using scratch-anchored paths; not evaded.

## Interpretive claims (mine, not verified fact)

- `read_files` missing-object nuance: `cat-file --batch` exits 0 for a missing
  object; the code raises on the ` missing` header marker (gitio.py:48-49). I
  read bullet 3's intent ("never a silent empty result") as satisfied. A
  stricter literal reading ("failing git command" = non-zero exit) would call
  this out-of-clause but it still can't produce a silent empty result.
- `git -C <dir>` on a directory *inside* some enclosing repo resolves against
  that enclosing repo (standard git discovery). E.g. `resolve_commit` pointed
  at a non-repo subdir of a repo answers from the enclosing repo. Git does not
  fail there, so no GitError is due under the bullet as written. Noted only in
  case a future spec wants an "is actually a repo root" guard — that would be a
  contract change, not a defect.
- The fence defect is a harness issue; nothing in this node's scope can fix it.

## Fixture layout (throwaway, .harness/scratch/fx/)

- `repo/` — C1 e6f184cb93723e6236a8e7323f6315588fb6e033 (src/a.py, src/b.py,
  notes.txt), C2 784c20062c4728bf4861b44f0aab96fe623b470a (a.py modified,
  b.py→c.py rename, R100 under `diff -M`). Worktree sits at C2.
- `repo.bare/` — bare clone.
- `probe.py` — rerunnable: `.venv/bin/python .harness/scratch/fx/probe.py`
  from the worktree root; prints PASS per bullet, exits 1 on any failure.

## Nothing pending

No REQUEST_MEM lines outstanding. No source edits proposed. Replacement would
only need to rerun probe.py if evidence must be regenerated.
