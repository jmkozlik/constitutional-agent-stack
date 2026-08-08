"""python -m lex — the entry point.

    python -m lex                open the operator
    python -m lex plan           open it and go straight to /plan
    python -m lex run 3d-1       open it and go straight to /run 3d-1

The v0 launcher (./lex-v0, which opens a Claude Code session carrying the
lex-operator skill) stays in the tree as a fallback shell. This is the
standalone program.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from lex import agent, repl
from lex.prompt import PromptError, load_system_prompt

KEY_ENV = "ANTHROPIC_API_KEY"


def _commit(repo) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()[:12]
    except (subprocess.CalledProcessError, OSError):
        return ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lex", description="The interactive interface to the harness."
    )
    parser.add_argument(
        "opening", nargs="*",
        help="opening verb, e.g. 'plan' or 'run 3d-1' (without the slash)",
    )
    parser.add_argument("--repo", default=".", help="repo root; default cwd")
    parser.add_argument("--model", default=agent.MODEL)
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / "harness").is_dir():
        print(
            f"lex: {repo} does not look like the lex repo (no harness/). "
            "Run it from the repo root or pass --repo.",
            file=sys.stderr,
        )
        return 2

    api_key = os.environ.get(KEY_ENV, "").strip()
    if not api_key:
        print(
            f"lex: {KEY_ENV} is not set.\n"
            "lex v1 talks to the Anthropic API directly, so it needs a key:\n"
            f"    export {KEY_ENV}=sk-ant-...\n"
            "(The v0 fallback, ./lex-v0, rides the claude CLI instead.)",
            file=sys.stderr,
        )
        return 2

    try:
        system = load_system_prompt(repo)
    except PromptError as exc:
        print(f"lex: {exc}", file=sys.stderr)
        return 2

    try:
        client = agent.build_client(api_key)
    except agent.AgentError as exc:
        print(f"lex: {exc}", file=sys.stderr)
        return 2

    opening = " ".join(args.opening).strip()
    if opening:
        opening = f"/{opening.lstrip('/')}"

    repl.run(
        client,
        system=system,
        repo=repo,
        model=args.model,
        commit=_commit(repo),
        opening=opening,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
