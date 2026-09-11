---
name: mermaid-diagram
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
| Max retry iterations | 3 |
| Output | Fenced `mermaid` code block + one-line explanation |

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

**If PASS:** Present the Mermaid diagram to the user (Step 6).

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

## Step 6 — Present Output

Present the final Mermaid diagram in a fenced code block:

````markdown
```mermaid
<diagram code here>
```
````

Follow with:
- One sentence explaining what the diagram shows
- An offer: "Want me to adjust anything? I can also change direction (top-down vs left-right), add/remove components, or annotate edges with more detail."

If the user asks for modifications, treat the updated diagram as a new prompt and re-run the full pipeline (Step 1–5) with the modification request + the current diagram as context.

---

## Diagram Type Reference

For quick classification when the Analyst's type differs from what you expected:

| User says... | Likely type |
|---|---|
| flow, process, steps, if/else, decision | `flowchart` |
| API call, request/response, message, auth, token exchange | `sequenceDiagram` |
| cloud, AWS, Azure, GCP, services, infrastructure, platform | `architecture-beta` |
| database, table, schema, foreign key, entity, ER | `erDiagram` |
| class, object, inheritance, interface, UML | `classDiagram` |

---

## Error Handling

- If an agent fails to return in the expected format, extract what you can and continue. Do not re-dispatch unless the output is completely unusable.
- If the Mermaid code contains obvious syntax errors (mismatched brackets, HTML tags in labels, reserved keywords as node IDs), fix them inline before dispatching the Validator. This is not a validation loop — it's a syntax repair.
- If the user provides feedback after seeing the diagram, treat it as a modification request (not a new diagram) unless they explicitly ask to start over.
