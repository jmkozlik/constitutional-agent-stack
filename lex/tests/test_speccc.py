"""Spec format v0.2/v0.3: the `surface:` field, W06, W07."""

from harness import speccc

BASE_NODE = {
    "id": "n1",
    "one_liner": "Does a thing.",
    "references": [],
    "writes": ["core/a.py"],
    "done_when": ["It works."],
}


def test_surface_is_optional_and_parsed():
    node = {**BASE_NODE, "surface": {"callables": ["core.a.run(x: int) -> int"]}}
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert index["n1"]["surface"]["callables"] == ["core.a.run(x: int) -> int"]


def test_surface_wrong_type_is_e01():
    node = {**BASE_NODE, "surface": ["core.a.run"]}
    try:
        speccc.validate([node], {"n1": "spec.yaml"})
    except speccc.SpecError as err:
        assert "surface" in str(err)
    else:
        raise AssertionError("expected SpecError")


def test_done_when_without_surface_is_w06():
    index = speccc.validate([dict(BASE_NODE)], {"n1": "spec.yaml"})
    assert any("[W06]" in w and "n1" in w for w in speccc.warnings(index))


def test_types_only_surface_still_w06():
    node = {**BASE_NODE, "surface": {"types": ["core.a.Thing(x: int)"]}}
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert any("[W06]" in w for w in speccc.warnings(index))


def test_surface_callables_present_no_w06():
    node = {**BASE_NODE, "surface": {"callables": ["core.a.run(x: int) -> int"]}}
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W06]" in w for w in speccc.warnings(index))


def test_bullet_with_no_anchor_warns_w07():
    # v0.4: anchor-presence — every done_when bullet must name at least one
    # surface entry (callable, type, or error). No NLP.
    node = {
        **BASE_NODE,
        "done_when": ["Indexing the same commit twice produces identical output."],
        "surface": {"callables": ["core.a.run(x: int) -> int"]},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    w07 = [w for w in speccc.warnings(index) if "[W07]" in w]
    assert len(w07) == 1 and "no anchor" in w07[0]


def test_bullet_anchored_by_callable_terminal_no_w07():
    node = {
        **BASE_NODE,
        "done_when": ["Calling run twice gives identical results."],
        "surface": {"callables": ["core.a.run(x: int) -> int"]},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W07]" in w for w in speccc.warnings(index))


def test_bullet_anchored_by_type_or_error_terminal_no_w07():
    node = {
        **BASE_NODE,
        "done_when": [
            "Every record carries its definition location.",
            "A bad floor raises GroundError.",
        ],
        "surface": {
            "callables": ["core.a.run(x: int) -> int"],
            "types": ["core.a.record(path: str, line: int)  [authored]"],
            "errors": ["core.a.GroundError: raised when the floor is bad  [seeded]"],
        },
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W07]" in w for w in speccc.warnings(index))


def test_anchor_is_word_bounded_not_substring():
    # "run" must not anchor via "runway"; the entry terminal is "runway".
    node = {
        **BASE_NODE,
        "done_when": ["The run completes."],
        "surface": {"callables": ["core.a.runway(x: int) -> int"]},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert any("[W07]" in w for w in speccc.warnings(index))


def test_spec_level_meta_language_line(tmp_path):
    (tmp_path / "s.yaml").write_text(
        "- language: python\n"
        "\n"
        "- id: n1\n"
        "  one_liner: A node.\n"
        "  references: []\n"
        "  writes: [core/a.py]\n"
        "  done_when:\n"
        "    - It works.\n"
    )
    nodes, origin, meta = speccc.load(str(tmp_path))
    assert meta == {"language": "python"}
    assert [n["id"] for n in nodes] == ["n1"]
