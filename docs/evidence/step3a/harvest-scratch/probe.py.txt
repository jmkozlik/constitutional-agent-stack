"""Independent fixtures for the four affected_symbols done_when bullets.

Throwaway. Builds tiny git repos under .harness/scratch/fixtures and runs
compute_affected against them, so each bullet gets evidence that does not
depend on reading tests/test_affected.py (outside this dispatch's read scope).
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analyzer.affected import compute_affected, render_report  # noqa: E402

ROOT = Path(__file__).resolve().parent / "fixtures"
FAILURES = []


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def new_repo(name):
    repo = ROOT / name
    if repo.exists():
        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "probe@example.invalid")
    git(repo, "config", "user.name", "probe")
    return repo


def commit(repo, files, msg):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def check(label, cond, detail=""):
    mark = "PASS" if cond else "FAIL"
    if not cond:
        FAILURES.append(label)
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))


def show(report):
    print("  --- render_report ---")
    render_report(report, out=sys.stdout)
    print("  --- rows ---")
    for r in report.rows:
        print(f"    path={r.path!r} category={r.category!r} detail={r.detail!r} "
              f"error={r.error} callers={r.callers}")
    print(f"  has_error={report.has_error}")


# ---------------------------------------------------------------- bullet 1
# "An import added at the top of a file reports every symbol as moved,
#  nothing as changed."
MOD_A = '''\
def alpha(x):
    return x + 1


def beta(y):
    return alpha(y) * 2


class Gamma:
    def method(self):
        return beta(3)
'''
OTHER_A = '''\
from mod import alpha


def outside():
    return alpha(5)
'''

print("\n=== BULLET 1: import added at top => every symbol moved ===")
repo = new_repo("b1_import_at_top")
old = commit(repo, {"mod.py": MOD_A, "other.py": OTHER_A}, "base")
new = commit(repo, {"mod.py": "import os\n\n\n" + MOD_A}, "add import at top")
rep = compute_affected(repo, old, new)
show(rep)
cats = {r.category for r in rep.rows}
paths = {r.path for r in rep.rows}
check("every row is 'moved'", cats == {"moved"}, f"categories={sorted(cats)}")
check(
    "every symbol in the touched file is reported",
    paths == {"mod.alpha", "mod.beta", "mod.Gamma", "mod.Gamma.method"},
    f"paths={sorted(paths)}",
)
check("nothing reported as changed",
      not (cats & {"signature", "body", "decorators", "added", "deleted", "unknown"}))
check("no error", rep.has_error is False)

# ---------------------------------------------------------------- bullet 2
# "A body only change reports the changed symbol with category body and empty
#  callers, and no signature or body row for any of its callers."
MOD_B1 = '''\
def target(x):
    return x + 1


def caller_one():
    return target(1)
'''
MOD_B2 = '''\
def target(x):
    return x + 2


def caller_one():
    return target(1)
'''
OTHER_B = '''\
from mod import target


def caller_two():
    return target(2)
'''

print("\n=== BULLET 2: body-only change => body, empty callers ===")
repo = new_repo("b2_body_only")
old = commit(repo, {"mod.py": MOD_B1, "other.py": OTHER_B}, "base")
new = commit(repo, {"mod.py": MOD_B2}, "body only")
rep = compute_affected(repo, old, new)
show(rep)
target_rows = [r for r in rep.rows if r.path == "mod.target"]
check("exactly one row for the changed symbol", len(target_rows) == 1)
check("category is 'body'", bool(target_rows) and target_rows[0].category == "body")
check("callers empty", bool(target_rows) and target_rows[0].callers == [],
      f"callers={target_rows[0].callers if target_rows else 'n/a'}")
caller_paths = {"mod.caller_one", "other.caller_two"}
bad = [r for r in rep.rows
       if r.path in caller_paths and r.category in {"signature", "body"}]
check("no signature/body row for any caller", bad == [], f"offending={bad}")
check("no error", rep.has_error is False)

# ---------------------------------------------------------------- bullet 3
# "A signature change names every call site."
MOD_C2 = '''\
def target(x, y=0):
    return x + 1


def caller_one():
    return target(1)
'''
OTHER_C = '''\
from mod import target


def caller_two():
    return target(2)


def caller_three():
    f = target
    return f(3)
'''

print("\n=== BULLET 3: signature change names every call site ===")
repo = new_repo("b3_signature")
old = commit(repo, {"mod.py": MOD_B1, "other.py": OTHER_C}, "base")
new = commit(repo, {"mod.py": MOD_C2}, "add parameter")
rep = compute_affected(repo, old, new)
show(rep)
sig_rows = [r for r in rep.rows if r.path == "mod.target"]
check("row category is 'signature'",
      bool(sig_rows) and sig_rows[0].category == "signature")
sites = {(c["file"], c["line"]) for c in (sig_rows[0].callers if sig_rows else [])}


def site_of(source, needle, path):
    """1-based line of `needle` in `source`, derived not hand-counted."""
    for i, line in enumerate(source.splitlines(), 1):
        if needle in line:
            return (path, i)
    raise AssertionError(f"probe bug: {needle!r} not in {path}")


# every place the fixture references `target`, located in the source text
expected = {
    site_of(MOD_B1, "return target(1)", "mod.py"),
    site_of(OTHER_C, "return target(2)", "other.py"),
    site_of(OTHER_C, "f = target", "other.py"),
    site_of(OTHER_C, "from mod import target", "other.py"),
}
print(f"  authored reference sites: {sorted(expected)}")
check("every authored call site named", expected <= sites,
      f"missing={sorted(expected - sites)} all={sorted(sites)}")
print(f"  caller records: {sig_rows[0].callers if sig_rows else 'n/a'}")

# ---------------------------------------------------------------- bullet 4
# "Deleting a symbol with recorded callers is an error, not a silent success."
MOD_D2 = '''\
def caller_one():
    return target(1)
'''

print("\n=== BULLET 4: delete with recorded callers is an error ===")
repo = new_repo("b4_delete_with_callers")
old = commit(repo, {"mod.py": MOD_B1, "other.py": OTHER_B}, "base")
new = commit(repo, {"mod.py": MOD_D2}, "delete target")
rep = compute_affected(repo, old, new)
show(rep)
del_rows = [r for r in rep.rows if r.path == "mod.target"]
check("deleted symbol reported", len(del_rows) == 1)
check("category is 'deleted'", bool(del_rows) and del_rows[0].category == "deleted")
check("row.error set", bool(del_rows) and del_rows[0].error is True)
check("callers recorded on the row", bool(del_rows) and len(del_rows[0].callers) > 0,
      f"callers={del_rows[0].callers if del_rows else 'n/a'}")
check("report.has_error true", rep.has_error is True)

# control: deletion with NO callers must NOT be an error
print("\n=== BULLET 4 control: delete with no callers is not an error ===")
repo = new_repo("b4_control_no_callers")
old = commit(repo, {"mod.py": "def lonely():\n    return 1\n\n\ndef keep():\n    return 2\n"}, "base")
new = commit(repo, {"mod.py": "def keep():\n    return 2\n"}, "delete lonely")
rep = compute_affected(repo, old, new)
show(rep)
check("no error when nothing referenced it", rep.has_error is False)

print("\n==================== SUMMARY ====================")
print("FAILURES:", FAILURES if FAILURES else "none")
sys.exit(1 if FAILURES else 0)
