import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SHOPIFY_SHOP_DOMAIN", "test.myshopify.com")
os.environ.setdefault("SHOPIFY_ACCESS_TOKEN", "fake")

from src.models import Order, LineItem
from src.router import route, Warehouse


def _order(skus: list) -> Order:
    return Order(
        id="gid://shopify/Order/1",
        name="#1001",
        email="test@test.com",
        created_at="2025-01-01T00:00:00Z",
        line_items=[LineItem(id=str(i), title="Item", quantity=1, sku=sku) for i, sku in enumerate(skus)],
    )


class TestRouter(unittest.TestCase):
    def test_eu_prefix(self):           self.assertEqual(route(_order(["EU-001"])), Warehouse.EU)
    def test_us_prefix(self):           self.assertEqual(route(_order(["US-001"])), Warehouse.US)
    def test_eu_beats_us(self):         self.assertEqual(route(_order(["US-001", "EU-002"])), Warehouse.EU)
    def test_no_skus(self):             self.assertEqual(route(_order([])), Warehouse.UNKNOWN)
    def test_none_skus(self):           self.assertEqual(route(_order([None, None])), Warehouse.UNKNOWN)
    def test_unknown_prefix(self):      self.assertEqual(route(_order(["AU-001"])), Warehouse.UNKNOWN)
    def test_none_mixed_with_eu(self):  self.assertEqual(route(_order([None, "EU-999"])), Warehouse.EU)
    def test_lowercase_eu(self):        self.assertEqual(route(_order(["eu-001"])), Warehouse.EU)
    def test_lowercase_us(self):        self.assertEqual(route(_order(["us-001"])), Warehouse.US)


class TestOrderModel(unittest.TestCase):
    def test_from_node_sku_fallback_and_address(self):
        node = {
            "id": "gid://shopify/Order/1", "name": "#1001", "email": "a@b.com",
            "createdAt": "2025-01-01T00:00:00Z",
            "lineItems": {"edges": [
                {"node": {"id": "1", "title": "A", "quantity": 1, "sku": "EU-001", "variant": None}},
                {"node": {"id": "2", "title": "B", "quantity": 1, "sku": None, "variant": {"sku": "US-002"}}},
                {"node": {"id": "3", "title": "C", "quantity": 1, "sku": None, "variant": None}},
            ]},
            "shippingAddress": {
                "firstName": "John", "lastName": "Doe", "address1": "123 Main St",
                "address2": "", "city": "Fremont", "province": "CA",
                "country": "US", "zip": "94538", "phone": "555-1234",
            },
            "totalPriceSet": {"shopMoney": {"amount": "50.00", "currencyCode": "USD"}},
        }
        order = Order.from_node(node)
        self.assertEqual(order.skus(), ["EU-001", "US-002"])
        self.assertEqual(order.shipping_address.city, "Fremont")

    def test_missing_shipping_address(self):
        node = {
            "id": "gid://shopify/Order/2", "name": "#1002", "email": "b@b.com",
            "createdAt": "2025-01-01T00:00:00Z",
            "lineItems": {"edges": []},
            "shippingAddress": None,
            "totalPriceSet": {"shopMoney": {"amount": "0.00", "currencyCode": "USD"}},
        }
        order = Order.from_node(node)
        self.assertEqual(order.shipping_address.city, "")
