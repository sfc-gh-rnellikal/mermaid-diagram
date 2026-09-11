# Template: ER Schema

Database entity-relationship diagrams for common data domain patterns.

## When to use

Use this template when the user describes a database schema, asks for an ER diagram, describes entities with foreign key relationships, or wants to visualize a data model.

## Template: E-Commerce Schema

```mermaid
erDiagram
    CUSTOMER {
        int customer_id PK
        string first_name
        string last_name
        string email UK
        string phone
        date created_at
    }
    ADDRESS {
        int address_id PK
        int customer_id FK
        string street
        string city
        string country
        string postal_code
    }
    ORDER {
        int order_id PK
        int customer_id FK
        int shipping_address_id FK
        date order_date
        string status
        float total_amount
    }
    ORDER_ITEM {
        int item_id PK
        int order_id FK
        int product_id FK
        int quantity
        float unit_price
    }
    PRODUCT {
        int product_id PK
        int category_id FK
        string name
        string description
        float price
        int stock_quantity
    }
    CATEGORY {
        int category_id PK
        string name
        int parent_category_id FK
    }

    CUSTOMER ||--o{ ORDER : "places"
    CUSTOMER ||--o{ ADDRESS : "has"
    ORDER }o--|| ADDRESS : "ships to"
    ORDER ||--|{ ORDER_ITEM : "contains"
    ORDER_ITEM }o--|| PRODUCT : "references"
    PRODUCT }o--|| CATEGORY : "belongs to"
    CATEGORY o|--o| CATEGORY : "parent of"
```

## Template: Star Schema (Data Warehouse)

```mermaid
erDiagram
    FACT_SALES {
        int sale_id PK
        int date_key FK
        int customer_key FK
        int product_key FK
        int store_key FK
        float sale_amount
        int quantity_sold
        float discount_amount
    }
    DIM_DATE {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        string month_name
        int day_of_week
        boolean is_weekend
        boolean is_holiday
    }
    DIM_CUSTOMER {
        int customer_key PK
        string customer_id
        string name
        string segment
        string region
        string country
    }
    DIM_PRODUCT {
        int product_key PK
        string product_id
        string product_name
        string category
        string subcategory
        float list_price
    }
    DIM_STORE {
        int store_key PK
        string store_id
        string store_name
        string city
        string state
        string country
    }

    FACT_SALES }o--|| DIM_DATE : "on date"
    FACT_SALES }o--|| DIM_CUSTOMER : "by customer"
    FACT_SALES }o--|| DIM_PRODUCT : "of product"
    FACT_SALES }o--|| DIM_STORE : "at store"
```

## Key customization points

- Add a `FACT_RETURNS` table linking back to `FACT_SALES` via `sale_id FK`
- Add a `DIM_PROMOTION` for discount/campaign tracking
- Add `SCD_TYPE2` fields to dimension tables: `effective_date`, `expiry_date`, `is_current`
- Add a bridge table for many-to-many relationships (e.g., products with multiple categories)
