---
name: mermaid-diagram
version: "2.0"
authors:
  - name: Ratheesh Nellikal
description: "Generate Mermaid diagrams from natural language or faithfully replicate an architecture diagram from a screenshot using a transcription audit plus a 3-agent pipeline (Analyst → Builder → Validator with auto-retry). Use when: creating flowcharts, architecture diagrams, sequence diagrams, ER schemas, data pipelines, class diagrams, redrawing an existing architecture diagram, reproducing a diagram from a screenshot, or converting a screenshot into Mermaid. Renders directly in .md files and CoCo presentations. Triggers: diagram, flowchart, architecture diagram, sequence diagram, flow, draw, visualize system, ER diagram, class diagram, data pipeline diagram, mermaid, create a diagram, make a diagram, screenshot, pasted image, paste a diagram, replicate, redraw, recreate this diagram, reproduce a diagram, convert a screenshot."
---

# Mermaid Diagram Generator

Converts a natural language description into a validated Mermaid diagram, or faithfully replicates an architecture-diagram screenshot into Mermaid, using a transcription audit plus specialized Analyst, Builder, and Validator agents. The Auditor checks the source representation before build work begins, and the Validator checks the Mermaid output against the active source of truth with automatic retries.

---

## Quick Reference

| Item | Value |
|---|---|
| Skill root | `SKILL_DIR` (the directory containing this file) |
| Agent prompts | `SKILL_DIR/agents/` |
| Syntax references | `SKILL_DIR/references/` |
| Templates | `SKILL_DIR/templates/` |
| Snowflake brand icons | `SKILL_DIR/assets/icons/` (registry: `references/snowflake-icons.md`) |
| Post-processing scripts | `SKILL_DIR/scripts/` |
| Audit retry iterations | 3 |
| Builder/validator retry iterations | 3 |
| Worst-case dispatch ceiling | Roughly 10 subagent dispatches |
| Output | SVG file + image reference injected into target `.md` |

---

## Step 0 — Mode Detection and Ground Truth (Always First)

Before dispatching any agent, detect the mode once and keep it for the life of the diagram.

**Routing is deterministic:**

- If the current request includes an image attachment or pasted image, route to **REPLICATE**.
- If the current request includes no image, route to **GENERATE**.

Do not use word count to choose the mode. A pasted screenshot with two words is still REPLICATE.

**Mode stickiness is mandatory:**

- Persist the diagram's `mode`, the latest post-audit transcription, and the substitution ledger for the life of the diagram.
- A follow-up change request such as "fix box 3" or "rename the consumer node" re-enters the same mode even if that follow-up turn carries no image.
- Do not silently fall back to GENERATE on a follow-up turn. Reuse the preserved mode and carry the preserved transcription and ledger forward when you re-run the pipeline.

**When both an image and text are supplied:**

- In REPLICATE mode, the image is authoritative for visible structure: labels, grouping, nesting, edge endpoints, and any tint that visibly encodes identity.
- The text is supplemental context: terminology, requested emphasis, or explicit changes the user wants beyond the screenshot.
- If the text conflicts with the image, stop and ask the user which should win before dispatching any agent. Do not let only the text reach the agents and do not resolve the conflict silently.

**Reject non-diagram images:**

- If the image is a photo, chart, table, UI screenshot, or otherwise not an architecture diagram, say so and stop.
- Do not transcribe non-diagram imagery into nodes.

**GENERATE-only vagueness check:**

- Apply the old clarifying-question rule only in GENERATE mode.
- A prompt is too vague if it has fewer than ~8 words AND contains no named system, service, person, or entity (for example, "make a diagram" with nothing else).
- If vague: ask ONE clarifying question — "What are the main components or actors involved, and how do they interact?"
- If sufficient detail exists: proceed immediately. Do not ask questions you can infer.

---

## Step 0a — Resolve and Copy the Source Image (REPLICATE Only)

Skip this step in GENERATE mode.

Before transcribing, resolve the source image path and make a durable project copy.

