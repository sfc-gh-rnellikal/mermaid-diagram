# Template: Microservices Architecture

A flowchart showing a microservices architecture with an API gateway, service mesh, async messaging, and data stores.

## When to use

Use this template when the user describes a microservices system, a service mesh, bounded contexts, an event-driven architecture, or services communicating via a message bus.

## Template: Domain-Driven Microservices

```mermaid
flowchart TD
    subgraph clients [Client Layer]
        WebApp["Web App"]
        MobileApp["Mobile App"]
        ExternalAPI["External API Consumer"]
    end

    subgraph gateway [API Gateway Layer]
        Gateway["API Gateway"]
        AuthMiddleware["Auth Middleware"]
        RateLimiter["Rate Limiter"]
    end

    subgraph services [Domain Services]
        subgraph orderDomain [Order Domain]
            OrderService["Order Service"]
            OrderDB[("Order DB")]
        end
        subgraph inventoryDomain [Inventory Domain]
            InventoryService["Inventory Service"]
            InventoryDB[("Inventory DB")]
        end
        subgraph paymentDomain [Payment Domain]
            PaymentService["Payment Service"]
            PaymentDB[("Payment DB")]
        end
        subgraph notificationDomain [Notification Domain]
            NotificationService["Notification Service"]
        end
    end

    subgraph messaging [Async Messaging]
        EventBus["Event Bus (Kafka)"]
    end

    subgraph observability [Observability]
        Monitoring["Monitoring"]
        Logging["Logging"]
    end

    WebApp --> Gateway
    MobileApp --> Gateway
    ExternalAPI --> Gateway
    Gateway --> AuthMiddleware
    AuthMiddleware --> RateLimiter
    RateLimiter --> OrderService
    RateLimiter --> InventoryService
    RateLimiter --> PaymentService

    OrderService --> OrderDB
    InventoryService --> InventoryDB
    PaymentService --> PaymentDB

    OrderService -->|"OrderPlaced event"| EventBus
    PaymentService -->|"PaymentProcessed event"| EventBus
    InventoryService -->|"StockReserved event"| EventBus
    EventBus -->|"subscribe"| NotificationService
    EventBus -->|"subscribe"| InventoryService
    EventBus -->|"subscribe"| PaymentService

    OrderService -.->|"logs"| Logging
    PaymentService -.->|"metrics"| Monitoring
    Gateway -.->|"traces"| Monitoring
```

## Simplified variant: core services only

```mermaid
flowchart LR
    Client["Client"] --> APIGateway["API Gateway"]

    subgraph services [Services]
        UserService["User Service"]
        OrderService["Order Service"]
        PaymentService["Payment Service"]
        NotificationService["Notification Service"]
    end

    APIGateway --> UserService
    APIGateway --> OrderService
    APIGateway --> PaymentService

    OrderService -->|"OrderCreated"| MessageBus["Message Bus"]
    PaymentService -->|"PaymentDone"| MessageBus
    MessageBus -->|"event"| NotificationService
    MessageBus -->|"event"| OrderService
```

## Key customization points

- Replace `Kafka` with `RabbitMQ`, `SNS/SQS`, or `Snowflake Dynamic Tables` for the event bus
- Add a `Service Registry` (e.g., Consul) connected to the Gateway for service discovery
- Add a `Circuit Breaker` between the Gateway and downstream services
- Add `Read Replicas` beside each database for query scaling
- Show async vs sync paths: solid arrows for synchronous, dashed `-.->` for async/events
