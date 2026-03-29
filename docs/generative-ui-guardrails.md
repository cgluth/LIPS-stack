# Visualization Pipeline — Generative UI Guardrails

## Source

The visualization stage (`backend/viz_pipeline.py`) was designed in alignment with the reliability principles described in:

> **"Generative UI: LLMs are Effective UI Generators"**
> Leviathan et al., Google Research
> https://generativeui.github.io/static/pdfs/paper.pdf

The module docstring explicitly records this:

```python
"""
Second-LLM visualization pipeline — aligned with Generative UI paper (Google Research).

Reliability principles (paper §2, Appendix A.5):
  1. HTML Marker Rule     — ```html...``` extraction via re.DOTALL; never edge-strip.
  2. Tailwind mandate     — cdn.tailwindcss.com required; <style> blocks allowed for
                            things Tailwind cannot express.
  3. JS robustness        — DOMContentLoaded wrapper + try/catch on all math.
  4. JS restrictions      — window.parent/top forbidden; no localStorage/sessionStorage.
  5. Zero placeholders    — verbatim from paper's Core Philosophy section.
  6. Responsive design    — required per paper ("variety of devices").
  7. Self-healing retry   — extraction failure and validation failure each produce a
                            precise rejection message fed back to the LLM.
"""
```

---

## The Paper's Reliability Framework

The paper argues that reliable LLM-generated UIs require three co-operating layers:

| Layer | Role | Our implementation |
|---|---|---|
| **1. System Instructions** | Preventive — tell the model exactly what to produce | `VIZ_SYSTEM_PROMPT` + 16 prompt rules (R1–R16) |
| **2. Post-Processors / Validation** | Corrective — catch what instructions miss | `_validate_html()` + structured rejection messages |
| **3. Self-Healing Retry** | Recovery — feed rejection back as a new user turn | `MAX_RETRIES = 2` conversational retry loop |

These layers are not independent; each is designed to compensate for the limits of the previous one. Instructions reduce failures, validation catches what slips through, and the retry loop converts failures into corrected outputs.

---

## How Each Principle Is Implemented

### Principle 1 — HTML Marker Rule
*The LLM must output exactly one fenced ` ```html ``` ` block. Extraction must use `re.DOTALL` so multi-line HTML is captured in full; no edge-stripping.*

**In the system prompt:**
```
Your entire response MUST consist of exactly one fenced code block.
Start your response with the line:
```html
…and end it with the line:
```
There MUST be no text, explanation, commentary, or whitespace outside those two fence markers.
```

**In `_call_mistral()`:**
```python
match = re.search(r"```html\s*(.*?)\s*```", raw, re.DOTALL)
if match:
    return match.group(1).strip(), raw
return None, raw   # triggers rejection message on next retry
```

**In `VIZ_USER_PROMPT_TEMPLATE` (R1):**
```
R1. Your ENTIRE response MUST be a single ```html … ``` fenced block.
    No prose. No explanation. No text outside the fences. Ever.
```

---

### Principle 2 — Tailwind Mandate
*Tailwind CSS CDN must be present. Custom `<style>` blocks are allowed only for effects that Tailwind cannot express (animations, Plotly colour overrides, canvas rules).*

**In `_validate_html()` — hard validation (one of seven checks):**
```python
if "cdn.tailwindcss.com" not in lower:
    return _REJECTION_MESSAGES["no_tailwind"]
```

**In `VIZ_USER_PROMPT_TEMPLATE` (R2, R3):**
```
R2. You MUST include BOTH of these <script> tags:
      <script src="https://cdn.tailwindcss.com"></script>
      <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

R3. Use Tailwind CSS utility classes for layout and primary styling.
    For visual effects that Tailwind cannot express … you MAY use a
    <style> block — but Tailwind must remain the primary styling mechanism.
```

---

### Principle 3 — JavaScript Robustness
*All initialisation must run inside `DOMContentLoaded`. All numerical/simulation code must be wrapped in `try/catch` so failures surface in the browser console rather than silently breaking the page.*

**In `VIZ_USER_PROMPT_TEMPLATE` (R4, R5):**
```
R4. ALL initialisation logic MUST be inside a single:
      document.addEventListener('DOMContentLoaded', () => { … });
    Never call Plotly or read DOM elements at the top level.

R5. EVERY simulation / numerical loop MUST be wrapped:
      try {
        // … simulation code …
      } catch (err) {
        console.error('Simulation error:', err);
      }
    Failures MUST surface in the browser console, never silently swallowed.
```

