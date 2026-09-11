# Common Mermaid Patterns

Patterns that apply across multiple diagram types: subgraph grouping, notes, icons, click events, and cross-type tips.

## Universal Syntax Rules (All Types)

These rules apply to every diagram type:

1. **No spaces in node/participant IDs** — IDs must be single tokens
2. **Never use reserved keywords as IDs** — `end`, `subgraph`, `graph`, `flowchart`, `direction`
3. **Use `<br/>` for multi-line labels, never `\n`** — `\n` renders as literal text in SVG; `<br/>` renders as a real line break. Other HTML tags (`<b>`, `<i>`) still render as literal text — avoid them.
4. **Use the Snowflake brand palette via `classDef`** — assign major node groups with shared `classDef` and `class` rules. Up to five slots, each a pale tint over the full-strength brand stroke: `#D6EFFA/#11567F` Mid-Blue for sources and providers, `#E9F7FD/#29B5E8` Snowflake Blue for the core platform, `#EDE7F5/#7254A3` Purple Moon for replication and transport, `#E4F6F8/#75CDD7` Star Blue for the consumer side, `#FFF1E0/#FF9F36` Valencia Orange for downstream outputs. All classes use `stroke-width:2px,color:#000000`. Snowflake Blue and Mid-Blue carry the diagram; the other three are accents used sparingly. Give subgraphs `fill:#F5FBFE` with a `color:#11567F` title.
5. **Quote edge labels with special characters** — parentheses, slashes, colons, commas

## Subgraph / Grouping Patterns

### Flowchart Subgraph

```mermaid
flowchart LR
    subgraph ingestion [Ingestion Layer]
        Kafka["Kafka"]
        Snowpipe["Snowpipe"]
    end

    subgraph storage [Storage Layer]
        RawDB[("Raw Database")]
        CuratedDB[("Curated Database")]
    end

    Kafka --> Snowpipe
    Snowpipe --> RawDB
    RawDB --> CuratedDB
```

### Stacked Stages — hub and companion (preferred for pipelines)

For a multi-stage pipeline, give each group one **hub** node carrying both the
inbound and outbound edge, listed first, with **no internal edge** to its
companion. All hubs land in one column, producing a straight vertical spine with
every group left-aligned.

```mermaid
flowchart TB
    subgraph provider["1  PROVIDER REGION"]
        direction LR
        ProdDb["PROD_DB<br/><small>provider-owned database</small>"]
        SourceTbl["Source Tables<br/><small>CHANGE_TRACKING = TRUE</small>"]
    end

    subgraph publish["2  PUBLISH"]
        direction LR
        Listing["Private Listing<br/><small>auto-fulfillment enabled</small>"]
        Share["Secure Share<br/><small>backs the private listing</small>"]
    end

    ProdDb -->|"grant objects to share"| Listing

    classDef slot1 fill:#D6EFFA,stroke:#11567F,stroke-width:2px,color:#000000
    classDef slot2 fill:#E9F7FD,stroke:#29B5E8,stroke-width:2px,color:#000000
    class ProdDb,SourceTbl slot1
    class Listing,Share slot2

    style provider fill:#F5FBFE,stroke:#11567F,stroke-width:2px,color:#11567F
    style publish fill:#F5FBFE,stroke:#29B5E8,stroke-width:2px,color:#11567F
```

Adding `ProdDb --> SourceTbl` here would stack that pair into two rows and break
the spine. Note also that the subtitle lengths are within a few characters of one
another — that is what keeps the box edges aligned.

### Nested Subgraphs

Subgraphs can be nested inside other subgraphs:

```mermaid
flowchart TD
    subgraph cloud [Cloud Infrastructure]
        subgraph compute [Compute]
            API["API Server"]
            Worker["Worker"]
        end
        subgraph data [Data]
            DB[("Database")]
            Cache[("Redis Cache")]
        end
    end

    API --> DB
    API --> Cache
    Worker --> DB
```

### Cross-Subgraph Edges

Edges can freely cross subgraph boundaries — just reference the node IDs:

```mermaid
flowchart LR
    subgraph frontend [Frontend]
        Browser["Browser"]
    end
    subgraph backend [Backend]
        API["API"]
        Auth["Auth"]
    end

    Browser --> API
    API --> Auth
```

## Note / Annotation Patterns

### Sequence Diagram Notes

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Note over Client,Server: TLS handshake required
    Client->>Server: GET /resource
    Note right of Server: Validates JWT
    Server-->>Client: 200 OK
```

### Flowchart Comment Notes

Mermaid flowcharts don't have a native note block, but you can use a descriptive rectangle node and a dashed edge to convey annotation. Assign it with the same palette-based `classDef` approach as the rest of the diagram:

```mermaid
flowchart TD
    Process["Process Order"]
    Note1["Note: retries up to 3x on failure"]
    Process -.-> Note1
```

## Aliases and Display Names

### Flowchart (label in node definition)

```mermaid
flowchart TD
    gwNode["API Gateway"]
    authNode["Auth Service v2"]
    gwNode --> authNode
```

### Sequence Diagram (participant alias)

```mermaid
sequenceDiagram
    participant gw as "API Gateway"
    participant auth as "Auth Service"
    gw->>auth: validate token
```

## Long Labels — Keeping Them Readable

Long labels in nodes should be kept under ~30 characters. For longer text, abbreviate or split responsibility between the node and the edge label:

- Instead of: `ProcessPaymentAndUpdateInventory["Process Payment and Update Inventory"]`
- Use: `OrderFulfillment["Order Fulfillment"]` with an edge label that provides the detail

## Pipeline / Data Flow Pattern (flowchart LR)

The most readable pattern for ETL/ELT pipelines:

```mermaid
flowchart LR
    Source[("Source DB")] -->|"CDC events"| Kafka["Kafka"]
    Kafka -->|"consume"| SnowpipeSDK["Snowpipe Streaming"]
    SnowpipeSDK -->|"ingest"| StagingTable[("Staging")]
    StagingTable -->|"transform"| DynamicTables["Dynamic Tables"]
    DynamicTables -->|"serve"| Analytics["Analytics Layer"]

    subgraph snowflake [Snowflake]
        SnowpipeSDK
        StagingTable
        DynamicTables
        Analytics
    end
```

## Parallel Paths Pattern

Show parallel execution in flowchart:

```mermaid
flowchart TD
    Start(["Start"]) --> A["Validate Request"]
    A --> B["Authorize User"]
    A --> C["Rate Limit Check"]
    B --> D{"Both passed?"}
    C --> D
    D -- Yes --> E["Process Request"]
    D -- No --> F["Return 403"]
```

## Retry Loop Pattern

Show a retry loop with a counter or max attempts:

```mermaid
flowchart TD
    A["Send Request"] --> B{"Success?"}
    B -- Yes --> C["Done"]
    B -- No --> D{"Retries < 3?"}
    D -- Yes --> A
    D -- No --> E["Fail with error"]
```

## Mermaid Version Compatibility Notes

| Feature | Min version |
|---|---|
| `flowchart` keyword | v8+ |
| `sequenceDiagram` | v8+ |
| `erDiagram` | v8+ |
| `classDiagram` | v8+ |
| `architecture-beta` | v11+ |

CoCo's markdown preview and GitHub both support Mermaid v10+. Use `architecture-beta` only when you're confident the rendering environment supports v11. When in doubt, use `flowchart LR` with cylinder nodes `[("Database")]` for infrastructure diagrams — it's compatible everywhere.
