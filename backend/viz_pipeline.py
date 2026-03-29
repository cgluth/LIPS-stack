"""
Second-LLM visualization pipeline — aligned with Generative UI paper (Google Research).

Reliability principles (paper §2, Appendix A.5):
  1. HTML Marker Rule     — ```html...``` extraction via re.DOTALL; never edge-strip.
  2. Tailwind mandate     — cdn.tailwindcss.com required; <style> blocks allowed for
                            things Tailwind cannot express (per paper: "custom CSS
                            beyond Tailwind utilities within <style> tags").
  3. JS robustness        — DOMContentLoaded wrapper + try/catch on all math.
  4. JS restrictions      — window.parent/top forbidden; no localStorage/sessionStorage.
  5. Zero placeholders    — verbatim from paper's Core Philosophy section.
  6. Responsive design    — required per paper ("variety of devices").
  7. Self-healing retry   — extraction failure and validation failure each produce a
                            precise rejection message fed back to the LLM.
"""

import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MISTRAL_URL  = "https://api.mistral.ai/v1/chat/completions"
MAX_RETRIES  = 2

_SKIP_DIRS   = {"__pycache__", ".git", "tests", "test", ".venv", "venv", "node_modules",
                "visualization", "visualisation", "plot", "plots", "plotting"}
_CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini"}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

VIZ_SYSTEM_PROMPT = """\
You are an expert, meticulous, and creative front-end developer specialising in \
physics simulation and scientific computing. Your primary task is to generate ONLY \
the raw HTML code for a complete, valid, functional, visually stunning, and \
INTERACTIVE HTML page document that visualises a physics simulation.

━━ CORE PHILOSOPHY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Build Interactive Apps First. Your primary goal is always to create an \
interactive application — not a static display.
• No walls of text. Use interactive features and visual elements instead of \
long text blocks.
• Implement Fully & Thoughtfully. Implement complex functionality fully using \
JavaScript. Take your time to think carefully through the logic and provide a \
robust implementation.
• No Placeholders. No placeholder controls, mock functionality, or dummy text \
data. Absolutely FORBIDDEN are any kinds of placeholders. If an element cannot \
be fully implemented, remove it completely — never show example/stub functionality.
• Quality & Depth. Prioritise high-quality design, robust implementation, and \
feature richness.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT — NON-NEGOTIABLE:
Your entire response MUST consist of exactly one fenced code block.
Start your response with the line:
```html
…and end it with the line:
```
There MUST be no text, explanation, commentary, or whitespace outside those two \
fence markers. Any content outside the fences will cause automatic rejection."""

