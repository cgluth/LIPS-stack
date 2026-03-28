# LIPS IDE

A browser-based IDE for the **LIPS** (LLM-driven Iterative Physics Synthesis) pipeline.
Write a physics prompt → generate Python simulation code with AI → visualise it interactively.

---

## What it does

| Step | What happens |
|------|-------------|
| **Write** | Describe your physics simulation in plain English |
| **Generate** | Run the LIPS pipeline stages (requirements → specifications → code) |
| **Visualise** | A second LLM pass produces a live HTML visualisation with Plotly.js, playback controls, and parameter sliders |

---

## Prerequisites

| Tool | Min version | Install |
|------|------------|---------|
| Python | 3.11 | [python.org](https://python.org) |
| Node.js | 18 | [nodejs.org](https://nodejs.org) |
| Mistral API key | — | [console.mistral.ai](https://console.mistral.ai) |

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/cgluth/LIPS-stack.git lips-ide
cd lips-ide
```

### 2. Set your API key

```bash
cp .env.example .env
# Open .env and replace the placeholder with your real key:
#   MISTRAL_API_KEY=sk-...
```

You can also set or change the key later from inside the IDE (click the key
indicator in the top-right corner of the header).

### 3. Start

```bash
./start.sh
```

Then open **http://localhost:5173** in your browser.

`start.sh` automatically:
- checks Python / Node versions
- installs Python and npm dependencies
- polls until the backend is ready before printing the URLs
- shuts down both servers cleanly on Ctrl+C

---

## First use

1. Click **+ New** → choose a template → give it a name → **Create Project**
2. In the editor, replace the placeholder in `product-requirements.md` with your
   physics simulation description (see examples below)
3. Press **Ctrl+S** to save
4. Click the pipeline stages in order: **requirements → specifications → code-raw**
   — each stage streams its LLM output to the console on the right
5. Once all stages show ✓, click **Visualize**
6. The interactive visualisation appears in the bottom pane:
   - **▶ Play / ⏸ Pause / ↺ Reset** animate the trajectory through time
   - Duration slider controls how long the simulation runs
   - Physics parameter sliders update the simulation and restart the animation

---

## Example prompts

### Lorentz force (charged particle in a magnetic field)

```
# 3D Lorentz Force Simulation

Simulate a charged particle moving through a uniform 3D magnetic field.
Use scipy odeint to solve the equation of motion F = q(v × B).

Parameters:
- mass = 1.67e-27 kg (proton)
- charge = 1.6e-19 C
- initial velocity = [1e5, 0, 0] m/s
- magnetic field = [0, 0, 1] T

Output trajectory_data.json with x, y, z arrays.
```

### Lorenz attractor

```
# Lorenz Attractor

Simulate the Lorenz system using RK4:
  dx/dt = σ(y − x)
  dy/dt = x(ρ − z) − y
  dz/dt = xy − βz

Default parameters: σ=10, ρ=28, β=8/3
Initial conditions: (1, 1, 1)
Run for t = 0..50, dt = 0.01
```

---

## How the pipeline works

Each stage calls `python -m lips.compile <stage>` from your workspace directory.
LIPS uses the Mistral LLM to progressively refine:

```
requirements  →  structured requirement document
     ↓
specifications →  technical spec + class/sequence diagrams
     ↓
code-raw       →  working Python simulation code
```

The **Visualize** button calls a separate LLM pass that reads the generated Python
code, re-implements the physics in JavaScript, and returns a single self-contained
HTML file rendered in the bottom iframe.

---

## Troubleshooting

**"MISTRAL_API_KEY is not set"**
Either add it to `.env` or click the key indicator in the IDE header.

**Port already in use**
```bash
lsof -ti:8000 | xargs kill -9   # stop existing backend
lsof -ti:5173 | xargs kill -9   # stop existing frontend
./start.sh
```

**Visualisation shows nothing / blank pane**
Open browser DevTools (F12) → Console tab. A JavaScript error will be shown.
Click **Visualize** again — the LLM will use the error to generate a corrected version.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite |
| Editor | Monaco Editor (same as VS Code) |
| Styling | Tailwind CSS |
| Backend | FastAPI + Uvicorn |
| Streaming | WebSockets |
| LLM | Mistral `mistral-large-latest` |
| Visualisation | Plotly.js (CDN, generated at runtime) |
