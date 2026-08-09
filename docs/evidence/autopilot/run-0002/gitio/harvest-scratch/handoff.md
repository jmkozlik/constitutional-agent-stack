# Handoff — node gitio (validation-only dispatch)

packet: node=gitio role=executor commit=225e2da300ea9253100fd93e870cca06fe67def5 plan=66e648664216 packet_hash=e6917f70b492

## Status
Complete. Empty delta confirmed in practice: no writes to analyzer/gitio.py or
anywhere outside .harness/. All three done_when bullets ATTESTED (see
.harness/out/attestation.md), zero defects filed (.harness/out/defects.md).

## Verified facts (each backed by command output in attestation.md)
- Full suite passes at packet commit: 440 passed, 1 skipped
  (`.venv/bin/python -m pytest`).
- `list_py_files` and `read_files` work against a bare clone (no worktree
  exists) and ignore dirty worktree state in a non-bare repo. Only plumbing
  commands appear in the module: rev-parse, ls-tree, cat-file --batch, diff.
- A byte-identical `git mv` (git's own `-M` diff reports R100) comes out of
  `changed_files` as old-path pure delete `([(1,3)], [])` plus new-path pure
  add `([], [(1,3)])`; no rename entry.
- All four callables raise GitError naming the failed command on bad revs /
  missing directories. `read_files` also raises on a missing object even
  though `cat-file --batch` exits zero there (message: "object <rev>:<path>
  not found") — stronger than the seeded error line requires.
- Probe script is reproducible: `.venv/bin/python .harness/scratch/probe_gitio.py`
  rebuilds its fixtures from scratch on every run (fixture SHAs differ per run
  because commits are re-created; behavior is identical).

## Interpretive claims (mine, not verified law)
- Git repo discovery walks up: passing a non-repo directory that sits inside
  an enclosing repo silently answers from the enclosing repo (observed with
  `resolve_commit(".harness/scratch", "HEAD")` → this worktree's HEAD). I
  judged this conforming — the seeded error contract keys on non-zero exit,
  and the command exits zero — so I recorded it as an observation in
  defects.md rather than filing. A future spec author might want a
  strict-repo check if callers ever pass user-supplied paths.
- `read_files(repo, rev, [])` → `{}` with no git invocation. I read this as
  fine under bullet 3 (no command ran, nothing failed silently).
- Edge not probed: paths containing characters git quotes even with
  core.quotePath=false (tab/newline/quote in filename) in `changed_files`
  diff-header parsing. Exotic, no caller in the packet exercises it, and no
  done_when bullet covers it — noting for completeness only.

## Scratch inventory
- probe_gitio.py — the probe script (self-contained, rebuilds fixtures).
- fixture-repo/, fixture-bare.git/ — throwaway git fixtures from last run.
