"""Provenance wrappers — the one design law, as a data shape.

docs/lab-brief.md: *"EVERY NUMBER IS A CITATION… A number the UI cannot
cite does not render."*

The law is enforced here rather than in the frontend, for the same reason
the confirm gate lives in `lex.tools` and not in the operator's prompt: a
rule that depends on every future caller remembering it is a request, not a
rule. The read layer has no way to emit a bare number — every value leaves
as `{"v": …, "cite": {…}}` or `{"v": None, "unavailable": "…"}`, and
`tests/test_lab_reader.py::test_every_number_in_the_runs_payload_is_cited`
walks the real payload asserting there is no third shape.

The frontend then needs no discipline at all: it renders every leaf through
one function, and a value with no provenance has nowhere to appear.
"""


def cited(value, *, path: str, field: str, note: str = "") -> dict:
    """A value that came from `field` of the file at `path`."""
    citation = {"path": path, "field": field}
    if note:
        citation["note"] = note
    return {"v": value, "cite": citation}


def derived(value, *, path: str, fields: list, how: str) -> dict:
    """A computed value: it cites every input and states the arithmetic.

    Wall-clock is the common case — it is usually not stored, and
    `finished - started` is still a number the reader must be able to
    defend.
    """
    return {"v": value, "cite": {"path": path, "fields": list(fields),
                                 "how": how, "field": " & ".join(fields)}}


def unavailable(reason: str) -> dict:
    """Explicitly not known, and why — never a blank cell.

    A blank reads as zero, and zero is a claim. "nobody was counting" and
    "the count was nought" are different facts and must look different.
    """
    return {"v": None, "unavailable": reason}
