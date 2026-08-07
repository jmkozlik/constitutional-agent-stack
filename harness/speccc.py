#!/usr/bin/env python3
"""speccc - spec compiler front end.

Deterministic. No model calls. Loads nodes/, validates, resolves references,
throws on cycles and write collisions, and prints the parallelism plan.

    python3 speccc.py nodes/
"""
import sys, os, glob, hashlib, re
from collections import defaultdict
import yaml

REQUIRED = {"id": str, "one_liner": str, "references": list,
            "writes": list, "done_when": list}
# surface (format v0.3): mapping of callables / types / errors lists.
OPTIONAL = {"open": list, "surface": dict}

_CAMEL = re.compile(r"\b[A-Z][a-z0-9]*[A-Z]\w*\b")


class SpecError(Exception):
    def __init__(self, code, msg):
        super().__init__(f"[{code}] {msg}")
        self.code = code


def load(spec_dir):
    nodes, origin = [], {}
    for path in sorted(glob.glob(os.path.join(spec_dir, "*.yaml"))):
        with open(path) as f:
            try:
                docs = yaml.safe_load(f) or []
            except yaml.YAMLError as e:
                raise SpecError("E01", f"{path}: unparseable YAML: {e}")
        if not isinstance(docs, list):
            raise SpecError("E01", f"{path}: top level must be a list of nodes")
        for n in docs:
            nodes.append(n)
            origin[n.get("id", "<no id>")] = os.path.basename(path)
    return nodes, origin


def validate(nodes, origin):
    errors, seen = [], {}
    for n in nodes:
        nid = n.get("id", "<no id>")
        for field, typ in REQUIRED.items():
            if field not in n:
                errors.append(f"[E01] {nid}: missing required field '{field}'")
            elif not isinstance(n[field], typ):
                errors.append(f"[E01] {nid}: field '{field}' must be {typ.__name__}")
        for field, typ in OPTIONAL.items():
            if field in n and not isinstance(n[field], typ):
                errors.append(f"[E01] {nid}: field '{field}' must be {typ.__name__}")
        if nid in seen:
            errors.append(f"[E02] duplicate id '{nid}' in {origin[nid]} and {seen[nid]}")
        seen[nid] = origin.get(nid, "?")
    if errors:
        raise SpecError("E01", "schema violations:\n  " + "\n  ".join(errors))
    return {n["id"]: n for n in nodes}


def resolve(index):
    dangling = []
    for nid, n in index.items():
        for ref in n["references"]:
            if ref not in index:
                near = [k for k in index if _close(k, ref)]
                hint = f" (did you mean {near[0]}?)" if near else ""
                dangling.append(f"[E03] {nid} -> '{ref}' resolves to nothing{hint}")
    if dangling:
        raise SpecError("E03", "null resolution:\n  " + "\n  ".join(dangling))


def _close(a, b):
    if abs(len(a) - len(b)) > 2:
        return False
    return sum(1 for x, y in zip(a, b) if x != y) <= 2


def find_cycle(index):
    WHITE, GREY, BLACK = 0, 1, 2
    color = defaultdict(int)
    stack = []

    def visit(nid):
        color[nid] = GREY
        stack.append(nid)
        for ref in index[nid]["references"]:
            if color[ref] == GREY:
                return stack[stack.index(ref):] + [ref]
            if color[ref] == WHITE:
                found = visit(ref)
                if found:
                    return found
        stack.pop()
        color[nid] = BLACK
        return None

    for nid in index:
        if color[nid] == WHITE:
            cyc = visit(nid)
            if cyc:
                raise SpecError("E04", "cycle: " + " -> ".join(cyc))


def levelize(index):
    depth = {}

    def d(nid, seen):
        if nid in depth:
            return depth[nid]
        seen = seen | {nid}
        refs = [r for r in index[nid]["references"] if r not in seen]
        depth[nid] = 0 if not refs else 1 + max(d(r, seen) for r in refs)
        return depth[nid]

    for nid in index:
        d(nid, frozenset())
    levels = defaultdict(list)
    for nid, lv in depth.items():
        levels[lv].append(nid)
    return {k: sorted(v) for k, v in sorted(levels.items())}


def check_writes(index, levels):
    clashes = []
    for lv, ids in levels.items():
        owners = defaultdict(list)
        for nid in ids:
            for w in index[nid]["writes"]:
                owners[w].append(nid)
        for sym, who in owners.items():
            if len(who) > 1:
                clashes.append(f"[E05] level {lv}: {' and '.join(who)} both write '{sym}'")
    if clashes:
        raise SpecError("E05", "write collisions:\n  " + "\n  ".join(clashes))


def warnings(index):
    out = []
    for nid, n in sorted(index.items()):
        for item in n.get("open", []):
            out.append(f"[W01] {nid}: undecided - {item}")
        if len(n["references"]) >= 4:
            out.append(f"[W03] {nid}: references {len(n['references'])} nodes, packet may exceed budget")
        surface = n.get("surface") or {}
        if n["done_when"] and not surface.get("callables"):
            out.append(f"[W06] {nid}: done_when has no surface to test through")
        # W07 (v0.3 closure lint): done_when may only name things the
        # surface carries. Internal-CamelCase tokens catch type/error names
        # without tripping on sentence-initial capitals.
        surface_text = " ".join(
            str(entry) for section in surface.values() for entry in section
        )
        flagged = set()
        for item in n["done_when"]:
            for token in sorted(set(_CAMEL.findall(item))):
                if token not in surface_text and token not in flagged:
                    flagged.add(token)
                    out.append(
                        f"[W07] {nid}: done_when names {token} with no surface entry")
            if re.search(r"\berrors?\b", item, re.I) and not surface.get("errors") \
                    and "errors-empty" not in flagged:
                flagged.add("errors-empty")
                out.append(
                    f"[W07] {nid}: done_when speaks of an error but surface declares none")
    return out


def plan_hash(index, levels):
    h = hashlib.sha256()
    for lv in sorted(levels):
        for nid in levels[lv]:
            h.update(f"{lv}|{nid}|{','.join(sorted(index[nid]['writes']))}\n".encode())
    return h.hexdigest()[:12]


def main(spec_dir):
    nodes, origin = load(spec_dir)
    index = validate(nodes, origin)
    resolve(index)
    find_cycle(index)
    levels = levelize(index)
    check_writes(index, levels)

    atoms = [n for n in index.values() if not n["references"]]
    width = max(len(v) for v in levels.values())

    print(f"compiled {len(index)} nodes from {spec_dir}")
    print(f"  atoms:         {len(atoms)}")
    print(f"  levels:        {len(levels)}  (critical path)")
    print(f"  max width:     {width}  (max parallel executors)")
    print(f"  plan hash:     {plan_hash(index, levels)}")
    print()
    print("parallelism plan")
    for lv, ids in levels.items():
        print(f"  level {lv}  ({len(ids)} parallel)")
        for nid in ids:
            print(f"    - {nid}")
    warns = warnings(index)
    if warns:
        print(f"\n{len(warns)} warnings")
        for w in warns:
            print(f"  {w}")
    print("\nOK")


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else "nodes")
    except SpecError as e:
        print(f"COMPILE FAILED\n{e}", file=sys.stderr)
        sys.exit(1)
