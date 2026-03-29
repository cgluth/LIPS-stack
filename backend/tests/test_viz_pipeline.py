"""Tests for the visualization pipeline (viz_pipeline.py)."""
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from viz_pipeline import (
    _validate_html,
    _call_mistral,
    _find_code_contents,
    _build_prompt,
    run_visualization,
    MAX_RETRIES,
)

# ---------------------------------------------------------------------------
# A valid HTML document that should pass all validation checks
# ---------------------------------------------------------------------------

VALID_HTML = """<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
<div id="plot" style="position:fixed;inset:0"></div>
<script>
document.addEventListener('DOMContentLoaded', () => {
  Plotly.newPlot('plot', [], {});
});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Sync tests — _validate_html
# ---------------------------------------------------------------------------

def test_validate_html_passes_valid():
    result = _validate_html(VALID_HTML)
    assert result is None


def test_validate_html_rejects_missing_doctype():
    html = "<div>Hello</div>"
    result = _validate_html(html)
    assert result is not None
    assert "DOCTYPE" in result


def test_validate_html_rejects_missing_tailwind():
    html = VALID_HTML.replace("https://cdn.tailwindcss.com", "https://cdn.example.com")
    result = _validate_html(html)
    assert result is not None
    assert "Tailwind" in result


def test_validate_html_rejects_missing_plotly():
    # Build HTML with no visualisation library reference at all
    html = """<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
<script>document.addEventListener('DOMContentLoaded', () => {});</script>
</body>
</html>"""
    result = _validate_html(html)
    assert result is not None
    assert "visualisation" in result.lower() or "REJECTION" in result


def test_validate_html_rejects_missing_script():
    # Remove all script tags
    import re
    html = re.sub(r"<script[^>]*>.*?</script>", "", VALID_HTML, flags=re.DOTALL | re.IGNORECASE)
    result = _validate_html(html)
    assert result is not None
    assert "script" in result.lower()


def test_validate_html_rejects_missing_domcontentloaded():
    html = VALID_HTML.replace("document.addEventListener('DOMContentLoaded', () => {", "window.onload = () => {").replace("});", "};")
    result = _validate_html(html)
    assert result is not None
    assert "DOMContentLoaded" in result


def test_validate_html_rejects_no_fixed_plot():
    # HTML with no fixed/absolute positioning on the plot div
    html = """<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
</head>
<body>
<div id="plot" class="h-screen w-full"></div>
<script>
document.addEventListener('DOMContentLoaded', () => {
  Plotly.newPlot('plot', [], {});
});
</script>
</body>
</html>"""
    result = _validate_html(html)
    assert result is not None
    assert "full-bleed" in result or "position" in result.lower()


# ---------------------------------------------------------------------------
# Sync tests — filesystem helpers
# ---------------------------------------------------------------------------

def test_find_code_contents_finds_code_raw(tmp_path):
    contents = tmp_path / "code-raw" / "contents"
    contents.mkdir(parents=True)
    (contents / "main.py").write_text("print('hello')", encoding="utf-8")

    result = _find_code_contents(tmp_path)
    assert result == contents


def test_find_code_contents_prefers_code_final(tmp_path):
    raw_contents = tmp_path / "code-raw" / "contents"
    raw_contents.mkdir(parents=True)
    (raw_contents / "main.py").write_text("# raw", encoding="utf-8")

    final_contents = tmp_path / "code-final" / "contents"
    final_contents.mkdir(parents=True)
    (final_contents / "main.py").write_text("# final", encoding="utf-8")

    result = _find_code_contents(tmp_path)
    assert result == final_contents


def test_find_code_contents_returns_none_when_no_py(tmp_path):
    contents = tmp_path / "code-raw" / "contents"
    contents.mkdir(parents=True)
    (contents / "config.json").write_text("{}", encoding="utf-8")

    result = _find_code_contents(tmp_path)
    assert result is None


def test_build_prompt_includes_source(tmp_path):
    contents = tmp_path / "code-raw" / "contents"
    contents.mkdir(parents=True)
    source_code = "def simulate():\n    return 42\n"
    (contents / "main.py").write_text(source_code, encoding="utf-8")

    prompt = _build_prompt(contents)
    assert "def simulate()" in prompt
    assert "return 42" in prompt


# ---------------------------------------------------------------------------
# Async tests — _call_mistral
# ---------------------------------------------------------------------------

async def test_call_mistral_extracts_html():
    raw_content = "```html\n" + VALID_HTML + "\n```"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": raw_content}}]
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        html, raw_reply = await _call_mistral("test-key", [{"role": "user", "content": "test"}])

    assert html is not None
    assert html.strip() == VALID_HTML.strip()
    assert raw_reply is not None
    assert raw_reply == raw_content


async def test_call_mistral_no_fence_returns_none_html():
    raw_content = "Here is some text without a code fence."
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": raw_content}}]
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        html, raw_reply = await _call_mistral("test-key", [{"role": "user", "content": "test"}])

    assert html is None
    assert raw_reply is not None
    assert raw_reply == raw_content


async def test_call_mistral_api_failure_returns_none_none():
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        html, raw_reply = await _call_mistral("test-key", [{"role": "user", "content": "test"}])

    assert html is None
    assert raw_reply is None


# ---------------------------------------------------------------------------
# Async tests — run_visualization
# ---------------------------------------------------------------------------

def _make_viz_workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace with a Python file in code-raw/contents."""
    ws = tmp_path / "viz-ws"
    contents = ws / "code-raw" / "contents"
    contents.mkdir(parents=True)
    (contents / "main.py").write_text("def simulate():\n    return [1, 2, 3]\n", encoding="utf-8")
    # Create .env
    (ws / ".env").write_text('MISTRAL_API_KEY="test-key-placeholder"\n', encoding="utf-8")
    return ws


