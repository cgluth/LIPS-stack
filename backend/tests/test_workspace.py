"""Tests for workspace management endpoints."""
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from tests.helpers import _make_stage, _make_workspace
import main as _main_module


# ---------------------------------------------------------------------------
# Tests using `client` fixture (empty workspace/template directories)
# ---------------------------------------------------------------------------

def test_list_workspaces_empty(client):
    resp = client.get("/api/workspaces")
    assert resp.status_code == 200
    assert resp.json() == {"workspaces": []}


def test_list_templates_empty(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 200
    assert resp.json() == {"templates": []}


def test_create_workspace_template_not_found(client):
    resp = client.post("/api/workspaces", json={"template": "nonexistent-template", "name": "my-ws"})
    assert resp.status_code == 404


def test_create_workspace_duplicate(client, tmp_dirs, monkeypatch):
    ws_dir, tpl_dir = tmp_dirs
    # Create a real template so the first POST succeeds
    tpl = tpl_dir / "my-template"
    _make_stage(tpl, "requirements")
    _make_stage(tpl, "specifications")
    _make_stage(tpl, "code-raw")
    # Seed an empty requirements file so the SAMPLE_REQUIREMENTS seeding logic works
    req_file = tpl / "requirements" / "contents" / "product-requirements.md"
    req_file.write_text("", encoding="utf-8")

    payload = {"template": "my-template", "name": "dup-ws"}
    resp1 = client.post("/api/workspaces", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/workspaces", json=payload)
    assert resp2.status_code == 400


def test_delete_workspace_not_found(client):
    resp = client.delete("/api/workspaces/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests that set up a real template directly via tmp_dirs + monkeypatch
# ---------------------------------------------------------------------------

def _build_template(tpl_dir: Path, name: str) -> Path:
    """Create a template directory with the three standard stages."""
    tpl = tpl_dir / name
    for stage_name in ("requirements", "specifications", "code-raw"):
        _make_stage(tpl, stage_name)
    # Create an empty product-requirements.md so SAMPLE_REQUIREMENTS gets written
    req_file = tpl / "requirements" / "contents" / "product-requirements.md"
    req_file.write_text("", encoding="utf-8")
    return tpl


def test_create_workspace_success(tmp_dirs, monkeypatch):
    ws_dir, tpl_dir = tmp_dirs
    monkeypatch.setattr(_main_module, "WORKSPACES_DIR", ws_dir)
    monkeypatch.setattr(_main_module, "TEMPLATES_DIR", tpl_dir)
    _build_template(tpl_dir, "newtonian-3d-pipeline")

    test_client = TestClient(_main_module.app)
    resp = test_client.post("/api/workspaces", json={"template": "newtonian-3d-pipeline", "name": "my-new-ws"})
    assert resp.status_code == 201
    assert resp.json() == {"workspace": "my-new-ws"}

    list_resp = test_client.get("/api/workspaces")
    assert "my-new-ws" in list_resp.json()["workspaces"]


def test_create_workspace_seeds_requirements(tmp_dirs, monkeypatch):
    """After creation the requirements file should contain the SAMPLE_REQUIREMENTS text."""
    ws_dir, tpl_dir = tmp_dirs
    monkeypatch.setattr(_main_module, "WORKSPACES_DIR", ws_dir)
    monkeypatch.setattr(_main_module, "TEMPLATES_DIR", tpl_dir)
    _build_template(tpl_dir, "newtonian-3d-pipeline")

    test_client = TestClient(_main_module.app)
    test_client.post("/api/workspaces", json={"template": "newtonian-3d-pipeline", "name": "seeded-ws"})

    file_resp = test_client.get(
        "/api/workspaces/seeded-ws/file",
        params={"path": "requirements/contents/product-requirements.md"},
    )
    assert file_resp.status_code == 200
    data = file_resp.json()
    assert data["exists"] is True
    assert "My Physics Simulation" in data["content"]


def test_delete_workspace_success(tmp_dirs, monkeypatch):
    ws_dir, tpl_dir = tmp_dirs
    monkeypatch.setattr(_main_module, "WORKSPACES_DIR", ws_dir)
    monkeypatch.setattr(_main_module, "TEMPLATES_DIR", tpl_dir)
    _build_template(tpl_dir, "newtonian-3d-pipeline")

    test_client = TestClient(_main_module.app)
    test_client.post("/api/workspaces", json={"template": "newtonian-3d-pipeline", "name": "to-delete"})

    # Workspace should exist
    list_resp = test_client.get("/api/workspaces")
    assert "to-delete" in list_resp.json()["workspaces"]

    del_resp = test_client.delete("/api/workspaces/to-delete")
    assert del_resp.status_code == 200

    list_resp2 = test_client.get("/api/workspaces")
    assert "to-delete" not in list_resp2.json()["workspaces"]
