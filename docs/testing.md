# LIPS IDE — Test Suite

## Overview

The project has a two-part automated test suite: a **Python backend suite** (pytest) and a **TypeScript frontend suite** (vitest). Together they cover 78 tests across 9 test modules, all passing with zero failures.

```
Backend  (pytest)   43 tests  5 modules
Frontend (vitest)   35 tests  4 modules
─────────────────────────────────────────
Total               78 tests
```

Run the full suite:

```bash
# Backend
cd backend
python3 -m pytest tests/ -v

# Frontend
cd frontend
npm test
```

---

## Testing Philosophy

### What we test

The suite targets **behaviour at module boundaries**, not implementation internals. Each test exercises the system the same way a real caller would:

- HTTP endpoints are called through FastAPI's `TestClient` — the full request/response cycle runs, including middleware, path validation, and JSON serialisation.
- The WebSocket endpoint is tested with a real `WebSocketTestSession`, with `asyncio.create_subprocess_exec` replaced by a lightweight async mock that simulates streaming stdout and exit codes.
- The visualization pipeline is tested by mocking the outbound Mistral HTTP call (`_call_mistral`) so tests run instantly without network access, while the retry loop, HTML extraction, and validation logic all execute for real.
- Frontend components are rendered into a jsdom DOM using React Testing Library. Tests query elements by accessible role and text content — never by CSS class or internal component state.

### What we do not mock

| Component | Approach |
|---|---|
| FastAPI routing + middleware | Real (TestClient runs the full app) |
| Filesystem read/write | Real (pytest `tmp_path` fixture provides isolated temp dirs) |
| HTML validation logic | Real (`_validate_html` runs against actual HTML strings) |
| LLM retry loop | Real (mock controls return values; loop logic is exercised) |
| WebSocket framing | Real (starlette test session handles framing) |

### External dependencies we do mock

| Dependency | Why mocked |
|---|---|
| `asyncio.create_subprocess_exec` | Cannot spawn real processes in CI; mock simulates streaming stdout and exit codes |
| `httpx.AsyncClient.post` (Mistral) | Avoids network calls and API costs in tests |
| `load_dotenv` (in select tests) | Prevents the project root `.env` from overriding the test environment |
| Monaco Editor, react-resizable-panels | jsdom has no layout engine; these are stubbed at the module level |
| `WebSocket` global | jsdom has no WebSocket; replaced with a `vi.fn()` mock |
| `ResizeObserver` / `scrollIntoView` | Not implemented in jsdom; stubbed in `test-setup.ts` |

---

## Backend Test Modules

### `test_workspace.py` — Workspace CRUD (8 tests)

Tests the workspace lifecycle via HTTP:

| Test | What it checks |
|---|---|
| `test_list_workspaces_empty` | `GET /api/workspaces` returns `[]` on an empty directory |
| `test_list_templates_empty` | `GET /api/templates` returns `[]` on an empty directory |
| `test_create_workspace_template_not_found` | `POST /api/workspaces` with a non-existent template returns HTTP 404 |
| `test_create_workspace_duplicate` | Creating the same workspace twice returns HTTP 400 |
| `test_delete_workspace_not_found` | `DELETE /api/workspaces/x` returns HTTP 404 for a missing workspace |
| `test_create_workspace_success` | Workspace is created, appears in list, returns HTTP 201 |
| `test_create_workspace_seeds_requirements` | `product-requirements.md` is populated with `SAMPLE_REQUIREMENTS` on creation |
| `test_delete_workspace_success` | Workspace is created, deleted, no longer in list |

---

### `test_files.py` — File Read/Write (6 tests)

Tests file I/O endpoints with real filesystem operations in `tmp_path`:

| Test | What it checks |
|---|---|
| `test_read_existing_file` | `GET /file` returns file content with `exists: true` |
| `test_read_nonexistent_file` | `GET /file` returns `exists: false` and empty content (not 404) |
| `test_write_then_read_file` | `POST /file` persists content; subsequent `GET` reads it back |
| `test_path_traversal_blocked` | `../../etc/passwd` style paths return HTTP 403 |
| `test_list_files_contains_requirements` | `GET /files` always includes `requirements/contents/product-requirements.md` |
| `test_write_creates_parent_dirs` | Writing to a path with missing intermediate directories succeeds |

The path traversal test (`../..`) is a security boundary test — it verifies `_safe_path()` raises HTTP 403 before any filesystem access occurs.

---

### `test_stages.py` — Stage Discovery (6 tests)

Tests the stage detection logic and status flags:

