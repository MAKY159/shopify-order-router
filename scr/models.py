from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineItem:
    id: str
    title: str
    quantity: int
    sku: str | None


@dataclass
class Order:
    id: str
    name: str
    email: str
    created_at: str
    line_items: list[LineItem] = field(default_factory=list)
    total_price: str = ""
    currency: str = ""

    def skus(self) -> list[str]:
        return [item.sku for item in self.line_items if item.sku]

    def to_payload(self) -> dict[str, Any]:
        return {
            "shopify_order_id": self.id,
            "order_name": self.name,
            "email": self.email,
            "created_at": self.created_at,
            "total_price": self.total_price,
            "currency": self.currency,
            "line_items": [
                {"id": li.id, "title": li.title, "quantity": li.quantity, "sku": li.sku}
                for li in self.line_items
            ],
        }

    @classmethod
    def from_node(cls, node: dict[str, Any]) -> Order:
        line_items = []
        for edge in node.get("lineItems", {}).get("edges", []):
            n = edge["node"]
            sku = n.get("sku") or (n.get("variant") or {}).get("sku") or None
            line_items.append(LineItem(id=n["id"], title=n["title"], quantity=n["quantity"], sku=sku))

        money = node.get("totalPriceSet", {}).get("shopMoney", {})
        return cls(
            id=node["id"],
            name=node["name"],
            email=node.get("email", ""),
            created_at=node["createdAt"],
            line_items=line_items,
            total_price=money.get("amount", "0.00"),
            currency=money.get("currencyCode", ""),
        )
