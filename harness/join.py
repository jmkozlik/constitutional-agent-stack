"""The join — step 2 of the harness build order.

speccc owns the structural half (schema, resolution, cycles, levels,
file-level write collisions: E01–E05). The join adds everything that
needs the analyzer's index: writes resolved to real symbols, undeclared
edges at symbol precision (E08/W04/W05), low-confidence regions that
force serialization (W02, enacted — the printed plan is the safe plan,
never a warned-about unsafe one), and context-packet assembly.

Run: python -m harness.join plan|packet ...
"""

import argparse
import hashlib
import posixpath
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from analyzer.indexer import build_index
from harness import speccc

# v0 stub for the hook manifest (ARCHITECTURE §(2): the tool list is
# generated, identity files stay tool-free; this constant is what the
# manifest replaces in a later phase).
TOOLS = {
    "executor": "read, write, edit, bash, request_mem",
    "tester": "read, write, bash",
}


class JoinError(Exception):
    pass


@dataclass
class Plan:
    nodes: dict
    levels: dict
    plan_hash: str


@dataclass
class AdjustedPlan:
    levels: list  # [(label, [node ids])] — the dispatch-safe structure
    plan_hash: str


@dataclass
class Finding:
    code: str
    message: str
    nodes: tuple = ()

    @property
    def is_error(self) -> bool:
        return self.code.startswith("E")


def load_plan(specs_dir) -> Plan:
    nodes, origin = speccc.load(str(specs_dir))
    index = speccc.validate(nodes, origin)
    speccc.resolve(index)
    speccc.find_cycle(index)
    levels = speccc.levelize(index)
    speccc.check_writes(index, levels)
    return Plan(
        nodes=index,
        levels={lv: list(ids) for lv, ids in levels.items()},
        plan_hash=speccc.plan_hash(index, levels),
    )


# --- writes resolution ------------------------------------------------------


def resolve_writes(plan: Plan, code_index: dict) -> dict:
    """Per node: {writes entry -> {"status", "symbols"}}.

    status: "indexed" (file in the index, symbols attached), "to_create"
    (a .py path that does not exist at this commit — the normal case for
    greenfield specs), "opaque" (not a Python file; outside the index).
    E06 is reserved for uninterpretable entries: absolute paths or paths
    escaping the repo root.
    """
    known_files = set(code_index["files"])
    by_file: dict[str, list[dict]] = defaultdict(list)
    for record in code_index["symbols"]:
        by_file[record["file"]].append(record)
    errors = []
    resolved: dict[str, dict[str, dict]] = {}
    for nid in sorted(plan.nodes):
        node_map = {}
        for entry in plan.nodes[nid]["writes"]:
            norm = posixpath.normpath(entry)
            if posixpath.isabs(entry) or norm.startswith(".."):
                errors.append(
                    f"[E06] {nid}: writes entry '{entry}' is not a "
                    "repo-relative path"
                )
                continue
            if entry in known_files:
                node_map[entry] = {
                    "status": "indexed",
                    "symbols": sorted(
                        by_file.get(entry, []),
                        key=lambda s: (s["path"], s["start_line"], s["sig_hash"]),
                    ),
                }
            elif entry.endswith(".py"):
                node_map[entry] = {"status": "to_create", "symbols": []}
            else:
                node_map[entry] = {"status": "opaque", "symbols": []}
        resolved[nid] = node_map
    if errors:
        raise JoinError(
            "unresolvable writes (index: "
            f"{len(known_files)} files at "
            f"{code_index['commit'] or 'worktree'}):\n  " + "\n  ".join(errors)
        )
    return resolved


# --- symbol-level plan checks -----------------------------------------------


def _unique_symbols(entry_map: dict):
    seen = set()
    for entry in sorted(entry_map):
        for symbol in entry_map[entry]["symbols"]:
            if symbol["path"] not in seen:
                seen.add(symbol["path"])
                yield entry, symbol


