"""The standing gate, as a harness command.

F37, ratified: the three-probe packet-sufficiency protocol lived in
`docs/evidence/step3t/gate.js`, a JS runner that lex had no lever for — so
the interface could not run the gate that gates dispatches, and its evals
tool had to print a NOT RUN HERE caveat about its own blind spot.

**Instrument continuity (F26).** The protocol text here is transcribed from
the archived `gate.js` verbatim: the same preamble, the same three probes,
the same per-probe `extra` line, the same verdict enum. F26 was filed
because the "identical three-probe protocol" had been depending on
memory between rounds; a port that quietly reworded the prompt would
reintroduce exactly that, with a version boundary to hide behind. Parity
against the JS runner is demonstrated once and documented, so gate results
stay comparable across the port.

The probes read ONLY the packet. No tools, no files — that is the whole
measurement, and it is why the runner passes the packet as prompt text
rather than a path.

Run: python -m harness.gate [--commit REV] [--json]
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ARCHIVED_PROTOCOL = Path("docs/evidence/step3t/gate.js")

# Transcribed verbatim from the archived gate.js. Checked against it by
# test_gate.py::test_preamble_matches_the_archived_protocol — if the archive
# and this string ever diverge, that test fails rather than the gate
# silently measuring something else.
PROBE_PREAMBLE = (
    "You are a packet-sufficiency probe for a context-compilation system. "
    "Below is a context packet compiled for a coding agent. Judge it EXACTLY "
    "as the agent would experience it: you may NOT read any files, run any "
    "commands, or use any tools — everything you know about the codebase must "
    "come from the packet text below. The question (the system's acceptance "
    "test): could you complete the task described in the packet, to its stated "
    "bar, using ONLY this packet plus the ability to write code in the named "
    "write scope? List every concrete thing you would still need (a schema, a "
    "convention, a command, an interface) as \"missing\". Be specific and "
    "honest — misses here are the system's most valuable telemetry. Do not pad "
    "the list with nice-to-haves; only things you would actually be blocked or "
    "forced to guess on."
)

PROBES = [
    ("executor:symbol_table", "symbol_table", "executor",
     "Your task per the packet is to implement/modify the symbol_table node."),
    ("executor:affected_symbols", "affected_symbols", "executor",
     "Your task per the packet is to implement/modify the affected_symbols node."),
    ("tester:affected_symbols", "affected_symbols", "tester",
     "Your task per the packet is to write the TESTS for the affected_symbols "
     "node from its guarantees, without ever seeing the implementation. Judge "
     "whether the guarantees are testable as written: can you name the thing "
     "to invoke?"),
]

VERDICTS = ("sufficient", "sufficient_with_gaps", "insufficient")

# gate.js constrains the response with an out-of-band `schema` parameter, so
# its PROMPT is protocol text only. The shape instruction therefore lives
# out-of-band here too — a system message plus response_format — and the
# probe prompt stays byte-identical to the archived instrument. Putting it
# in the prompt would have changed what the gate measures while keeping its
# name, which is the F26 failure with a version boundary to hide behind.
SHAPE_SYSTEM = (
    "Answer with a single JSON object and nothing else, matching exactly: "
    '{"verdict": "sufficient" | "sufficient_with_gaps" | "insufficient", '
    '"missing": [string], "notes": string}. '
    "This constrains only the FORM of your answer, never its content."
)


class GateError(Exception):
    pass


def build_prompt(packet: str, extra: str) -> str:
    # Byte-identical to gate.js's construction. Nothing is appended.
    return (
        PROBE_PREAMBLE + "\n" + extra
        + "\n\n=== PACKET BEGINS ===\n" + packet + "\n=== PACKET ENDS ==="
    )


def _packet(node: str, role: str, repo, commit, specs) -> str:
    argv = [
        sys.executable, "-m", "harness.join", "packet", node,
        "--role", role, "--repo", str(repo), "--specs", str(specs),
    ]
    argv += ["--commit", commit] if commit else ["--worktree"]
    result = subprocess.run(argv, capture_output=True, text=True, cwd=str(repo))
    if result.returncode != 0:
        raise GateError(f"packet {node}/{role} failed: {result.stderr.strip()}")
    return result.stdout


def _call(prompt: str, *, model: str, api_key: str, base_url: str) -> dict:
    import httpx

    response = httpx.post(
        base_url,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
        json={"model": model, "max_tokens": 4000,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": SHAPE_SYSTEM},
                           {"role": "user", "content": prompt}]},
        timeout=600.0,
    )
    if response.status_code >= 400:
        raise GateError(f"probe failed: HTTP {response.status_code} — "
                        f"{response.text[:300]}")
    text = ((response.json().get("choices") or [{}])[0]
            .get("message") or {}).get("content") or ""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise GateError(f"probe returned no JSON object: {text[:200]}")
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GateError(f"probe returned unparseable JSON: {exc}") from exc
    if parsed.get("verdict") not in VERDICTS:
        raise GateError(f"probe returned an unknown verdict: "
                        f"{parsed.get('verdict')!r}")
    return parsed


def run(*, repo=".", commit=None, specs="harness/specs", model=None,
        api_key=None, base_url="https://api.x.ai/v1/chat/completions") -> dict:
    """Run the three probes and return their verdicts."""
    api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
    if not api_key:
        raise GateError("no API key — export XAI_API_KEY to run the gate")
    model = model or os.environ.get("LEX_MODEL", "grok-4")
    repo = Path(repo)

    prompts = {}
    for key, node, role, extra in PROBES:
        prompts[key] = build_prompt(_packet(node, role, repo, commit, specs), extra)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_call, prompt, model=model, api_key=api_key,
                        base_url=base_url): key
            for key, prompt in prompts.items()
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except GateError as exc:
                results[key] = {"verdict": None, "error": str(exc)}
    return {
        "protocol": "three-probe packet-sufficiency (ported from gate.js)",
        "model": model,
        "probes": [
            {"probe": key, **results[key]} for key, *_ in PROBES
        ],
    }


def render(report: dict) -> str:
    lines = [f"gate — {report['protocol']}, model {report['model']}", ""]
    for probe in report["probes"]:
        verdict = probe.get("verdict") or f"ERROR ({probe.get('error', '')[:80]})"
        lines.append(f"  {probe['probe']:<28} {verdict}")
        for miss in (probe.get("missing") or [])[:3]:
            lines.append(f"      - {miss[:110]}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness.gate",
        description="The standing three-probe packet-sufficiency gate.",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--specs", default="harness/specs")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = run(repo=args.repo, commit=args.commit, specs=args.specs,
                     model=args.model)
    except GateError as exc:
        print(f"gate: {exc}", file=sys.stderr)
        return 2
    if args.json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(render(report))
    return 0 if all(p.get("verdict") for p in report["probes"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
