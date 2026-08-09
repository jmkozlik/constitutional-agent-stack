"""harness/taskcompile.py — the first WRAP row, executed.

WRAP's headline finding: the stack's contract template is already a
hand-authored spec node. This fills the template from a compiled node, so
the contract becomes a compiler output instead of the chair's typing.
"""

import pytest

from harness import taskcompile
from tests.conftest import PROJECT_ROOT

TEMPLATE = """---
type: contract
labels: [contract, run]
run-id: <run-id>
status: immutable
---
# Contract — <task-id>
## Goal
<one paragraph: what done looks like>
## Files owned (exhaustive — touching anything else is a violation)
- <path>
## Standing clause that must survive verbatim
Do not touch this text.
## Interface spec (what the test-engineer builds fixtures from)
- <signatures, behaviors, error cases — precise enough to test from alone>
## Model tier
<sonnet | opus> — <one-line rationale>
## Dependencies
- <task-ids or "none">
"""


def compiled(tmp_path, node="index_assembly", **kw):
    template = tmp_path / "contract.md"
    template.write_text(TEMPLATE)
    return taskcompile.compile_contract(
        node, specs=PROJECT_ROOT / "harness" / "specs",
        template=template, run_id="r-test", **kw,
    )


def test_fills_the_five_wrap_mapped_fields(tmp_path):
    out = compiled(tmp_path)
    assert "# Contract — index_assembly" in out
    assert "run-id: r-test" in out
    assert "<task-id>" not in out and "<run-id>" not in out
    # Goal <- one_liner
    assert "Assembles the index for a repo at a commit" in out
    # Files owned <- writes
    assert "- analyzer/indexer.py" in out
    # Interface spec <- done_when
    assert "Indexing the same commit twice produces byte identical output" in out
    # Dependencies <- references
    assert "gitio" in out and "reference_map" in out


def test_standing_clauses_survive_verbatim(tmp_path):
    out = compiled(tmp_path)
    assert "## Standing clause that must survive verbatim\nDo not touch this text." in out


def test_model_tier_is_not_invented(tmp_path):
    # WRAP proposes adding `model:` to the spec format; it is not ratified,
    # so the compiler marks the gap rather than choosing a tier.
    out = compiled(tmp_path)
    assert "UNFILLED" in out
    assert "model" in out.lower()
    assert "sonnet | opus" not in out


def test_surface_rides_into_the_interface_spec(tmp_path):
    out = compiled(tmp_path)
    assert "analyzer.indexer.import_origins" in out


def test_unknown_node_is_an_error(tmp_path):
    with pytest.raises(taskcompile.CompileError):
        compiled(tmp_path, node="no_such_node")


def test_deterministic(tmp_path):
    assert compiled(tmp_path) == compiled(tmp_path)


def test_against_the_real_stack_template(tmp_path):
    template = PROJECT_ROOT.parent.parent / "vault" / "_system" / "templates" / "contract.md"
    if not template.is_file():
        pytest.skip("vault template not present")
    out = taskcompile.compile_contract(
        "gitio", specs=PROJECT_ROOT / "harness" / "specs",
        template=template, run_id="r-lex-001",
    )
    assert "# Contract — gitio" in out
    assert "- analyzer/gitio.py" in out
    # the stack's hard-won standing clauses must come through untouched
    assert "Orphan-removal sweep" in out
    assert "motion m-w1b" in out