async def test_run_visualization_success(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-placeholder")
    ws = _make_viz_workspace(tmp_path)

    with patch("viz_pipeline._call_mistral", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = (VALID_HTML, "raw")
        result = await run_visualization(ws)

    assert result.get("type") == "html"
    assert result.get("data") == VALID_HTML


async def test_run_visualization_no_api_key(tmp_path, monkeypatch):
    # Remove MISTRAL_API_KEY from environment and prevent load_dotenv from
    # re-loading it from the project root .env file
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    ws = _make_viz_workspace(tmp_path)
    (ws / ".env").write_text("", encoding="utf-8")

    with patch("viz_pipeline.load_dotenv"):  # prevent root .env from being read
        result = await run_visualization(ws)
    assert "error" in result
    assert "MISTRAL_API_KEY" in result["error"]


async def test_run_visualization_no_code(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-placeholder")
    ws = tmp_path / "no-code-ws"
    ws.mkdir()
    (ws / ".env").write_text('MISTRAL_API_KEY="test-key-placeholder"\n', encoding="utf-8")
    # No code-raw/code-final directory with .py files

    result = await run_visualization(ws)
    assert "error" in result
    assert "No generated Python code" in result["error"]


async def test_run_visualization_retries_on_no_fence(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-placeholder")
    ws = _make_viz_workspace(tmp_path)

    call_count = 0

    async def mock_call(api_key, messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return (None, "some text without html fence")
        return (VALID_HTML, "raw")

    with patch("viz_pipeline._call_mistral", side_effect=mock_call):
        result = await run_visualization(ws)

    assert result.get("type") == "html"
    assert result.get("data") == VALID_HTML
    assert call_count == 2


async def test_run_visualization_exhausts_retries(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-placeholder")
    ws = _make_viz_workspace(tmp_path)

    call_count = 0

    async def mock_call(api_key, messages):
        nonlocal call_count
        call_count += 1
        return (None, "no fence text")

    with patch("viz_pipeline._call_mistral", side_effect=mock_call):
        result = await run_visualization(ws)

    assert "error" in result
    assert call_count == MAX_RETRIES + 1


async def test_run_visualization_retries_on_validation_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key-placeholder")
    ws = _make_viz_workspace(tmp_path)

    # Invalid HTML: missing tailwind CDN
    invalid_html = VALID_HTML.replace("https://cdn.tailwindcss.com", "https://cdn.example.com")

    call_count = 0

    async def mock_call(api_key, messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return (invalid_html, "```html\n" + invalid_html + "\n```")
        return (VALID_HTML, "```html\n" + VALID_HTML + "\n```")

    with patch("viz_pipeline._call_mistral", side_effect=mock_call):
        result = await run_visualization(ws)

    assert result.get("type") == "html"
    assert result.get("data") == VALID_HTML
    assert call_count == 2
