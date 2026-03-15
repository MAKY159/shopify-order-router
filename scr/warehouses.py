from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from .config import settings
from .models import Order

logger = logging.getLogger(__name__)

SHIPBOB_API = "https://api.shipbob.com/2026-01"
DCL_API = "https://api.dclcorp.com/api/v1"


class EUWarehouseClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {settings.shipbob_pat}",
            "Content-Type": "application/json",
        })
        if settings.shipbob_channel_id:
            self._session.headers["shipbob_channel_id"] = settings.shipbob_channel_id

    def _build_payload(self, order: Order) -> dict[str, Any]:
        sa = order.shipping_address
        return {
            "reference_id": order.id,
            "order_number": order.name.lstrip("#"),
            "type": "DTC",
            "shipping_method": settings.shipbob_shipping_method,
            "recipient": {
                "name": f"{sa.first_name} {sa.last_name}".strip(),
                "email": order.email,
                "phone_number": sa.phone,
                "address": {
                    "address1": sa.address1,
                    "address2": sa.address2,
                    "city": sa.city,
                    "state": sa.province,
                    "country": sa.country,
                    "zip_code": sa.zip,
                },
            },
            "products": [
                {
                    "reference_id": item.sku,
                    "name": item.title,
                    "quantity": item.quantity,
                }
                for item in order.line_items
                if item.sku
            ],
        }

    def send_order(self, order: Order) -> dict[str, Any]:
        payload = self._build_payload(order)

        if settings.dry_run:
            logger.info("DRY RUN | ShipBob POST /2026-01/order\n%s", json.dumps(payload, indent=2))
            return {"dry_run": True}

        for attempt in range(1, 4):
            resp = self._session.post(f"{SHIPBOB_API}/order", json=payload, timeout=30)
            if resp.status_code == 429:
                time.sleep(float(resp.headers.get("Retry-After", 2 * attempt)))
                continue
            resp.raise_for_status()
            return resp.json()

        raise RuntimeError("ShipBob: max retries exceeded.")


class USWarehouseClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._auth = (settings.dcl_username, settings.dcl_password)

    def _build_order(self, order: Order) -> dict[str, Any]:
        sa = order.shipping_address
        return {
            "order_number": order.name.lstrip("#"),
            "account_number": settings.dcl_account_number,
            "ordered_date": order.created_at[:10],
            "shipping_carrier": settings.dcl_shipping_carrier,
            "shipping_service": settings.dcl_shipping_service,
            "shipping_address": {
                "attention": f"{sa.first_name} {sa.last_name}".strip(),
                "address1": sa.address1,
                "address2": sa.address2,
                "city": sa.city,
                "state_province": sa.province,
                "postal_code": sa.zip,
                "country_code": sa.country,
                "phone": sa.phone,
            },
            "lines": [
                {
                    "line_number": i + 1,
                    "item_number": item.sku,
                    "description": item.title,
                    "quantity": item.quantity,
                }
                for i, item in enumerate(order.line_items)
                if item.sku
            ],
        }

    def send_order(self, order: Order) -> dict[str, Any]:
        payload = {
            "allow_partial": False,
            "orders": [self._build_order(order)],
        }

        if settings.dry_run:
            logger.info("DRY RUN | DCL POST api/v1/batches\n%s", json.dumps(payload, indent=2))
            return {"dry_run": True}

        for attempt in range(1, 4):
            resp = self._session.post(
                f"{DCL_API}/batches",
                json=payload,
                auth=self._auth,
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 * attempt)
                continue
            resp.raise_for_status()
            result = resp.json()

            if result.get("error_code", 0) != 0:
                raise RuntimeError(f"DCL batch error: {result.get('error_message')}")

            for status in result.get("order_statuses", []):
                if status.get("error_code", 0) != 0:
                    raise RuntimeError(
                        f"DCL order error [{status.get('order_number')}]: {status.get('error_message')}"
                    )

            return result

        raise RuntimeError("DCL: max retries exceeded.")
