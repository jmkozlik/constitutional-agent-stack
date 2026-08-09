# Attestation — node gitio (validation-only dispatch)

packet: node=gitio role=executor commit=225e2da300ea9253100fd93e870cca06fe67def5 plan=66e648664216 packet_hash=e6917f70b492

No code changes made. Evidence below is from the packet's verify command plus
probe fixtures built under `.harness/scratch/` (script: `.harness/scratch/probe_gitio.py`).

Full-suite verify (packet's stated verify command):

```
$ .venv/bin/python -m pytest
================== 440 passed, 1 skipped, 1 warning in 26.14s ==================
```

## ATTEST — read_files and list_py_files answer from git objects, never a checkout

Two lines of evidence.

Static: every git invocation in `analyzer/gitio.py` is an object-reading
plumbing command — no checkout, worktree, stash, or archive anywhere:

```
$ grep -n '"git"\|_git(' analyzer/gitio.py | grep -v 'def _git'
17:        ["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
29:    return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
33:    out = _git(repo, "ls-tree", "-r", "--name-only", "--full-tree", rev).decode()
41:    out = _git(repo, "cat-file", "--batch", input_bytes=queries)
70:    out = _git(
```

(line 70 continues into `"diff", "--no-ext-diff", "--no-renames", "--unified=0"`.)

Behavioral: both callables answer correctly against a **bare** clone — a repo
with no worktree to check out from — and against a non-bare repo whose worktree
was deliberately dirtied after commit:

```
$ .venv/bin/python .harness/scratch/probe_gitio.py
bare repo has no worktree: is_bare=true
list_py_files(BARE, c1) = ['src/a.py', 'top.py']
read_files(BARE, c1, ['src/a.py']) = {'src/a.py': b'line1\nline2\nline3\n'}
worktree top.py now: 'DIRTY WORKTREE CONTENT\n'
read_files(REPO, c1)['top.py'] = b'x = 1\n'
list_py_files(REPO, c1) = ['src/a.py', 'top.py']  (renamed.py absent at c1: OK)
```

The dirty worktree content never leaks into results; the bare repo works at all.

## ATTEST — changed_files surfaces a renamed file as a delete plus an add, never a rename

Fixture: `git mv src/a.py src/renamed.py` with byte-identical content — the
exact case git's rename detection would collapse (git itself reports R100
when asked with `-M`):

```
$ .venv/bin/python .harness/scratch/probe_gitio.py
git itself with -M sees a rename: 'R100\tsrc/a.py\tsrc/renamed.py'
changed_files(REPO, c1, c2) = {'src/a.py': ([(1, 3)], []), 'src/renamed.py': ([], [(1, 3)])}
old path is pure delete, new path is pure add: OK
```

Both paths appear: the old path as pure delete (old-side ranges only), the new
path as pure add (new-side ranges only). No rename entry. The seeded suite's
`tests/test_gitio.py::test_rename_appears_as_delete_plus_add` also passes:

```
$ .venv/bin/python -m pytest tests/test_gitio.py -v
tests/test_gitio.py::test_rename_appears_as_delete_plus_add PASSED       [ 85%]
============================== 7 passed in 0.97s ===============================
```

## ATTEST — a failing git command raises GitError, never a silent empty result

Every surface callable probed with a failing underlying command; each raises
`GitError` naming the failed command, none returns an empty result:

```
$ .venv/bin/python .harness/scratch/probe_gitio.py
resolve_commit bad rev: GitError: git rev-parse --verify no-such-rev^{commit} failed: fatal: Needed a single revision
list_py_files bad rev: GitError: git ls-tree -r --name-only --full-tree no-such-rev failed: fatal: Not a valid object name no-such-rev
changed_files bad rev: GitError: git diff --no-ext-diff --no-renames --unified=0 no-such-rev 8dfdb64e4a331a02a6fc8823a0187cd3f8c9dc6a failed: fatal: ambiguous argument 'no-such-rev': unknown revision or path not in the working tree.
read_files missing path: GitError: object eb7ef7e656fa7302ded5c2b670b53e33b9cd38a8:nope.py not found
resolve_commit missing dir: GitError: git rev-parse --verify HEAD^{commit} failed: fatal: cannot change to '.harness/scratch/no-such-dir': No such file or directory
```

The `read_files missing path` case is one step stronger than the bullet
requires: `cat-file --batch` exits zero on a missing object, and the parser
still raises rather than silently returning fewer blobs.

Note: `read_files(repo, rev, [])` returns `{}` without invoking git — an empty
input, not a swallowed failure; no git command runs, so no conflict with this
bullet.