- If the user pasted an image and refers to "the image just pasted", first treat CoCo's persisted image directory as a convenience path only: `~/.snowflake/cortex/conversations/<conversation-id>/images/<session-id>/`.
- Filenames in that directory contain spaces, for example `Pasted Image-<uuid>.png`. Quote every path you pass to shell commands.
- Resolve the intended image as the newest file by modification time.
- Read the chosen image and report exactly which file was selected together with its pixel dimensions so a mis-resolution is visible.
- Treat "no image found" as a normal branch. This directory is a CoCo implementation detail and may change across versions; do not assume it exists.

Establish the diagram slug now and keep it fixed for the rest of the run:

- If the user supplied meaningful text, derive the slug from that text as described in Step 6.
- If the request is image-only, derive the slug from a visible diagram title or top-level group label if one is legible in the source image.
- If no stable title is legible, use `replicated-diagram`.

If a concrete source image path is available:

- Copy it to `<project>/diagram-sources/<slug>.png` and use that project copy for Stage A of the audit and for the later back-check.
- The app-owned copy under `~/.snowflake/cortex/conversations/...` is session-scoped and not durable; do not audit against it directly once the project copy exists.

If no concrete source image path is available:

- Continue with main-session transcription from the image present in the request.
- Mark the audit as **DEGRADED** up front, because Stage A cannot run without an image path.
- Never present that run as fully audited.

---

## Step 0b — Transcribe the Source Diagram (REPLICATE Only)

Skip this step in GENERATE mode.

The orchestrator reads the image in the main session and produces the transcription. The image binary is never handed to a subagent.

The transcription is a contract consumed by the Auditor and the Validator, so it must be structured JSON, not free-form prose:

```json
{
  "elements": [
    {
      "id": "<stable identifier>",
      "label": "<visible label>",
      "type": "<service | database | person | decision | icon-bearing box | unknown>",
      "parent_group": "<immediate group label or ''>",
      "nesting_depth": 0
    }
  ],
  "edges": [
    {
      "from": "<element id>",
      "to": "<element id>",
      "label": "<visible edge label or ''>"
    }
  ],
  "groups": [
    {
      "label": "<group label>",
      "depth": 0,
      "styling_tint_intent": "<identity-bearing tint or decorative tint intent or ''>"
    }
  ],
  "non_diagram_content": [
    "<cursor, comment button, toolbar, selection handle, watermark, cropped partial box>"
  ],
  "uncertainties": [
    "<specific unresolved reading issue>"
  ],
  "ledger_candidates": [
    {
      "source_feature": "<what the source showed>",
      "substitution": "<what Mermaid must produce instead>",
      "reason": "<why the source cannot be reproduced exactly>"
    }
  ]
}
```

Rules:

- Enumerate every diagram element, edge, and group explicitly so they can be counted later.
- Exclude application chrome: cursors, comment buttons, toolbars, selection handles, watermarks, and cropped partial boxes are not diagram content.
- Record any visual distinction that Mermaid cannot reproduce in `ledger_candidates` so it flows into the substitution ledger instead of disappearing.
- Preserve visible nesting depth. Do not flatten the source structure during transcription.

Store this transcription. It persists with the diagram and is reused on follow-up modifications in REPLICATE mode.

---

## Step 0c — Two-Stage Audit Before Build

This audit gates downstream work. It is separate from the Validator and has its own retry cap of 3. Combined with the Builder/Validator cap of 3, a worst-case run is roughly 10 subagent dispatches. Users should not discover that cost by surprise.

### REPLICATE mode

Read `agents/transcription-reader-prompt.md` and `agents/transcription-auditor-prompt.md` from `SKILL_DIR/agents/`.

**Stage A — Independent Reader**

Dispatch a `generalPurpose` subagent using the Task tool. Pass the following as the subagent prompt:

```
[CONTENT OF agents/transcription-reader-prompt.md]

---
IMAGE PATH:
<absolute path to the project copy from Step 0a>
```

Stage A dispatch rules:

- Pass the image path only.
- Do not include the orchestrator transcription.
- Do not include Mermaid code, neighboring filenames, or any other hint about the diagram contents.
- Independence is structural, not merely requested.
- Stage A must write its JSON reading to a file before Stage B begins.

**If no image path resolved in Step 0a:**

