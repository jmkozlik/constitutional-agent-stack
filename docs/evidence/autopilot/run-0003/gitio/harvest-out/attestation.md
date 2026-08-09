# Attestation — node gitio (validation-only dispatch)

packet: node=gitio role=executor commit=9d3bc13c0611b8bea23658237a755960245344bb plan=66e648664216 packet_hash=1df844bc2c8a

Empty delta; no source changes made. `analyzer/gitio.py` untouched.

Fixture: `.harness/scratch/fx/repo` — commit C1 `e6f184cb93723e6236a8e7323f6315588fb6e033`
(`src/a.py` = `a = 1\n`, `src/b.py` = `b = 2\n`, `notes.txt`), commit C2
`784c20062c4728bf4861b44f0aab96fe623b470a` (modifies `a.py`, renames `b.py`→`c.py`;
git itself detects it as a rename: `git -C .harness/scratch/fx/repo diff -M --name-status HEAD~1 HEAD`
→ `M\tsrc/a.py` / `R100\tsrc/b.py\tsrc/c.py`). Bare clone at `.harness/scratch/fx/repo.bare`.
Probe script: `.harness/scratch/fx/probe.py`, run with `.venv/bin/python .harness/scratch/fx/probe.py`.

## Bullet 1 — read_files and list_py_files answer from git objects, never a checkout

ATTEST

Two independent proofs. (a) Both callables answer correctly against a **bare**
clone, which has no checkout at all. (b) In the non-bare repo the worktree sits
at C2 — `src/b.py` is absent from disk and `src/a.py` on disk differs from C1 —
yet querying C1 returns C1's committed bytes, not disk state.

```
$ .venv/bin/python .harness/scratch/fx/probe.py
== Bullet 1: git objects, never a checkout ==
bare list_py_files@C1: ['src/a.py', 'src/b.py']
bare read_files@C1: {'src/a.py': b'a = 1\n', 'src/b.py': b'b = 2\n'}
worktree src/a.py on disk: b'a = 1\nextra = 2\n'
read_files@C1 from non-bare repo: {'src/a.py': b'a = 1\n', 'src/b.py': b'b = 2\n'}
PASS bullet 1
```

Corroborating source (packet source listing, lines 32-53): `list_py_files` shells
to `git ls-tree -r --name-only --full-tree`, `read_files` to `git cat-file --batch`
— pure object reads; no checkout, stash, or temp-worktree command appears anywhere
in the module.

## Bullet 2 — changed_files surfaces a renamed file as a delete plus an add, never a rename

ATTEST

C1→C2 contains a 100%-similarity rename (`src/b.py` → `src/c.py`, confirmed R100
by git above — the strongest case, since git would pair it if allowed).
`changed_files` reports the old path as a pure delete (old-side range only) and
the new path as a pure add (new-side range only); no rename pairing exists in the
return shape.

```
$ .venv/bin/python .harness/scratch/fx/probe.py
== Bullet 2: rename surfaces as delete + add, never a rename ==
changed_files(C1, C2): {'src/a.py': ([], [(2, 2)]), 'src/b.py': ([(1, 1)], []), 'src/c.py': ([], [(1, 1)])}
PASS bullet 2
```

The seeded test suite covers the same behavior and passes:

```
$ .venv/bin/python -m pytest tests/test_gitio.py -v
tests/test_gitio.py::test_rename_appears_as_delete_plus_add PASSED       [ 85%]
...
============================== 7 passed in 0.98s ===============================
```

## Bullet 3 — a failing git command raises GitError, never a silent empty result

ATTEST

Every surface callable was driven into a failing-git-command state; each raised
`GitError` naming the failed command (or, for `read_files` on a missing object,
naming the missing `rev:path`). None returned an empty result.

```
$ .venv/bin/python .harness/scratch/fx/probe.py
== Bullet 3: failing git command raises GitError, never silent empty ==
resolve_commit bad rev: GitError: git rev-parse --verify no-such-rev^{commit} failed: fatal: Needed a single revision
list_py_files bad rev: GitError: git ls-tree -r --name-only --full-tree no-such-rev failed: fatal: Not a valid object name no-such-rev
read_files bad rev: GitError: object no-such-rev:src/a.py not found
read_files missing path: GitError: object 784c20062c4728bf4861b44f0aab96fe623b470a:src/nope.py not found
changed_files bad rev: GitError: git diff --no-ext-diff --no-renames --unified=0 e6f184cb93723e6236a8e7323f6315588fb6e033 no-such-rev failed: fatal: ambiguous argument 'no-such-rev': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]'
resolve_commit nonexistent dir: GitError: git rev-parse --verify HEAD^{commit} failed: fatal: cannot change to '.harness/scratch/fx/no-such-dir': No such file or directory
PASS bullet 3
```

Note: `read_files`'s missing-object case is not literally a non-zero git exit
(`cat-file --batch` exits 0 and prints `<obj> missing`); the code detects that
marker and raises `GitError` anyway (gitio.py:48-49), which satisfies the
"never a silent empty result" clause — attested, with the nuance recorded.

## Packet verify command

```
$ .venv/bin/python -m pytest
================== 441 passed, 1 skipped, 1 warning in 25.88s ==================
```
