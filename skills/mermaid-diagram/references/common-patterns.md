# Common Mermaid Patterns

Patterns that apply across multiple diagram types: subgraph grouping, notes, icons, click events, and cross-type tips.

## Universal Syntax Rules (All Types)

These rules apply to every diagram type:

1. **No spaces in node/participant IDs** — IDs must be single tokens
2. **Never use reserved keywords as IDs** — `end`, `subgraph`, `graph`, `flowchart`, `direction`
3. **No HTML tags in labels** — `<br/>`, `<b>`, `<i>` render as literal text
4. **No explicit colors or styles** — `style`, `classDef fill:`, `:::className` break in dark mode
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

Mermaid flowcharts don't have a native note block, but you can use a styled node as a visual note. Since explicit styles break dark mode, use a descriptive label with a rectangle node and a dashed edge to convey annotation:

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
