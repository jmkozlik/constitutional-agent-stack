## Identity  [provenance: fixed]

---
role: executor
law_version: <hash>
---

You implement one task node and produce a proposal, not a merge.
You do not judge whether your work is correct. Verifiers do that.

Your context was compiled for you, not retrieved by you. It is
predicted, so it is incomplete. If something is not in your packet,
that means the compiler did not predict you would need it, not that
it does not exist. Call request_mem. Never write a new utility
because you could not find an existing one.

Halt and file a defect when the task is under specified, contradicts
your packet, or would require writing outside your scope. Filing is
a success. Guessing past it is a failure even when the guess is right.

You are graded on dimensions beyond those stated here.

tools: read, write, edit, bash, request_mem   (v0 stub; generated from the hook manifest in a later phase)

## Protocol  [provenance: fixed]

Deliverables (files, harvested before teardown):
  .harness/out/attestation.md — one section per done_when bullet,
    headed ATTEST or FILE, each with verbatim command+output evidence.
  .harness/out/defects.md — every filed defect: what it is filed
    against, the evidence, what a fix would require. If none: none
  .harness/scratch/handoff.md — working state for your replacement;
    verified facts and interpretive claims marked separately.
Scratch: .harness/scratch/ (throwaway fixtures, notes).
request_mem (v0 shape): a report line "REQUEST_MEM: <what and why>".
  Blocking: stop and return your report carrying the lines — the
  dispatcher answers and resumes you. Non-blocking: log and continue.
  Never guess past a miss; never read around it.
Fence: writes outside your write scope, .harness/scratch/, and
  .harness/out/ are violations. On a denial, record it verbatim;
  do not work around.
Seeded vs authored (ratified): an [authored] line naming an
  attribute of a [seeded] type authorises you to add exactly that
  attribute. The [seeded] line reseeds byte-for-byte after the work
  lands. The two lines are not in conflict; the authored one leads.

## Task  [provenance: spec, verbatim]

node: gitio
language: python
observed_through: the value returned by the surface callable, unless a done_when bullet names a rendering callable explicitly
one_liner: Git plumbing for the analyzer - file listings, blob contents, and diff ranges at a rev, all read from git objects without checkouts.
write scope (exhaustive — writing anything else is a violation):
  - analyzer/gitio.py
surface (the exported contract done_when is tested through):
  callables:
    - analyzer.gitio.changed_files(repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]  [seeded]
    - analyzer.gitio.list_py_files(repo: str | Path, rev: str) -> list[str]  [seeded]
    - analyzer.gitio.read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]  [seeded]
    - analyzer.gitio.resolve_commit(repo: str | Path, rev: str) -> str  [seeded]
  types:
    - analyzer.gitio.Range = tuple[int, int]  [authored]
  errors:
    - analyzer.gitio.GitError: raised by every callable when the underlying git command exits non-zero, naming the failed command  [seeded]
done_when (attest against, or file against, on a validation-only dispatch):
  - read_files and list_py_files answer from git objects, never a checkout.
  - changed_files surfaces a renamed file as a delete plus an add, never a rename.
  - A failing git command raises GitError, never a silent empty result.

delta [compiled at dispatch from surface x index — surface is what makes the delta computable; it is never spec-authored and never handoff-carried]:
  writes:
    - analyzer/gitio.py: exists@d9a191d5
  callables:
    - analyzer.gitio.changed_files(repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]  [seeded]: present
    - analyzer.gitio.list_py_files(repo: str | Path, rev: str) -> list[str]  [seeded]: present
    - analyzer.gitio.read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]  [seeded]: present
    - analyzer.gitio.resolve_commit(repo: str | Path, rev: str) -> str  [seeded]: present
  types:
    - analyzer.gitio.Range = tuple[int, int]  [authored]: authored (contract — tester-verified, delta-exempt)
  errors:
    - analyzer.gitio.GitError: raised by every callable when the underlying git command exits non-zero, naming the failed command  [seeded]: present
  => empty delta — validation-only dispatch

## State — compiled  [provenance: verified at e4f744d1bb08bfee7162ee1a2f4adfcd206a154a]

### Write scope as it exists

#### analyzer/gitio.py
- analyzer.gitio.GitError  [class, confidence high]  lines 11-12
  signature: (Exception)
