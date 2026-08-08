"""lab/app.py — the local server.

Read-only by construction: there is no route that writes. The one route
that can reach arbitrary paths is /api/file, which exists because the
design law's second half is "clicking goes there" — so it gets the
adversarial test.
"""

import pytest

from tests.conftest import PROJECT_ROOT

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from lab import app as lab_app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(lab_app.create_app(PROJECT_ROOT))


def test_runs_endpoint_returns_cited_rows(client):
    payload = client.get("/api/runs").json()
    assert payload["rows"]
    row = payload["rows"][0]
    assert "cite" in row["id"]
    assert set(row) >= {"id", "node", "role", "gate", "wall_clock",
                        "tokens_in", "reads_out_of_packet"}
    assert payload["empty_reason"] is None


def test_run_detail_and_a_missing_one(client):
    assert client.get("/api/runs/3d-1r").json()["record"]["dispatch_id"] == "3d-1r"
    assert client.get("/api/runs/nope").status_code == 404


def test_file_route_serves_a_cited_path(client):
    payload = client.get(
        "/api/file",
        params={"path": "docs/evidence/step3b/dispatch_record_3b.json"},
    ).json()
    assert '"dispatch_id"' in payload["text"]


def test_file_route_refuses_to_escape_the_repo(client):
    for attempt in ("../../../../etc/passwd", "/etc/passwd",
                    "docs/../../etc/passwd"):
        assert client.get("/api/file", params={"path": attempt}).status_code == 404


def test_index_is_served(client):
    body = client.get("/").text
    assert "lex lab" in body.lower()


def test_no_route_mutates_the_repo(client):
    """The lab is an instrument, not a second set of hands. Mutation goes
    through lex's tool layer and its confirm gate; nothing here may write."""
    methods = {
        method
        for route in client.app.routes
        for method in (getattr(route, "methods", None) or set())
    }
    assert methods <= {"GET", "HEAD"}
