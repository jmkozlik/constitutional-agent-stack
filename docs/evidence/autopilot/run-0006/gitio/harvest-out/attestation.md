# Attestation — node gitio (validation-only dispatch)

packet: node=gitio role=executor commit=e4f744d1bb08bfee7162ee1a2f4adfcd206a154a plan=66e648664216 packet_hash=552627c88186

Worktree verified against packet before probing:

```
$ git rev-parse HEAD && git status --porcelain && shasum analyzer/gitio.py
e4f744d1bb08bfee7162ee1a2f4adfcd206a154a
?? .venv
da28eaab8116b8b37936e95479efd83b97607cfb  analyzer/gitio.py
```

All evidence below is from one probe run observing only the values returned
by the surface callables (per observed_through). Fixture: a source repo with
two commits (c1 adds pkg/a.py, pkg/b.py, notes.txt; c2 does `git mv
pkg/b.py pkg/renamed.py` with identical content, i.e. a 100%-similarity
rename git would otherwise detect), plus a **bare clone** of it. Probe
script: `.harness/scratch/probe_done_when.py`.

```
$ .venv/bin/python .harness/scratch/probe_done_when.py
```

## ATTEST — read_files and list_py_files answer from git objects, never a checkout

Both callables were run against the **bare clone**, a repository that has no
working tree anywhere — there is no checkout they could possibly answer
from. Both returned correct listings and byte-exact contents, including for
the old rev whose tree is checked out nowhere.

```
[1] bare repo contains no .py working files: True ([])
[1] list_py_files(bare, new) = ['pkg/a.py', 'pkg/renamed.py']
[1] read_files(bare, new, ...) = {'pkg/a.py': b'x = 1\ny = 2\n', 'pkg/renamed.py': b'def f():\n    return 3\n'}
[1] read_files(bare, old, ['pkg/b.py']) = {'pkg/b.py': b'def f():\n    return 3\n'}
[1] PASS
```

## ATTEST — changed_files surfaces a renamed file as a delete plus an add, never a rename

The fixture rename is 100%-similarity (`git mv`, content untouched), the
case git's rename detection would collapse. changed_files returned two
entries — the old path as a pure delete (old-side ranges only) and the new
path as a pure add (new-side ranges only) — and no rename pairing:

```
[2] changed_files(bare, old, new) = {'pkg/b.py': ([(1, 2)], []), 'pkg/renamed.py': ([], [(1, 2)])}
[2] PASS: rename -> delete (old side only) + add (new side only)
```

## ATTEST — A failing git command raises GitError, never a silent empty result

Every surface callable was driven into failure two ways: a bad rev/path in
a good repo, and a nonexistent repo directory (git itself fails to start).
All eight cases raised GitError naming the failed command; none returned an
empty result:

```
[3] resolve_commit bad rev: GitError: git rev-parse --verify no-such-rev^{commit} failed: fatal: Needed a single revision
[3] list_py_files bad rev: GitError: git ls-tree -r --name-only --full-tree no-such-rev failed: fatal: Not a valid object name no-such-rev
[3] read_files missing path: GitError: object 5abc388d8db2e0ccfee57ce6c3f995fbb1dcd6b7:pkg/missing.py not found
[3] changed_files bad rev: GitError: git diff --no-ext-diff --no-renames --unified=0 no-such-rev 5abc388d8db2e0ccfee57ce6c3f995fbb1dcd6b7 failed: fatal: ambiguous argument 'no-such-rev': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
[3] resolve_commit bad repo dir: GitError: git rev-parse --verify HEAD^{commit} failed: fatal: cannot change to '/Users/rokko/experiments/.lex-dispatches/gitio/.harness/scratch/fixtures/absent': No such file or directory
[3] changed_files bad repo dir: GitError: git diff --no-ext-diff --no-renames --unified=0 HEAD~1 HEAD failed: fatal: cannot change to '/Users/rokko/experiments/.lex-dispatches/gitio/.harness/scratch/fixtures/absent': No such file or directory
[3] read_files bad repo dir: GitError: git cat-file --batch failed: fatal: cannot change to '/Users/rokko/experiments/.lex-dispatches/gitio/.harness/scratch/fixtures/absent': No such file or directory
[3] list_py_files bad repo dir: GitError: git ls-tree -r --name-only --full-tree HEAD failed: fatal: cannot change to '/Users/rokko/experiments/.lex-dispatches/gitio/.harness/scratch/fixtures/absent': No such file or directory
[3] PASS
```

Note: `read_files` on a missing path is not strictly "a failing git
command" — `git cat-file --batch` exits 0 and reports ` missing` in-band —
but the implementation converts that in-band miss to a GitError rather than
a silent empty dict, which satisfies the bullet's intent (never a silent
empty result). Included above as evidence, not as a stretch of the bullet.

## Suite verification (packet-named command)

```
$ .venv/bin/python -m pytest
================== 455 passed, 1 skipped, 1 warning in 26.12s ==================
```
