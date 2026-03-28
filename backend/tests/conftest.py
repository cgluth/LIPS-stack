import os
import sys
from pathlib import Path

# Add backend/ to sys.path so that main, lips_runner, viz_pipeline are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set the API key before importing main so the module-level load_dotenv doesn't wipe it
os.environ["MISTRAL_API_KEY"] = "test-key-placeholder"

import main as _main_module  # noqa: E402  (after sys.path and env setup)

import pytest
from starlette.testclient import TestClient
from tests.helpers import _make_stage, _make_workspace


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dirs(tmp_path: Path):
    """Return (ws_dir, tpl_dir) both freshly created under tmp_path."""
    ws_dir = tmp_path / "workspaces"
    ws_dir.mkdir()
    tpl_dir = tmp_path / "templates" / "physical-simulations"
    tpl_dir.mkdir(parents=True)
    return ws_dir, tpl_dir


@pytest.fixture
def client(tmp_dirs, monkeypatch):
    """TestClient with WORKSPACES_DIR and TEMPLATES_DIR patched to temp dirs."""
    ws_dir, tpl_dir = tmp_dirs
    monkeypatch.setattr(_main_module, "WORKSPACES_DIR", ws_dir)
    monkeypatch.setattr(_main_module, "TEMPLATES_DIR", tpl_dir)
    return TestClient(_main_module.app)


@pytest.fixture
def ws_client(tmp_dirs, monkeypatch):
    """
    Like `client` but also pre-creates a 'test-ws' workspace with seeded
    requirements content.

    Returns (TestClient, workspace_path).
    """
    ws_dir, tpl_dir = tmp_dirs
    monkeypatch.setattr(_main_module, "WORKSPACES_DIR", ws_dir)
    monkeypatch.setattr(_main_module, "TEMPLATES_DIR", tpl_dir)

    ws_path = _make_workspace(ws_dir, "test-ws")

    # Seed the requirements content file
    req_file = ws_path / "requirements" / "contents" / "product-requirements.md"
    req_file.write_text("# Test\nPhysics content.", encoding="utf-8")

    test_client = TestClient(_main_module.app)
    return test_client, ws_path
