import os
import json
import shutil
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv, set_key

from lips_runner import run_lips_stage
from viz_pipeline import run_visualization

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LIPS_IDE_ROOT  = Path(__file__).resolve().parent.parent   # lips-ide/
ROOT           = LIPS_IDE_ROOT.parent                      # PythonProject/ (or wherever lips-ide lives)

# Workspaces live inside lips-ide/workspaces/ — self-contained, git-ignored
WORKSPACES_DIR = LIPS_IDE_ROOT / "workspaces"
WORKSPACES_DIR.mkdir(exist_ok=True)

# Templates: prefer sibling LIPS-project-templates repo, fall back to bundled copy
_templates_sibling = ROOT / "LIPS-project-templates" / "physical-simulations"
_templates_bundled = LIPS_IDE_ROOT / "templates" / "physical-simulations"
TEMPLATES_DIR = _templates_sibling if _templates_sibling.exists() else _templates_bundled

# Load .env from lips-ide/ first, then parent directory
load_dotenv(LIPS_IDE_ROOT / ".env")
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Sample starter prompt written into every new workspace's requirements file
# ---------------------------------------------------------------------------
SAMPLE_REQUIREMENTS = """\
# My Physics Simulation

## Scope
A Python simulation run from the terminal.

## Example
Replace this entire file with your own description. For example:

---

# Double Pendulum Simulation

## Scope
A Python program that simulates a double pendulum system using the
Runge-Kutta 4th-order method and saves an animated GIF of the motion.

## Input
Hard-coded initial conditions:
- Rod lengths: L1 = 1.0 m, L2 = 1.0 m
- Masses: m1 = 1.0 kg, m2 = 1.0 kg
- Initial angles: theta1 = 120°, theta2 = -10° (measured from vertical)
- Initial angular velocities: 0 for both

## Output
- Saves `simulation.gif` in the current directory showing the pendulum motion
- Prints total simulation time and number of frames

## Requirements
- Use only standard Python libraries plus numpy and matplotlib
- Simulate 10 seconds of motion at 60 fps
- The GIF must show both rods and trace the path of the second bob
"""

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="LIPS IDE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_lips_stage(path: Path) -> bool:
    return (path / "configs" / "api.json").exists()


# Canonical pipeline stage order. Stages not in this list sort after.
_STAGE_ORDER: dict[str, int] = {
    "requirements":   0,
    "specifications": 1,
    "code-raw":       2,
    "code-final":     3,
}


def _discover_stages(workspace_path: Path) -> list[dict]:
    """Return stages in pipeline order (requirements → specifications → code-raw)."""
    stages = []
    for sub in workspace_path.iterdir():
        if sub.is_dir() and _is_lips_stage(sub):
            out_dir = sub / "out"
            has_output = out_dir.exists() and any(out_dir.iterdir())
            stages.append({"name": sub.name, "has_output": has_output})
    stages.sort(key=lambda s: _STAGE_ORDER.get(s["name"], 99))
    return stages


def _resolve_workspace(workspace_id: str) -> Path:
    path = WORKSPACES_DIR / workspace_id
    if not path.exists():
        raise HTTPException(404, f"Workspace '{workspace_id}' not found.")
    return path


def _safe_path(workspace_path: Path, rel: str) -> Path:
    """Resolve rel inside workspace_path and raise 403 on traversal attempts."""
    target = (workspace_path / rel).resolve()
    try:
        target.relative_to(workspace_path.resolve())
    except ValueError:
        raise HTTPException(403, "Path traversal is not allowed.")
    return target


# ---------------------------------------------------------------------------
# API key config
# ---------------------------------------------------------------------------

ROOT_ENV = ROOT / ".env"


def _write_key_everywhere(api_key: str) -> None:
    """Write MISTRAL_API_KEY to root .env and every existing workspace .env."""
    # Root .env
    ROOT_ENV.touch(exist_ok=True)
    set_key(str(ROOT_ENV), "MISTRAL_API_KEY", api_key)
    os.environ["MISTRAL_API_KEY"] = api_key

    # All workspace .env files
    if WORKSPACES_DIR.exists():
        for ws in WORKSPACES_DIR.iterdir():
            env_file = ws / ".env"
            if env_file.exists():
                set_key(str(env_file), "MISTRAL_API_KEY", api_key)


