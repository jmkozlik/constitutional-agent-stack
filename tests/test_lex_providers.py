"""lex/providers.py — the agent loop, on a second vendor.

lex v1 was ratified on the Anthropic API. This adds an xAI/Grok path
behind an adapter so the loop is not re-pinned to one vendor, and so the
law can be shown to be provider-independent rather than assumed to be.
"""

import json

import pytest

from lex import providers


def test_translate_user_and_assistant_history():
    messages = [
        {"role": "user", "content": "compile the plan"},
        {"role": "assistant", "content": [
            providers.TextBlock("on it"),
            providers.ToolUseBlock("call_1", "join_plan", {"specs": "harness/specs"}),
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "call_1", "content": "ok"},
        ]},
    ]
    out = providers.to_openai(messages, system="THE SKILL")
    assert out[0] == {"role": "system", "content": "THE SKILL"}
    assert out[1] == {"role": "user", "content": "compile the plan"}
    assistant = out[2]
    assert assistant["role"] == "assistant" and assistant["content"] == "on it"
    call = assistant["tool_calls"][0]
    assert call["id"] == "call_1" and call["function"]["name"] == "join_plan"
    assert json.loads(call["function"]["arguments"]) == {"specs": "harness/specs"}
    assert out[3] == {"role": "tool", "tool_call_id": "call_1", "content": "ok"}


def test_tool_schemas_translate_to_openai_function_shape():
    tools = providers.to_openai_tools([
        {"name": "join_plan", "description": "compile", "input_schema":
            {"type": "object", "properties": {"specs": {"type": "string"}}}},
    ])
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "join_plan"
    assert tools[0]["function"]["parameters"]["properties"]["specs"]["type"] == "string"


def test_xai_turn_normalises_a_tool_call(monkeypatch):
    payload = {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "content": "running the plan",
                "tool_calls": [{
                    "id": "call_9", "type": "function",
                    "function": {"name": "join_plan",
                                 "arguments": '{"specs": "harness/specs"}'},
                }],
            },
        }]
    }
    provider = providers.XAIProvider(api_key="k", model="grok-4")
    monkeypatch.setattr(provider, "_post", lambda body: payload)
    message = provider.turn(messages=[], system="S", tools=[], out=None)
    assert message.stop_reason == "tool_use"
    kinds = [b.type for b in message.content]
    assert kinds == ["text", "tool_use"]
    tool = message.content[1]
    assert tool.name == "join_plan" and tool.input == {"specs": "harness/specs"}
    assert tool.id == "call_9"


def test_xai_turn_normalises_a_plain_answer(monkeypatch):
    payload = {"choices": [{"finish_reason": "stop",
                            "message": {"content": "no tools needed"}}]}
    provider = providers.XAIProvider(api_key="k", model="grok-4")
    monkeypatch.setattr(provider, "_post", lambda body: payload)
    message = provider.turn(messages=[], system="S", tools=[], out=None)
    assert message.stop_reason == "end_turn"
    assert message.content[0].text == "no tools needed"


def test_malformed_tool_arguments_do_not_crash_the_loop(monkeypatch):
    payload = {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"content": None, "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "join_plan", "arguments": "{not json"}},
            ]},
        }]
    }
    provider = providers.XAIProvider(api_key="k", model="grok-4")
    monkeypatch.setattr(provider, "_post", lambda body: payload)
    message = provider.turn(messages=[], system="S", tools=[], out=None)
    tool = [b for b in message.content if b.type == "tool_use"][0]
    # unparseable arguments become an empty input, which the tool layer
    # then gates and refuses — never a silent crash mid-turn
    assert tool.input == {}


def test_select_prefers_explicit_provider_then_available_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("XAI_API_KEY", "x")
    assert providers.select()[0] == "xai"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert providers.select()[0] == "anthropic"   # ratified default wins
    monkeypatch.setenv("LEX_PROVIDER", "xai")
    assert providers.select()[0] == "xai"         # explicit beats default


def test_select_reports_when_no_key_is_present(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "XAI_API_KEY", "GROK_API_KEY", "LEX_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(providers.ProviderError) as err:
        providers.select()
    assert "ANTHROPIC_API_KEY" in str(err.value) and "XAI_API_KEY" in str(err.value)


def test_the_law_is_provider_independent(monkeypatch):
    """The confirm gate lives in the tool layer, not the provider. A model on
    ANY vendor that asks for a mutating action must still be refused when the
    human says no."""
    from lex import confirm, tools

    calls = []
    monkeypatch.setattr(tools, "execute",
                        lambda argv, **kw: calls.append(argv) or {"argv": argv})
    monkeypatch.setattr(tools, "confirm", lambda q, d="": confirm.Decision(False, "n"))
    result = tools.run_tool("dispatch_run", {"action": "prepare", "node": "gitio"},
                            repo=".")
    assert result["refused"] is True and calls == []


def test_preflight_reports_a_bad_model_clearly(monkeypatch):
    provider_errors = providers.ProviderError("xai: HTTP 404 — model not found")

    def boom(self, body):
        raise provider_errors

    monkeypatch.setattr(providers.XAIProvider, "_post", boom)
    result = providers.preflight("xai", "k", model="grok-nope")
    assert result["ok"] is False
    assert "404" in result["error"] and result["model"] == "grok-nope"


def test_preflight_reports_success(monkeypatch):
    monkeypatch.setattr(
        providers.XAIProvider, "_post",
        lambda self, body: {"choices": [{"message": {"content": "ok"}}]},
    )
    result = providers.preflight("xai", "k", model="grok-4")
    assert result["ok"] is True and result["reply"] == "ok"
