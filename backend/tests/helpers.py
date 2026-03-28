"""Shared filesystem helpers for test modules."""
from pathlib import Path


def _make_stage(base: Path, name: str) -> None:
    """Create a minimal LIPS stage directory inside *base*."""
    stage = base / name
    (stage / "configs").mkdir(parents=True, exist_ok=True)
    (stage / "configs" / "api.json").write_text("{}", encoding="utf-8")
    (stage / "contents").mkdir(parents=True, exist_ok=True)


def _make_workspace(ws_dir: Path, name: str) -> Path:
    """Create a workspace directory with the standard three stages and a .env file."""
    ws = ws_dir / name
    ws.mkdir(parents=True, exist_ok=True)
    for stage_name in ("requirements", "specifications", "code-raw"):
        _make_stage(ws, stage_name)
    env_file = ws / ".env"
    env_file.write_text('MISTRAL_API_KEY="test-key-placeholder"\n', encoding="utf-8")
    return ws
