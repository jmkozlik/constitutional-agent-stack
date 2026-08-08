"""lex/usage.py — the session reporting its own cost.

Ordered with the second leg: lex prints what it spent, so the loop's cost
per dispatch stops being a thing only the vendor console knows. The
accumulator is deliberately dumb; the part worth testing is that the two
vendors' token fields mean the same thing after normalisation, because
they do NOT mean the same thing on the wire.
"""

from lex import usage


def test_anthropic_usage_normalises():
    class Usage:  # what the SDK hands back
        input_tokens = 120
        output_tokens = 40
        cache_read_input_tokens = 9000
        cache_creation_input_tokens = 300

    counted = usage.from_anthropic(Usage())
    assert counted == {"input": 120, "output": 40,
                       "cache_read": 9000, "cache_write": 300}


def test_openai_cached_tokens_are_a_subset_and_are_not_double_counted():
    # The trap: Anthropic's input_tokens EXCLUDES cache reads, while
    # OpenAI/xAI's prompt_tokens INCLUDES them. Adding both vendors' raw
    # numbers into one column would overcount every cached xAI turn.
    counted = usage.from_openai({
        "prompt_tokens": 10_000,
        "completion_tokens": 250,
        "prompt_tokens_details": {"cached_tokens": 9_600},
    })
    assert counted == {"input": 400, "output": 250,
                       "cache_read": 9_600, "cache_write": 0}


def test_openai_without_cache_details_is_all_fresh_input():
    counted = usage.from_openai({"prompt_tokens": 500, "completion_tokens": 20})
    assert counted == {"input": 500, "output": 20,
                       "cache_read": 0, "cache_write": 0}


def test_missing_usage_is_recorded_as_unreported_not_as_zero():
    # A turn whose usage the vendor did not report is not a free turn. If it
    # were counted as zero the session total would read as authoritative
    # while being short, which is the kind of quiet wrong number that gets
    # cited in a report.
    tally = usage.Usage()
    tally.record(None)
    assert tally.turns == 1 and tally.unreported == 1
    assert "1 turn with no usage reported" in tally.render()


def test_accumulates_across_turns():
    tally = usage.Usage()
    tally.record({"input": 100, "output": 10, "cache_read": 0, "cache_write": 5})
    tally.record({"input": 200, "output": 20, "cache_read": 900, "cache_write": 0})
    assert tally.turns == 2
    assert (tally.input, tally.output) == (300, 30)
    assert (tally.cache_read, tally.cache_write) == (900, 5)


def test_record_accepts_a_message_object_from_either_provider():
    class AnthropicUsage:
        input_tokens, output_tokens = 7, 3
        cache_read_input_tokens = cache_creation_input_tokens = 0

    class AnthropicMessage:
        usage = AnthropicUsage()

    class LexMessage:  # lex.providers.Message
        usage = {"input": 5, "output": 1, "cache_read": 0, "cache_write": 0}

    tally = usage.Usage()
    tally.record(AnthropicMessage())
    tally.record(LexMessage())
    assert (tally.input, tally.output) == (12, 4) and tally.turns == 2


def test_render_states_tokens_and_asserts_no_price():
    # No price table: lex would be inventing the numbers, and an invented
    # cost is worse than no cost. Tokens are the datapoint; the report can
    # multiply them by a rate the human actually knows.
    tally = usage.Usage()
    tally.record({"input": 1_000, "output": 100, "cache_read": 20_000,
                  "cache_write": 0})
    text = tally.render(model="grok-4")
    assert "grok-4" in text
    assert "1,000" in text and "100" in text and "20,000" in text
    assert "$" not in text
    assert "no price table" in text.lower()


def test_render_is_a_single_line_when_nothing_is_cached():
    tally = usage.Usage()
    tally.record({"input": 10, "output": 2, "cache_read": 0, "cache_write": 0})
    assert tally.render().count("\n") == 0


def test_session_accumulates_usage_across_turns_and_tool_rounds(monkeypatch):
    """The loop counts every API turn, including the extra turns a tool round
    costs — which is the whole point: a dispatch's real price is the tool
    rounds, not the one visible answer."""
    from lex import agent, providers

    turns = [
        providers.Message(
            content=[providers.ToolUseBlock("c1", "join_plan", {})],
            stop_reason="tool_use",
            usage={"input": 900, "output": 30, "cache_read": 0, "cache_write": 0},
        ),
        providers.Message(
            content=[providers.TextBlock("done")], stop_reason="end_turn",
            usage={"input": 1_200, "output": 60, "cache_read": 800,
                   "cache_write": 0},
        ),
    ]

    class Stub:
        def turn(self, **kwargs):
            return turns.pop(0)

    class Log:
        def __getattr__(self, _):
            return lambda *a, **k: None

    import io

    session = agent.Session(None, system="S", repo=".", transcript=Log(),
                            out=io.StringIO(), provider=Stub())
    monkeypatch.setattr(agent, "run_tool", lambda *a, **k: {"exit_code": 0})
    monkeypatch.setattr(agent, "render", lambda r: "ok")
    session.send("go")

    assert session.usage.turns == 2
    assert session.usage.input == 2_100
    assert session.usage.output == 90
    assert session.usage.cache_read == 800
    assert session.usage.unreported == 0


def test_a_provider_that_reports_no_usage_is_counted_as_unreported():
    from lex import agent, providers
    import io

    class Stub:
        def turn(self, **kwargs):
            return providers.Message(content=[providers.TextBlock("hi")],
                                     stop_reason="end_turn")

    class Log:
        def __getattr__(self, _):
            return lambda *a, **k: None

    session = agent.Session(None, system="S", repo=".", transcript=Log(),
                            out=io.StringIO(), provider=Stub())
    session.send("go")
    assert session.usage.turns == 1 and session.usage.unreported == 1
    assert session.usage.input == 0