def _cross_sites(resolved: dict, a: str, b: str):
    """Sites in b's files referencing symbols in a's write scope, split
    into (confident, ambiguous) edge descriptions."""
    b_files = set(resolved[b])
    confident, ambiguous = [], []
    for entry, symbol in _unique_symbols(resolved[a]):
        sites = [s for s in symbol["referenced_by"] if s["file"] in b_files]
        exact = sorted({(s["file"], s["line"]) for s in sites if not s.get("ambiguous")})
        fuzzy = sorted({(s["file"], s["line"]) for s in sites if s.get("ambiguous")})
        if exact:
            where = ", ".join(f"{f}:{line}" for f, line in exact)
            confident.append(f"{symbol['path']} ({entry}) referenced from {where}")
        elif fuzzy:
            where = ", ".join(f"{f}:{line}" for f, line in fuzzy)
            ambiguous.append(
                f"{symbol['path']} ({entry}) possibly referenced from {where}"
            )
    return confident, ambiguous


def _ancestors(plan: Plan, node_id: str) -> set:
    out, stack = set(), list(plan.nodes[node_id]["references"])
    while stack:
        nid = stack.pop()
        if nid not in out:
            out.add(nid)
            stack.extend(plan.nodes[nid]["references"])
    return out


def _owners(plan: Plan, path: str) -> list:
    return sorted(
        nid for nid, node in plan.nodes.items() if path in node["writes"]
    )


def consumed_interfaces(
    plan: Plan, code_index: dict, resolved: dict, node_id: str
) -> list:
    """Symbols outside the node's write scope that its files reference,
    tagged declared (owner is an ancestor) / undeclared / unowned."""
    write_files = set(resolved[node_id])
    ancestors = _ancestors(plan, node_id)
    seen = set()
    out = []
    for symbol in code_index["symbols"]:
        if symbol["file"] in write_files or symbol["path"] in seen:
            continue
        sites = [s for s in symbol["referenced_by"] if s["file"] in write_files]
        if not sites:
            continue
        seen.add(symbol["path"])
        owners = _owners(plan, symbol["file"])
        if not owners:
            tag, owner = "unowned", None
        elif any(o in ancestors for o in owners):
            tag = "declared"
            owner = next(o for o in owners if o in ancestors)
        else:
            tag, owner = "undeclared", owners[0]
        out.append({"symbol": symbol, "tag": tag, "owner": owner})
    return sorted(out, key=lambda c: c["symbol"]["path"])


def plan_checks(plan: Plan, code_index: dict, resolved: dict) -> list:
    findings: list[Finding] = []
    level_of = {
        nid: lv for lv, ids in plan.levels.items() for nid in ids
    }
    # E08 / W04 — same-level cross-references: the symbol-precision
    # read-write extension of E05. Confident sites are a compile error;
    # ambiguous-only sites assume an edge and serialize (W04 + JA1).
    for lv, ids in sorted(plan.levels.items()):
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                conf_ab, ambi_ab = _cross_sites(resolved, a, b)
                conf_ba, ambi_ba = _cross_sites(resolved, b, a)
                confident = conf_ab + conf_ba
                ambiguous = ambi_ab + ambi_ba
                if confident:
                    findings.append(
                        Finding(
                            "E08",
                            f"[E08] level {lv}: {a} and {b} cannot run in "
                            f"parallel: {'; '.join(confident)} — declare the "
                            "reference or restructure",
                            nodes=(a, b),
                        )
                    )
                elif ambiguous:
                    findings.append(
                        Finding(
                            "W04",
                            f"[W04] level {lv}: ambiguous edge between {a} and "
                            f"{b}: {'; '.join(ambiguous)} — assuming an edge; "
                            "serialized",
                            nodes=(a, b),
                        )
                    )
    # W02 — unresolvable regions: the node's true edge set is unknowable,
    # so it serializes against every same-level peer (enacted via JA1).
    unresolved_by_file: dict[str, list[dict]] = defaultdict(list)
    for record in code_index["unresolved"]:
        unresolved_by_file[record["file"]].append(record)
    for lv, ids in sorted(plan.levels.items()):
        for nid in ids:
            reasons = []
            for entry in sorted(resolved[nid]):
                records = unresolved_by_file.get(entry, [])
                low = any(
                    s["confidence"] == "low"
                    for s in resolved[nid][entry]["symbols"]
                )
                if records or low:
                    detail = (
                        ", ".join(
                            f"{u['reason']} at line {u['line']}" for u in records
                        )
                        or "low-confidence symbols"
                    )
                    reasons.append(f"{entry} ({detail})")
            if reasons:
                peers = [p for p in ids if p != nid]
                peer_note = (
                    f"; serialize against level-{lv} peers: {', '.join(peers)}"
                    if peers
                    else ""
                )
                findings.append(
                    Finding(
                        "W02",
                        f"[W02] {nid}: unresolvable region forces "
                        f"serialization: {'; '.join(reasons)}{peer_note}",
                        nodes=(nid,),
                    )
                )
    # W05 — consumption from a node that is neither an ancestor nor a
    # same-level peer: an edge the spec's ordering does not protect.
    for nid in sorted(plan.nodes):
        offenders = defaultdict(list)
        for consumed in consumed_interfaces(plan, code_index, resolved, nid):
            owner = consumed["owner"]
            if (
                consumed["tag"] == "undeclared"
                and owner is not None
                and level_of[owner] != level_of[nid]
            ):
                offenders[owner].append(consumed["symbol"]["path"])
        for owner in sorted(offenders):
            findings.append(
                Finding(
                    "W05",
                    f"[W05] {nid} (level {level_of[nid]}) consumes "
                    f"{', '.join(sorted(offenders[owner]))} owned by {owner} "
                    f"(level {level_of[owner]}) with no spec path between "
                    "them — the compiled order does not protect this edge",
                    nodes=(nid, owner),
                )
            )
    return findings