VIZ_USER_PROMPT_TEMPLATE = """\
Below is the source code of a physics simulation written in Python.

Your task: study the source code, re-implement the physics in JavaScript, and \
produce ONE completely self-contained, interactive HTML visualisation.

════════════════════════════════════════════════════════════════════════
 ABSOLUTE REQUIREMENTS — violation of ANY rule causes automatic rejection
════════════════════════════════════════════════════════════════════════

── OUTPUT FORMAT ───────────────────────────────────────────────────────
R1. Your ENTIRE response MUST be a single ```html … ``` fenced block.
    No prose. No explanation. No text outside the fences. Ever.
    REQUIRED FORMAT:
      ```html
      <!DOCTYPE html>
      ...
      </html>
      ```

── MANDATORY CDN SCRIPTS (copy these EXACTLY into <head>) ─────────────
R2. You MUST include BOTH of these <script> tags:
      <script src="https://cdn.tailwindcss.com"></script>
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

── STYLING ─────────────────────────────────────────────────────────────
R3. Use Tailwind CSS utility classes for layout and primary styling.
    For visual effects that Tailwind cannot express (e.g. CSS keyframe
    animations, Plotly colour overrides, canvas element rules), you MAY
    use a <style> block in <head> — but Tailwind must remain the primary
    styling mechanism.
    The page background MUST be bg-[#0f0f0f] (deep neutral dark).

    CRITICAL LAYOUT: The Plotly canvas MUST be "full-bleed" — a single
    <div id="plot"> that fills 100vw × 100vh (position:fixed or absolute,
    inset-0). The control panel (Play/Pause/Reset, sliders, readouts) MUST
    be an absolute-positioned semi-transparent overlay floating on top,
    for example:
      <div class="absolute top-4 right-4 bg-gray-900/80 backdrop-blur
                  z-10 p-4 rounded-2xl shadow-xl w-64 space-y-3">
    This makes the simulation the full visual focus with controls as a HUD.
    NEVER split the screen into a "plot area" and a "controls area" side by
    side or stacked — the plot must always fill the entire viewport.

    CRITICAL POINTER EVENTS: The overlay container div MUST have
    style="pointer-events:none" so mouse drag/rotate on the Plotly canvas
    is never blocked. Re-enable pointer events only on the interactive
    children (buttons, inputs, labels):
      <div class="absolute top-4 right-4 ..." style="pointer-events:none">
        <button style="pointer-events:auto" ...>Play</button>
        <input  style="pointer-events:auto" type="range" ...>
      </div>
    Without this, the overlay intercepts mouse events and 3D rotation stops working.

── JAVASCRIPT ARCHITECTURE ─────────────────────────────────────────────
R4. ALL initialisation logic (Plotly.newPlot, slider wiring, first
    simulation run) MUST be inside a single:
      document.addEventListener('DOMContentLoaded', () => {{ … }});
    Never call Plotly or read DOM elements at the top level.

R5. EVERY simulation / numerical loop MUST be wrapped:
      try {{
        // … simulation code …
      }} catch (err) {{
        console.error('Simulation error:', err);
      }}
    Failures MUST surface in the browser console, never silently swallowed.

R6. FORBIDDEN JavaScript:
    • window.parent or window.top access (iframe isolation)
    • localStorage or sessionStorage
    • alert(), confirm(), prompt()
    • document.write()
    • window.location changes

── SIMULATION FIDELITY ─────────────────────────────────────────────────
R7. RE-IMPLEMENT the exact equations, parameters, and initial conditions
    from the Python source in JavaScript. Do not invent different physics
    or substitute placeholder numbers for real ones from the source.

── PLOTLY RENDERING — CRITICAL (most common failure cause) ─────────────
R8. The Plotly chart container div MUST fill the full viewport. Use an
    explicit inline style so it works inside an iframe (Tailwind h-screen
    resolves to 0px inside iframes):
      <div id="plot" style="position:fixed;inset:0;width:100%;height:100%"></div>
    NEVER rely solely on Tailwind height classes (h-full, h-screen,
    flex-1) for the Plotly div — always pair them with the inline style.

R9. Call Plotly.newPlot with the responsive config:
      Plotly.newPlot(plotDiv, data, layout, {{ responsive: true }});
    The {{ responsive: true }} config object is MANDATORY.

R9b. For a modern, borderless look your Plotly layout object MUST hide
    all grids, background planes, and axis containers.
    REQUIRED in EVERY Plotly layout (non-negotiable — omitting causes white background):
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor:  'rgba(0,0,0,0)',
    For 3D scenes, REQUIRED inside the scene object (ALL fields — omitting any
    one causes white planes or visible grid lines on a dark background):
      scene: {{
        xaxis: {{ showgrid: false, zeroline: false, visible: false }},
        yaxis: {{ showgrid: false, zeroline: false, visible: false }},
        zaxis: {{ showgrid: false, zeroline: false, visible: false }},
        bgcolor: 'rgba(0,0,0,0)',
        aspectmode: 'cube',
        camera: {{ eye: {{ x: 1.5, y: 1.5, z: 1.0 }} }}
      }}
    The aspectmode:'cube' keeps all three axes equally scaled so the trajectory
    is never squashed or stretched. The camera eye prevents the initial view
    from being zoomed so close that the particle starts off-screen.
    For 2D plots hide axis lines and gridlines similarly:
      xaxis: {{ showgrid: false, zeroline: false, showline: false }},
      yaxis: {{ showgrid: false, zeroline: false, showline: false }}

R10. After the initial Plotly.newPlot call, add:
      window.addEventListener('resize',
        () => Plotly.Plots.resize(plotDiv));

R11. On every slider change / re-simulation, update with:
      Plotly.react(plotDiv, newData, newLayout);
    NEVER call Plotly.newPlot a second time — it creates duplicate
    charts and leaks memory.

R12. Before passing simulation arrays to Plotly, validate them:
      if (!xs.every(isFinite)) {{
        console.error('Simulation produced non-finite values');
        document.getElementById('error-msg').textContent =
          'Simulation diverged — adjust parameters.';
        return;
      }}
    Always include a visible <div id="error-msg"> for such messages.

── ANIMATION PLAYBACK (MANDATORY) ──────────────────────────────────────
R13. The visualisation MUST play through time automatically. Implement
    this EXACT pattern — no variations:

    a) Pre-compute the FULL trajectory array once on load (and again
       whenever a physics parameter slider changes).

    b) Maintain animation state:
         let frameIndex = 0;
         let animHandle = null;
         const STEPS_PER_FRAME = 5; // points revealed per RAF tick

    c) In the animation loop use requestAnimationFrame and reveal the
       trajectory incrementally with Plotly.react().
       CRITICAL: declare the callback with the `function` keyword so it
       is hoisted — NEVER use `const tick = () => {{...}}` or any arrow
       function, which would be undefined when first referenced:
         function tick() {{
           frameIndex = Math.min(frameIndex + STEPS_PER_FRAME,
                                 trajectory.length - 1);
           Plotly.react(plotDiv,
             [{{ x: xs.slice(0, frameIndex+1),
                 y: ys.slice(0, frameIndex+1),
                 z: zs.slice(0, frameIndex+1), ... }}],
             layout);
           updateTimeDisplay(times[frameIndex]);
           if (frameIndex < trajectory.length - 1)
             animHandle = requestAnimationFrame(tick);
           else
             onPlaybackEnd();
         }}

    d) Provide three clearly labelled control buttons.
       All helper functions (play, pause, reset, onPlaybackEnd) MUST also
       use `function` declarations, not arrow functions:
         ▶ Play   — starts / resumes (calls requestAnimationFrame(tick))
         ⏸ Pause  — stops  (calls cancelAnimationFrame(animHandle))
         ↺ Reset  — sets frameIndex = 0, redraws first frame, stops loop

    e) Show a live time readout next to the buttons:
         t = 3.42 s   (updated every tick from the times array)

    f) Also include a seek slider (type="range" min=0 max=trajectory
       length-1) so the user can jump to any point. Moving it must
       cancel the animation and redraw that single frame.

    g) On initial page load the simulation MUST start playing
       automatically — call requestAnimationFrame(tick) at the end of
       the DOMContentLoaded handler.

── SIMULATION DURATION CONTROL ──────────────────────────────────────────
R14. Add a "Duration" slider in the controls panel that lets the user
    change how long the simulation runs (the total time t_max / end time).
    This slider MUST:
    • be labelled "Duration" with its current value shown live (e.g. "50 s"),
    • have a sensible range — default to the t_max from the source code,
      min = 10% of that default, max = 500% of that default, step = 1% of
      the default (or a clean round number),
    • on 'input': stop any running animation, re-compute the full trajectory
      using the new t_max, reset frameIndex to 0, then auto-play from the
      beginning.

── PHYSICS PARAMETER CONTROLS ──────────────────────────────────────────
R15. Separately from the duration and time controls above, create sliders
    for the key PHYSICS parameters (mass, charge, field strength, etc.)
    extracted from the source. Each slider MUST:
    • show its current value live next to the label,
    • on 'input': stop any running animation, re-compute the full
      trajectory with the new parameters, reset frameIndex to 0,
      then auto-play from the beginning.

── ZERO PLACEHOLDER RULE (ABSOLUTE) ────────────────────────────────────
R16. Placeholders, mock data, stub functions, hard-coded fake output,
    "TODO" comments, and dummy controls are STRICTLY FORBIDDEN.
    Every slider, display, and simulation element MUST be fully
    implemented. Complexity is NOT an excuse to skip implementation.

════════════════════════════════════════════════════════════════════════

--- PYTHON SOURCE CODE ---
{code}
--- END SOURCE CODE ---

Mandatory thought process (internal, do not include in output):
1. Identify the core physics equations and all named parameters/constants.
2. Plan the JavaScript ODE solver (Euler / RK4) and output arrays.
3. Plan the Plotly chart type (3D scatter, surface, 2D line, etc.).
4. Plan the full-bleed layout: Plotly div fills 100vw × 100vh; controls
   are an absolute overlay (top-4 right-4). List all controls: Play/Pause/
   Reset, time readout, seek slider, duration slider, physics sliders.
5. Determine the duration slider range from t_max in the source.
   List every physics parameter slider with min/max/step from the source.
6. Then generate the complete, final HTML inside the ```html … ``` block.

Remember: respond with ONLY the ```html … ``` block. Nothing else."""

