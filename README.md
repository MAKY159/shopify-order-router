shopify-order-router

Python middleware that pulls orders from the Shopify Admin GraphQL API and routes them to the correct warehouse based on SKU prefixes.

Architecture

```
ShopifyClient → Order.from_node() → route() → EUWarehouseClient / USWarehouseClient
```

| File | Role |
|------|------|
| `src/config.py` | Env-based config via pydantic-settings |
| `src/shopify.py` | GraphQL client with pagination and retry |
| `src/models.py` | Order and LineItem dataclasses |
| `src/router.py` | SKU-based routing logic |
| `src/warehouses.py` | EU (ShipBob) and US (DCL) clients |
| `main.py` | Entry point |

Routing Rules

| SKU prefix | Destination |
|------------|-------------|
| `EU-` | ShipBob EU |
| `US-` | DCL US |
| EU- beats US- if both present | ShipBob EU |
| No match | Logged and skipped |

Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your credentials.

Run

```bash
python main.py
```

`DRY_RUN=true` (default) logs the payload instead of sending it. Set to `false` for live dispatch.

Tests

```bash
python -m unittest discover -s tests -v
```

Assumptions

- Shopify API version `2025-01`
- Only open orders are fetched; change the `orders()` query filter as needed
- SKU matching is case-insensitive
- If a line item has no `sku` field, the variant's `sku` is used as fallback
- ShipBob endpoint: `POST /api/order`, DCL endpoint: `POST /orders`
