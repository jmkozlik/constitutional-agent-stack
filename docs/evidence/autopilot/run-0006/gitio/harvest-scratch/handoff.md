# Handoff — node gitio, validation-only dispatch

## Verified facts (command evidence in .harness/out/attestation.md)
- Worktree HEAD is e4f744d1bb08bfee7162ee1a2f4adfcd206a154a, matching the
  packet; analyzer/gitio.py was not modified (delta was empty, none needed).
- All three done_when bullets ATTESTED via
  `.venv/bin/python .harness/scratch/probe_done_when.py` (fixture-building
  probe, rerunnable from the worktree root; rebuilds its fixtures under
  .harness/scratch/fixtures/ on every run):
  1. list_py_files/read_files work against a bare clone (no working tree
     exists anywhere), including reads at a rev checked out nowhere.
  2. A 100%-similarity `git mv` rename comes back as
     {old_path: ([(1,2)], []), new_path: ([], [(1,2)])} — pure delete +
     pure add, no rename pairing (--no-renames doing its job).
  3. All four callables raise GitError naming the failed command on bad
     revs and on a nonexistent repo dir; read_files also raises (not empty
     dict) on a missing path even though `cat-file --batch` exits 0 there.
- Full suite: 455 passed, 1 skipped (`.venv/bin/python -m pytest`).

## Probe pitfall worth keeping (verified)
- "Not a repo" cannot be probed with an empty dir under this worktree:
  `git -C <dir>` discovers the repository *upward*, so a scratch dir nested
  inside the worktree resolves against the worktree repo and the command
  succeeds (resolve_commit returned the worktree HEAD). Use a nonexistent
  dir instead — git fails to start, which is a genuinely failing command.

## Interpretive claims (mine, not verified facts)
- The read_files missing-path GitError satisfies the bullet's *intent*
  ("never a silent empty result") though the underlying git command exits 0;
  flagged in attestation.md so a verifier can judge rather than trust me.
- Not probed (judged out of the three bullets' scope, no defect filed):
  paths containing newlines are unrepresentable in the `cat-file --batch`
  line protocol; changed_files header parsing on paths containing tabs.
  If a later spec bullet touches exotic paths, start there.