- Stage A cannot run.
- State plainly in the output that the audit is **DEGRADED** because no durable image path was available for the independent reader.
- Continue only with that disclosure. Never present the run as audited.

**Stage B — Comparison Auditor**

If Stage A ran, dispatch a `generalPurpose` subagent with:

```
[CONTENT OF agents/transcription-auditor-prompt.md]

---
MODE: REPLICATE

ORCHESTRATOR TRANSCRIPTION:
<paste the JSON transcription from Step 0b>

STAGE A READING:
<paste the JSON written by Stage A>
```

The Auditor must return:

```text
VERDICT: PASS | FAIL
DISCREPANCIES:
- classification: STRUCTURAL | STYLING
  element: <specific element, edge, or group>
  reading_a: <what one reading says>
  reading_b: <what the other reading says>
  suggested_correction: <actionable correction or operator-arbitration note>
```

Classification rule: the test is whether the discrepancy changes what the diagram asserts.

- `STRUCTURAL` blocks: missing, extra, or misattributed element; wrong edge endpoint; wrong nesting parent; missing or extra relationship that changes meaning; an edge label that changes the relationship's meaning; or a tint that encodes identity such as Azure vs AWS.
- `STYLING` advises only: palette, font, spacing, meaning-preserving wording, or tint with no identity payload.

Retry rules:

- If Stage B returns `VERDICT: PASS`, proceed to Step 1.
- If Stage B returns `VERDICT: FAIL` with any `STRUCTURAL` discrepancy and the audit attempt count is less than 3, correct the orchestrator transcription in the main session and re-run Stage B against the unchanged Stage A reading.
- If the two readings disagree and neither is demonstrably right from the available evidence, stop and ask the user to arbitrate. Do not silently pick one.
- If the audit still fails after 3 attempts, stop and present the unresolved discrepancies to the user. Never silently proceed.

### GENERATE mode

The audit still runs, but it is text-to-text rather than vision-based. Dispatch it after the Analyst returns the brief and before the Builder runs. See Step 1b.

---

## Step 1 — Dispatch Agent 1: Analyst

Read the file `agents/analyst-prompt.md` from SKILL_DIR.

Dispatch a `generalPurpose` subagent using the Task tool. Pass the following as the subagent prompt:

```
[CONTENT OF agents/analyst-prompt.md]

---
MODE:
<GENERATE or REPLICATE>

USER PROMPT:
<paste the user's original prompt verbatim>

CONVERSATION CONTEXT (if any prior turns are relevant):
<any relevant prior context — system names already mentioned, constraints stated, etc.>

POST-AUDIT TRANSCRIPTION (REPLICATE mode only):
<paste the corrected JSON transcription from Step 0c, or "N/A">

AUTHORITATIVE GROUND-TRUTH NOTE:
<for REPLICATE: "Image-authoritative for visible structure; follow any explicit user conflict resolution"; for GENERATE: "Written requirement only">
```

The Analyst returns a **Structured Brief** in this format:
```json
{
  "diagram_type": "flowchart | sequenceDiagram | architecture-beta | erDiagram | classDiagram",
  "direction": "TD | LR | BT | RL",
  "components": ["ComponentA", "ComponentB", "..."],
  "relationships": [
    {"from": "ComponentA", "to": "ComponentB", "label": "description of the link"}
  ],
  "groupings": ["group-name: [ComponentA, ComponentB]"],
  "notes": "any special formatting or styling requirements",
  "ambiguities": ["unclear thing 1", "unclear thing 2"]
}
```

Store this brief. You will pass it to every downstream agent.

In REPLICATE mode, the post-audit transcription is the source of truth for the brief. The Analyst should preserve source direction, grouping density, and nesting depth instead of normalizing them away.

If the brief contains `ambiguities` with more than 2 items and they materially affect what the diagram should show, ask the user to clarify before proceeding. Otherwise proceed with what's known.

---

## Step 1b — Audit the Analyst Brief (GENERATE Only)

Skip this step in REPLICATE mode; REPLICATE already completed the audit in Step 0c.

Read `agents/transcription-auditor-prompt.md` from `SKILL_DIR/agents/`.

Dispatch a `generalPurpose` subagent using the Task tool. Pass:

