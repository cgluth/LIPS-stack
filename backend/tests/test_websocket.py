"""Tests for the WebSocket stage-runner endpoint."""
import asyncio as _asyncio
import pytest
import json

import lips_runner


# ---------------------------------------------------------------------------
# Mock subprocess helpers
# ---------------------------------------------------------------------------

class MockStreamReader:
    def __init__(self, lines):
        self._lines = [l.encode() if isinstance(l, str) else l for l in lines]
        self._lines.append(b"")  # EOF sentinel
        self._idx = 0

    async def readline(self):
        if self._idx < len(self._lines):
            line = self._lines[self._idx]
            self._idx += 1
            return line
        return b""


class MockProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = MockStreamReader(lines)
        self.returncode = returncode

    async def wait(self):
        pass


# ---------------------------------------------------------------------------
# Helper to drain WebSocket messages
# ---------------------------------------------------------------------------

def collect_ws_messages(ws, max_messages: int = 30) -> list:
    """Receive JSON messages until type=='done' or exception; return the list."""
    messages = []
    for _ in range(max_messages):
        try:
            raw = ws.receive_text()
            msg = json.loads(raw)
            messages.append(msg)
            if msg.get("type") == "done":
                break
        except Exception:
            break
    return messages


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_ws_missing_workspace(ws_client):
    test_client, ws_path = ws_client
    with test_client.websocket_connect("/ws/nonexistent/run/requirements") as ws:
        messages = collect_ws_messages(ws)

    types = [m["type"] for m in messages]
    assert "error" in types
    assert messages[-1]["type"] == "done"
    assert messages[-1]["data"] == 1


def test_ws_missing_stage(ws_client):
    test_client, ws_path = ws_client
    with test_client.websocket_connect("/ws/test-ws/run/nonexistent-stage") as ws:
        messages = collect_ws_messages(ws)

    error_messages = [m for m in messages if m["type"] == "error"]
    assert len(error_messages) > 0
    combined_error = " ".join(m["data"] for m in error_messages)
    assert "not found" in combined_error.lower() or "nonexistent-stage" in combined_error

    assert messages[-1]["type"] == "done"
    assert messages[-1]["data"] == 1


def test_ws_missing_api_key(ws_client, monkeypatch):
    test_client, ws_path = ws_client

    def _return_empty():
        return ""

    monkeypatch.setattr(lips_runner, "_get_api_key", _return_empty)

    with test_client.websocket_connect("/ws/test-ws/run/requirements") as ws:
        messages = collect_ws_messages(ws)

    error_messages = [m for m in messages if m["type"] == "error"]
    assert len(error_messages) > 0
    combined = " ".join(m["data"] for m in error_messages)
    assert "MISTRAL_API_KEY" in combined

    assert messages[-1]["type"] == "done"
    assert messages[-1]["data"] == 1


def test_ws_success_streams_stdout_lines(ws_client, monkeypatch):
    test_client, ws_path = ws_client

    async def _mock_exec(*args, **kwargs):
        return MockProcess(["Step 1\n", "Step 2\n"], returncode=0)

    monkeypatch.setattr(_asyncio, "create_subprocess_exec", _mock_exec)

    with test_client.websocket_connect("/ws/test-ws/run/requirements") as ws:
        messages = collect_ws_messages(ws)

    # Should have an info message with the command
    info_messages = [m for m in messages if m["type"] == "info"]
    assert any("$ python -m lips.compile" in m["data"] for m in info_messages)

    # Should have two stdout messages
    stdout_messages = [m for m in messages if m["type"] == "stdout"]
    stdout_texts = [m["data"] for m in stdout_messages]
    assert any("Step 1" in t for t in stdout_texts)
    assert any("Step 2" in t for t in stdout_texts)

    # Last message should be done with returncode 0
    assert messages[-1] == {"type": "done", "data": 0}

    # Should have a success message
    success_messages = [m for m in messages if m["type"] == "success"]
    assert len(success_messages) > 0
    assert any("completed successfully" in m["data"] for m in success_messages)


def test_ws_failure_exit_code_sends_error(ws_client, monkeypatch):
    test_client, ws_path = ws_client

    async def _mock_exec(*args, **kwargs):
        return MockProcess(["Error output\n"], returncode=1)

    monkeypatch.setattr(_asyncio, "create_subprocess_exec", _mock_exec)

    with test_client.websocket_connect("/ws/test-ws/run/requirements") as ws:
        messages = collect_ws_messages(ws)

    error_messages = [m for m in messages if m["type"] == "error"]
    assert len(error_messages) > 0
    combined = " ".join(m["data"] for m in error_messages)
    assert "failed (exit code 1)" in combined

    assert messages[-1] == {"type": "done", "data": 1}
