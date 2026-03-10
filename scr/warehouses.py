from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from .config import settings

logger = logging.getLogger(__name__)


class _BaseWarehouseClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"

        if settings.dry_run:
            logger.info("DRY RUN | POST %s\n%s", url, json.dumps(payload, indent=2))
            return {"dry_run": True}

        for attempt in range(1, 4):
            resp = self._session.post(url, json=payload, timeout=30)
            if resp.status_code == 429:
                time.sleep(float(resp.headers.get("Retry-After", 2 * attempt)))
                continue
            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Max retries exceeded for {url}")

    def send_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class EUWarehouseClient(_BaseWarehouseClient):
    def __init__(self) -> None:
        super().__init__("https://developer.shipbob.com", settings.eu_warehouse_token)

    def send_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/order", payload)


class USWarehouseClient(_BaseWarehouseClient):
    def __init__(self) -> None:
        super().__init__("https://api.dclcorp.com", settings.us_warehouse_token)

    def send_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/orders", payload)