| Test | What it checks |
|---|---|
| `test_stages_discovered` | `GET /stages` returns all three standard stages in order |
| `test_requirements_not_empty` | `requirements_empty: false` after writing content to the requirements file |
| `test_requirements_empty_when_cleared` | `requirements_empty: true` after the file is cleared |
| `test_has_output_false_initially` | `has_output: false` when the `out/` directory does not exist |
| `test_has_output_true_after_out_file` | `has_output: true` after creating a file inside `out/` |
| `test_workspace_not_found` | `GET /stages` on a missing workspace returns HTTP 404 |

The `has_output` flag drives the sequential unlock logic in the UI — these tests ensure the server-side check is correct.

---

### `test_viz_pipeline.py` — Visualization Pipeline (16 tests)

The largest and most detailed module. Tests are split into synchronous unit tests and asynchronous integration tests. The visualization pipeline was built following the reliability framework from the Google Research paper *"Generative UI: LLMs are Effective UI Generators"* (Leviathan et al.) — see [generative-ui-guardrails.md](generative-ui-guardrails.md) for the full design rationale. The tests cover all three layers of that framework: system prompt rules (validated indirectly through `_build_prompt`), post-processor validation (`_validate_html`), and the self-healing retry loop (`run_visualization`).

**Synchronous — `_validate_html` (5 tests)**

| Test | What it checks |
|---|---|
| `test_validate_html_passes_valid` | Well-formed HTML with all required elements returns `None` (pass) |
| `test_validate_html_rejects_missing_doctype` | HTML without `<!DOCTYPE html>` returns a rejection message containing "DOCTYPE" |
| `test_validate_html_rejects_missing_tailwind` | Missing `cdn.tailwindcss.com` returns a rejection message containing "Tailwind" |
| `test_validate_html_rejects_missing_plotly` | HTML with no visualisation library returns a rejection with "REJECTION" |
| `test_validate_html_rejects_missing_script` | HTML with all `<script>` tags stripped returns a rejection containing "script" |

**Synchronous — filesystem helpers (4 tests)**

| Test | What it checks |
|---|---|
| `test_find_code_contents_finds_code_raw` | `_find_code_contents` returns `.py` files from `code-raw/contents/` |
| `test_find_code_contents_prefers_code_final` | When both `code-raw/` and `code-final/` exist, `code-final/` is preferred |
| `test_find_code_contents_returns_none_when_no_py` | Returns `None` when no `.py` files are found in either directory |
| `test_build_prompt_includes_source` | The constructed prompt string contains the source code content |

**Asynchronous — `_call_mistral` (3 tests, httpx mocked)**

| Test | What it checks |
|---|---|
| `test_call_mistral_extracts_html` | A valid ` ```html ``` ` block is extracted and returned |
| `test_call_mistral_no_fence_returns_none_html` | A reply without a code fence returns `(None, raw_reply)` |
| `test_call_mistral_api_failure_returns_none_none` | A non-200 HTTP response returns `(None, None)` |

**Asynchronous — `run_visualization` end-to-end (6 tests)**

| Test | What it checks |
|---|---|
| `test_run_visualization_success` | Returns `{type: "html", data: …}` when `_call_mistral` returns valid HTML |
| `test_run_visualization_no_api_key` | Returns `{error: "…MISTRAL_API_KEY…"}` when the key is absent |
| `test_run_visualization_no_code` | Returns `{error: "No generated Python code…"}` when no `.py` files exist |
| `test_run_visualization_retries_on_no_fence` | First call returns `(None, text)` (no fence); second returns valid HTML; result is success |
| `test_run_visualization_exhausts_retries` | Every call returns `(None, text)`; after `MAX_RETRIES + 1` attempts returns `{error: …}` |
| `test_run_visualization_retries_on_validation_failure` | First call returns HTML missing Tailwind (validation fails); second returns valid HTML; result is success |

The retry tests directly exercise the conversational feedback loop: they verify that the retry count is correct and that a successful attempt after failures still returns the final valid result.

---

### `test_websocket.py` — WebSocket Pipeline (5 tests)

Tests the real-time subprocess streaming endpoint. `asyncio.create_subprocess_exec` is replaced by `MockProcess` / `MockStreamReader`, which simulate line-by-line stdout delivery and a configurable exit code.

```python
class MockStreamReader:
    """Delivers pre-set lines via async readline(), ending with b""."""

class MockProcess:
    """Wraps MockStreamReader; has a configurable returncode and async wait()."""
```

