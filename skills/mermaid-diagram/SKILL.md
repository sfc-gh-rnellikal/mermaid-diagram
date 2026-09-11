---
name: mermaid-diagram
version: "1.2"
authors:
  - name: Ratheesh Nellikal
description: "Generate Mermaid diagrams from natural language using a 3-agent pipeline (Analyst → Builder → Validator with auto-retry). Use when: creating flowcharts, architecture diagrams, sequence diagrams, ER schemas, data pipelines, class diagrams. Renders directly in .md files and CoCo presentations. Triggers: diagram, flowchart, architecture diagram, sequence diagram, flow, draw, visualize system, ER diagram, class diagram, data pipeline diagram, mermaid, create a diagram, make a diagram."
---

# Mermaid Diagram Generator

Converts a natural language description into a validated Mermaid diagram using three specialized agents. The Validator checks the output against the original requirements and triggers automatic retries, making the result accurate and complete.

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
| Max retry iterations | 3 |
| Output | SVG file + image reference injected into target `.md` |

---

## Step 0 — Pre-check (Always First)

Before dispatching agents, check one thing:

**Is the user's prompt too vague to extract components?**

A prompt is too vague if it has fewer than ~8 words AND contains no named system, service, person, or entity (e.g. "make a diagram" with nothing else).

- If vague: ask ONE clarifying question — "What are the main components or actors involved, and how do they interact?"
- If sufficient detail exists: proceed to Step 1 immediately. Do not ask questions you can infer.

---

## Step 1 — Dispatch Agent 1: Analyst

Read the file `agents/analyst-prompt.md` from SKILL_DIR.

Dispatch a `generalPurpose` subagent using the Task tool. Pass the following as the subagent prompt:

```
[CONTENT OF agents/analyst-prompt.md]

---
USER PROMPT:
<paste the user's original prompt verbatim>

CONVERSATION CONTEXT (if any prior turns are relevant):
<any relevant prior context — system names already mentioned, constraints stated, etc.>
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

If the brief contains `ambiguities` with more than 2 items and they materially affect what the diagram should show, ask the user to clarify before proceeding. Otherwise proceed with what's known.

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

## Step 3 — Dispatch Agent 2: Builder (iteration = 1)

Read `agents/builder-prompt.md` from SKILL_DIR.

Dispatch a second `generalPurpose` subagent. Pass:

```
[CONTENT OF agents/builder-prompt.md]

---
STRUCTURED BRIEF:
<paste the JSON brief from Agent 1>

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

Store the Mermaid code. Proceed to Step 4.

---

## Step 4 — Dispatch Agent 3: Validator

Read `agents/validator-prompt.md` from SKILL_DIR.

Dispatch a third `generalPurpose` subagent. Pass:

```
[CONTENT OF agents/validator-prompt.md]

---
ORIGINAL USER PROMPT (verbatim — do not paraphrase):
<paste the user's original prompt>

STRUCTURED BRIEF:
<paste the JSON brief from Agent 1>

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

Derive a slug from the first 6 meaningful words in the user's original prompt. Skip filler words: `a`, `an`, `the`, `draw`, `create`, `make`, `show`. Convert the remaining words to kebab-case.

Example:
- "draw a Kafka to Snowflake streaming pipeline" → `kafka-to-snowflake-streaming-pipeline`

Determine paths as follows:
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

### Box normalization — mandatory for flowcharts

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

It sets every node rect to one width centred on its origin, squares up node
columns, and gives every group rect a common x and width with its title
re-centred. Columns an edge terminates on are left where they are, so baked edge
paths never end up dangling. The pass is idempotent and works on both the default
HTML-label path and `htmlLabels: false`.

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

### Aspect ratio check — mandatory

Exported SVGs carry `width="100%"` and scale to their container, so an over-wide diagram shrinks its own text into illegibility. Verify the rendered aspect ratio before injecting:

```bash
grep -o 'viewBox="[^"]*"' "{target_dir}/{slug}.svg" | head -1
```

The viewBox is `min-x min-y width height`. Divide width by height.

If the ratio exceeds **2.5**, the diagram will not be readable at normal markdown width. Do not inject it. Instead:

1. Rebuild the diagram as `flowchart TB` so the groups stack vertically — this is the only reliable lever on aspect ratio. See the layout-direction rules in `agents/builder-prompt.md`
2. Reduce nodes per group to 2–4. Inner `direction LR` will not spread them horizontally once a group has any edge crossing its boundary, so each extra node adds a row of height
3. Keep stage-to-stage edges node to node, never to a subgraph ID
4. Re-render and re-check

If the ratio is still above 2.5 after restructuring, tell the user the diagram has too many parallel stages to render legibly in one image and offer to split it into two diagrams.

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
- "To update the diagram, re-run `$mermaid-diagram` with your changes."

If the user asks for modifications, treat the updated diagram as a new prompt and re-run the full pipeline (Step 1–5) with the modification request + the current diagram as context.

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