# --- the dispatch-safe plan (JA1) -------------------------------------------


def serialize_plan(plan: Plan, findings: list) -> AdjustedPlan:
    """Split levels so nothing the checks flagged runs in parallel. The
    printed plan is the safe plan; the warning text is its explanation."""
    conflicts = set()
    for finding in findings:
        if finding.code == "W02":
            (nid,) = finding.nodes
            lv = next(l for l, ids in plan.levels.items() if nid in ids)
            for peer in plan.levels[lv]:
                if peer != nid:
                    conflicts.add(frozenset((nid, peer)))
        elif finding.code == "W04":
            conflicts.add(frozenset(finding.nodes))
    adjusted = []
    for lv, ids in sorted(plan.levels.items()):
        sublevels: list[list[str]] = []
        for nid in ids:
            placed = False
            for sub in sublevels:
                if not any(frozenset((nid, other)) in conflicts for other in sub):
                    sub.append(nid)
                    placed = True
                    break
            if not placed:
                sublevels.append([nid])
        for i, sub in enumerate(sublevels):
            label = str(lv) if len(sublevels) == 1 else f"{lv}.{i}"
            adjusted.append((label, sub))
    digest = hashlib.sha256()
    for label, ids in adjusted:
        for nid in ids:
            writes = ",".join(sorted(plan.nodes[nid]["writes"]))
            digest.update(f"{label}|{nid}|{writes}\n".encode())
    return AdjustedPlan(levels=adjusted, plan_hash=digest.hexdigest()[:12])


# --- packet assembly --------------------------------------------------------


def _identity_section(role: str, identities_dir: Path) -> list:
    body = (Path(identities_dir) / f"{role}.md").read_text().rstrip()
    return [
        "## Identity  [provenance: fixed]",
        "",
        body,
        "",
        f"tools: {TOOLS[role]}   (v0 stub; generated from the hook manifest "
        "in a later phase)",
        "",
    ]


def _symbol_lines(symbol: dict, indent: str = "") -> list:
    lines = [
        f"{indent}- {symbol['path']}  [{symbol['kind']}, confidence "
        f"{symbol['confidence']}]  lines {symbol['start_line']}-{symbol['end_line']}",
        f"{indent}  signature: {symbol['signature'] or '(none)'}",
    ]
    if symbol["doc"]:
        doc = symbol["doc"].replace("\n", f"\n{indent}    ")
        lines.append(f"{indent}  doc: {doc}")
    return lines