| Test | What it checks |
|---|---|
| `test_ws_missing_workspace` | Connecting with an unknown workspace ID receives `{type:"error"}` then `{type:"done", data:1}` |
| `test_ws_missing_stage` | Connecting with a missing stage directory receives the same error/done pair |
| `test_ws_missing_api_key` | When `MISTRAL_API_KEY` is unset, receives error message before any subprocess is spawned |
| `test_ws_success_streams_stdout_lines` | Each line produced by the mock process is delivered as `{type:"stdout"}` in order; final `{type:"done", data:0}` |
| `test_ws_failure_exit_code_sends_error` | Mock process exits with code `1`; final message is `{type:"error"}` then `{type:"done", data:1}` |

These are the most structurally complex tests in the suite — they verify that the streaming protocol the frontend depends on is correct, including message ordering and the terminal `done` event.

---

## Frontend Test Modules

All frontend tests use **React Testing Library** (`@testing-library/react`) with a jsdom environment. Queries use accessible roles and visible text, not CSS selectors or component internals.

### `App.test.tsx` — Welcome Screen (7 tests)

| Test | What it checks |
|---|---|
| Renders LIPS IDE heading | `<h1>` with "LIPS IDE" is visible |
| Renders subtitle text | Descriptive text below the heading is present |
| Renders New Project button | CTA button is visible |
| Renders feature badges | "Write", "Generate", "Visualize" badges are all present |
| API key button — not set | Shows "Set API Key" text when the API returns `{set: false}` |
| API key button — set | Shows masked key text when the API returns `{set: true}` |
| Opens new project modal | Clicking "+ New Project" renders the modal |

---

### `ControlPanel.test.tsx` — Pipeline Controls (10 tests)

| Test | What it checks |
|---|---|
| Renders all stage names | All three stage names appear in the panel |
| All stages disabled when `requirementsEmpty` | Every stage button has `disabled` attribute |
| Shows warning banner | "Write your prompt first" text is present when requirements are empty |
| First stage enabled when ready | Button is enabled when `requirementsEmpty=false` and no stage is running |
| Second stage disabled when first has no output | Sequential lock is enforced: second stage is disabled |
| Second stage enabled when first has output | Sequential unlock: second stage becomes enabled |
| Running stage shows spinner | When `runningStage` matches a stage name, the button is disabled |
| Visualize button disabled when busy | Button is disabled while a stage is running or visualizing |
| Visualize button calls `onVisualize` | Clicking the button fires the callback |
| Visualize button shows "Visualizing…" text | Text changes while `isVisualizing=true` |

---

### `ConsolePane.test.tsx` — Console Output (9 tests)

| Test | What it checks |
|---|---|
| Shows empty state when no lines | Empty state message is rendered |
| Does not show empty state when lines exist | Empty state hides when lines are present |
| Renders line text content | Line text is visible in the DOM |
| Renders success line | Success-type line is present |
| Renders error line | Error-type line is present |
| Renders info line | Info-type line is present |
| Renders multiple lines | All lines in the array are rendered |
| Clear button is visible | "Clear" button is always present |
| Clear button calls `onClear` | Clicking fires the callback |

---

### `VisualizerPane.test.tsx` — Visualization Panel (9 tests)

| Test | What it checks |
|---|---|
| Shows empty state when no result | Empty state message rendered |
| Shows loading state | Spinner visible when `isLoading=true`; iframe is absent |
| Renders iframe for HTML result | `<iframe>` with the correct `srcDoc` is in the DOM |
| Does not render iframe when loading | Loading spinner takes priority |
| Shows error UI | Error message and `result.error` text are visible |
| Shows live badge | Green "live" badge present for a successful result |
| Show script button visible | Toggle button is visible when `script` is present |
| Script button toggles to show script | After click, script content is visible |
| Script button toggles back to output | Second click restores the iframe view |

---

## Test Infrastructure

### Backend (`backend/`)

| File | Purpose |
|---|---|
| `pytest.ini` | `asyncio_mode = auto` (bare `async def test_*` without decorator); `testpaths = tests` |
| `tests/conftest.py` | `sys.path` setup; `MISTRAL_API_KEY` env var; `tmp_dirs`, `client`, `ws_client` fixtures |
| `tests/helpers.py` | `_make_stage()` and `_make_workspace()` filesystem builders shared across modules |

The `client` and `ws_client` fixtures use `monkeypatch.setattr` to swap `WORKSPACES_DIR` and `TEMPLATES_DIR` with `tmp_path` subdirectories, so no test ever touches the real workspaces on disk.

### Frontend (`frontend/`)

| File | Purpose |
|---|---|
| `vitest.config.ts` | jsdom environment, `globals: true`, points to `test-setup.ts` |
| `src/test-setup.ts` | Imports `@testing-library/jest-dom`; stubs `ResizeObserver`, `scrollIntoView`, and `WebSocket` |

Monaco Editor and `react-resizable-panels` are mocked at the module level inside the test files because they require a real browser layout engine.
