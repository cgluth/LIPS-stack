"""Tests for the /api/workspaces/{id}/stages endpoint."""
import pytest
from pathlib import Path


def test_stages_discovered(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get("/api/workspaces/test-ws/stages")
    assert resp.status_code == 200
    data = resp.json()
    names = [s["name"] for s in data["stages"]]
    assert "requirements" in names
    assert "specifications" in names
    assert "code-raw" in names


def test_requirements_not_empty(ws_client):
    """ws_client seeds content so requirements_empty should be False."""
    test_client, ws_path = ws_client
    resp = test_client.get("/api/workspaces/test-ws/stages")
    assert resp.status_code == 200
    assert resp.json()["requirements_empty"] is False


def test_requirements_empty_when_cleared(ws_client):
    test_client, ws_path = ws_client
    # Overwrite the file with empty content via the API
    test_client.post(
        "/api/workspaces/test-ws/file",
        json={"path": "requirements/contents/product-requirements.md", "content": ""},
    )
    resp = test_client.get("/api/workspaces/test-ws/stages")
    assert resp.status_code == 200
    assert resp.json()["requirements_empty"] is True


def test_has_output_false_initially(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get("/api/workspaces/test-ws/stages")
    assert resp.status_code == 200
    for stage in resp.json()["stages"]:
        assert stage["has_output"] is False


def test_has_output_true_after_out_file(ws_client):
    test_client, ws_path = ws_client
    # Create an output file for the requirements stage
    out_dir = ws_path / "requirements" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.log").write_text("some output", encoding="utf-8")

    resp = test_client.get("/api/workspaces/test-ws/stages")
    assert resp.status_code == 200
    stages = resp.json()["stages"]
    req_stage = next(s for s in stages if s["name"] == "requirements")
    assert req_stage["has_output"] is True

    # Other stages should still be False
    specs_stage = next(s for s in stages if s["name"] == "specifications")
    assert specs_stage["has_output"] is False


def test_workspace_not_found(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get("/api/workspaces/doesnt-exist/stages")
    assert resp.status_code == 404