```
[CONTENT OF agents/transcription-auditor-prompt.md]

---
MODE: GENERATE

OPERATOR REQUIREMENT:
<paste the user's original prompt verbatim>

ANALYST BRIEF:
<paste the JSON brief from Step 1>
```

Use the same `VERDICT: PASS | FAIL` and classified discrepancy contract described in Step 0c.

- If the Auditor returns `VERDICT: PASS`, proceed to Step 2.
- If the Auditor returns `VERDICT: FAIL` with any `STRUCTURAL` discrepancy and the audit attempt count is less than 3, re-dispatch the Analyst with the same user prompt plus the audit discrepancies and the prior brief, then re-run this step.
- If the brief and the written requirement disagree and neither side can be resolved confidently from the prompt, ask the user to arbitrate. Do not let the Builder proceed on a silent assumption.
- If the audit still fails after 3 attempts, stop and present the unresolved discrepancies to the user. Do not build.

---

## Step 2 — Load the Syntax Reference

Based on `diagram_type` from the brief, load the matching reference file from SKILL_DIR:

| diagram_type | Reference file |
|---|---|
| `flowchart` | `references/flowchart-syntax.md` |
| `sequenceDiagram` | `references/sequence-syntax.md` |
| `architecture-beta` | `references/architecture-syntax.md` |
| `erDiagram` | `references/er-syntax.md` |
| `classDiagram` | `references/er-syntax.md` (class section) |

Read the relevant reference file. You will pass its contents to the Builder agent.

Also check if a matching template exists in `SKILL_DIR/templates/` for the diagram type and load it too if present. Templates are working examples the Builder can use for structural guidance.

---

## Step 2b — Snowflake brand icons (opt-in)

Diagrams default to plain styled nodes. Official Snowflake icons are available but are **never applied automatically** — using them changes the render pipeline (an extra post-processing step) and constrains labels, so it has to be a deliberate choice.

Use icons when **either**:
- The user explicitly asks for them ("use the Snowflake icons", "brand this", "use the template icons"), **or**
- The diagram is Snowflake-specific *and* the user has opted in earlier in the conversation.

If the diagram is clearly Snowflake architecture and the user has not expressed a preference, ask once with `ask_user_question`:
- "Use official Snowflake brand icons for the Snowflake objects, or plain styled boxes?"
  - "Brand icons" — description: "Official icons from the Snowflake template for databases, dynamic tables, warehouses etc."
  - "Plain boxes" — description: "Current default. Shorter pipeline, labels can be longer."

Do not ask this for non-Snowflake diagrams — there are no icons for them.

**If icons are in use:** read `references/snowflake-icons.md` and pass its full contents to the Builder alongside the syntax reference. It carries the registry, the image-shape syntax, and the label constraints. Resolve `SKILL_DIR` to an absolute path before passing it, because `img:` paths must be absolute at render time.

**If icons are not in use:** skip this step entirely and do not mention it.

---

## Step 3 — Dispatch Builder (iteration = 1)

Read `agents/builder-prompt.md` from SKILL_DIR.

Dispatch a `generalPurpose` subagent. Pass:

```
[CONTENT OF agents/builder-prompt.md]

---
STRUCTURED BRIEF:
<paste the JSON brief from Agent 1>

POST-AUDIT TRANSCRIPTION (REPLICATE mode only):
<paste the corrected JSON transcription from Step 0c, or "N/A">

SUBSTITUTION LEDGER CANDIDATES (REPLICATE mode only):
<paste the ledger candidate list from the transcription, or "None yet">

SYNTAX REFERENCE:
<paste the contents of the relevant syntax reference file>

TEMPLATE EXAMPLE (if available):
<paste the relevant template file contents, or "None available">

ITERATION: 1
VALIDATOR ISSUES FROM PRIOR ITERATION: None
```

