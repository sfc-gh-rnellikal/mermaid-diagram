# Template: API Sequence Flow

A sequence diagram showing a client authenticating via OAuth2, then making an authorized API call.

## When to use

Use this template when the user describes an API authentication flow, a token exchange, an OAuth or JWT flow, or any request/response sequence between a client and backend services.

## Template: OAuth2 Token Exchange

```mermaid
sequenceDiagram
    actor User as "End User"
    participant ClientApp as "Client App"
    participant Gateway as "API Gateway"
    participant Auth as "Auth Service"
    participant Resource as "Resource API"
    participant DB as "Database"

    User->>ClientApp: enter credentials

    ClientApp->>+Gateway: POST /auth/token
    Gateway->>+Auth: forward auth request
    Auth->>+DB: lookup user record
    DB-->>-Auth: user + hashed password
    
    alt credentials valid
        Auth-->>-Gateway: 200 OK + JWT
        Gateway-->>-ClientApp: 200 OK + JWT
        
        ClientApp->>+Gateway: GET /api/resource (Authorization: Bearer JWT)
        Gateway->>Auth: validate JWT
        Auth-->>Gateway: token valid + claims
        Gateway->>+Resource: forward request with claims
        Resource->>+DB: query data
        DB-->>-Resource: data records
        Resource-->>-Gateway: 200 OK + data
        Gateway-->>-ClientApp: 200 OK + data
        ClientApp->>User: display result
        
    else credentials invalid
        Auth-->>Gateway: 401 Unauthorized
        Gateway-->>ClientApp: 401 Unauthorized
        ClientApp->>User: show error message
    end
```

## Simplified variant: request/response only

```mermaid
sequenceDiagram
    participant Client
    participant API as "API Server"
    participant Auth as "Auth Service"
    participant DB as "Database"

    Client->>API: POST /login
    API->>Auth: validate credentials
    Auth-->>API: JWT token
    API-->>Client: 200 OK + token

    Client->>API: GET /data (Bearer token)
    API->>Auth: verify token
    Auth-->>API: valid
    API->>DB: SELECT data
    DB-->>API: rows
    API-->>Client: 200 OK + data
```

## Key customization points

- Add `loop` blocks for retry logic: `loop up to 3 retries ... end`
- Add `opt` block for refresh token: `opt token expired ... end`
- Add rate limiting: `Gateway->>RateLimiter: check rate` before forwarding
- For microservices, expand `Resource API` into multiple downstream services
