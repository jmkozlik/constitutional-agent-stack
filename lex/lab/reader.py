"""File readers over the harness's own artifacts.

Read-only, local, no external services (docs/lab-brief.md, TECH
CONSTRAINTS). Everything returned is wrapped by `lab.cite`, so the payload
carries its own provenance and the UI cannot render an uncitable number.

Where the records actually are: the brief names `runs/`, which does not
exist in this repo — dispatch records were written next to their evidence
under `docs/evidence/step*/`. Both locations are read, `runs/` first, so
the brief's layout becomes true the moment `dispatch.harvest` writes there
without anything here changing.
"""

import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from lab import cite

RECORD_GLOBS = ("runs/*/dispatch_record*.json", "runs/dispatch_record*.json",
                "docs/evidence/*/dispatch_record_*.json")


class ReaderError(Exception):
    pass


def _rel(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def record_paths(repo) -> list:
    repo = Path(repo)
    found = []
    for pattern in RECORD_GLOBS:
        found.extend(sorted(repo.glob(pattern)))
    return found


def runs_empty_reason(repo) -> str:
    return ("no dispatch records yet — runs/ is empty and no "
            "docs/evidence/*/dispatch_record_*.json exists")


def _seconds(started: str, finished: str):
    fmt = "%Y-%m-%dT%H:%M:%S%z"
    try:
        return int((datetime.datetime.strptime(finished, fmt)
                    - datetime.datetime.strptime(started, fmt)).total_seconds())
    except (TypeError, ValueError):
        return None


def _wall_clock(record: dict, rel: str, name: str):
    if isinstance(record.get("wall_clock_seconds"), (int, float)):
        return cite.cited(int(record["wall_clock_seconds"]), path=rel,
                          field="wall_clock_seconds")
    stated = record.get("wall_clock")
    if isinstance(stated, str):
        # Recorded as prose ("~20m dispatch-to-artifacts"). Parsed to seconds
        # so the column sorts, with the original text carried as the note so
        # the citation shows what was actually written — including the "~".
        match = re.search(r"(?:(\d+)\s*m)(?:\s*(\d+)\s*s)?|(\d+)\s*s", stated)
        if match:
            minutes, secs, only_secs = match.groups()
            return cite.cited(int(minutes or 0) * 60 + int(secs or only_secs or 0),
                              path=rel, field="wall_clock", note=stated)
    seconds = _seconds(record.get("started"), record.get("finished"))
    if seconds is not None:
        return cite.derived(seconds, path=rel, fields=["started", "finished"],
                            how="finished - started")
    return cite.unavailable(f"no wall-clock and no start/finish pair in {name}")


def _tokens(record: dict, rel: str, name: str, key: str, field: str):
    tokens = record.get("tokens")
    if not isinstance(tokens, dict) or tokens.get(key) is None:
        # Two different absences, one honest answer: the count is not known.
        # Rendering 0 would claim the dispatch was free.
        return cite.unavailable(f"token counts not recorded in {name}")
    return cite.cited(int(tokens[key]), path=rel, field=field)


def _reads(record: dict, rel: str, name: str):
    reads = record.get("reads_out_of_packet")
    if reads is None:
        return cite.unavailable(
            f"read telemetry not recorded in {name} — this dispatch predates "
            "the read fence (F29), so nobody was counting"
        )
    return cite.cited(len(reads), path=rel, field="reads_out_of_packet")


def _gate(record: dict, rel: str, name: str):
    gate = record.get("gate")
    if gate:
        violations = record.get("violations") or []
        note = f"{len(violations)} violation(s)" if violations else ""
        return cite.cited(gate, path=rel, field="gate", note=note)
    if record.get("verdict"):
        # The early records wrote a prose verdict instead of a gate field.
        # Shown as-is rather than reclassified into a chip the record never
        # claimed.
        return cite.cited("recorded as prose", path=rel, field="verdict",
                          note=str(record["verdict"])[:400])
    return cite.unavailable(f"no gate result recorded in {name}")


def runs(repo) -> list:
    repo = Path(repo)
    rows = []
    for path in record_paths(repo):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ReaderError(f"{_rel(repo, path)}: {exc}") from exc
        rel, name = _rel(repo, path), path.name
        rows.append({
            "id": cite.cited(record.get("dispatch_id") or path.stem,
                             path=rel, field="dispatch_id"),
            "node": cite.cited(record.get("node"), path=rel, field="node"),
            "role": cite.cited(record.get("role"), path=rel, field="role"),
            "gate": _gate(record, rel, name),
            "wall_clock": _wall_clock(record, rel, name),
            "tokens_in": _tokens(record, rel, name, "input_incl_cache",
                                 "tokens.input_incl_cache"),
            "tokens_out": _tokens(record, rel, name, "output", "tokens.output"),
            "reads_out_of_packet": _reads(record, rel, name),
            "packet_hash": cite.cited(record.get("packet_hash"), path=rel,
                                      field="packet_hash"),
            "commit": cite.cited(record.get("commit"), path=rel,
                                 field="commit"),
            "artifacts": cite.cited(len(record.get("artifacts") or []),
                                    path=rel, field="artifacts"),
        })
    return sorted(rows, key=lambda row: row["id"]["v"])


def run_detail(repo, dispatch_id: str) -> dict:
    repo = Path(repo)
    for path in record_paths(repo):
        record = json.loads(path.read_text())
        if (record.get("dispatch_id") or path.stem) != dispatch_id:
            continue
        rel = _rel(repo, path)
        return {
            "id": dispatch_id,
            "path": rel,
            "record": record,
            "artifacts": record.get("artifacts")
                         or record.get("artifacts_landed") or [],
            "fence_allowed": record.get("fence_allowed") or {},
            "reads_out_of_packet": record.get("reads_out_of_packet"),
            "evidence_dir": _rel(repo, path.parent),
        }
    raise ReaderError(f"no dispatch record with id {dispatch_id!r}")


def _f36_state(repo: Path):
    """Read the finding's state out of the code that implements it.

    A hardcoded badge would drift the moment the finding moved; this is the
    same discipline as the citation itself.
    """
    tools = repo / "lex" / "tools.py"
    if not tools.exists():
        return cite.unavailable("lex/tools.py not found")
    text = tools.read_text()
    if "_handoff_replayable" in text:
        return cite.cited("landed", path="lex/tools.py",
                          field="_handoff_replayable",
                          note="citability is per-packet: a packet with no "
                               "handoff replays regardless of the record")
    if "F36_OPEN = True" in text:
        return cite.cited("open", path="lex/tools.py", field="F36_OPEN")
    return cite.unavailable("F36 state not determinable from lex/tools.py")


def plan_hash(repo) -> dict:
    """The current plan hash, from the compiler rather than from a cache.

    Its own endpoint because it costs an index build; the status bar fills
    this cell in when it lands instead of holding the page.
    """
    repo = Path(repo)
    result = subprocess.run(
        [sys.executable, "-m", "harness.join", "plan", "--repo", str(repo)],
        capture_output=True, text=True, cwd=str(repo),
    )
    match = re.search(r"dispatch plan hash:\s*([0-9a-f]+)", result.stdout)
    if not match:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return cite.unavailable(
            "harness.join plan did not report a hash"
            + (f": {detail[-1][:120]}" if detail else "")
        )
    return cite.cited(match.group(1), path="harness/specs",
                      field="harness.join plan → dispatch plan hash",
                      note="recompiled on request; not cached")


def status(repo) -> dict:
    repo = Path(repo)
    provider = os.environ.get("LEX_PROVIDER", "").strip().lower()
    if not provider:
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY"):
            provider = "xai"
    provider_value = (
        cite.cited(provider, path="(environment)", field="LEX_PROVIDER")
        if provider else
        cite.unavailable("no API key in the environment — lex cannot open a "
                         "session (ANTHROPIC_API_KEY or XAI_API_KEY)")
    )
    model = os.environ.get("LEX_MODEL")
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True)
        commit = cite.cited(head.stdout.strip()[:12], path="(git)",
                            field="rev-parse HEAD")
    except (subprocess.CalledProcessError, OSError):
        commit = cite.unavailable("git rev-parse HEAD failed in this repo")
    return {
        "provider": provider_value,
        "model": (cite.cited(model, path="(environment)", field="LEX_MODEL")
                  if model else
                  cite.unavailable("LEX_MODEL unset — lex would use its "
                                   "per-provider default")),
        "commit": commit,
        "f36": _f36_state(repo),
        "records": cite.cited(len(record_paths(repo)), path="(filesystem)",
                              field="dispatch_record_*.json"),
    }
