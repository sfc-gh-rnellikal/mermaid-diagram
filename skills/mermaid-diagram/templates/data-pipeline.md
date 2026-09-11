# Template: Data Pipeline (ETL/ELT)

A left-to-right flowchart showing a data pipeline from source to consumption. Suitable for ETL, ELT, streaming, and batch pipelines.

## When to use

Use this template when the user describes a data pipeline, an ingestion flow, an ETL process, a streaming architecture, or a batch transformation workflow.

## Template: Kafka Streaming Pipeline

```mermaid
flowchart LR
    subgraph sources [Source Systems]
        OLTP[("OLTP Database")]
        AppLogs["Application Logs"]
        ThirdParty["Third-Party API"]
    end

    subgraph streaming [Streaming Layer]
        KafkaProducer["Kafka Producer"]
        KafkaTopic["Kafka Topic"]
        KafkaConsumer["Kafka Consumer"]
    end

    subgraph snowflake [Snowflake]
        SnowpipeSDK["Snowpipe Streaming"]
        Staging[("Staging Tables")]
        DynamicTables["Dynamic Tables"]
        Curated[("Curated Layer")]
        DataQuality["Data Quality DMFs"]
    end

    subgraph consumers [Consumers]
        Analyst["Analysts / BI"]
        CortexAI["Cortex AI"]
        ExternalApp["External App"]
    end

    OLTP -->|"CDC"| KafkaProducer
    AppLogs -->|"publish"| KafkaProducer
    ThirdParty -->|"webhook"| KafkaProducer
    KafkaProducer -->|"produce"| KafkaTopic
    KafkaTopic -->|"consume"| KafkaConsumer
    KafkaConsumer -->|"insertRows"| SnowpipeSDK
    SnowpipeSDK -->|"ingest"| Staging
    Staging -->|"source"| DynamicTables
    Staging -->|"monitor"| DataQuality
    DynamicTables -->|"materialize"| Curated
    Curated -->|"query"| Analyst
    Curated -->|"context"| CortexAI
    Curated -->|"serve"| ExternalApp
```

## Template: Batch ELT Pipeline

```mermaid
flowchart LR
    subgraph extract [Extract]
        S3[("S3")]
        GCS[("GCS")]
        SFTP["SFTP"]
    end

    subgraph load [Load]
        Stage["Snowflake Stage"]
        COPY["COPY INTO"]
        RawTables[("Raw Tables")]
    end

    subgraph transform [Transform]
        StagingModels["Staging Models"]
        IntermediateModels["Intermediate Models"]
        MartModels["Mart Models"]
    end

    subgraph serve [Serve]
        Tableau["Tableau"]
        LookerStudio["Looker Studio"]
        API["REST API"]
    end

    S3 -->|"PUT"| Stage
    GCS -->|"PUT"| Stage
    SFTP -->|"PUT"| Stage
    Stage -->|"COPY INTO"| COPY
    COPY -->|"load"| RawTables
    RawTables -->|"dbt source"| StagingModels
    StagingModels -->|"dbt model"| IntermediateModels
    IntermediateModels -->|"dbt model"| MartModels
    MartModels -->|"query"| Tableau
    MartModels -->|"query"| LookerStudio
    MartModels -->|"expose"| API
```

## Key customization points

- Add a `DataQuality` node with dashed edges for monitoring steps
- Add a `Failed Records` branch from Staging for dead-letter handling
- Collapse source systems into one node (`SourceSystems`) for a simpler overview diagram
- Add a task scheduler (`AirflowDAG` or `SnowflakeTasks`) connected to the transform layer