The Builder returns:
- A fenced ```` ```mermaid ```` code block containing the complete diagram
- Optionally: a single line of explanation after the block

Store the Mermaid code.

In REPLICATE mode, turn `ledger_candidates` plus any additional Mermaid-imposed substitutions visible in the generated code into the current substitution ledger before Step 4. The ledger is allowed to evolve across Builder iterations, but it must exist before validation so the Validator can check whether every deviation is accounted for.

Proceed to Step 4.

---

## Step 4 — Dispatch Validator

Read `agents/validator-prompt.md` from SKILL_DIR.

Dispatch a `generalPurpose` subagent. Pass:

```
[CONTENT OF agents/validator-prompt.md]

---
ORIGINAL USER PROMPT (verbatim — do not paraphrase):
<paste the user's original prompt>

STRUCTURED BRIEF:
<paste the JSON brief from Agent 1>

POST-AUDIT TRANSCRIPTION (REPLICATE mode only):
<paste the corrected JSON transcription from Step 0c, or "N/A">

SUBSTITUTION LEDGER:
<paste the current substitution ledger, or "None">

MERMAID CODE TO VALIDATE:
<paste the Mermaid code block from Agent 2>

ITERATION: <current iteration number>
```

The Validator returns one of:

**PASS:**
```
VERDICT: PASS
NOTES: <optional brief comment on quality>
```

**FAIL:**
```
VERDICT: FAIL
ISSUES:
- [issue 1 — specific and actionable]
- [issue 2]
SUGGESTIONS:
- [how to fix issue 1]
- [how to fix issue 2]
```

---

## Step 5 — Loop or Output

**If PASS:** Proceed to Step 6.

**If FAIL and iteration < 3:**
- Increment the iteration counter
- Dispatch Agent 2 again (Step 3) with the updated prompt:

```
[CONTENT OF agents/builder-prompt.md]

---
STRUCTURED BRIEF:
<same brief>

POST-AUDIT TRANSCRIPTION (REPLICATE mode only):
<same corrected transcription, or "N/A">

SUBSTITUTION LEDGER CANDIDATES (REPLICATE mode only):
<same ledger candidates, or "None yet">

SYNTAX REFERENCE:
<same syntax reference>

TEMPLATE EXAMPLE (if available):
<same template>

