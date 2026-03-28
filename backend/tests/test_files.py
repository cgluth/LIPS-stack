"""Tests for file read/write/list endpoints."""
import pytest


def test_read_existing_file(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get(
        "/api/workspaces/test-ws/file",
        params={"path": "requirements/contents/product-requirements.md"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["exists"] is True
    assert "Physics content" in data["content"]


def test_read_nonexistent_file(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get(
        "/api/workspaces/test-ws/file",
        params={"path": "requirements/contents/does-not-exist.md"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == ""
    assert data["exists"] is False


def test_write_then_read_file(ws_client):
    test_client, ws_path = ws_client
    new_content = "# Updated\nThis is new content."
    write_resp = test_client.post(
        "/api/workspaces/test-ws/file",
        json={"path": "requirements/contents/product-requirements.md", "content": new_content},
    )
    assert write_resp.status_code == 200
    assert write_resp.json() == {"ok": True}

    read_resp = test_client.get(
        "/api/workspaces/test-ws/file",
        params={"path": "requirements/contents/product-requirements.md"},
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["content"] == new_content


def test_path_traversal_blocked(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get(
        "/api/workspaces/test-ws/file",
        params={"path": "../../etc/passwd"},
    )
    assert resp.status_code == 403


def test_list_files_contains_requirements(ws_client):
    test_client, ws_path = ws_client
    resp = test_client.get("/api/workspaces/test-ws/files")
    assert resp.status_code == 200
    files = resp.json()["files"]
    assert "requirements/contents/product-requirements.md" in files


def test_write_creates_parent_dirs(ws_client):
    test_client, ws_path = ws_client
    nested_path = "requirements/contents/subdir/new.md"
    write_resp = test_client.post(
        "/api/workspaces/test-ws/file",
        json={"path": nested_path, "content": "nested content"},
    )
    assert write_resp.status_code == 200

    # Verify on disk
    full_path = ws_path / nested_path
    assert full_path.exists()
    assert full_path.read_text(encoding="utf-8") == "nested content"