---

### Principle 4 — JavaScript Restrictions
*`window.parent`/`window.top` access is forbidden (iframe isolation). `localStorage`/`sessionStorage` are forbidden. `alert()`, `document.write()`, `window.location` changes are forbidden.*

**In `VIZ_USER_PROMPT_TEMPLATE` (R6):**
```
R6. FORBIDDEN JavaScript:
    • window.parent or window.top access (iframe isolation)
    • localStorage or sessionStorage
    • alert(), confirm(), prompt()
    • document.write()
    • window.location changes
```

The iframe in `VisualizerPane.tsx` enforces the isolation boundary independently:
```tsx
<iframe
  srcDoc={result.data}
  sandbox="allow-scripts allow-same-origin"
  title="Simulation visualization"
/>
```
`window.parent` calls inside the iframe receive a cross-origin error by design even if the model ignores R6.

---

### Principle 5 — Zero Placeholders
*Quoted verbatim from the paper's "Core Philosophy" section. No stub controls, no dummy data, no TODO comments. If something cannot be fully implemented, it must be removed entirely.*

**In `VIZ_SYSTEM_PROMPT` (Core Philosophy section):**
```
• No Placeholders. No placeholder controls, mock functionality, or dummy text
  data. Absolutely FORBIDDEN are any kinds of placeholders. If an element
  cannot be fully implemented, remove it completely — never show
  example/stub functionality.
```

**In `VIZ_USER_PROMPT_TEMPLATE` (R16 — the last and most emphatic rule):**
```
R16. Placeholders, mock data, stub functions, hard-coded fake output,
    "TODO" comments, and dummy controls are STRICTLY FORBIDDEN.
    Every slider, display, and simulation element MUST be fully
    implemented. Complexity is NOT an excuse to skip implementation.
```

R16 is placed last in the prompt so it is the most recent instruction the model reads before generating output — a deliberate ordering choice.

---

### Principle 6 — Responsive Design
*The output must work across different viewport sizes.*

**In `VIZ_USER_PROMPT_TEMPLATE` (R8, R9, R10):**
```
R8. The Plotly chart container div MUST fill the full viewport. Use an
    explicit inline style so it works inside an iframe:
      <div id="plot" style="position:fixed;inset:0;width:100%;height:100%"></div>
    NEVER rely solely on Tailwind height classes for the Plotly div.

R9. Call Plotly.newPlot with the responsive config:
      Plotly.newPlot(plotDiv, data, layout, { responsive: true });

R10. After the initial Plotly.newPlot call, add:
      window.addEventListener('resize', () => Plotly.Plots.resize(plotDiv));
```

The `position:fixed;inset:0` override was added specifically because Tailwind's `h-screen` resolves to `0px` inside an iframe — the inline style is always required.

---

### Principle 7 — Self-Healing Retry
*When extraction or validation fails, a precise, structured rejection message is appended to the conversation history and the full updated history is re-sent. The model sees its own failing output alongside the critique, enabling targeted self-correction.*

**The retry loop in `run_visualization()`:**
```python
MAX_RETRIES = 2

for attempt in range(MAX_RETRIES + 1):
    html, raw_reply = await _call_mistral(api_key, messages)

    # API failure — unrecoverable
    if html is None and raw_reply is None:
        return {"error": "Mistral API call failed or returned empty output."}

    # No fence found — append rejection and retry
    if html is None:
        messages.append({"role": "assistant", "content": raw_reply})
        messages.append({"role": "user",      "content": _REJECTION_MESSAGES["no_fence"]})
        continue

    # Fence found — validate structure
    rejection = _validate_html(html)
    if rejection is None:
        return {"type": "html", "data": html}   # success

    # Validation failed — append rejection and retry
    messages.append({"role": "assistant", "content": raw_reply})
    messages.append({"role": "user",      "content": rejection})

return {"error": f"Failed after {MAX_RETRIES + 1} attempts. Last error: {last_error}"}
```

**The rejection messages are structured, not generic:**

