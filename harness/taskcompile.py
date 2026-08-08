"""task.compile — the first WRAP row, executed.

WRAP.md's headline finding is that the constitutional stack's contract
template is already a hand-authored spec node: Goal is `one_liner`, Files
owned is `writes`, Dependencies is `references`, Interface spec is
`done_when`. The chair has been hand-compiling that mapping for a dozen
runs. This makes it a compiler output.

What it does NOT do is rewrite the template. Every standing clause the
stack won through its own motions — the malformed-input floor, the ARIA
role pinning, the orphan sweep — passes through untouched. Only the
placeholder fields are filled, and a field the spec format cannot supply
is marked UNFILLED rather than guessed: WRAP proposes adding `model:` to
the spec format, that proposal is not ratified, and inventing a model tier
would be exactly the self-ratification the loop forbids.

Run: python -m harness.taskcompile <node> --run-id <id> [--template PATH]
"""

import argparse
import re
import sys
from pathlib import Path

from harness import join

VAULT_TEMPLATE = Path.home() / "vault" / "_system" / "templates" / "contract.md"

UNFILLED = (
    "UNFILLED — the spec format carries no `model:` field. WRAP proposes "
    "adding one; until that is ratified the chair supplies the tier by hand. "
    "A compiler that guessed here would be ratifying its own proposal."
)


class CompileError(Exception):
    pass


def _bullets(items) -> str:
    return "\n".join(f"- {item}" for item in items) if items else '- none'


def _interface_spec(node: dict) -> str:
    """done_when is the interface spec; the surface is what it is tested
    through, so both ride — a test-engineer building from this file needs
    the names as much as the guarantees."""
    lines = [f"- {item}" for item in node["done_when"]]
    surface = node.get("surface") or {}
    for section in ("callables", "types", "errors"):
        entries = surface.get(section) or []
        if entries:
            lines.append(f"- {section}:")
            lines += [f"  - {entry}" for entry in entries]
    return "\n".join(lines)


def _replace_section(text: str, heading_prefix: str, body: str) -> str:
    """Replace the body under a `## heading` up to the next heading, leaving
    the heading itself and every other clause untouched."""
    pattern = re.compile(
        rf"(^##\s+{re.escape(heading_prefix)}[^\n]*\n)(.*?)(?=^##\s|\Z)",
        re.M | re.S,
    )
    if not pattern.search(text):
        raise CompileError(f"template has no '## {heading_prefix}' section")
    return pattern.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n", text, count=1)


def compile_contract(node_id: str, *, specs, template, run_id: str) -> str:
    plan = join.load_plan(specs)
    if node_id not in plan.nodes:
        raise CompileError(
            f"unknown node {node_id!r} — the spec compiles "
            f"{', '.join(sorted(plan.nodes))}"
        )
    node = plan.nodes[node_id]
    text = Path(template).read_text(encoding="utf-8")

    text = text.replace("<run-id>", run_id).replace("<task-id>", node_id)
    text = _replace_section(text, "Goal", node["one_liner"].strip())
    text = _replace_section(text, "Files owned", _bullets(node["writes"]))
    text = _replace_section(text, "Interface spec", _interface_spec(node))
    text = _replace_section(text, "Model tier", UNFILLED)
    text = _replace_section(text, "Dependencies", _bullets(node["references"]))
    if node.get("open"):
        text = text.rstrip("\n") + "\n## Open (undecided — do not resolve by expanding scope)\n" \
            + _bullets(node["open"]) + "\n"
    return text.rstrip("\n") + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.taskcompile",
        description="Fill the stack's contract template from a spec node.",
    )
    parser.add_argument("node")
    parser.add_argument("--specs", default="harness/specs")
    parser.add_argument("--template", default=str(VAULT_TEMPLATE))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args(argv)
    try:
        out = compile_contract(
            args.node, specs=args.specs, template=args.template,
            run_id=args.run_id,
        )
    except (CompileError, join.JoinError, OSError) as exc:
        print(f"taskcompile: {exc}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"contract -> {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
