import os
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Settings:
    shopify_shop_domain: str
    shopify_access_token: str
    shipbob_pat: str
    shipbob_channel_id: str
    shipbob_shipping_method: str
    dcl_username: str
    dcl_password: str
    dcl_account_number: str
    dcl_shipping_carrier: str
    dcl_shipping_service: str
    dry_run: bool
    orders_since: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [k for k in ("SHOPIFY_SHOP_DOMAIN", "SHOPIFY_ACCESS_TOKEN") if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

        since = os.getenv(
            "ORDERS_SINCE",
            datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z"),
        )

        return cls(
            shopify_shop_domain=os.environ["SHOPIFY_SHOP_DOMAIN"],
            shopify_access_token=os.environ["SHOPIFY_ACCESS_TOKEN"],
            shipbob_pat=os.getenv("SHIPBOB_PAT", "placeholder"),
            shipbob_channel_id=os.getenv("SHIPBOB_CHANNEL_ID", ""),
            shipbob_shipping_method=os.getenv("SHIPBOB_SHIPPING_METHOD", "Standard"),
            dcl_username=os.getenv("DCL_USERNAME", "placeholder"),
            dcl_password=os.getenv("DCL_PASSWORD", "placeholder"),
            dcl_account_number=os.getenv("DCL_ACCOUNT_NUMBER", ""),
            dcl_shipping_carrier=os.getenv("DCL_SHIPPING_CARRIER", "FEDEX"),
            dcl_shipping_service=os.getenv("DCL_SHIPPING_SERVICE", "GROUND"),
            dry_run=os.getenv("DRY_RUN", "true").lower() != "false",
            orders_since=since,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.from_env()
