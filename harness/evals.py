"""The reader over what the loop has already produced.

Nothing here runs a dispatch or a probe. It reads the artifacts the loop
already writes — dispatch records, harvested attestations and defect
filings, read-event logs, and the reports' findings ledger — and answers
four questions the loop has so far been answering from memory:

- **miss depth per node** — how often a node's dispatches had to ask,
  which ARCHITECTURE (5) calls telemetry about the spec rather than about
  the agent;
- **defects by catch layer** — where problems are actually being found:
  inside a dispatch, or only later in a report;
- **cost per dispatch** — wall clock, tokens where a record carries them,
  and self-served reads;
- **finding recurrence** — how many reports a finding survives, which is
  the amendment loop's own scoreboard.

Everything is derived from files. A measure with no artifact behind it is
absent rather than estimated.

Run: python -m harness.evals [--evidence DIR] [--reports DIR] [--json]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REQUEST_MEM = re.compile(r"^\s*(?:[-*>]\s*)?REQUEST_MEM\b", re.M)
DEFECT_HEADING = re.compile(r"^##+\s+(?:D-|D\d)", re.M)
FINDING = re.compile(r"\bF\d{1,3}\b")
NEW_FINDING = re.compile(r"\|\s*\*\*(F\d{1,3})\*\*\s*\|[^|]*\bNEW\b", re.I)


def _records(evidence: Path) -> list:
    out = []
    for path in sorted(evidence.rglob("dispatch_record_*.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        record["_dir"] = path.parent
        out.append(record)
    return out


def _text_of(directory: Path, *names) -> str:
    chunks = []
    for name in names:
        path = directory / "harvest-out" / name
        if path.is_file():
            chunks.append(path.read_text(errors="replace"))
    return "\n".join(chunks)


def collect(*, evidence, reports) -> dict:
    evidence, reports = Path(evidence), Path(reports)
    records = _records(evidence) if evidence.is_dir() else []
    report_files = sorted(reports.glob("*.md")) if reports.is_dir() else []

    cost, misses = [], defaultdict(lambda: {"request_mem": 0, "dispatches": 0})
    filed_defects = 0
    for record in records:
        directory = record["_dir"]
        node = record.get("node", "?")
        # Testers file tester_report.md, executors attestation.md. Reading
        # only the executor's shape reported a tester's asks as zero.
        attestation = _text_of(
            directory, "attestation.md", "defects.md", "tester_report.md"
        )
        asked = len(REQUEST_MEM.findall(attestation))
        misses[node]["request_mem"] += asked
        misses[node]["dispatches"] += 1
        filed_defects += len(DEFECT_HEADING.findall(
            _text_of(directory, "defects.md")
        ))
        reads = record.get("reads_out_of_packet") or []
        tokens = record.get("tokens") or {}
        cost.append({
            "dispatch_id": record.get("dispatch_id", "?"),
            "node": node,
            "role": record.get("role", "?"),
            "wall_clock_seconds": record.get("wall_clock_seconds"),
            "output_tokens": tokens.get("output"),
            "self_served_misses": record.get("self_served_misses", len(reads)),
            "gate": record.get("gate", "?"),
            "request_mem": asked,
        })

    # Where a defect was caught: inside a dispatch (its own filing) or only
    # afterwards, in a report's ledger. The ratio is the interesting part —
    # a loop that only ever finds things in reports is not dispatching well.
    new_in_reports = 0
    recurrence = defaultdict(lambda: {"reports": 0, "first": None, "last": None})
    for path in report_files:
        text = path.read_text(errors="replace")
        stem = path.stem
        new_in_reports += len(NEW_FINDING.findall(text))
        for finding in sorted(set(FINDING.findall(text))):
            row = recurrence[finding]
            row["reports"] += 1
            row["first"] = row["first"] or stem
            row["last"] = stem

    return {
        "totals": {
            "dispatches": len(records),
            "reports": len(report_files),
            "findings_tracked": len(recurrence),
        },
        "miss_depth_per_node": [
            {"node": node, **counts} for node, counts in sorted(misses.items())
        ],
        "defects_by_catch_layer": {
            "dispatch": filed_defects,
            "report": new_in_reports,
        },
        "cost_per_dispatch": sorted(cost, key=lambda c: c["dispatch_id"]),
        "finding_recurrence": [
            {"finding": name, **row}
            for name, row in sorted(
                recurrence.items(), key=lambda kv: (-kv[1]["reports"], kv[0])
            )
        ],
    }


def render(report: dict) -> str:
    totals = report["totals"]
    lines = [
        f"evals — {totals['dispatches']} dispatches, {totals['reports']} reports, "
        f"{totals['findings_tracked']} findings tracked",
        "",
        "miss depth per node (request_mem lines raised, by the node dispatched)",
    ]
    for row in report["miss_depth_per_node"]:
        per = row["request_mem"] / row["dispatches"] if row["dispatches"] else 0
        lines.append(
            f"  {row['node']:<18} {row['request_mem']:>3} asks over "
            f"{row['dispatches']} dispatch(es)   {per:.1f}/dispatch"
        )
    layers = report["defects_by_catch_layer"]
    caught = layers["dispatch"] + layers["report"]
    share = (layers["dispatch"] / caught * 100) if caught else 0
    lines += [
        "",
        "defects by catch layer",
        f"  in-dispatch (filed by the agent)   {layers['dispatch']:>3}",
        f"  in-report   (found afterwards)     {layers['report']:>3}",
        f"  caught inside the dispatch: {share:.0f}%",
        "",
        "cost per dispatch",
    ]
    for row in report["cost_per_dispatch"]:
        wall = row["wall_clock_seconds"]
        wall_s = f"{wall // 60}m{wall % 60:02d}s" if isinstance(wall, int) else "  —  "
        lines.append(
            f"  {row['dispatch_id']:<7} {row['node']:<18} {row['role']:<9} "
            f"{wall_s:>7}  asks {row['request_mem']:>2}  "
            f"self-served {row['self_served_misses']:>2}  gate {row['gate']}"
        )
    lines += ["", "finding recurrence (reports a finding appears in)"]
    for row in report["finding_recurrence"][:12]:
        lines.append(
            f"  {row['finding']:<5} {row['reports']:>2} reports  "
            f"{row['first']}..{row['last']}"
        )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.evals",
        description="Read the loop's own artifacts and report on them.",
    )
    parser.add_argument("--evidence", default="docs/evidence")
    parser.add_argument("--reports", default="harness/reports")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = collect(evidence=args.evidence, reports=args.reports)
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