def assemble_packet(
    plan: Plan,
    code_index: dict,
    resolved: dict,
    node_id: str,
    role: str,
    *,
    identities_dir,
) -> str:
    if node_id not in plan.nodes:
        raise JoinError(f"unknown node {node_id!r}")
    if role not in TOOLS:
        raise JoinError(f"unknown role {role!r} (executor|tester)")
    node = plan.nodes[node_id]
    ref = code_index["commit"] or "worktree (uncommitted, not replayable)"
    lines = _identity_section(role, identities_dir)

    lines += ["## Task  [provenance: spec, verbatim]", "", f"node: {node_id}"]
    if role == "tester":
        # P6/JA7: the tester's packet is the spec node's guarantees alone —
        # no one_liner, writes, open items, and no compiled state. The
        # implementation is structurally absent, not merely elided.
        lines.append("guarantees to verify (done_when):")
        lines += [f"  - {item}" for item in node["done_when"]]
        lines.append("")
        return _finish_packet(lines, plan, node_id, role, ref)

    lines.append(f"one_liner: {node['one_liner']}")
    lines.append("write scope (exhaustive — writing anything else is a violation):")
    lines += [f"  - {entry}" for entry in node["writes"]]
    if node.get("open"):
        lines.append("open (undecided — TODO, do not resolve by expanding scope):")
        lines += [f"  - {item}" for item in node["open"]]
    lines.append("")

    lines += [f"## State — compiled  [provenance: verified at {ref}]", ""]

    lines.append("### Write scope as it exists")
    for entry in node["writes"]:
        lines += ["", f"#### {entry}"]
        info = resolved[node_id][entry]
        if info["status"] == "to_create":
            lines.append(f"(does not exist at {ref} — you are creating this file)")
        elif info["status"] == "opaque":
            lines.append("(not a Python file — outside the index)")
        elif not info["symbols"]:
            lines.append("(exists; defines no symbols)")
        else:
            seen = set()
            for symbol in info["symbols"]:
                if symbol["path"] in seen:
                    continue
                seen.add(symbol["path"])
                lines += _symbol_lines(symbol)
    lines.append("")

    lines.append("### Interfaces you consume")
    consumed = consumed_interfaces(plan, code_index, resolved, node_id)
    listed = {c["symbol"]["path"] for c in consumed}
    surface = []
    for c in consumed:
        if c["tag"] == "declared":
            tag = f"[declared: {c['owner']}]"
        elif c["tag"] == "undeclared":
            tag = f"[UNDECLARED — owned by {c['owner']}, no spec path; spec-quality signal]"
        else:
            tag = "[unowned file]"
        surface.append((c["symbol"], tag))
    # Union in declared dependencies' surfaces so greenfield nodes still
    # see what exists (JA4).
    for dep in sorted(_ancestors(plan, node_id)):
        for entry in plan.nodes[dep]["writes"]:
            for _, symbol in _unique_symbols(
                {entry: resolved.get(dep, {}).get(entry, {"symbols": []})}
            ):
                if symbol["path"] not in listed:
                    listed.add(symbol["path"])
                    surface.append((symbol, f"[available: {dep}]"))
    if surface:
        for symbol, tag in sorted(surface, key=lambda s: s[0]["path"]):
            entry_lines = _symbol_lines(symbol)
            entry_lines[0] += f"  {tag}"
            lines += entry_lines
    else:
        lines.append("(none recorded)")
    lines.append("")

    lines.append("### Callers of your write scope")
    any_caller = False
    for entry in sorted(resolved[node_id]):
        for _, symbol in _unique_symbols({entry: resolved[node_id][entry]}):
            sites = [
                s
                for s in symbol["referenced_by"]
                if s["file"] not in set(resolved[node_id])
            ]
            for site in sorted(
                sites, key=lambda s: (s["file"], s["line"], s["in_symbol"])
            ):
                any_caller = True
                mark = " [ambiguous]" if site.get("ambiguous") else ""
                args = (
                    f" args=({', '.join(site['args'])})" if "args" in site else ""
                )
                lines.append(
                    f"- {symbol['path']} <- {site['file']}:{site['line']} "
                    f"in {site['in_symbol']}{args}{mark}"
                )
    if not any_caller:
        lines.append("(no recorded callers outside your scope)")
    lines.append("")

    lines.append("### Unresolved sites in scope")
    in_scope = [
        u for u in code_index["unresolved"] if u["file"] in set(resolved[node_id])
    ]
    if in_scope:
        lines.append(
            "These files are low confidence — assume an edge to everything here:"
        )
        for u in in_scope:
            lines.append(
                f"- {u['file']}:{u['line']}  {u['reason']}  {u['expression']}"
            )
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("### Coverage")
    lines.append(
        f"Compiled from an index of {len(code_index['files'])} files at {ref}. "
        f"This packet includes your write scope ({len(node['writes'])} entries), "
        f"{len(surface)} consumed/available interface symbols, and every "
        "recorded caller of your scope. Anything not listed was not searched. "
        "Missing means query (request_mem), never build. "
        "verify with: python -m pytest"
    )
    lines.append("")

    lines += [
        "## State — handoff  [provenance: agent-authored, claim not fact]",
        "",
        "(none for this dispatch)",
        "",
    ]
    return _finish_packet(lines, plan, node_id, role, ref)


