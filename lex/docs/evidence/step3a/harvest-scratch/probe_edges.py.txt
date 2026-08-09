"""Diagnostic (non-gating) edges behind the done_when bullets.

Asks the harder questions the happy-path fixtures in probe.py do not:
  E1  signature change on a CLASS METHOD called through an instance
  E2  import added at top of a file that also HAS a changed symbol
  E3  signature change where a call site is statically undecidable
Prints what compute_affected does; asserts nothing.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analyzer.affected import compute_affected, render_report  # noqa: E402

ROOT = Path(__file__).resolve().parent / "fixtures"


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


def show(report):
    print("  --- render_report ---")
    render_report(report, out=sys.stdout)
    print("  --- rows ---")
    for r in report.rows:
        print(f"    path={r.path!r} category={r.category!r} detail={r.detail!r} "
              f"error={r.error} callers={r.callers}")
    print(f"  has_error={report.has_error}")

print("\n### E1: method signature change, called through an instance ###")
MOD_1 = '''\
class Service:
    def handle(self, payload):
        return payload
'''
MOD_2 = '''\
class Service:
    def handle(self, payload, retries=0):
        return payload
'''
USER = '''\
from mod import Service


def run():
    svc = Service()
    return svc.handle({"a": 1})
'''
repo = new_repo("e1_method_sig")
old = commit(repo, {"mod.py": MOD_1, "user.py": USER}, "base")
new = commit(repo, {"mod.py": MOD_2}, "add retries param")
show(compute_affected(repo, old, new))

print("\n### E2: import added at top AND one symbol's body edited ###")
BASE = '''\
def alpha(x):
    return x + 1


def beta(y):
    return y * 2
'''
EDIT = '''\
import os


def alpha(x):
    return x + 99


def beta(y):
    return y * 2
'''
repo = new_repo("e2_import_plus_edit")
old = commit(repo, {"mod.py": BASE}, "base")
new = commit(repo, {"mod.py": EDIT}, "import + body edit")
show(compute_affected(repo, old, new))

print("\n### E3: signature change with a dynamic call site ###")
DYN = '''\
import mod


def run(name):
    fn = getattr(mod, name)
    return fn(1)
'''
repo = new_repo("e3_dynamic")
old = commit(repo, {"mod.py": "def target(x):\n    return x\n", "dyn.py": DYN}, "base")
new = commit(repo, {"mod.py": "def target(x, y=0):\n    return x\n"}, "add param")
rep = compute_affected(repo, old, new)
show(rep)
