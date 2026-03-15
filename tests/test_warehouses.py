import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SHOPIFY_SHOP_DOMAIN", "test.myshopify.com")
os.environ.setdefault("SHOPIFY_ACCESS_TOKEN", "fake")

from src.models import Order, LineItem, Address
from src.warehouses import EUWarehouseClient, USWarehouseClient


def _eu_order() -> Order:
    return Order(
        id="gid://shopify/Order/1",
        name="#1001",
        email="john@example.com",
        created_at="2025-01-01T00:00:00Z",
        line_items=[LineItem(id="li_1", title="Widget", quantity=2, sku="EU-WDG-01")],
        shipping_address=Address(
            first_name="John", last_name="Doe",
            address1="123 Main St", address2="",
            city="Amsterdam", province="NH",
            country="NL", zip="1000AA", phone="555-0000",
        ),
    )


def _us_order() -> Order:
    return Order(
        id="gid://shopify/Order/2",
        name="#1002",
        email="jane@example.com",
        created_at="2025-01-01T00:00:00Z",
        line_items=[LineItem(id="li_2", title="Gadget", quantity=1, sku="US-GDG-01")],
        shipping_address=Address(
            first_name="Jane", last_name="Smith",
            address1="456 Oak Ave", address2="Suite 5",
            city="Fremont", province="CA",
            country="US", zip="94538", phone="555-1111",
        ),
    )


class TestEUWarehouseClient(unittest.TestCase):

    def test_payload_structure(self):
        client = EUWarehouseClient()
        payload = client._build_payload(_eu_order())
        self.assertEqual(payload["reference_id"], "gid://shopify/Order/1")
        self.assertEqual(payload["order_number"], "1001")
        self.assertEqual(payload["recipient"]["name"], "John Doe")
        self.assertEqual(payload["recipient"]["address"]["city"], "Amsterdam")
        self.assertEqual(payload["products"][0]["reference_id"], "EU-WDG-01")
        self.assertEqual(payload["products"][0]["quantity"], 2)

    @patch("src.warehouses.settings")
    def test_send_order_success(self, mock_settings):
        mock_settings.dry_run = False
        mock_settings.shipbob_pat = "token"
        mock_settings.shipbob_channel_id = "100"
        mock_settings.shipbob_shipping_method = "Standard"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 99}
        client = EUWarehouseClient()
        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            result = client.send_order(_eu_order())
            self.assertEqual(result["id"], 99)
            self.assertTrue(mock_post.called)

    @patch("src.warehouses.time.sleep")
    @patch("src.warehouses.settings")
    def test_retries_on_429(self, mock_settings, mock_sleep):
        mock_settings.dry_run = False
        mock_settings.shipbob_pat = "token"
        mock_settings.shipbob_channel_id = "100"
        mock_settings.shipbob_shipping_method = "Standard"
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "1"}
        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"id": 42}
        client = EUWarehouseClient()
        with patch.object(client._session, "post", side_effect=[rate_limited, success]) as mock_post:
            result = client.send_order(_eu_order())
            self.assertEqual(result["id"], 42)
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_called_once_with(1.0)


class TestUSWarehouseClient(unittest.TestCase):

    def test_payload_structure(self):
        client = USWarehouseClient()
        payload = client._build_order(_us_order())
        self.assertEqual(payload["order_number"], "1002")
        self.assertEqual(payload["ordered_date"], "2025-01-01")
        self.assertEqual(payload["shipping_address"]["city"], "Fremont")
        self.assertEqual(payload["lines"][0]["item_number"], "US-GDG-01")
        self.assertEqual(payload["lines"][0]["line_number"], 1)

    @patch("src.warehouses.settings")
    def test_send_order_success(self, mock_settings):
        mock_settings.dry_run = False
        mock_settings.dcl_username = "user"
        mock_settings.dcl_password = "pass"
        mock_settings.dcl_account_number = "ACC"
        mock_settings.dcl_shipping_carrier = "FEDEX"
        mock_settings.dcl_shipping_service = "GROUND"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error_code": 0, "order_statuses": [{"error_code": 0}]}
        client = USWarehouseClient()
        with patch.object(client._session, "post", return_value=mock_resp) as mock_post:
            result = client.send_order(_us_order())
            self.assertEqual(result["error_code"], 0)
            self.assertTrue(mock_post.called)

    @patch("src.warehouses.settings")
    def test_dcl_error_code_raises(self, mock_settings):
        mock_settings.dry_run = False
        mock_settings.dcl_username = "user"
        mock_settings.dcl_password = "pass"
        mock_settings.dcl_account_number = "ACC"
        mock_settings.dcl_shipping_carrier = "FEDEX"
        mock_settings.dcl_shipping_service = "GROUND"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error_code": 5, "error_message": "Invalid account"}
        client = USWarehouseClient()
        with patch.object(client._session, "post", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as ctx:
                client.send_order(_us_order())
            self.assertIn("Invalid account", str(ctx.exception))

    @patch("src.warehouses.time.sleep")
    @patch("src.warehouses.settings")
    def test_retries_on_429(self, mock_settings, mock_sleep):
        mock_settings.dry_run = False
        mock_settings.dcl_username = "user"
        mock_settings.dcl_password = "pass"
        mock_settings.dcl_account_number = "ACC"
        mock_settings.dcl_shipping_carrier = "FEDEX"
        mock_settings.dcl_shipping_service = "GROUND"
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {}
        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {"error_code": 0, "order_statuses": []}
        client = USWarehouseClient()
        with patch.object(client._session, "post", side_effect=[rate_limited, success]) as mock_post:
            client.send_order(_us_order())
            self.assertEqual(mock_post.call_count, 2)
            mock_sleep.assert_called_once()


    @patch("src.warehouses.settings")
    def test_dcl_order_status_error_raises(self, mock_settings):
        mock_settings.dry_run = False
        mock_settings.dcl_username = "user"
        mock_settings.dcl_password = "pass"
        mock_settings.dcl_account_number = "ACC"
        mock_settings.dcl_shipping_carrier = "FEDEX"
        mock_settings.dcl_shipping_service = "GROUND"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "error_code": 0,
            "error_message": "",
            "order_statuses": [{"error_code": 4, "error_message": "quantity must be > 0", "order_number": "1002"}],
        }
        client = USWarehouseClient()
        with patch.object(client._session, "post", return_value=mock_resp):
            with self.assertRaises(RuntimeError) as ctx:
                client.send_order(_us_order())
            self.assertIn("quantity must be > 0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