ITERATION: <new iteration number>
VALIDATOR ISSUES FROM PRIOR ITERATION:
<paste the ISSUES and SUGGESTIONS from the Validator>
PRIOR MERMAID CODE (for reference — fix the specific issues, do not rewrite from scratch):
<paste the prior Mermaid code>
```

Return to Step 4 with the new output.

**If FAIL and iteration = 3:**
- Present the diagram to the user with the Validator's issues listed
- Say: "Here's the best version after 3 iterations. The Validator flagged these remaining issues: [list]. Would you like me to address any specific one?"

---

## Step 6 — SVG Export and .md Injection

After validation passes, ask the user where to insert the diagram. Use `ask_user_question` with both questions in the same call:
- Question 1 (`options`): "Where should I insert the diagram?"
  - Option A: "Create a new .md file" — description: "A new {slug}.md will be created in the current working directory"
  - Option B: "Insert into an existing .md" — description: "You provide the path to an existing markdown file"
- Question 2 (`text`): "If inserting into an existing file, provide the path (ignored if creating new):" with default value `README.md`

In REPLICATE mode, the faithful replica is the primary deliverable. Do not substitute a more readable variant during this step. Offer the readable variant only after the faithful replica has been rendered, checked, and saved.

Derive a slug once and keep it for the whole run:

- In GENERATE mode, derive it from the first 6 meaningful words in the user's original prompt.
- In REPLICATE mode, prefer meaningful words from any accompanying text. If the request was image-only, use the visible title or top-level group label captured during Step 0a; if none is stable, use `replicated-diagram`.
- Skip filler words: `a`, `an`, `the`, `draw`, `create`, `make`, `show`. Convert the remaining words to kebab-case.

Example:
- "draw a Kafka to Snowflake streaming pipeline" → `kafka-to-snowflake-streaming-pipeline`

Determine paths as follows:
- `project_dir`: the current working directory where the skill was invoked
- `diagram_source_dir`: `{project_dir}/diagram-sources`
- `target_dir`: the directory of the existing `.md` path if the user chose Option B, otherwise the current working directory
- `mmd_path`: `{target_dir}/{slug}.mmd`
- `svg_path`: `{target_dir}/{slug}.svg`
- `md_path`: the user-supplied path if the user chose Option B, otherwise `{target_dir}/{slug}.md`

If the user chose Option B, confirm `{md_path}` exists before writing any files. If it does not exist, report the missing path to the user and ask for a corrected one — do not write `.mmd` or run `mmdc`.

Before writing `{mmd_path}`, replace any literal `\n` sequences inside quoted node labels with `<br/>` — `mmdc` renders `\n` as literal text in SVG, while `<br/>` produces a real line break.

Write the corrected Mermaid code to `{mmd_path}` using the Write tool. Write only the raw Mermaid diagram source, not a fenced code block.

Run `mmdc` from `target_dir` using:

```bash
cd "{target_dir}" && mmdc -i "{slug}.mmd" -o "{slug}.svg"
```

If the command exits non-zero, surface the error to the user and stop. Do not proceed to `.md` injection.

### Box normalization — use for flowcharts, but document the real skip cases

Mermaid sizes every node to its own text and offers no node-width property, so
peer nodes doing the same job come out at different widths. Measured on a
five-stage flowchart: box widths 203.73–228.52px, aspect ratios 2.61–2.93, and
group rects 530.62–561.19px wide. The diagram reads as sloppy even when the
node centres are mathematically exact.

Author-side label tuning narrows the spread but cannot close it. Run this pass to
square up the geometry:

```bash
python3 "SKILL_DIR/scripts/normalize-boxes.py" "{target_dir}/{slug}.svg"
```

It always normalizes node widths when it finds flowchart nodes. Cluster widening
is conditional: it gives stacked group rects a common x and width with their
titles re-centred, but it does **not** widen side-by-side sibling groups, and on
nested diagrams it reports the cluster pass as skipped instead of pretending it
ran. The pass is idempotent and works on both the default HTML-label path and
`htmlLabels: false`.

It also **grows the SVG viewBox when widening pushes a group border past the
canvas edge.** `mmdc` sizes the viewBox from the pre-normalization geometry, so
without this the left and right borders of every stacked band are silently
clipped — measured at 13.71px lost on the left and 51.45px on the right of a
five-band diagram whose groups were widened to x -13.71 width 1552.95 against a
viewBox of 0 .. 1487.78. The `max-width` that `mmdc` writes beside the viewBox is
kept in sync. Nothing is ever shrunk, so a diagram that already fits is untouched.

**Groups that sit side by side are left alone.** Sibling subgraphs on the same
rank share a vertical band; giving them a common x and width slams them on top of
each other and one border disappears completely, so the two groups read as one.
The pass only widens a group that is alone in its band. Verified against a
diagram with two sibling CX-managed account groups: both keep their own geometry
while the four stacked groups are squared up.

On nested output, expect an explicit summary line like:

```text
normalize-boxes: ... cluster normalization skipped for nested diagram (... clusters skipped)
```

That is the real behavior. Do not describe cluster normalization as mandatory in
a mode where the script honestly skips it.

Add `--square-columns` to also snap node columns to a common x:

```bash
python3 "SKILL_DIR/scripts/normalize-boxes.py" "{target_dir}/{slug}.svg" --square-columns
```

This is **opt-in** and only appropriate for a clean two-column layout such as the
hub-and-companion pattern, where it takes column spread to 0.00px. Column
detection is by x-proximity, so on a wide multi-column graph it can merge columns
that should stay distinct. Nodes an edge terminates on are never moved either
way, so baked edge paths cannot be left dangling.

`--strict` is a verification switch, not the normal render path:

```bash
python3 "SKILL_DIR/scripts/normalize-boxes.py" "{target_dir}/{slug}.svg" --strict
```

With `--strict`, the script exits `2` when the SVG would be unchanged and prints:

```text
normalize-boxes: --strict, exiting 2 because the SVG was unchanged
```

If no flowchart nodes are found, it prints `normalize-boxes: no flowchart nodes found; nothing to do`; with `--strict`, that branch also exits `2`. Treat exit `0` as success and exit `2` as an unchanged-file signal, not as a broken render.

Do not try to do this with `themeCSS`. It is applied to the live DOM only — it
changes a rasterized PNG but never reaches the exported SVG, and Mermaid strips
it from frontmatter `config:` as unsafe. The geometry has to be written into the
attributes after the fact.

### Icon inlining — mandatory when icons are used

Skip this if the diagram uses no icons.

`mmdc` writes image shapes as `href="/absolute/path/icon.png"` with `preserveAspectRatio="none"`. The absolute path does not survive the SVG being moved or shared and markdown previews generally refuse to load it; the forced aspect ratio stretches each icon to a box that was sized from the label. Both must be corrected:

```bash
python3 "SKILL_DIR/scripts/inline-icons.py" "{target_dir}/{slug}.svg"
```

Then confirm no filesystem references survive:

```bash
grep -c 'href="/' "{target_dir}/{slug}.svg"
```

This must print `0`. If it prints anything else, an `img:` path was wrong — the icons will render broken. Fix the path in `{slug}.mmd`, re-run `mmdc`, and re-run the inliner before continuing.

### Edge routing check — before rendering

Confirm the `.mmd` frontmatter sets `curve: stepAfter` for any architecture,
platform, or infrastructure diagram. All three `step` variants give orthogonal
right-angle edges (measured 100% axis-aligned segments), but they differ sharply
in bend count: `stepAfter` 18 total bends, `stepBefore` 21, `step` 39 — `step`
never manages fewer than 3 per turning edge. `linear` is 84% axis-aligned and the
diagonal remainder reads as zig-zag; Mermaid's unset default `basis` gives loose
curves. If it is missing or set to anything else, fix it and re-render — it
changes only edge paths, never node placement or aspect ratio.

**Do not promise one bend per edge.** Bend count is dagre's, not the curve's: an
edge that changes rank and moves sideways gets a mid-flight waypoint and costs two
bends. Reducing it further is structural, not styling. `layout: elk` is measured
worse. Full measurements and the reasoning in `agents/builder-prompt.md`.

### Subgraph title margin check — before rendering

Confirm the `.mmd` frontmatter sets `subGraphTitleMargin` for any diagram that
uses subgraphs:

```
config:
  flowchart:
    subGraphTitleMargin:
      top: 4
      bottom: 24
