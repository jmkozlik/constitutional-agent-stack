"""Vendor adapters for the agent loop.

lex v1 was ratified on the Anthropic API, and that stays the default. This
module adds an xAI (Grok) path so the loop is not re-pinned to one vendor,
and so a missing key on one side is not a dead end.

The design keeps ONE canonical history — Anthropic-shaped content blocks —
and translates on the way out. The loop in `lex.agent` never learns which
vendor it is talking to, which is what keeps the translation in one place
instead of smeared through the conversation logic.

What does NOT live here, deliberately: the confirm gate and the tool
allow-list. Those are in `lex.tools`, on the far side of every provider, so
the law does not have to be re-implemented per vendor and cannot be weaker
on one of them. `test_the_law_is_provider_independent` asserts it.

Wire formats differ in three ways that matter:
  - system prompt: a top-level field vs a leading `system` message;
  - tool calls: `tool_use` content blocks vs `tool_calls` on the assistant;
  - tool results: a `tool_result` block vs a `role: "tool"` message.
"""

import json
import os
from dataclasses import dataclass, field

API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_XAI_MODEL = os.environ.get("LEX_MODEL", "grok-4")
TIMEOUT = 300.0


class ProviderError(Exception):
    pass


# --- the canonical block shape the loop reads -------------------------------


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class Message:
    content: list
    stop_reason: str
    stop_details: object = None


# --- translation ------------------------------------------------------------


def _block_attr(block, name, default=None):
    """History mixes dataclasses (ours) with SDK objects and plain dicts."""
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def to_openai(messages: list, *, system: str) -> list:
    """Canonical history -> OpenAI/xAI chat messages."""
    out = [{"role": "system", "content": system}]
    for message in messages:
        role, content = message["role"], message["content"]
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text = "".join(
                _block_attr(b, "text", "") for b in content
                if _block_attr(b, "type") == "text"
            )
            calls = [
                {
                    "id": _block_attr(b, "id"),
                    "type": "function",
                    "function": {
                        "name": _block_attr(b, "name"),
                        "arguments": json.dumps(_block_attr(b, "input") or {}),
                    },
                }
                for b in content
                if _block_attr(b, "type") == "tool_use"
            ]
            entry = {"role": "assistant", "content": text or None}
            if calls:
                entry["tool_calls"] = calls
            out.append(entry)
            continue
        # user turn: tool results become their own messages, prose stays user
        prose = []
        for block in content:
            kind = _block_attr(block, "type")
            if kind == "tool_result":
                body = _block_attr(block, "content", "")
                out.append({
                    "role": "tool",
                    "tool_call_id": _block_attr(block, "tool_use_id"),
                    "content": body if isinstance(body, str) else json.dumps(body),
                })
            elif kind == "text":
                prose.append(_block_attr(block, "text", ""))
        if prose:
            out.append({"role": "user", "content": "\n".join(prose)})
    return out


def to_openai_tools(schemas: list) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema")
                or {"type": "object", "properties": {}},
            },
        }
        for tool in schemas
    ]


# --- providers --------------------------------------------------------------


class AnthropicProvider:
    """The ratified path. Streams, so the operator sees the turn arrive."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str, effort: str = "high",
                 max_tokens: int = 16000):
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError(
                "the 'anthropic' package is not installed — "
                "uv pip install -e '.[lex]'"
            ) from exc
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model, self.effort, self.max_tokens = model, effort, max_tokens

    def params(self, *, messages, system, tools) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
            "tools": tools,
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": self.effort},
        }


class XAIProvider:
    """xAI/Grok over the OpenAI-compatible endpoint.

    Non-streaming: the turn is printed when it lands rather than as it
    arrives. Less pleasant to watch, and it keeps the adapter small enough
    to reason about — which matters more for a path the law runs through.
    """

    name = "xai"

    def __init__(self, api_key: str, model: str = DEFAULT_XAI_MODEL,
                 max_tokens: int = 16000):
        self.api_key, self.model, self.max_tokens = api_key, model, max_tokens

    def _post(self, body: dict) -> dict:
        import httpx

        try:
            response = httpx.post(
                API_URL, json=body, timeout=TIMEOUT,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"xai: request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ProviderError(
                f"xai: HTTP {response.status_code} — {response.text[:400]}\n"
                f"(model {self.model!r}; set LEX_MODEL to change it)"
            )
        return response.json()

    def turn(self, *, messages, system, tools, out) -> Message:
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": to_openai(messages, system=system),
            "tools": to_openai_tools(tools),
        }
        if not body["tools"]:
            body.pop("tools")
        payload = self._post(body)
        choice = (payload.get("choices") or [{}])[0]
        message = choice.get("message") or {}

        blocks = []
        text = message.get("content")
        if text:
            blocks.append(TextBlock(text))
            if out is not None:
                out.write("\n" + text + "\n")
                out.flush()
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except (TypeError, json.JSONDecodeError):
                # An unparseable argument object is handed on as empty. The
                # tool layer then fails closed on it and refuses — better
                # than dying mid-turn on the vendor's formatting.
                arguments = {}
            blocks.append(
                ToolUseBlock(call.get("id") or "", function.get("name") or "",
                             arguments if isinstance(arguments, dict) else {})
            )
        finish = choice.get("finish_reason")
        stop = {
            "tool_calls": "tool_use",
            "stop": "end_turn",
            "length": "max_tokens",
            "content_filter": "refusal",
        }.get(finish, "end_turn")
        return Message(content=blocks or [TextBlock("")], stop_reason=stop)


def preflight(vendor: str, api_key: str, model: str | None = None) -> dict:
    """One cheap call that answers: is the key good, is the model name real.

    The xAI model id here is a default I chose, not one I verified against
    the vendor's catalogue. Preflight turns that guess into a checked fact
    before a session depends on it.
    """
    if vendor != "xai":
        return {"vendor": vendor, "checked": False,
                "note": "preflight implemented for xai only; the anthropic "
                        "path is the ratified default and fails loudly on its own"}
    provider = XAIProvider(api_key=api_key, model=model or DEFAULT_XAI_MODEL)
    try:
        payload = provider._post({
            "model": provider.model,
            "max_tokens": 16,
            "messages": [{"role": "user", "content": "reply with the word ok"}],
        })
    except ProviderError as exc:
        return {"vendor": "xai", "model": provider.model, "ok": False,
                "error": str(exc)}
    reply = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content")
    return {"vendor": "xai", "model": provider.model, "ok": True,
            "reply": (reply or "").strip()[:80]}


def select(model: str | None = None):
    """(name, provider_factory_args) for whichever vendor is configured.

    The ratified default is Anthropic; an explicit LEX_PROVIDER overrides.
    Returning the choice rather than the client keeps this importable and
    testable without either package installed.
    """
    explicit = os.environ.get("LEX_PROVIDER", "").strip().lower()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    xai_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")

    if explicit == "xai":
        if not xai_key:
            raise ProviderError("LEX_PROVIDER=xai but XAI_API_KEY is not set")
        return "xai", xai_key
    if explicit == "anthropic":
        if not anthropic_key:
            raise ProviderError(
                "LEX_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set"
            )
        return "anthropic", anthropic_key
    if anthropic_key:
        return "anthropic", anthropic_key
    if xai_key:
        return "xai", xai_key
    raise ProviderError(
        "no API key found. lex needs one of:\n"
        "  export ANTHROPIC_API_KEY=...   (the ratified default)\n"
        "  export XAI_API_KEY=...         (Grok, via the OpenAI-compatible API)\n"
        "Set LEX_PROVIDER=xai|anthropic to choose when both are present."
    )