def _finish_packet(lines, plan: Plan, node_id: str, role: str, ref: str) -> str:
    body = "\n".join(lines).rstrip("\n") + "\n"
    packet_hash = hashlib.sha256(body.encode()).hexdigest()[:12]
    trailer = (
        f"packet: node={node_id} role={role} commit={ref} "
        f"plan={plan.plan_hash} packet_hash={packet_hash}"
    )
    return body + trailer + "\n"


# --- CLI --------------------------------------------------------------------


def _cmd_plan(args) -> int:
    plan = load_plan(args.specs)
    index = build_index(args.repo, args.commit)
    resolved = resolve_writes(plan, index)
    findings = plan_checks(plan, index, resolved)
    adjusted = serialize_plan(plan, findings)
    ref = index["commit"] or "worktree (uncommitted)"
    print(f"index: {len(index['files'])} files at {ref}")
    print(f"spec plan hash: {plan.plan_hash}   dispatch plan hash: {adjusted.plan_hash}")
    print()
    print("dispatch-safe plan")
    for label, ids in adjusted.levels:
        print(f"  level {label}  ({len(ids)} parallel)")
        for nid in ids:
            statuses = {
                entry: resolved[nid][entry]["status"] for entry in sorted(resolved[nid])
            }
            notes = [e for e, s in statuses.items() if s != "indexed"]
            note = f"  [{', '.join(f'{e}: {statuses[e]}' for e in notes)}]" if notes else ""
            print(f"    - {nid}{note}")
    if findings:
        print(f"\n{len(findings)} findings")
        for finding in findings:
            print(f"  {finding.message}")
    return 1 if any(f.is_error for f in findings) else 0


def _cmd_packet(args) -> int:
    commit = None if args.worktree else (args.commit or "HEAD")
    plan = load_plan(args.specs)
    index = build_index(args.repo, commit)
    resolved = resolve_writes(plan, index)
    packet = assemble_packet(
        plan,
        index,
        resolved,
        args.node,
        args.role,
        identities_dir=Path(args.specs).parent / "identities",
    )
    if args.output:
        Path(args.output).write_text(packet, encoding="utf-8")
        print(f"packet -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(packet)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.join",
        description="Resolve a spec against the symbol index; assemble context packets.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="compile + resolve + symbol-level checks")
    p_plan.add_argument("--specs", default="harness/specs")
    p_plan.add_argument("--repo", default=".")
    p_plan.add_argument("--commit", default=None)
    p_plan.set_defaults(func=_cmd_plan)

    p_packet = sub.add_parser("packet", help="assemble one context packet")
    p_packet.add_argument("node")
    p_packet.add_argument("--role", default="executor", choices=sorted(TOOLS))
    p_packet.add_argument("--specs", default="harness/specs")
    p_packet.add_argument("--repo", default=".")
    p_packet.add_argument(
        "--commit", default=None, help="rev to compile from (default HEAD)"
    )
    p_packet.add_argument(
        "--worktree",
        action="store_true",
        help="compile from the uncommitted worktree (stamped not replayable)",
    )
    p_packet.add_argument("-o", "--output", default=None)
    p_packet.set_defaults(func=_cmd_packet)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (JoinError, speccc.SpecError) as exc:
        print(f"join: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