# ---------------------------------------------------------------------------
# Helpers — reading source code
# ---------------------------------------------------------------------------

def _find_code_contents(workspace_path: Path) -> Path | None:
    for name in ["code-final", "code-raw"]:
        p = workspace_path / name / "contents"
        if p.exists() and any(p.rglob("*.py")):
            return p
    candidates = [
        sub / "contents"
        for sub in workspace_path.iterdir()
        if sub.is_dir()
        and (sub / "contents").exists()
        and any((sub / "contents").rglob("*.py"))
    ]
    return sorted(candidates)[-1] if candidates else None


def _is_config(path: Path) -> bool:
    return path.suffix in _CONFIG_EXTS and any(
        kw in path.parts
        for kw in ("sample", "samples", "config", "configs", "example", "examples",
                   "resources", "data")
    )


def _safe_read(path: Path, max_bytes: int = 8_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_bytes:
            text = text[:max_bytes] + f"\n… [truncated — {len(text)} chars total]"
        return text
    except Exception:
        return "[unreadable]"


def _build_prompt(contents_path: Path) -> str:
    sections: list[str] = []

    for f in sorted(contents_path.rglob("*.py")):
        if any(s in f.parts for s in _SKIP_DIRS):
            continue
        rel = f.relative_to(contents_path)
        sections.append(f"# === {rel} ===\n{_safe_read(f)}")

    for f in sorted(contents_path.rglob("*")):
        if any(s in f.parts for s in _SKIP_DIRS):
            continue
        if f.is_file() and _is_config(f):
            rel = f.relative_to(contents_path)
            sections.append(f"# === {rel} (config) ===\n{_safe_read(f)}")

    return VIZ_USER_PROMPT_TEMPLATE.format(code="\n\n".join(sections))


# ---------------------------------------------------------------------------
# LLM call + extraction
# ---------------------------------------------------------------------------

async def _call_mistral(
    api_key: str, messages: list[dict]
) -> tuple[str | None, str | None]:
    """
    Returns (html, raw_reply):
      • html is the content extracted from the ```html...``` block.
      • html is None (raw_reply is not None) when no ```html``` fence was found.
      • Both None on API-level failure.
    """
    payload = {
        "model": "mistral-large-latest",
        "messages": messages,
        "max_tokens": 8192,
        "temperature": 0,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            MISTRAL_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code != 200:
        return None, None

    raw: str = resp.json()["choices"][0]["message"]["content"]

    # Bulletproof extraction: explicitly target the ```html … ``` block.
    # re.DOTALL so the HTML body (which contains newlines) is captured in full.
    match = re.search(r"```html\s*(.*?)\s*```", raw, re.DOTALL)
    if match:
        return match.group(1).strip(), raw

    # No properly-fenced block found — return None so the retry loop sends
    # a precise rejection message.
    return None, raw


# ---------------------------------------------------------------------------
# HTML validation
# ---------------------------------------------------------------------------

_REJECTION_MESSAGES = {
    "no_fence": (
        "REJECTION — no ```html … ``` code block found in your response.\n"
        "Your entire response MUST be one fenced block in this format:\n"
        "```html\n"
        "<!DOCTYPE html>\n"
        "...\n"
        "</html>\n"
        "```\n"
        "No text outside those markers."
    ),
    "no_doctype": (
        "REJECTION — the extracted HTML does not begin with <!DOCTYPE html> or <html>.\n"
        "The very first line inside the ```html block must be <!DOCTYPE html>."
    ),
    "no_tailwind": (
        "REJECTION — Tailwind CSS CDN script tag is missing.\n"
        "Add this EXACTLY to <head>:\n"
        '  <script src="https://cdn.tailwindcss.com"></script>'
    ),
    "no_plotly": (
        "REJECTION — no visualisation library found.\n"
        "Add this EXACTLY to <head>:\n"
        '  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>'
    ),
    "no_script": (
        "REJECTION — no <script> tags found.\n"
        "The simulation logic MUST be implemented in JavaScript inside <script> tags."
    ),
    "no_domcontentloaded": (
        "REJECTION — DOMContentLoaded event listener is missing.\n"
        "ALL initialisation (Plotly.newPlot, slider wiring, simulation) MUST be inside:\n"
        "  document.addEventListener('DOMContentLoaded', () => { … });\n"
        "Never call Plotly or read DOM elements at the top level of a <script> block."
    ),
    "no_fixed_plot": (
        "REJECTION — the Plotly chart container is not full-bleed.\n"
        "The plot <div> MUST have this exact inline style so it fills the viewport inside an iframe:\n"
        '  <div id="plot" style="position:fixed;inset:0;width:100%;height:100%"></div>\n'
        "NEVER rely on Tailwind height classes alone — they resolve to 0px inside iframes.\n"
        "This is the most common cause of a blank white page."
    ),
    "no_paper_bgcolor": (
        "REJECTION — paper_bgcolor and plot_bgcolor are missing from the Plotly layout.\n"
        "Without these the chart renders with a white background that obscures the dark page.\n"
        "Your Plotly layout object MUST include BOTH:\n"
        "  paper_bgcolor: 'rgba(0,0,0,0)',\n"
        "  plot_bgcolor:  'rgba(0,0,0,0)',\n"
        "This makes the chart transparent so the dark page background shows through."
    ),
    "no_responsive": (
        "REJECTION — the Plotly.newPlot call is missing the responsive config.\n"
        "Call Plotly.newPlot with the responsive flag:\n"
        "  Plotly.newPlot(plotDiv, data, layout, { responsive: true });\n"
        "Without this the chart does not resize with the window."
    ),
}


def _validate_html(html: str) -> str | None:
    """Return a rejection message string, or None if all checks pass."""
    lower    = html.lower()
    stripped = html.lstrip()

    if not (stripped.lower().startswith("<!doctype html") or
            stripped.lower().startswith("<html")):
        return _REJECTION_MESSAGES["no_doctype"]

    if "cdn.tailwindcss.com" not in lower:
        return _REJECTION_MESSAGES["no_tailwind"]

    if "plotly" not in lower and "three.js" not in lower and "threejs" not in lower:
        return _REJECTION_MESSAGES["no_plotly"]

    if "<script" not in lower:
        return _REJECTION_MESSAGES["no_script"]

    if "domcontentloaded" not in lower:
        return _REJECTION_MESSAGES["no_domcontentloaded"]

    # The plot div must have explicit fixed/absolute positioning with a size.
    # Without this the chart renders into a 0-height container and nothing is visible.
    has_fixed    = "position:fixed"    in html or "position: fixed"    in html
    has_absolute = "position:absolute" in html or "position: absolute" in html
    has_inset    = "inset:0"           in html or "inset: 0"           in html
    has_100w     = "width:100%"        in html or "width: 100%"        in html
    has_100h     = "height:100%"       in html or "height: 100%"       in html
    has_100vh    = "height:100vh"      in html or "height: 100vh"      in html
    if not (has_fixed or (has_absolute and (has_inset or (has_100w and (has_100h or has_100vh))))):
        return _REJECTION_MESSAGES["no_fixed_plot"]

    # Plotly background colours must be explicitly transparent or the chart renders
    # with a white background, completely hiding the dark page behind it.
    if "plotly" in lower:
        if "paper_bgcolor" not in lower:
            return _REJECTION_MESSAGES["no_paper_bgcolor"]

        # Responsive config is required so the chart resizes with the window.
        if "responsive" not in lower:
            return _REJECTION_MESSAGES["no_responsive"]

    # If requestAnimationFrame is used, the callback must be a hoisted `function`
    # declaration. Arrow functions assigned to const/let are not hoisted and cause
    # "X is not a function" runtime errors when the callback name is referenced
    # before the declaration line.
    import re as _re
    if "requestanimationframe" in lower:
        # Find callback name: requestAnimationFrame(someName)
        raf_names = set(_re.findall(r"requestanimationframe\(\s*(\w+)\s*\)", lower))
        # Check each callback name is declared with `function name(` not `const/let name =`
        for name in raf_names:
            is_function_decl = bool(_re.search(rf"\bfunction\s+{name}\s*\(", lower))
            is_arrow         = bool(_re.search(rf"\b(?:const|let)\s+{name}\s*=", lower))
            if is_arrow and not is_function_decl:
                return (
                    f"REJECTION — animation callback '{name}' is declared as a const/let "
                    f"arrow function, which is not hoisted.\n"
                    f"This causes 'step is not a function' (or similar) runtime errors.\n"
                    f"Change it to a `function` declaration:\n"
                    f"  function {name}() {{ … }}\n"
                    f"ALL requestAnimationFrame callbacks and animation helpers MUST use "
                    f"`function` declarations, never `const`/`let` arrow functions."
                )

    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_visualization(workspace_path: Path) -> dict:
    _root = Path(__file__).resolve().parent.parent.parent
    load_dotenv(_root / ".env", override=True)
    load_dotenv(workspace_path / ".env")
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        return {"error": "MISTRAL_API_KEY is not set."}

    code_contents = _find_code_contents(workspace_path)
    if not code_contents:
        return {"error": "No generated Python code found. Run the pipeline first."}

    user_prompt = _build_prompt(code_contents)
    messages: list[dict] = [
        {"role": "system", "content": VIZ_SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    html: str | None = None
    last_error = "Unknown error."

    for attempt in range(MAX_RETRIES + 1):
        html, raw_reply = await _call_mistral(api_key, messages)

        # ── API failure ────────────────────────────────────────────────────
        if html is None and raw_reply is None:
            return {"error": "Mistral API call failed or returned empty output."}

        # ── Extraction failure (no ```html``` fence found) ─────────────────
        if html is None:
            last_error = _REJECTION_MESSAGES["no_fence"]
            if attempt < MAX_RETRIES:
                messages.append({"role": "assistant", "content": raw_reply})
                messages.append({
                    "role": "user",
                    "content": (
                        f"{last_error}\n\n"
                        "Rewrite your response now as a single ```html … ``` block."
                    ),
                })
            continue

        # ── Content validation ─────────────────────────────────────────────
        validation_error = _validate_html(html)
        if validation_error is None:
            return {"type": "html", "data": html}

        last_error = validation_error
        if attempt < MAX_RETRIES:
            messages.append({"role": "assistant", "content": raw_reply})
            messages.append({
                "role": "user",
                "content": (
                    f"{last_error}\n\n"
                    "Fix ONLY the listed issue and return the corrected, complete HTML "
                    "inside a single ```html … ``` block. No prose outside the block."
                ),
            })

    return {"error": last_error, "script": html}