| Failure mode | Rejection message content |
|---|---|
| No ` ```html ``` ` fence | Exact required format shown as an example |
| Missing `<!DOCTYPE html>` | Points to the exact first-line requirement |
| Missing Tailwind CDN | Shows the exact `<script>` tag to copy |
| Missing visualisation library | Shows the exact Plotly CDN `<script>` tag |
| No `<script>` tag at all | States that JS must be in `<script>` tags |
| Missing `DOMContentLoaded` | States all init must be inside the event listener |
| Missing `position:fixed` on plot div | Shows the exact required inline style; explains why Tailwind alone fails inside iframes |
| Missing `paper_bgcolor` | Explains the white-background cause; shows the exact transparent colour values to use |
| Missing `responsive: true` | Shows the exact `Plotly.newPlot` call signature with the config object |
| `const`/`let` RAF callback | Names the offending callback, explains hoisting, shows the corrected `function` declaration |

Structured messages are more effective than generic "try again" prompts because they give the model a specific, actionable diff between what it produced and what is required.

---

## Additional Design Decisions Beyond the Paper

These rules go beyond the paper's core principles but were added to address problems specific to this application:

| Rule | Problem it solves |
|---|---|
| **R3 full-bleed layout** (`position:fixed;inset:0`) | Models often split the screen into plot + controls side-by-side, making the simulation visually small. The full-bleed mandate with floating HUD overlay gives the plot the entire viewport. |
| **R3 `pointer-events:none`** on overlay container | The HUD overlay div was intercepting mouse drag events on the Plotly canvas, breaking 3D rotation. The overlay must be click-through except on its own interactive children. |
| **R9b transparent Plotly backgrounds** (`paper_bgcolor`, `plot_bgcolor: 'rgba(0,0,0,0)'`) | Plotly's default white/grey backgrounds create a jarring box inside the dark IDE theme. Transparent backgrounds make the plot feel native to the dark canvas. `_validate_html()` rejects HTML that uses Plotly but omits `paper_bgcolor`, triggering the retry loop. |
| **R9b `aspectmode: 'cube'` and camera defaults** | Without `aspectmode: 'cube'`, Plotly auto-scales each axis independently, making a particle's trajectory appear squashed or stretched. Without a default camera position, Plotly sometimes chooses an initial view that is zoomed in so close the particle starts off-screen. R9b now mandates `aspectmode: 'cube'` and `camera: { eye: { x: 1.5, y: 1.5, z: 1.0 } }` in every 3D scene. |
| **Validation: `responsive: true`** | Without the `{ responsive: true }` config object, the Plotly chart does not resize with the window, breaking the full-bleed layout on any viewport change. `_validate_html()` rejects HTML that uses Plotly but omits the word `responsive`. |
| **R13 mandatory animation playback** | Static "show final state" plots are not useful for physics simulations. The pre-computed trajectory array + `requestAnimationFrame` loop pattern gives consistent, memory-safe animation across all simulation types. |
| **R13 `function` declarations for RAF callbacks** | The LLM was generating `const step = () => {...}` for the animation callback. Arrow functions assigned to `const`/`let` are not hoisted, so `requestAnimationFrame(step)` called at load time found `step` undefined — causing a "step is not a function" runtime error and a frozen still frame. The prompt now requires `function step() {}` declarations. `_validate_html()` detects and rejects any HTML where a `requestAnimationFrame` callback name is declared as `const`/`let` instead of `function`. |
| **R14 duration slider** | Users frequently want to explore longer or shorter time ranges. The slider changes `t_max` and triggers a full trajectory recompute, so physics remain accurate at any duration. |
| **R15 physics parameter sliders** | The core interactive value of the visualizer — letting users explore how changing mass, charge, field strength, etc. changes the simulation — without needing to re-run the full LIPS pipeline. |
| **Validation: `DOMContentLoaded`** | The LLM occasionally initialises Plotly or reads DOM elements at the top level of a `<script>` block, before the DOM exists. `_validate_html()` rejects HTML that doesn't contain `DOMContentLoaded`, triggering the retry loop. |
| **Validation: `position:fixed` on plot div** | Tailwind's `h-screen` / `h-full` classes resolve to `0px` inside an iframe. Without an explicit `position:fixed;inset:0;width:100%;height:100%` inline style, the Plotly container has zero height and renders nothing — producing a blank white page. `_validate_html()` rejects HTML missing this inline style. |
| **`_SKIP_DIRS` excludes Python visualization dirs** | LIPS-generated code often includes a Python `visualization/` or `plot/` directory containing matplotlib code. Sending this to the LLM alongside the physics code caused it to mirror the matplotlib approach (static images) rather than building an interactive Plotly.js page. These directories are now excluded from `_build_prompt()`. |