@app.get("/api/config/apikey")
def get_apikey():
    load_dotenv(ROOT_ENV, override=False)
    key = os.getenv("MISTRAL_API_KEY", "")
    # Return masked value so the UI can show whether a key is set
    masked = (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("set" if key else "")
    return {"set": bool(key), "masked": masked}


class ApiKeyBody(BaseModel):
    api_key: str


@app.post("/api/config/apikey")
def set_apikey(body: ApiKeyBody):
    if not body.api_key.strip():
        raise HTTPException(400, "API key cannot be empty.")
    _write_key_everywhere(body.api_key.strip())
    return {"ok": True}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@app.get("/api/templates")
def list_templates():
    if not TEMPLATES_DIR.exists():
        return {"templates": []}
    names = [
        d.name for d in sorted(TEMPLATES_DIR.iterdir())
        if d.is_dir() and any(_is_lips_stage(s) for s in d.iterdir() if s.is_dir())
    ]
    return {"templates": names}


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------

@app.get("/api/workspaces")
def list_workspaces():
    names = [
        d.name for d in sorted(WORKSPACES_DIR.iterdir())
        if d.is_dir() and any(_is_lips_stage(s) for s in d.iterdir() if s.is_dir())
    ]
    return {"workspaces": names}


class CreateWorkspaceBody(BaseModel):
    template: str
    name: str


@app.post("/api/workspaces", status_code=201)
def create_workspace(body: CreateWorkspaceBody):
    src = TEMPLATES_DIR / body.template
    if not src.exists():
        raise HTTPException(404, f"Template '{body.template}' not found.")

    dst = WORKSPACES_DIR / body.name
    if dst.exists():
        raise HTTPException(400, f"Workspace '{body.name}' already exists.")

    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "out"))

    # Always pull the freshest key (root .env > environment)
    load_dotenv(ROOT_ENV, override=False)
    api_key = os.getenv("MISTRAL_API_KEY", "")
    env_file = dst / ".env"
    env_file.touch(exist_ok=True)
    set_key(str(env_file), "MISTRAL_API_KEY", api_key)

    # Pre-seed product-requirements.md so the user knows exactly what to write
    req_file = dst / "requirements" / "contents" / "product-requirements.md"
    req_file.parent.mkdir(parents=True, exist_ok=True)
    if not req_file.exists() or req_file.stat().st_size == 0:
        req_file.write_text(SAMPLE_REQUIREMENTS, encoding="utf-8")

    return {"workspace": body.name}


@app.delete("/api/workspaces/{workspace_id}", status_code=200)
def delete_workspace(workspace_id: str):
    path = _resolve_workspace(workspace_id)
    shutil.rmtree(path)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Stages & status
# ---------------------------------------------------------------------------

@app.get("/api/workspaces/{workspace_id}/stages")
def get_stages(workspace_id: str):
    ws = _resolve_workspace(workspace_id)
    stages = _discover_stages(ws)
    # Also report whether product-requirements.md has any content
    req_file = ws / "requirements" / "contents" / "product-requirements.md"
    req_empty = (not req_file.exists()) or (req_file.stat().st_size == 0)
    return {"stages": stages, "requirements_empty": req_empty}


@app.get("/api/workspaces/{workspace_id}/status")
def get_status(workspace_id: str):
    return {"stages": _discover_stages(_resolve_workspace(workspace_id))}


# ---------------------------------------------------------------------------
# File operations
# ---------------------------------------------------------------------------

@app.get("/api/workspaces/{workspace_id}/file")
def read_file(workspace_id: str, path: str = Query(...)):
    workspace_path = _resolve_workspace(workspace_id)
    fp = _safe_path(workspace_path, path)
    if not fp.exists():
        return {"content": "", "exists": False}
    return {"content": fp.read_text(encoding="utf-8", errors="replace"), "exists": True}


class WriteFileBody(BaseModel):
    path: str
    content: str


@app.post("/api/workspaces/{workspace_id}/file")
def write_file(workspace_id: str, body: WriteFileBody):
    workspace_path = _resolve_workspace(workspace_id)
    fp = _safe_path(workspace_path, body.path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(body.content, encoding="utf-8")
    return {"ok": True}


@app.get("/api/workspaces/{workspace_id}/files")
def list_files(workspace_id: str):
    """Return all files under each stage's contents/ directory."""
    workspace_path = _resolve_workspace(workspace_id)
    files: list[str] = []

    for stage_dir in sorted(workspace_path.iterdir()):
        if not stage_dir.is_dir() or not _is_lips_stage(stage_dir):
            continue
        contents = stage_dir / "contents"
        if contents.exists():
            for f in sorted(contents.rglob("*")):
                if f.is_file():
                    files.append(str(f.relative_to(workspace_path)))

    # Always expose the main requirements input even before it exists
    req_file = "requirements/contents/product-requirements.md"
    if req_file not in files:
        files.insert(0, req_file)

    return {"files": files}


# ---------------------------------------------------------------------------
# WebSocket — run a LIPS stage
# ---------------------------------------------------------------------------

@app.websocket("/ws/{workspace_id}/run/{stage}")
async def ws_run_stage(websocket: WebSocket, workspace_id: str, stage: str):
    await websocket.accept()
    workspace_path = WORKSPACES_DIR / workspace_id
    if not workspace_path.exists():
        await websocket.send_json({"type": "error", "data": f"Workspace '{workspace_id}' not found.\n"})
        await websocket.send_json({"type": "done", "data": 1})
        await websocket.close()
        return

    try:
        await run_lips_stage(websocket, workspace_path, stage)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "data": f"Internal error: {exc}\n"})
            await websocket.send_json({"type": "done", "data": 1})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Visualization pipeline
# ---------------------------------------------------------------------------

@app.post("/api/workspaces/{workspace_id}/visualize")
async def visualize(workspace_id: str):
    workspace_path = _resolve_workspace(workspace_id)
    return await run_visualization(workspace_path)
