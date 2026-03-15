# shopify-order-router

Python script that pulls open orders from Shopify and routes them to the right warehouse based on SKU prefixes.

## How it works

Connects to Shopify via the Admin GraphQL API, pulls orders created since `ORDERS_SINCE`, and checks each order's SKUs:

- SKU starts with `EU-` → sends to ShipBob (EU)
- SKU starts with `US-` → sends to DCL (US)
- If an order has both, EU wins
- No match → logged and skipped

After a successful dispatch, the order gets tagged `routed-to-eu` or `routed-to-us` in Shopify so re-running the script doesn't send duplicates. ShipBob also uses the Shopify order GID as `reference_id` for its own idempotency.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with your credentials.

## Credentials

**Shopify** — Admin API access token (`shpat_...`) with `read_orders` and `write_orders` scopes.

**ShipBob** — Personal Access Token from Integrations → API Tokens. Channel ID from `GET https://api.shipbob.com/2026-01/channel` — use the one with `orders_write` scope.

**DCL** — HTTP Basic Auth (username + password). Account number included in every order payload.

## Run

```bash
python main.py
```

Or with Docker:

```bash
docker build -t shopify-order-router .
docker run --env-file .env shopify-order-router
```

`DRY_RUN=true` by default — logs payloads without sending. `ORDERS_SINCE` defaults to start of today UTC. `LOG_LEVEL` defaults to INFO.

Script exits with code `1` if any orders failed to dispatch, so it can be monitored by a scheduler or alerting system.

## Adding a new warehouse

To add a third warehouse (e.g. Canada), four things need changing:

1. Add `CA = "CA"` to `Warehouse` enum in `src/router.py`

2. Add a routing rule in `src/router.py` — rules are evaluated in registration order, so add higher-priority rules before lower-priority ones:

```python
@register
def _ca_rule(order: Order) -> Warehouse | None:
    if any(s.upper().startswith("CA-") for s in order.skus()):
        return Warehouse.CA
    return None
```

3. Add `CAWarehouseClient` in `src/warehouses.py`

4. Wire it up in `main.py` clients dict: `Warehouse.CA: CAWarehouseClient()`

## Tests

```bash
python -m unittest discover -s tests -v
```

## Assumptions

- Shopify API 2026-01
- SKU matching is case-insensitive
- If a line item has no SKU, falls back to `variant.sku`
- Shipping method/carrier/service are configurable via env vars
- The EU warehouse endpoint in the task (`developer.shipbob.com/api/channels/get-channels`) is the ShipBob docs site, not an order submission endpoint. The actual Orders API is `POST https://api.shipbob.com/2026-01/order` per ShipBob documentation
- Routing rules are evaluated in registration order — EU before US by design
