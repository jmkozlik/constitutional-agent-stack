"""The agent loop: Anthropic Messages API, tool use, one conversation.

The system prompt is the lex-operator skill verbatim (lex.prompt). The tool
set is the harness levers and nothing else (lex.tools). Everything this module
adds is plumbing: stream the turn, run the tools the model asks for, surface
REQUEST_MEM to the human, and hand the answers back.

It adds no authority. A refusal from the confirm gate comes back as an
ordinary tool result and the loop keeps going — there is no retry, no
escalation, and no path here that runs a gated command without the gate.
"""

import sys

from lex import request_mem
from lex.tools import render, run_tool, schemas

MODEL = "claude-opus-5"
MAX_TOKENS = 32_000
EFFORT = "high"
# A turn that wants more tool rounds than this has stopped converging; say so
# rather than letting it spend the night in a loop.
MAX_TOOL_ROUNDS = 40


class AgentError(Exception):
    pass


def build_client(api_key: str):
    """Imported lazily so the rest of lex — including every confirm-gate test
    — runs without the anthropic package installed."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - import-time environment
        raise AgentError(
            "the 'anthropic' package is not installed. Install the extra:\n"
            "    .venv/bin/pip install -e '.[lex]'"
        ) from exc
    return anthropic.Anthropic(api_key=api_key)


class Session:
    """One lex conversation. Owns the message list and the tool loop."""

    def __init__(
        self,
        client,
        *,
        system: str,
        repo,
        transcript,
        model: str = MODEL,
        max_tokens: int = MAX_TOKENS,
        effort: str = EFFORT,
        out=None,
    ):
        self.client = client
        self.system = system
        self.repo = repo
        self.transcript = transcript
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.out = out or sys.stdout
        self.messages: list = []

    # --- API ---------------------------------------------------------------

    def _params(self) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            # The skill is stable for the whole session and sits at the front
            # of every request; cache it rather than re-reading it each turn.
            "system": [
                {
                    "type": "text",
                    "text": self.system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": self.messages,
            "tools": schemas(),
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": self.effort},
        }

    def _stream_turn(self):
        """Stream one assistant turn, printing as it arrives, and return the
        accumulated message."""
        thinking_open = False
        text_open = False
        thinking_parts: list = []
        with self.client.messages.stream(**self._params()) as stream:
            for event in stream:
                if getattr(event, "type", None) != "content_block_delta":
                    continue
                delta = event.delta
                kind = getattr(delta, "type", None)
                if kind == "thinking_delta":
                    if not thinking_open:
                        self.out.write("\n\x1b[2m[thinking]\x1b[0m ")
                        thinking_open = True
                    chunk = getattr(delta, "thinking", "")
                    thinking_parts.append(chunk)
                    self.out.write(f"\x1b[2m{chunk}\x1b[0m")
                    self.out.flush()
                elif kind == "text_delta":
                    if thinking_open:
                        self.out.write("\n")
                        thinking_open = False
                    if not text_open:
                        self.out.write("\n")
                        text_open = True
                    self.out.write(delta.text)
                    self.out.flush()
            message = stream.get_final_message()
        self.out.write("\n")
        self.out.flush()
        if thinking_parts:
            self.transcript.thinking("".join(thinking_parts))
        return message

    # --- the loop ----------------------------------------------------------

    def send(self, content) -> None:
        """Add a user turn and run to the model's end_turn."""
        self.messages.append({"role": "user", "content": content})
        rounds = 0
        while True:
            message = self._stream_turn()
            self.messages.append({"role": "assistant", "content": message.content})

            text = "".join(
                block.text
                for block in message.content
                if getattr(block, "type", None) == "text"
            )
            if text.strip():
                self.transcript.operator(text)

            stop = getattr(message, "stop_reason", None)
            if stop == "refusal":
                detail = getattr(message, "stop_details", None)
                note = (
                    "the API declined this turn"
                    f" (category: {getattr(detail, 'category', None)})."
                    " Nothing was run."
                )
                self._say(note)
                self.transcript.note(note)
                return
            if stop == "max_tokens":
                note = (
                    "the turn hit max_tokens and was cut off — treat the text "
                    "above as incomplete."
                )
                self._say(note)
                self.transcript.note(note)

            tool_uses = [
                block
                for block in message.content
                if getattr(block, "type", None) == "tool_use"
            ]

            # REQUEST_MEM the operator raised in its own prose.
            answers = request_mem.collect(text, source="lex")
            if answers:
                self.transcript.request_mem(answers, source="lex")

            if not tool_uses:
                if answers:
                    self.messages.append(
                        {"role": "user", "content": request_mem.render(answers)}
                    )
                    continue
                return

            rounds += 1
            if rounds > MAX_TOOL_ROUNDS:
                note = (
                    f"lex stopped the turn after {MAX_TOOL_ROUNDS} tool rounds. "
                    "This is a runtime guard, not a completed task."
                )
                self._say(note)
                self.transcript.note(note)
                return

            results = []
            for block in tool_uses:
                results.append(self._run(block))
            if answers:
                results.append(
                    {"type": "text", "text": request_mem.render(answers)}
                )
            self.messages.append({"role": "user", "content": results})

    def _run(self, block) -> dict:
        name = getattr(block, "name", "")
        tool_input = getattr(block, "input", {}) or {}
        self._say(f"→ {name} {tool_input}")
        result = run_tool(name, tool_input, repo=self.repo)
        self.transcript.tool(name, tool_input, result)
        body = render(result)
        self._echo(result, name)

        # REQUEST_MEM carried in artifacts or an agent's report on stdout.
        answers = request_mem.collect(body, source=f"tool:{name}")
        if answers:
            self.transcript.request_mem(answers, source=f"tool:{name}")
            body += request_mem.render(answers)
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": body,
        }

    def _echo(self, result: dict, name: str) -> None:
        if result.get("refused"):
            self._say(f"← {name}: {result['message'].splitlines()[0]}")
        else:
            self._say(f"← {name}: exit {result.get('exit_code')}")

    def _say(self, text: str) -> None:
        self.out.write(f"\x1b[2m{text}\x1b[0m\n")
        self.out.flush()
