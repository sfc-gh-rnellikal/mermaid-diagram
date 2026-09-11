# Snowflake brand icons

Official icons extracted from **SNOWFLAKE TEMPLATE JANUARY 2026**, slides 71–72
("Icons: Reference Architecture") and slide 65. These are the brand-approved
icons — do not substitute lookalikes from other icon sets.

They live in `SKILL_DIR/assets/icons/` as 160×160 transparent PNGs.

---

## Registry

| Icon name | File | Use for |
|---|---|---|
| `database` | `database.png` | Generic / non-Snowflake database, OLTP source |
| `snowflake_database` | `snowflake_database.png` | A Snowflake database |
| `schema` | `schema.png` | Schema |
| `stream` | `stream.png` | Stream, CDC, change feed |
| `tag` | `tag.png` | Tag, object tagging |
| `task` | `task.png` | Task, scheduled job |
| `volume` | `volume.png` | External volume |
| `virtual_warehouse` | `virtual_warehouse.png` | Virtual warehouse, compute |
| `pipe` | `pipe.png` | Pipe, Snowpipe, ingestion |
| `role` | `role.png` | Role, RBAC principal |
| `policy` | `policy.png` | Generic policy |
| `policy_masking` | `policy_masking.png` | Masking policy |
| `view` | `view.png` | View |
| `view_secure` | `view_secure.png` | Secure view |
| `storage` | `storage.png` | Storage layer, stage |
| `table` | `table.png` | Standard table |
| `table_dynamic` | `table_dynamic.png` | Dynamic table |
| `table_iceberg` | `table_iceberg.png` | Iceberg table |
| `table_hybrid` | `table_hybrid.png` | Hybrid table (Unistore) |

Anything not in this list has no approved icon — use a plain styled node
rather than improvising one.

---

## Syntax

Mermaid image-shape syntax, supported in mmdc 11.3+:

```
NodeId@{ img: "<absolute-path>/assets/icons/<name>.png", label: "Node Label", pos: "b", w: 70, h: 70 }
```

- `img` must be an **absolute** path at render time. The post-processor
  converts it to an embedded data URI afterwards.
- `pos: "b"` puts the label below the icon; `"t"` puts it above. There is no
  option to place the label beside the icon.
- `w` and `h` set the image box. Keep both at `70` so icons stay uniform —
  these sources are square.

Edges attach to image nodes exactly as they do to normal nodes:

```
    MultiTenantDb --> DynamicTable --> Consumer
```

---

## Constraints worth knowing

**The node box is sized from the label, not the icon.** A node labelled
"Multi-Tenant Provider Database" renders a much wider box than one labelled
"Stage", even at identical `w`/`h`. Keep labels on icon nodes short — two or
three words — or the row looks ragged.

**No inline icon-plus-text.** The icon sits strictly above or below its label.
A boxed layout with the icon beside the text is not reachable in Mermaid.

**Sources are raster, ~80px of real detail.** Cropped from a 1600×900 slide
export, which is the maximum resolution Google Slides will serve. Crisp at
40–70px on screen; visibly soft much beyond that. Do not scale past `w: 90`.

**Icons are Snowflake Blue and Mid-Blue only.** Per brand rules on slide 63,
Snowflake icons may appear only in Snowflake Blue, Mid-Blue, White or Black.
Do not recolour them. Node fill and stroke still come from the palette
`classDef` rules, so pick fills that keep the blue icon legible — the light
palette tints all work.

---

## Styling icon nodes

Icon nodes still need `classDef` styling, otherwise they inherit Mermaid's
default purple border. Apply the standard palette exactly as for plain nodes:

```
flowchart TB
    subgraph provider["1 &nbsp; PROVIDER"]
        direction LR
        Db@{ img: "/abs/path/assets/icons/snowflake_database.png", label: "Multi-Tenant DB", pos: "b", w: 70, h: 70 }
        Dt@{ img: "/abs/path/assets/icons/table_dynamic.png", label: "Dynamic Table", pos: "b", w: 70, h: 70 }
        Db --> Dt
    end

    classDef sf fill:#E6F7F1,stroke:#2DBD8E,stroke-width:2px,color:#1a1a2e
    class Db,Dt sf
```

---

## Required post-processing

After `mmdc` runs, the SVG references icons by absolute filesystem path and
carries `preserveAspectRatio="none"`. Both must be corrected or the diagram
will not render outside the machine that built it:

```bash
python3 "SKILL_DIR/scripts/inline-icons.py" "{target_dir}/{slug}.svg"
```

The script embeds each PNG as base64 and restores proportional scaling. Verify
it worked — zero remaining filesystem references is the pass condition:

```bash
grep -c 'href="/' "{target_dir}/{slug}.svg"
```

This must print `0`. Anything else means an icon path was wrong and the
diagram will render with broken images.
