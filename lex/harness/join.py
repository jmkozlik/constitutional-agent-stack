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
import os
import posixpath
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from analyzer.gitio import GitError
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
    meta: dict = field(default_factory=dict)


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
    specs = Path(specs_dir)
    if not specs.is_dir():
        raise JoinError(f"specs dir {str(specs)!r} does not exist")
    if not sorted(specs.glob("*.yaml")):
        raise JoinError(f"specs dir {str(specs)!r} contains no *.yaml files")
    nodes, origin, meta = speccc.load(str(specs_dir))
    index = speccc.validate(nodes, origin)
    # speccc validates field types but not element types; a non-string
    # writes entry would traceback deep in plan_hash otherwise.
    for nid, node in index.items():
        for fieldname in ("references", "writes", "done_when", "open"):
            for item in node.get(fieldname) or []:
                if not isinstance(item, str):
                    raise JoinError(
                        f"[E01] {nid}: {fieldname} entry {item!r} is not a string"
                    )
        surface = node.get("surface")
        if surface is not None:
            for key, entries in surface.items():
                if key not in ("callables", "types", "errors"):
                    raise JoinError(
                        f"[E01] {nid}: unknown surface section {key!r} "
                        "(callables|types|errors)"
                    )
                if not isinstance(entries, list):
                    raise JoinError(
                        f"[E01] {nid}: surface.{key} must be a list"
                    )
                for item in entries:
                    if isinstance(item, dict):
                        raise JoinError(
                            f"[E01] {nid}: surface.{key} entry {item!r} was "
                            "parsed as a mapping — quote entries containing "
                            "': '"
                        )
                    if not isinstance(item, str):
                        raise JoinError(
                            f"[E01] {nid}: surface.{key} entry {item!r} is "
                            "not a string"
                        )
    speccc.resolve(index)
    speccc.find_cycle(index)
    levels = speccc.levelize(index)
    speccc.check_writes(index, levels)
    return Plan(
        nodes=index,
        levels={lv: list(ids) for lv, ids in levels.items()},
        plan_hash=speccc.plan_hash(index, levels),
        meta=meta,
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
            # Classification and every downstream map use the NORMALIZED
            # path: git paths are always normalized, so './core/base.py'
            # must mean core/base.py, not a phantom new file.
            norm = posixpath.normpath(entry)
            if posixpath.isabs(entry) or norm.startswith("..") or norm in ("", "."):
                errors.append(
                    f"[E06] {nid}: writes entry '{entry}' is not a "
                    "repo-relative file path"
                )
                continue
            if norm in known_files:
                node_map[norm] = {
                    "status": "indexed",
                    "symbols": sorted(
                        by_file.get(norm, []),
                        key=lambda s: (s["path"], s["start_line"], s["sig_hash"]),
                    ),
                }
            elif norm.endswith(".py"):
                node_map[norm] = {"status": "to_create", "symbols": []}
            else:
                node_map[norm] = {"status": "opaque", "symbols": []}
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
        nid
        for nid, node in plan.nodes.items()
        if path in (posixpath.normpath(w) for w in node["writes"])
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
        out.append(
            {
                "symbol": symbol,
                "tag": tag,
                "owner": owner,
                # Truthful provenance: an edge known only through the
                # resolver's name-match fallback is a claim, not a fact.
                "ambiguous": all(s.get("ambiguous") for s in sites),
            }
        )
    return sorted(out, key=lambda c: c["symbol"]["path"])


def plan_checks(plan: Plan, code_index: dict, resolved: dict) -> list:
    findings: list[Finding] = []
    level_of = {
        nid: lv for lv, ids in plan.levels.items() for nid in ids
    }
    # E05 at normalized precision — speccc compares raw spec strings, so
    # aliased spellings of one file ('core/base.py' vs './core/base.py')
    # slip past it; after normalization they must still collide.
    for lv, ids in sorted(plan.levels.items()):
        owners = defaultdict(list)
        for nid in ids:
            for entry in resolved[nid]:
                owners[entry].append(nid)
        for entry, who in sorted(owners.items()):
            if len(who) > 1:
                findings.append(
                    Finding(
                        "E05",
                        f"[E05] level {lv}: {' and '.join(sorted(who))} both "
                        f"write '{entry}' (normalized)",
                        nodes=tuple(sorted(who)),
                    )
                )
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
                offenders[owner].append(
                    (consumed["symbol"]["path"], consumed["ambiguous"])
                )
        for owner in sorted(offenders):
            confident = sorted(p for p, ambi in offenders[owner] if not ambi)
            ambiguous = sorted(p for p, ambi in offenders[owner] if ambi)
            phrases = []
            if confident:
                phrases.append(f"consumes {', '.join(confident)}")
            if ambiguous:
                # Honesty bit survives into the warning: a name-match edge
                # is a claim, not a fact (P3, Appendix B).
                phrases.append(
                    f"possibly consumes {', '.join(ambiguous)} "
                    "(ambiguous attribution)"
                )
            findings.append(
                Finding(
                    "W05",
                    f"[W05] {nid} (level {level_of[nid]}) {'; '.join(phrases)} "
                    f"owned by {owner} (level {level_of[owner]}) with no spec "
                    "path between them — the compiled order does not protect "
                    "this edge",
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


# --- the compiled delta (spec format v0.2) ----------------------------------


def _parse_surface(entry: str) -> tuple:
    """'pkg.mod.fn(x: int) -> int' -> ('pkg.mod.fn', '(x: int) -> int')."""
    paren = entry.find("(")
    if paren < 0:
        return entry.strip(), None
    return entry[:paren].strip(), entry[paren:].strip()


def _anchor_terminal(entry: str) -> str:
    """The terminal name a surface entry declares, cutting at the first of
    the shapes an entry can take. speccc's anchor check already cuts this
    way; packet assembly disagreed, which is how prose lines leaked."""
    text, _ = _split_provenance(entry)
    cuts = [text.find(sep) for sep in ("(", " ∈ ", " = ", ": ")]
    cuts = [i for i in cuts if i >= 0]
    subject = text[: min(cuts)] if cuts else text
    return subject.strip().rsplit(".", 1)[-1]


def _surface_sections(node: dict) -> tuple:
    surface = node.get("surface") or {}
    return (
        surface.get("callables") or [],
        surface.get("types") or [],
        surface.get("errors") or [],
    )


_PROVENANCE = re.compile(r"\s*\[(seeded|authored)\]\s*$")


def _split_provenance(entry: str) -> tuple:
    """Format v0.4: every surface line is marked seeded | authored. Only
    seeded lines participate in the byte-for-byte no-invention proof;
    authored lines are contract — the tester's fixtures verify them, the
    delta cannot. Unmarked lines default to seeded."""
    match = _PROVENANCE.search(entry)
    if match:
        return entry[: match.start()].strip(), match.group(1)
    return entry.strip(), "seeded"


AUTHORED_STATUS = "authored (contract — tester-verified, delta-exempt)"


def _subject_in_scope(subject: str, scope_files: set) -> bool:
    """Does a dotted subject live in one of the node's own write-scope
    files? Tries successively shorter module prefixes so Class.method
    subjects resolve to their defining module."""
    parts = subject.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        stem = "/".join(parts[:cut])
        if f"{stem}.py" in scope_files or f"{stem}/__init__.py" in scope_files:
            return True
    return False


def _authored_status(
    text: str, by_path: dict, *, scope_files=None, section: str = ""
) -> str:
    """F20 (ratified, from 3b's D2 filing): an authored line whose subject
    is <DeclaredType>.<attr> makes a STRUCTURAL claim and presence-checks
    — 'present' or 'absent' (absent counts outstanding). Behavioral and
    non-structural authored lines remain exempt; the attestation channel
    is the backstop, as 3b demonstrated.

    Ratified extension (report 005's flagged mechanism question, answered
    YES): an authored CALLABLE line whose dotted subject lies inside the
    node's OWN write scope also presence-checks by name — absent until
    built. Callables outside the write scope stay behavioral: the node
    does not own them and cannot be held to their existence."""
    cuts = [(text.find(sep), sep) for sep in ("(", " ∈ ", ": ")]
    cuts = [(i, s) for i, s in cuts if i >= 0]
    if cuts:
        i, sep = min(cuts)
        if sep == "(":
            subject = text[:i].strip()
            if (
                section == "callables"
                and scope_files
                and _subject_in_scope(subject, scope_files)
            ):
                return "present" if subject in by_path else "absent"
            return AUTHORED_STATUS  # callable outside own scope: behavioral
        subject = text[:i].strip()
    else:
        subject = text.strip()
    owner, _, name = subject.rpartition(".")
    owner_is_class = any(
        r["kind"] == "class" for r in by_path.get(owner, [])
    )
    if not owner_is_class:
        return AUTHORED_STATUS  # bare type / module prose: behavioral
    if subject in by_path:
        return "present"  # property or method record
    for record in by_path.get(owner, []):
        if record["kind"] == "class" and any(
            f == name or f.startswith(f"{name}:") or f.startswith(f"{name} ")
            for f in record.get("fields") or []
        ):
            return "present"
    return "absent"


def _is_alias_entry(entry: str) -> bool:
    """`pkg.mod.Name = expr` — a module-level alias, not a class shape."""
    head = entry.split(" = ", 1)[0]
    return " = " in entry and "(" not in head


def _init_field_list(by_path: dict, class_path: str) -> str | None:
    """A constructor-shaped type's field list: the __init__ signature minus
    self (classes whose state is init-assigned have no class-body fields to
    seed from, but the index carries their __init__ record — I2)."""
    for record in by_path.get(f"{class_path}.__init__", []):
        signature = record["signature"]
        head, _, rest = signature.partition(" -> ")
        inner = head.strip()[1:-1]  # drop parens
        params = inner.split(", ")
        if params and params[0] == "self":
            params = params[1:]
        return f"({', '.join(params)})"
    return None


def _match_type_entry(entry: str, by_path: dict) -> str:
    if _is_alias_entry(entry):
        return "unindexed (module-level alias; brief open question)"
    path, field_sig = _parse_surface(entry)
    records = [r for r in by_path.get(path, []) if r["kind"] == "class"]
    if not records:
        return "absent"
    if field_sig is None:
        return "present"
    for record in records:
        rendered = f"({', '.join(record.get('fields') or [])})"
        if field_sig == rendered:
            return "present"
    init_rendered = _init_field_list(by_path, path)
    if init_rendered is not None and field_sig == init_rendered:
        return "present"
    return "shape-mismatch"


def _match_error_entry(entry: str, by_path: dict) -> str:
    # First ': ' splits observable from condition — condition prose may
    # itself contain colons (I3).
    path = entry.split(": ", 1)[0].strip()
    if path in by_path:
        return "present"
    owner, _, name = path.rpartition(".")
    for record in by_path.get(owner, []):
        if record["kind"] == "class" and any(
            f == name or f.startswith(f"{name}:") or f.startswith(f"{name} ")
            for f in record.get("fields") or []
        ):
            return "present"
    return "absent"


def compute_delta(
    plan: Plan, code_index: dict, resolved: dict, node_id: str, *, repo=None
) -> dict:
    """The work statement, compiled at dispatch from surface x index —
    never spec-authored, never handoff-carried (format v0.2). The spec
    stays a declarative end-state; the delta is the distance between
    that end-state and the pinned commit."""
    node = plan.nodes[node_id]
    writes_delta = []
    for entry, info in resolved[node_id].items():
        if info["status"] == "to_create":
            writes_delta.append((entry, "to_create"))
        elif info["status"] == "opaque":
            writes_delta.append((entry, "opaque (not indexed)"))
        else:
            source = _source_of(repo, code_index["commit"], entry)
            if source is None:
                writes_delta.append((entry, "exists"))
            else:
                digest = hashlib.sha256(source.encode()).hexdigest()[:8]
                writes_delta.append((entry, f"exists@{digest}"))
    by_path: dict[str, list[dict]] = defaultdict(list)
    for info in resolved[node_id].values():
        for record in info["symbols"]:
            by_path[record["path"]].append(record)
    scope_files = set(resolved[node_id])
    callables, types, errors = _surface_sections(node)
    callables_delta = []
    for entry in callables:
        text, provenance = _split_provenance(entry)
        if provenance == "authored":
            callables_delta.append((
                entry,
                _authored_status(
                    text, by_path, scope_files=scope_files, section="callables"
                ),
            ))
            continue
        path, signature = _parse_surface(text)
        records = by_path.get(path, [])
        if not records:
            status = "absent"
        elif signature is None or any(
            r["signature"] == signature for r in records
        ):
            status = "present"
        else:
            status = "signature-mismatch"
        callables_delta.append((entry, status))
    types_delta = []
    for entry in types:
        text, provenance = _split_provenance(entry)
        if provenance == "authored":
            types_delta.append((entry, _authored_status(text, by_path)))
        else:
            types_delta.append((entry, _match_type_entry(text, by_path)))
    errors_delta = []
    for entry in errors:
        text, provenance = _split_provenance(entry)
        if provenance == "authored":
            errors_delta.append((entry, _authored_status(text, by_path)))
        else:
            errors_delta.append((entry, _match_error_entry(text, by_path)))
    def counts(status):
        return status not in ("present", AUTHORED_STATUS) and not status.startswith(
            "unindexed"
        )

    outstanding = (
        [e for e, s in writes_delta if s == "to_create"]
        + [e for e, s in callables_delta if counts(s)]
        + [e for e, s in types_delta if counts(s)]
        + [e for e, s in errors_delta if counts(s)]
    )
    verifiable = [
        s
        for _, s in callables_delta + types_delta + errors_delta
        if s != AUTHORED_STATUS and not s.startswith("unindexed")
    ]
    if not callables_delta:
        kind = "no_surface"
    elif (
        all(s == "to_create" for _, s in writes_delta)
        and verifiable
        and all(s == "absent" for s in verifiable)
    ):
        kind = "full"
    elif not outstanding:
        kind = "empty"
    else:
        kind = "partial"
    return {
        "writes": writes_delta,
        "callables": callables_delta,
        "types": types_delta,
        "errors": errors_delta,
        "outstanding": outstanding,
        "kind": kind,
    }


_DELTA_VERDICT = {
    "empty": "=> empty delta — validation-only dispatch",
    "full": "=> full delta — greenfield build",
    "no_surface": "=> delta not computable: node declares no surface (W06)",
}


def _delta_lines(delta: dict) -> list:
    lines = [
        "delta [compiled at dispatch from surface x index — surface is what "
        "makes the delta computable; it is never spec-authored and never "
        "handoff-carried]:"
    ]
    lines += ["  writes:"] + [f"    - {e}: {s}" for e, s in delta["writes"]]
    for section in ("callables", "types", "errors"):
        if delta[section]:
            lines += [f"  {section}:"] + [
                f"    - {e}: {s}" for e, s in delta[section]
            ]
    verdict = _DELTA_VERDICT.get(delta["kind"])
    if verdict is None:
        verdict = (
            f"=> {len(delta['outstanding'])} outstanding: "
            + ", ".join(delta["outstanding"])
        )
    lines.append(f"  {verdict}")
    return lines


def delta_summary(delta: dict) -> str:
    if delta["kind"] == "empty":
        return "delta: empty (validation-only)"
    if delta["kind"] == "full":
        return "delta: full (greenfield)"
    if delta["kind"] == "no_surface":
        return "delta: not computable (no surface)"
    return f"delta: {len(delta['outstanding'])} outstanding"


# --- packet assembly --------------------------------------------------------


def _render_surface(plan: Plan, node_id: str, role: str = "executor") -> list:
    """The three surface subsections, with foreign types resolved from
    their owning node's surface at packet build (I5): any other node's
    type whose terminal name appears in this node's entries rides along,
    labeled with its owner."""
    node = plan.nodes[node_id]
    callables, types, errors = _surface_sections(node)
    if not (callables or types or errors):
        return []
    own_text = " ".join(callables + types)
    foreign = []
    # Ruled containment: a tester packet's type and callable lines are a
    # subset of its OWN node's surface. Foreign ride-along (I5) is an
    # executor affordance; for the blind role it is a containment hole.
    for other in [] if role == "tester" else sorted(plan.nodes):
        if other == node_id:
            continue
        _, other_types, _ = _surface_sections(plan.nodes[other])
        for entry in other_types:
            terminal = _anchor_terminal(entry)
            # An empty terminal used to compile to \b\b, which matches any
            # text — so a prose types line rode into every node's packet.
            if not terminal or entry in types:
                continue
            if re.search(rf"\b{re.escape(terminal)}\b", own_text):
                foreign.append(f"    - {entry}  [from {other}]")
    lines = ["  callables:"]
    lines += [f"    - {e}" for e in callables] or ["    (none declared)"]
    lines.append("  types:")
    lines += ([f"    - {e}" for e in types] + foreign) or ["    (none declared)"]
    lines.append("  errors:")
    lines += [f"    - {e}" for e in errors] or ["    (none declared)"]
    return lines


# F3 (ratified): the artifact contract and request_mem shape live in the
# packet's protocol section — dispatch prompts stop carrying law the
# packet should own. Frozen per role, like identity.
PROTOCOL = {
    "executor": [
        "Deliverables (files, harvested before teardown):",
        "  .harness/out/attestation.md — one section per done_when bullet,",
        "    headed ATTEST or FILE, each with verbatim command+output evidence.",
        "  .harness/out/defects.md — every filed defect: what it is filed",
        "    against, the evidence, what a fix would require. If none: none",
        "  .harness/scratch/handoff.md — working state for your replacement;",
        "    verified facts and interpretive claims marked separately.",
        "Scratch: .harness/scratch/ (throwaway fixtures, notes).",
        "request_mem (v0 shape): a report line \"REQUEST_MEM: <what and why>\".",
        "  Blocking: stop and return your report carrying the lines — the",
        "  dispatcher answers and resumes you. Non-blocking: log and continue.",
        "  Never guess past a miss; never read around it.",
        "Fence: writes outside your write scope, .harness/scratch/, and",
        "  .harness/out/ are violations. On a denial, record it verbatim;",
        "  do not work around.",
        "Seeded vs authored (ratified): an [authored] line naming an",
        "  attribute of a [seeded] type authorises you to add exactly that",
        "  attribute. The [seeded] line reseeds byte-for-byte after the work",
        "  lands. The two lines are not in conflict; the authored one leads.",
    ],
    "tester": [
        "Deliverables (files, harvested before teardown):",
        "  .harness/out/tests/ — your fixtures and tests, runnable as written.",
        "  .harness/out/tester_report.md — one section per guarantee: the",
        "    discriminating fixture, its expected-now verdict (pass |",
        "    fail-first), and any guarantee filed as untestable, with evidence.",
        "  .harness/scratch/handoff.md — working state for your replacement.",
        "Scratch: .harness/scratch/.",
        "request_mem (v0 shape): a report line \"REQUEST_MEM: <what and why>\";",
        "  blocking: stop and return; non-blocking: log and continue.",
        "The implementation is structurally absent from your packet (P6).",
        "  Tests invoke only the declared surface. Inventing an interface is",
        "  a failure even when the guess would match.",
        "Seeded vs authored (ratified): where an [authored] line names an",
        "  attribute a [seeded] type's field list does not carry, the",
        "  authored line leads — the attribute is contract, due to exist,",
        "  and is not a spec contradiction to file.",
    ],
}

# F21 (ratified): the tester's trigger catalog, compiled from SPEC content
# only — the brief §3 reason/shape table plus the ratified additions. P6
# untouched: nothing here derives from implementation.
TRIGGER_CATALOG = [
    ("subscript_call", "TABLE[key](...)"),
    ("getattr_call", "getattr(obj, name)(...)  — and bare getattr(obj, name)"),
    ("attribute_of_call", "factory()(...)"),
    ("star_import", "from x import *  (anywhere in the file)"),
    ("dynamic_attribute", "setattr(...) / def __getattr__ / __getattr__ = fn"),
    ("parse_error", "the file does not parse at the rev"),
    ("unresolved_import_target", "a from-import unresolvable through a star-importing module"),
]


def _protocol_section(role: str) -> list:
    return (
        ["## Protocol  [provenance: fixed]", ""]
        + PROTOCOL[role]
        + [""]
    )


def tester_containment(plan: Plan, code_index: dict, resolved: dict, *,
                       identities_dir, repo=None) -> list:
    """Ruled standing gate line: every tester packet's type and callable
    lines are a subset of that node's OWN surface. Returns violations —
    (node, offending line) — so a gate run asserts the class, not just the
    instance F33 fixed."""
    violations = []
    for node_id in sorted(plan.nodes):
        node = plan.nodes[node_id]
        callables, types, _ = _surface_sections(node)
        own = {entry.strip() for entry in callables + types}
        packet = assemble_packet(
            plan, code_index, resolved, node_id, "tester",
            identities_dir=identities_dir, repo=repo,
        )
        try:
            block = packet.split("surface (the only thing your tests may invoke):", 1)[1]
        except IndexError:
            continue
        block = block.split("guarantees to verify", 1)[0]
        section = None
        for raw in block.splitlines():
            line = raw.strip()
            if line in ("callables:", "types:", "errors:"):
                section = line[:-1]
                continue
            if not line.startswith("- ") or section == "errors":
                continue
            entry = line[2:].strip()
            if entry == "(none declared)":
                continue
            if entry not in own:
                violations.append((node_id, entry))
    return violations


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


def _source_of(repo, commit, rel_path: str) -> str | None:
    if repo is None:
        return None
    if commit:
        try:
            from analyzer import gitio

            return gitio.read_files(repo, commit, [rel_path])[rel_path].decode(
                errors="replace"
            )
        except GitError:
            return None
    try:
        return (Path(repo) / rel_path).read_text(errors="replace")
    except OSError:
        return None


def assemble_packet(
    plan: Plan,
    code_index: dict,
    resolved: dict,
    node_id: str,
    role: str,
    *,
    identities_dir,
    repo=None,
    handoff: str | None = None,
    handoff_path: str | None = None,
) -> str:
    if node_id not in plan.nodes:
        raise JoinError(f"unknown node {node_id!r}")
    if role not in TOOLS:
        raise JoinError(f"unknown role {role!r} (executor|tester)")
    node = plan.nodes[node_id]
    ref = code_index["commit"] or "worktree (uncommitted, not replayable)"
    # The trailer must identify the dispatch-safe structure this packet
    # belongs to (JA1), not the pre-adjustment spec levels.
    dispatch_hash = serialize_plan(
        plan, plan_checks(plan, code_index, resolved)
    ).plan_hash
    lines = _identity_section(role, identities_dir) + _protocol_section(role)

    lines += ["## Task  [provenance: spec, verbatim]", "", f"node: {node_id}"]
    if plan.meta.get("language"):
        lines.append(f"language: {plan.meta['language']}")
    # Proposal B (ratified): the observation channel, spec-level so it binds
    # every node at once — both probes split on whether a guarantee asserts
    # against the returned value or against rendered text.
    if plan.meta.get("observed_through"):
        lines.append(f"observed_through: {plan.meta['observed_through']}")
    surface_lines = _render_surface(plan, node_id, role)
    if role == "tester":
        # P6/JA7 + v0.2: the tester's packet is the spec node's guarantees
        # plus the declared surface — the one sanctioned seam through which
        # done_when is tested. No writes, no open items, no compiled state:
        # the implementation is structurally absent, not merely elided.
        if surface_lines:
            lines.append("surface (the only thing your tests may invoke):")
            lines += surface_lines
        lines.append(
            "trigger catalog [provenance: spec — brief §3 reason/shape table "
            "+ ratified additions]:"
        )
        for reason, shape in TRIGGER_CATALOG:
            lines.append(f"  {reason:<26} {shape}")
        _, type_entries, _ = _surface_sections(node)
        for entry in type_entries:
            text, _prov = _split_provenance(entry)
            if "importer set" in text:
                lines.append("importer set (ratified definition):")
                lines.append(f"  {text}")
        lines.append("guarantees to verify (done_when):")
        lines += [f"  - {item}" for item in node["done_when"]]
        lines.append("")
        return _finish_packet(lines, dispatch_hash, node_id, role, ref)

    lines.append(f"one_liner: {node['one_liner']}")
    lines.append("write scope (exhaustive — writing anything else is a violation):")
    lines += [f"  - {entry}" for entry in node["writes"]]
    if surface_lines:
        lines.append("surface (the exported contract done_when is tested through):")
        lines += surface_lines
    if node.get("open"):
        lines.append("open (undecided — TODO, do not resolve by expanding scope):")
        lines += [f"  - {item}" for item in node["open"]]
    # Ruling v0.3 clause 1: done_when routes to the executor verbatim,
    # directly above the DELTA block — the checklist a validation-only
    # dispatch attests or files against. Supersedes JA7 for done_when only.
    lines.append(
        "done_when (attest against, or file against, on a validation-only "
        "dispatch):"
    )
    lines += [f"  - {item}" for item in node["done_when"]]
    lines += [""] + _delta_lines(
        compute_delta(plan, code_index, resolved, node_id, repo=repo)
    )
    lines.append("")

    lines += [f"## State — compiled  [provenance: verified at {ref}]", ""]

    lines.append("### Write scope as it exists")
    for entry in resolved[node_id]:
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
        # You are MODIFYING these files: signatures alone are not enough
        # to edit against (packet-sufficiency probe finding).
        if info["status"] == "indexed":
            source = _source_of(repo, code_index["commit"], entry)
            if source is not None:
                lines.append("")
                lines.append(f"source (verbatim at {ref}):")
                for i, line in enumerate(source.splitlines(), start=1):
                    lines.append(f"  {i:>4}  {line}")
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
        if c["ambiguous"]:
            tag += " [ambiguous attribution — edge known only by name match]"
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
        "verify with: .venv/bin/python -m pytest"
    )
    lines.append("")

    lines += [
        "## State — handoff  [provenance: agent-authored, claim not fact]",
        "",
    ]
    # The channel ARCHITECTURE (2) specified and nothing ever populated:
    # a resumed dispatch reads its predecessor's state and the answers to
    # the questions it stopped on, instead of rediscovering both.
    # F36 (candidate 1): a handoff read from a repo-relative path AT THE
    # PINNED COMMIT is part of what replay rebuilds from, so a packet
    # carrying one stays reproducible. A handoff passed as raw text is not,
    # and is what broke the guarantee in the first place.
    if handoff_path:
        handoff = _source_of(repo, code_index["commit"], handoff_path)
        if handoff is None:
            raise JoinError(
                f"handoff {handoff_path!r} is not readable at "
                f"{code_index['commit'] or 'the worktree'} — a handoff must be "
                "committed before the packet is built, or the packet cannot "
                "be replayed (F36)"
            )
    lines += (handoff.rstrip().splitlines() if handoff else
              ["(none for this dispatch)"])
    lines.append("")
    return _finish_packet(lines, dispatch_hash, node_id, role, ref)


def _finish_packet(
    lines, dispatch_hash: str, node_id: str, role: str, ref: str
) -> str:
    body = "\n".join(lines).rstrip("\n") + "\n"
    packet_hash = hashlib.sha256(body.encode()).hexdigest()[:12]
    trailer = (
        f"packet: node={node_id} role={role} commit={ref} "
        f"plan={dispatch_hash} packet_hash={packet_hash}"
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
            summary = delta_summary(
                compute_delta(plan, index, resolved, nid, repo=args.repo)
            )
            print(f"    - {nid}{note}  [{summary}]")
    warns = speccc.warnings(plan.nodes)
    if findings or warns:
        print(f"\n{len(findings) + len(warns)} findings")
        for finding in findings:
            print(f"  {finding.message}")
        for warn in warns:
            print(f"  {warn}")
    return 1 if any(f.is_error for f in findings) else 0


def _cmd_packet(args) -> int:
    commit = None if args.worktree else (args.commit or "HEAD")
    plan = load_plan(args.specs)
    index = build_index(args.repo, commit)
    resolved = resolve_writes(plan, index)
    errors = [f for f in plan_checks(plan, index, resolved) if f.is_error]
    if errors:
        # A spec that fails compile must not hand out packets for the
        # conflicting nodes (JD5: exit 1 on any E-grade).
        for finding in errors:
            print(f"join: {finding.message}", file=sys.stderr)
        return 1
    packet = assemble_packet(
        plan,
        index,
        resolved,
        args.node,
        args.role,
        identities_dir=Path(args.specs).parent / "identities",
        repo=args.repo,
    )
    if args.output:
        Path(args.output).write_text(packet, encoding="utf-8")
        print(f"packet -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(packet)
    return 0


def _cmd_replay(args) -> int:
    """F19: the standing replay check as a first-class verdict.

    Rebuilds the packet at the pinned commit and compares byte-for-byte
    against the shipped packet. Verdicts are disjoint: IDENTICAL (exit 0),
    DIVERGED (exit 1), CHECK-ERROR (exit 2). A missing or unreadable
    input is an error state, never a divergence.

    F23 (ratified, candidate one): replay pins the JOIN VERSION as well as
    the spec. The whole tree at the recorded commit is exported and the
    rebuild runs from THAT commit's own harness/analyzer code. Otherwise a
    later change to the packet format makes every previously-correct packet
    report DIVERGED, conflating 'the packet was wrong' with 'the compiler
    moved on'. Only the git object store is shared — the repo argument
    supplies the blobs to index at that commit."""
    import difflib
    import subprocess as _sp
    import tempfile

    try:
        shipped = Path(args.shipped).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"CHECK-ERROR: cannot read shipped packet: {exc}", file=sys.stderr)
        return 2
    try:
        from analyzer import gitio

        sha = gitio.resolve_commit(args.repo, args.commit)
        tree_paths = gitio._git(
            args.repo, "ls-tree", "-r", "--name-only", "--full-tree", sha
        ).decode().splitlines()
        if not any(p.startswith("harness/specs/") and p.endswith(".yaml")
                   for p in tree_paths):
            print(
                f"CHECK-ERROR: no harness/specs/*.yaml at {sha[:12]} — "
                "replay requires the spec to be committed",
                file=sys.stderr,
            )
            return 2
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = _sp.run(
                ["git", "-C", str(args.repo), "archive", sha],
                capture_output=True, check=True,
            ).stdout
            _sp.run(["tar", "-x", "-C", str(root)], input=archive, check=True)
            proc = _sp.run(
                [sys.executable, "-m", "harness.join", "packet", args.node,
                 "--role", args.role, "--commit", sha,
                 "--repo", str(Path(args.repo).resolve()),
                 "--specs", str(root / "harness" / "specs")],
                capture_output=True, text=True, cwd=str(root),
                env={**os.environ, "PYTHONPATH": str(root)},
            )
            if proc.returncode != 0:
                print(
                    "CHECK-ERROR: rebuild at the pinned join version failed: "
                    f"{proc.stderr.strip()}",
                    file=sys.stderr,
                )
                return 2
            rebuilt = proc.stdout
    except (JoinError, speccc.SpecError, GitError, OSError,
            _sp.CalledProcessError) as exc:
        print(f"CHECK-ERROR: rebuild failed: {exc}", file=sys.stderr)
        return 2
    if rebuilt == shipped:
        print(f"IDENTICAL  node={args.node} role={args.role} commit={sha[:12]}")
        return 0
    print(f"DIVERGED  node={args.node} role={args.role} commit={sha[:12]}")
    diff = difflib.unified_diff(
        shipped.splitlines(keepends=True),
        rebuilt.splitlines(keepends=True),
        fromfile="shipped", tofile="rebuilt",
    )
    sys.stdout.writelines(list(diff)[:40])
    return 1


def _cmd_record(args) -> int:
    """3c: the dispatch-record emitter. Composes the record from the real
    artifacts — packet trailer, fence bytes, recomputed plan hashes — and
    cross-checks them against the stated dispatch. Retires MANUAL."""
    import json as _json
    from datetime import datetime

    packet_text = Path(args.packet).read_text(encoding="utf-8")
    trailer = packet_text.rstrip("\n").rsplit("\n", 1)[-1]
    fields = dict(
        part.split("=", 1) for part in trailer.replace("packet: ", "").split(" ")
        if "=" in part
    )
    from analyzer import gitio

    sha = gitio.resolve_commit(args.repo, args.commit)
    if fields.get("node") != args.node or fields.get("role") != args.role \
            or fields.get("commit") != sha:
        print(
            "record: trailer mismatch — packet says "
            f"node={fields.get('node')} role={fields.get('role')} "
            f"commit={fields.get('commit', '')[:12]}, dispatch says "
            f"node={args.node} role={args.role} commit={sha[:12]}",
            file=sys.stderr,
        )
        return 1
    fence_bytes = Path(args.fence).read_bytes()
    fence = _json.loads(fence_bytes)
    plan = load_plan(args.specs)
    index = build_index(args.repo, sha)
    resolved = resolve_writes(plan, index)
    dispatch = serialize_plan(plan, plan_checks(plan, index, resolved))
    started = datetime.fromisoformat(args.started)
    finished = datetime.fromisoformat(args.finished)
    record = {
        "record": "dispatch",
        "generator": "harness.join record/1",
        "dispatch_id": args.dispatch_id,
        "node": args.node,
        "role": args.role,
        "commit": sha,
        "spec_plan_hash": plan.plan_hash,
        "dispatch_plan_hash": dispatch.plan_hash,
        "packet_hash": fields.get("packet_hash"),
        "fence_sha256": hashlib.sha256(fence_bytes).hexdigest(),
        "fence_allowed": fence.get("allowed"),
        "started": args.started,
        "finished": args.finished,
        "wall_clock_seconds": int((finished - started).total_seconds()),
        "tokens": {"output": args.tokens_out, "input_incl_cache": args.tokens_in},
    }
    out = _json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"record -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
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

    p_replay = sub.add_parser(
        "replay", help="rebuild a packet at its pinned commit and compare"
    )
    p_replay.add_argument("node")
    p_replay.add_argument("--role", default="executor", choices=sorted(TOOLS))
    p_replay.add_argument("--repo", default=".")
    p_replay.add_argument("--commit", required=True)
    p_replay.add_argument("--shipped", required=True)
    p_replay.set_defaults(func=_cmd_replay)

    p_record = sub.add_parser("record", help="emit the dispatch record from artifacts")
    p_record.add_argument("node")
    p_record.add_argument("--role", default="executor", choices=sorted(TOOLS))
    p_record.add_argument("--repo", default=".")
    p_record.add_argument("--commit", required=True)
    p_record.add_argument("--specs", default="harness/specs")
    p_record.add_argument("--packet", required=True)
    p_record.add_argument("--fence", required=True)
    p_record.add_argument("--dispatch-id", required=True)
    p_record.add_argument("--started", required=True)
    p_record.add_argument("--finished", required=True)
    p_record.add_argument("--tokens-out", type=int, default=None)
    p_record.add_argument("--tokens-in", type=int, default=None)
    p_record.add_argument("-o", "--output", default=None)
    p_record.set_defaults(func=_cmd_record)
    p_packet.set_defaults(func=_cmd_packet)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (JoinError, speccc.SpecError, GitError, FileNotFoundError) as exc:
        print(f"join: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
