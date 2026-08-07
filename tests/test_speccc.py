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


def test_done_when_camelcase_without_surface_entry_is_w07():
    node = {
        **BASE_NODE,
        "done_when": ["Returns an AffectedReport for every change."],
        "surface": {"callables": ["core.a.run(x: int) -> int"]},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    w07 = [w for w in speccc.warnings(index) if "[W07]" in w]
    assert len(w07) == 1 and "AffectedReport" in w07[0]


def test_done_when_camelcase_resolved_by_surface_no_w07():
    node = {
        **BASE_NODE,
        "done_when": ["Returns an AffectedReport for every change."],
        "surface": {
            "callables": ["core.a.run(x: int) -> AffectedReport"],
            "types": ["core.a.AffectedReport(rows: list)"],
        },
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W07]" in w for w in speccc.warnings(index))


def test_done_when_error_word_with_empty_errors_is_w07():
    node = {
        **BASE_NODE,
        "done_when": ["Deleting a used symbol is an error, not a silent success."],
        "surface": {"callables": ["core.a.run(x: int) -> int"], "errors": []},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert any("[W07]" in w and "error" in w for w in speccc.warnings(index))


def test_sentence_initial_capitals_do_not_trip_w07():
    node = {
        **BASE_NODE,
        "done_when": ["Given a symbol path, returns its definition."],
        "surface": {"callables": ["core.a.run(x: int) -> int"]},
    }
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W07]" in w for w in speccc.warnings(index))