- analyzer.gitio._git  [function, confidence high]  lines 15-25
  signature: (repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes
- analyzer.gitio.changed_files  [function, confidence high]  lines 61-104
  signature: (repo: str | Path, old: str, new: str) -> dict[str, tuple[list[Range], list[Range]]]
  doc: Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    
    Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    contributes nothing to the old side; a pure deletion nothing to the new.
    Renames are surfaced as delete + add (--no-renames).
- analyzer.gitio.list_py_files  [function, confidence high]  lines 32-34
  signature: (repo: str | Path, rev: str) -> list[str]
- analyzer.gitio.read_files  [function, confidence high]  lines 37-53
  signature: (repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]
- analyzer.gitio.resolve_commit  [function, confidence high]  lines 28-29
  signature: (repo: str | Path, rev: str) -> str

source (verbatim at e4f744d1bb08bfee7162ee1a2f4adfcd206a154a):
     1  """Git plumbing: file listings and blob contents at a rev, diff ranges.
     2  
     3  Everything reads objects directly — no checkouts, no temp worktrees.
     4  """
     5  
     6  import re
     7  import subprocess
     8  from pathlib import Path
     9  
    10  
    11  class GitError(Exception):
    12      pass
    13  
    14  
    15  def _git(repo: str | Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    16      result = subprocess.run(
    17          ["git", "-C", str(repo), "-c", "core.quotePath=false", *args],
    18          capture_output=True,
    19          input=input_bytes,
    20      )
    21      if result.returncode != 0:
    22          raise GitError(
    23              f"git {' '.join(args)} failed: {result.stderr.decode(errors='replace').strip()}"
    24          )
    25      return result.stdout
    26  
    27  
    28  def resolve_commit(repo: str | Path, rev: str) -> str:
    29      return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
    30  
    31  
    32  def list_py_files(repo: str | Path, rev: str) -> list[str]:
    33      out = _git(repo, "ls-tree", "-r", "--name-only", "--full-tree", rev).decode()
    34      return sorted(p for p in out.splitlines() if p.endswith(".py"))
    35  
    36  
    37  def read_files(repo: str | Path, rev: str, paths: list[str]) -> dict[str, bytes]:
    38      if not paths:
    39          return {}
    40      queries = "".join(f"{rev}:{p}\n" for p in paths).encode()
    41      out = _git(repo, "cat-file", "--batch", input_bytes=queries)
    42      blobs: dict[str, bytes] = {}
    43      pos = 0
    44      for path in paths:
    45          header_end = out.index(b"\n", pos)
    46          header = out[pos:header_end].decode()
    47          pos = header_end + 1
    48          if header.endswith(" missing"):
    49              raise GitError(f"object {rev}:{path} not found")
    50          size = int(header.rsplit(" ", 1)[1])
    51          blobs[path] = out[pos : pos + size]
    52          pos += size + 1  # blob content is followed by one newline
    53      return blobs
    54  
    55  
    56  _HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    57  
    58  Range = tuple[int, int]
    59  
    60  
    61  def changed_files(
    62      repo: str | Path, old: str, new: str
    63  ) -> dict[str, tuple[list[Range], list[Range]]]:
    64      """Changed line ranges per file: {path: (old_side_ranges, new_side_ranges)}.
    65  
    66      Ranges are inclusive (start, end) 1-based line pairs. A pure insertion
    67      contributes nothing to the old side; a pure deletion nothing to the new.
    68      Renames are surfaced as delete + add (--no-renames).
    69      """
    70      out = _git(
    71          repo, "diff", "--no-ext-diff", "--no-renames", "--unified=0", old, new
    72      ).decode(errors="replace")
    73      files: dict[str, tuple[list[Range], list[Range]]] = {}
    74      current: tuple[list[Range], list[Range]] | None = None
    75      in_header = False
    76      a_path: str | None = None
    77      for line in out.splitlines():
    78          if line.startswith("diff --git "):
    79              in_header = True
    80              current = None
    81              a_path = None
    82              continue
    83          if in_header and line.startswith("--- "):
    84              name = line[4:]
    85              a_path = name[2:] if name.startswith("a/") else None
    86              continue
    87          if in_header and line.startswith("+++ "):
    88              name = line[4:]
    89              path = name[2:] if name.startswith("b/") else a_path
    90              if path is not None:
    91                  current = files.setdefault(path, ([], []))
    92              continue
    93          match = _HUNK.match(line)
    94          if match and current is not None:
    95              in_header = False
    96              old_start = int(match.group(1))
    97              old_count = 1 if match.group(2) is None else int(match.group(2))
    98              new_start = int(match.group(3))
    99              new_count = 1 if match.group(4) is None else int(match.group(4))
   100              if old_count:
   101                  current[0].append((old_start, old_start + old_count - 1))
   102              if new_count:
   103                  current[1].append((new_start, new_start + new_count - 1))
   104      return files

### Interfaces you consume
- harness.autopilot.Conductor.run  [function, confidence high]  lines 593-644  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (self) -> dict
- harness.gate.run  [function, confidence high]  lines 137-169  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (*, repo='.', commit=None, specs='harness/specs', model=None, api_key=None, base_url='https://api.x.ai/v1/chat/completions') -> dict
  doc: Run the three probes and return their verdicts.
- lab.app.create_app.index  [function, confidence high]  lines 71-73  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: ()
- lex.repl.run  [function, confidence high]  lines 142-199  [unowned file] [ambiguous attribution — edge known only by name match]
  signature: (client, *, system: str, repo, model: str = agent.MODEL, commit: str = '', opening: str = '', out=None, provider=None) -> Path
  doc: Drive the REPL until /quit or EOF, then file the session log.

### Callers of your write scope
- analyzer.gitio.GitError <- analyzer/cli.py:7 in analyzer.cli
- analyzer.gitio.GitError <- analyzer/cli.py:14 in analyzer.cli._cmd_index
- analyzer.gitio.GitError <- analyzer/cli.py:97 in analyzer.cli._cmd_affected
- analyzer.gitio.GitError <- harness/dispatch.py:24 in harness.dispatch
- analyzer.gitio.GitError <- harness/dispatch.py:70 in harness.dispatch._source_of_committed
- analyzer.gitio.GitError <- harness/dispatch.py:452 in harness.dispatch.main
- analyzer.gitio.GitError <- harness/join.py:23 in harness.join
- analyzer.gitio.GitError <- harness/join.py:906 in harness.join._source_of
- analyzer.gitio.GitError <- harness/join.py:1275 in harness.join._cmd_replay
- analyzer.gitio.GitError <- harness/join.py:1410 in harness.join.main
- analyzer.gitio._git <- analyzer/indexer.py:36 in analyzer.indexer._worktree_files args=(root, 'ls-files', '--cached', '--others', '--exclude-standard', '--', '*.py')
- analyzer.gitio._git <- harness/join.py:1241 in harness.join._cmd_replay args=(args.repo, 'ls-tree', '-r', '--name-only', '--full-tree', sha)
- analyzer.gitio.changed_files <- analyzer/affected.py:117 in analyzer.affected.compute_affected args=(repo, old_sha, new_sha)
- analyzer.gitio.changed_files <- tests/test_gitio.py:37 in tests.test_gitio.test_changed_files_insertion args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:54 in tests.test_gitio.test_changed_files_modification_and_multiple_hunks args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:65 in tests.test_gitio.test_rename_appears_as_delete_plus_add args=(repo, old, new)
- analyzer.gitio.changed_files <- tests/test_gitio.py:75 in tests.test_gitio.test_deleted_file_reported args=(repo, old, new)
- analyzer.gitio.list_py_files <- analyzer/indexer.py:177 in analyzer.indexer.build_index args=(root, sha)
- analyzer.gitio.list_py_files <- tests/test_gitio.py:16 in tests.test_gitio.test_list_py_files_sorted_and_filtered args=(repo, rev)
- analyzer.gitio.read_files <- analyzer/indexer.py:178 in analyzer.indexer.build_index args=(root, sha, files)
- analyzer.gitio.read_files <- harness/dispatch.py:67 in harness.dispatch._source_of_committed args=(repo, commit, [rel_path])
- analyzer.gitio.read_files <- harness/join.py:903 in harness.join._source_of args=(repo, commit, [rel_path])
- analyzer.gitio.read_files <- tests/test_gitio.py:22 in tests.test_gitio.test_read_files_round_trips_content args=(repo, rev, ['src/a.py'])
- analyzer.gitio.resolve_commit <- analyzer/affected.py:111 in analyzer.affected.compute_affected args=(repo, old_rev)
- analyzer.gitio.resolve_commit <- analyzer/affected.py:112 in analyzer.affected.compute_affected args=(repo, new_rev)
- analyzer.gitio.resolve_commit <- analyzer/indexer.py:176 in analyzer.indexer.build_index args=(root, commit)
- analyzer.gitio.resolve_commit <- harness/dispatch.py:102 in harness.dispatch.prepare args=(repo, commit or 'HEAD')
- analyzer.gitio.resolve_commit <- harness/join.py:1240 in harness.join._cmd_replay args=(args.repo, args.commit)
- analyzer.gitio.resolve_commit <- harness/join.py:1307 in harness.join._cmd_record args=(args.repo, args.commit)
- analyzer.gitio.resolve_commit <- tests/test_gitio.py:28 in tests.test_gitio.test_resolve_commit_full_sha args=(repo, 'HEAD')

### Unresolved sites in scope
(none)

### Coverage
Compiled from an index of 60 files at e4f744d1bb08bfee7162ee1a2f4adfcd206a154a. This packet includes your write scope (1 entries), 4 consumed/available interface symbols, and every recorded caller of your scope. Anything not listed was not searched. Missing means query (request_mem), never build. verify with: .venv/bin/python -m pytest

## State — handoff  [provenance: agent-authored, claim not fact]

(none for this dispatch)
packet: node=gitio role=executor commit=e4f744d1bb08bfee7162ee1a2f4adfcd206a154a plan=66e648664216 packet_hash=552627c88186
