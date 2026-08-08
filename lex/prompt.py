"""The system prompt: the lex-operator skill, transferred verbatim.

Only the YAML frontmatter is stripped — the body is passed through
byte-for-byte. lex's conduct is not paraphrased into code anywhere; if the
skill and the code disagree about how lex should behave, the skill is what
the model actually reads, and the disagreement is a defect in the code.

Operational environment (repo path, which levers exist, the standing state)
does NOT go here. It rides in the opening user turn, the same split
`harness.dispatch` makes between its law-free prompt and the packet.
"""

from pathlib import Path

SKILL = Path(".claude/skills/lex-operator/SKILL.md")


class PromptError(Exception):
    pass


def strip_frontmatter(text: str) -> str:
    """Remove a leading `---` fenced YAML block, and nothing else."""
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[i + 1 :]).lstrip("\n")
    # An unterminated fence is not frontmatter; hand back the file untouched
    # rather than silently eating the document.
    return text


def load_system_prompt(repo=".") -> str:
    path = Path(repo) / SKILL
    if not path.is_file():
        raise PromptError(
            f"the lex-operator skill is missing at {path} — lex's conduct is "
            "that file, so there is nothing to run without it"
        )
    body = strip_frontmatter(path.read_text(encoding="utf-8")).strip()
    if not body:
        raise PromptError(f"{path} has no body under its frontmatter")
    return body