```

Mermaid reserves the height of one title line. A title that wraps therefore
drops its second line onto the first child node, and that child box lands on the
cluster's top border — which renders as arrows and boxes merging into the border.
Measured on a 12-cluster diagram: `bottom: 24` is the smallest value that fully
clears a two-line title, and it costs 28px on a 1266px canvas. Set it
unconditionally; do not try to predict which titles will wrap.

A tspan scan will **not** catch this defect. The colliding line is present in the
markup, just painted under the child box, so parsing reports the title as
complete. Rasterize and look.

### Aspect ratio check and legibility guard

Exported SVGs carry `width="100%"` and scale to their container, so an over-wide diagram shrinks its own text into illegibility. Verify the rendered aspect ratio before injecting:

```bash
grep -o 'viewBox="[^"]*"' "{target_dir}/{slug}.svg" | head -1
```

The viewBox is `min-x min-y width height`. Divide width by height.

**GENERATE mode keeps the existing hard block.** If the ratio exceeds **2.5**, the diagram will not be readable at normal markdown width. Do not inject it. Instead:

1. Rebuild the diagram as `flowchart TB` so the groups stack vertically — this is the only reliable lever on aspect ratio. See the layout-direction rules in `agents/builder-prompt.md`
2. Reduce nodes per group to 2–4. Inner `direction LR` will not spread them horizontally once a group has any edge crossing its boundary, so each extra node adds a row of height
3. Keep stage-to-stage edges node to node, never to a subgraph ID
4. Re-render and re-check

If the ratio is still above 2.5 after restructuring, tell the user the diagram has too many parallel stages to render legibly in one image and offer to split it into two diagrams.

**REPLICATE mode is exempt from three readability rules that GENERATE still uses:**

1. the aspect-ratio `> 2.5` hard block in this step
2. `agents/builder-prompt.md`'s rule "Never emit a `flowchart LR` with 4 or more subgraphs"
3. the Analyst's TD-forcing and node-dropping rules for 4+ groups or 6+ nodes inside a group

In REPLICATE mode, replace those blocks with a non-blocking legibility guard:

- Measure and report the post-audit node count, the maximum nesting depth, and the rendered canvas ratio.
- Warn if the diagram is likely to read poorly at normal markdown width.
- Report renderer defects such as cluster-label overlap here, not in the substitution ledger.
- Deliver the faithful replica anyway.
- Offer a separate readable variant afterwards if the user wants one, but never substitute it automatically.

### Substitution ledger — required in REPLICATE mode

Prepare the substitution ledger alongside the diagram and include it in the final response. Each entry must say:

- what the source showed
- what was produced instead
- why the substitution was necessary

At minimum, capture these entries when they apply:

1. vertical stacking instead of horizontal sibling database sub-boxes
2. generic icons or text labels instead of cloud-provider logos
3. a single icon instead of a source node that carried two icons

Do not use the ledger for renderer defects. Those belong in the legibility guard report. Note that the cluster-label collision is **not** a renderer defect to be reported — it is fixed by `subGraphTitleMargin`, see the subgraph title margin check.

### Reconciliation — required in REPLICATE mode

Reconcile the rendered Mermaid diagram against the **post-audit transcription**. Count transcribed elements, edges, and groups against what is represented in the final diagram plus what is explicitly explained in the substitution ledger.

- Every transcribed element, edge, and group must be either present or ledger-accounted.
- No unexplained remainder is allowed.
- Write this reconciliation to a project-local file before delivery so the accounting is inspectable.

### Visual back-check — required in REPLICATE mode

After rendering, the orchestrator must visually compare the rendered output against the source image and write the observed differences to a file before delivery.

- This is the **secondary** fidelity check. It catches Builder or renderer faults that the Auditor never sees.
- Self-attestation with no artifact is not sufficient.
- If the audit was degraded because Step 0a could not resolve an image path, say so plainly here as well. Do not present the run as fully audited.

Inject the image reference into markdown:

- If the user chose Option A, write a new `{md_path}` containing:

  ```markdown
  # {Human-readable title — capitalize the slug words}

  ![{slug}](./{slug}.svg)
  ```

- If the user chose Option B, read the existing file and append the following, ensuring a blank line separates it from the existing content:

  ```markdown

  ## {Human-readable title}

  ![{slug}](./{slug}.svg)
  ```

Then confirm success to the user with:
- "Diagram saved as `{slug}.svg` and inserted into `{md_path}`."
- "`{slug}.mmd` is kept alongside the SVG for future edits."
- In REPLICATE mode, include the substitution ledger, the reconciliation summary, the back-check file location, and whether the audit was full or DEGRADED.
- In REPLICATE mode, offer a readable variant only after presenting the faithful replica.
- "To update the diagram, re-run `$mermaid-diagram` with your changes."

If the user asks for modifications, treat the updated diagram as a modification request rather than a new mode-detection event. Re-run the full pipeline in the diagram's existing mode: REPLICATE stays REPLICATE and GENERATE stays GENERATE. Carry forward the current source copy, the latest post-audit transcription, and the substitution ledger as context instead of re-detecting from the follow-up turn alone.

---

## Diagram Type Reference

For quick classification when the Analyst's type differs from what you expected:

| User says... | Likely type |
|---|---|
| flow, process, steps, if/else, decision | `flowchart` |
| API call, request/response, message, auth, token exchange | `sequenceDiagram` |
| cloud, AWS, Azure, GCP, services, infrastructure, platform | `flowchart LR (styled)` |
| database, table, schema, foreign key, entity, ER | `erDiagram` |
| class, object, inheritance, interface, UML | `classDiagram` |

---

## Error Handling

- If an agent fails to return in the expected format, extract what you can and continue. Do not re-dispatch unless the output is completely unusable.
- If the Mermaid code contains obvious syntax errors (mismatched brackets, HTML tags in labels, reserved keywords as node IDs), fix them inline before dispatching the Validator. This is not a validation loop — it's a syntax repair.
- If the user provides feedback after seeing the diagram, treat it as a modification request (not a new diagram) unless they explicitly ask to start over.
