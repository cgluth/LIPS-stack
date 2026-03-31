# LIPS IDE

A browser-based IDE for the **LIPS** (LLM-driven Iterative Physics Synthesis) pipeline.
Write a physics prompt → generate Python simulation code with AI → visualise it interactively in 3D.

---

## What it does

| Step | What happens |
|---|---|
| **Write** | Describe your physics simulation in plain English inside the built-in editor |
| **Generate** | Run the three LIPS pipeline stages (Requirements → Specifications → Code Review) — each streams live LLM output to the console |
| **Visualise** | A second LLM pass re-implements the physics in JavaScript and returns a self-contained interactive Plotly.js page |

The visualisation renders full-bleed in an iframe with Play/Pause/Reset controls, a seek slider, a duration slider, and live physics parameter sliders — all wired to a real in-browser ODE solver, not pre-computed data.

---

## Prerequisites

| Tool | Min version | Install |
|---|---|---|
| Python | 3.11 | [python.org](https://python.org) |
| Node.js | 18 | [nodejs.org](https://nodejs.org) |
| Mistral API key | — | [console.mistral.ai](https://console.mistral.ai) |

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/cgluth/LIPS-stack.git lips-ide
cd lips-ide

# 2. Set API key
cp .env.example .env
#   → open .env and set MISTRAL_API_KEY=sk-...

# 3. Start
bash start.sh          # macOS / Linux / WSL / Git Bash
start.bat              # Windows (Command Prompt — double-click or run in cmd)
```

Then open **http://localhost:5173**.

> **macOS/Linux:** run `bash start.sh` in a terminal (Terminal.app / iTerm2), not by double-clicking.
> **Windows:** double-click `start.bat` or run it from Command Prompt. Both scripts check for port conflicts and will tell you exactly what to do if a port is already in use.

`start.sh` checks prerequisites, creates a `.venv` virtual environment on first run, installs all Python and Node dependencies (including `lips` as an editable package), starts both servers, and shuts them down cleanly on Ctrl+C.

---

## First use

1. **+ New** → select template → name your project → **Create Project**
2. Replace `product-requirements.md` with your simulation description (see examples below)
3. **Ctrl+S** to save
4. Click each pipeline stage in order — the console streams live output as the LLM works
5. When all stages show **✓**, click **Visualize**
6. Interact: drag to rotate · sliders to adjust parameters and duration · ▶ / ⏸ / ↺ for playback

---

## Example prompts

### Lorenz attractor

```
# Lorenz Attractor

Simulate the Lorenz system using RK4:
  dx/dt = σ(y − x),  dy/dt = x(ρ − z) − y,  dz/dt = xy − βz
Parameters: σ=10, ρ=28, β=8/3 · Initial: (1, 1, 1) · t = 0..50, dt = 0.01
```

### Lorentz force (charged particle in a magnetic field)

```
# 3D Lorentz Force

Simulate a proton (m=1.67e-27 kg, q=1.6e-19 C) with initial velocity [1e5, 0, 0] m/s
in a uniform magnetic field B = [0, 0, 1] T. Solve F = q(v × B) with scipy odeint.
Output trajectory_data.json with x, y, z arrays.
```

---

## Architecture

```
Browser (React + Monaco)
    │  REST (axios)          WebSocket (live stdout)
    ▼                              ▼
FastAPI backend ──────────► lips_runner.py ──► python -m lips.compile <stage>
    │                                                     │
    │  POST /visualize                            Mistral API
    ▼                                          (stage-specific prompt)
viz_pipeline.py
    │  POST /v1/chat/completions (mistral-large-latest)
    ▼
Mistral API  →  ```html…```  →  _validate_html()  →  retry loop  →  <iframe>
```

All workspace data is stored on disk under `lips-ide/workspaces/`. Nothing persists in memory across requests.

See [`docs/architecture.md`](docs/architecture.md) for full system context, sequence, and component diagrams.

---

## Pipeline stages

Each stage calls `python -m lips.compile <stage>` from the workspace directory. LIPS reads `configs/api.json` for the stage prompt configuration and writes output to `out/`. Each stage is named after the folder it **reads from** and writes its output into the next stage's `contents/` directory.

```
requirements   reads requirements/contents/       → writes specifications/contents/
  (natural language prompt → dev guidelines, README, UML diagrams)
      ↓
specifications reads specifications/contents/     → writes code-raw/contents/
  (technical specs + diagrams → working Python simulation code)
      ↓
code-raw       reads specifications/ + code-raw/  → refines code-raw/contents/ in-place
  (reviews generated code against specs, fixes bugs, improves quality)
```

The Visualize step is separate from the LIPS pipeline — it reads the generated Python source from `code-raw/contents/`, builds a bespoke prompt, and calls Mistral directly from the backend to produce the HTML visualisation. The HTML extraction and validation follow the reliability principles from the Google Research paper *Generative UI: LLMs are Effective UI Generators* (self-healing retry loop with structured rejection messages). See [`docs/generative-ui-guardrails.md`](docs/generative-ui-guardrails.md).

---

## Project layout

```
LIPS-stack/
├── start.sh                   # Boots backend + frontend, checks prerequisites
├── .env / .env.example        # MISTRAL_API_KEY
├── frontend/                  # Vite + React IDE
│   └── src/
│       ├── App.tsx            # State, WebSocket handling, API calls
│       └── components/        # EditorPane, ControlPanel, ConsolePane,
│                              #   VisualizerPane, ApiKeyModal
├── backend/
│   ├── main.py                # FastAPI app — all HTTP + WebSocket routes
│   ├── lips_runner.py         # Subprocess launcher + stdout streamer
│   ├── viz_pipeline.py        # Visualisation LLM pipeline
│   └── tests/                 # pytest suite (49 tests)
├── lips/                      # LIPS package (vendored)
├── templates/physical-simulations/   # Project templates
├── workspaces/                # User projects (git-ignored)
└── docs/                      # Architecture, testing, and design docs
```

---

## Tests

```bash
# Backend — 49 tests
cd backend && python3 -m pytest tests/ -v

# Frontend — 35 tests
cd frontend && npm test
```

84 tests total, 0 failures. See [`docs/testing.md`](docs/testing.md) for full coverage documentation.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `MISTRAL_API_KEY is not set` | Add to `.env` or use the key button in the IDE header |
| Port already in use | `lsof -ti:8000 \| xargs kill -9` then `bash start.sh` |
| Blank visualisation pane | Open DevTools → Console, then click Visualize again (retry loop self-corrects) |
| `command not found: bash start.sh` | `cd lips-ide` first |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · TypeScript · Vite · Tailwind CSS · Inter |
| Editor | Monaco Editor |
| Backend | FastAPI · Uvicorn · httpx |
| Real-time | WebSockets (starlette) |
| LLM | Mistral `mistral-large-latest` |
| Visualisation | Plotly.js (runtime CDN, inside generated HTML) |
| Backend tests | pytest · pytest-asyncio |
| Frontend tests | vitest · React Testing Library · jsdom |

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System context, pipeline sequence diagram, component diagrams |
| [`docs/testing.md`](docs/testing.md) | Test philosophy, every test described, infrastructure notes |
| [`docs/generative-ui-guardrails.md`](docs/generative-ui-guardrails.md) | Paper-backed design principles for the visualisation pipeline |
