from __future__ import annotations

import time
import logging
from typing import Any, Generator

import requests

from .config import settings

logger = logging.getLogger(__name__)

_ORDERS_QUERY = """
query ($first: Int!, $after: String) {
  orders(first: $first, after: $after) {
    edges {
      node {
        id
        name
        email
        createdAt
        lineItems(first: 50) {
          edges {
            node {
              id
              title
              quantity
              sku
              variant {
                sku
              }
            }
          }
        }
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


class ShopifyClient:
    _API_VERSION = "2025-01"

    def __init__(self) -> None:
        self._endpoint = (
            f"https://{settings.shopify_shop_domain}"
            f"/admin/api/{self._API_VERSION}/graphql.json"
        )
        self._session = requests.Session()
        self._session.headers.update({
            "X-Shopify-Access-Token": settings.shopify_access_token,
            "Content-Type": "application/json",
        })

    def _execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, 6):
            try:
                resp = self._session.post(
                    self._endpoint,
                    json={"query": query, "variables": variables},
                    timeout=30,
                )
            except requests.RequestException:
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 429:
                time.sleep(float(resp.headers.get("Retry-After", 2 ** attempt)))
                continue

            resp.raise_for_status()
            data = resp.json()
            errors = data.get("errors", [])

            if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
                time.sleep(2 ** attempt)
                continue

            if errors:
                raise RuntimeError(f"GraphQL errors: {errors}")

            return data

        raise RuntimeError("Shopify API max retries exceeded.")

    def iter_orders(self) -> Generator[dict[str, Any], None, None]:
        cursor: str | None = None

        while True:
            variables: dict[str, Any] = {"first": 10}
            if cursor:
                variables["after"] = cursor

            data = self._execute(_ORDERS_QUERY, variables)
            orders = data["data"]["orders"]

            for edge in orders["edges"]:
                yield edge["node"]

            if not orders["pageInfo"]["hasNextPage"]:
                break

            cursor = orders["pageInfo"]["endCursor"]
