import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv, set_key
from fastapi import WebSocket

_LIPS_IDE_ROOT = Path(__file__).resolve().parent.parent   # lips-ide/
_ROOT          = _LIPS_IDE_ROOT.parent                    # PythonProject/ (or parent dir)


def _get_api_key() -> str:
    """Return MISTRAL_API_KEY from env, lips-ide/.env, or parent .env."""
    load_dotenv(_LIPS_IDE_ROOT / ".env", override=False)
    load_dotenv(_ROOT / ".env", override=False)
    return os.getenv("MISTRAL_API_KEY", "")


def _prepare_workspace_env(workspace_path: Path) -> dict:
    """
    Ensure workspace .env has the latest key, and return an env dict
    to pass directly to the subprocess so the key is available even
    before load_dotenv runs inside the child process.

    `lips` is installed as an editable package in the same venv that runs
    this server (via start.sh / start.bat), so sys.executable already has
    it on its path — no PYTHONPATH manipulation required.
    """
    api_key = _get_api_key()

    # Write key to workspace .env so LIPS's load_dotenv(cwd/.env) finds it
    env_file = workspace_path / ".env"
    env_file.touch(exist_ok=True)
    set_key(str(env_file), "MISTRAL_API_KEY", api_key)

    return {**os.environ, "MISTRAL_API_KEY": api_key}


async def run_lips_stage(websocket: WebSocket, workspace_path: Path, stage: str):
    """Run a LIPS stage as a subprocess and stream stdout/stderr to the WebSocket."""
    stage_path = workspace_path / stage
    if not stage_path.exists():
        await websocket.send_json({"type": "error", "data": f"Stage folder '{stage}' not found in workspace.\n"})
        await websocket.send_json({"type": "done", "data": 1})
        return

    subprocess_env = _prepare_workspace_env(workspace_path)
    api_key = subprocess_env.get("MISTRAL_API_KEY", "")

    if not api_key:
        await websocket.send_json({
            "type": "error",
            "data": "MISTRAL_API_KEY is not set. Use the ⚙ Settings button in the header to add your key.\n"
        })
        await websocket.send_json({"type": "done", "data": 1})
        return

    # Use sys.executable so we always use the same Python that runs the server
    cmd = [sys.executable, "-m", "lips.compile", stage]
    await websocket.send_json({"type": "info", "data": f"$ python -m lips.compile {stage}\n"})

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(workspace_path),
        env=subprocess_env,          # ← key injected directly, no .env race
    )

    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        await websocket.send_json({"type": "stdout", "data": line.decode("utf-8", errors="replace")})

    await proc.wait()

    if proc.returncode == 0:
        await websocket.send_json({"type": "success", "data": f"\n✓ Stage '{stage}' completed successfully.\n"})
    else:
        await websocket.send_json({"type": "error", "data": f"\n✗ Stage '{stage}' failed (exit code {proc.returncode}).\n"})

    await websocket.send_json({"type": "done", "data": proc.returncode})
