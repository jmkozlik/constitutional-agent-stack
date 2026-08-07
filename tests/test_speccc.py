"""Spec format v0.2: the `surface:` field and W06."""

from harness import speccc

BASE_NODE = {
    "id": "n1",
    "one_liner": "Does a thing.",
    "references": [],
    "writes": ["core/a.py"],
    "done_when": ["It works."],
}


def test_surface_is_optional_and_parsed():
    node = {**BASE_NODE, "surface": ["core.a.run(x: int) -> int"]}
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert index["n1"]["surface"] == ["core.a.run(x: int) -> int"]


def test_surface_wrong_type_is_e01():
    node = {**BASE_NODE, "surface": "core.a.run"}
    try:
        speccc.validate([node], {"n1": "spec.yaml"})
    except speccc.SpecError as err:
        assert "surface" in str(err)
    else:
        raise AssertionError("expected SpecError")


def test_done_when_without_surface_is_w06():
    index = speccc.validate([dict(BASE_NODE)], {"n1": "spec.yaml"})
    assert any("[W06]" in w and "n1" in w for w in speccc.warnings(index))


def test_surface_present_no_w06():
    node = {**BASE_NODE, "surface": ["core.a.run(x: int) -> int"]}
    index = speccc.validate([node], {"n1": "spec.yaml"})
    assert not any("[W06]" in w for w in speccc.warnings(index))
