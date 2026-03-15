from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Address:
    first_name: str = ""
    last_name: str = ""
    address1: str = ""
    address2: str = ""
    city: str = ""
    province: str = ""
    country: str = ""
    zip: str = ""
    phone: str = ""


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
    shipping_address: Address = field(default_factory=Address)
    total_price: str = ""
    currency: str = ""

    def skus(self) -> list[str]:
        return [item.sku for item in self.line_items if item.sku]

    @classmethod
    def from_node(cls, node: dict[str, Any]) -> Order:
        line_items = []
        for edge in node.get("lineItems", {}).get("edges", []):
            n = edge["node"]
            sku = n.get("sku") or (n.get("variant") or {}).get("sku") or None
            line_items.append(LineItem(id=n["id"], title=n["title"], quantity=n["quantity"], sku=sku))

        sa = node.get("shippingAddress") or {}
        money = node.get("totalPriceSet", {}).get("shopMoney", {})

        return cls(
            id=node["id"],
            name=node["name"],
            email=node.get("email", ""),
            created_at=node["createdAt"],
            line_items=line_items,
            shipping_address=Address(
                first_name=sa.get("firstName", ""),
                last_name=sa.get("lastName", ""),
                address1=sa.get("address1", ""),
                address2=sa.get("address2", ""),
                city=sa.get("city", ""),
                province=sa.get("province", ""),
                country=sa.get("country", ""),
                zip=sa.get("zip", ""),
                phone=sa.get("phone", ""),
            ),
            total_price=money.get("amount", "0.00"),
            currency=money.get("currencyCode", ""),
        )
