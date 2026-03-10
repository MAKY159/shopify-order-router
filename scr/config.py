import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    shopify_shop_domain: str
    shopify_access_token: str
    eu_warehouse_token: str
    us_warehouse_token: str
    dry_run: bool

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [k for k in ("SHOPIFY_SHOP_DOMAIN", "SHOPIFY_ACCESS_TOKEN") if not os.getenv(k)]
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

        return cls(
            shopify_shop_domain=os.environ["SHOPIFY_SHOP_DOMAIN"],
            shopify_access_token=os.environ["SHOPIFY_ACCESS_TOKEN"],
            eu_warehouse_token=os.getenv("EU_WAREHOUSE_TOKEN", "placeholder"),
            us_warehouse_token=os.getenv("US_WAREHOUSE_TOKEN", "placeholder"),
            dry_run=os.getenv("DRY_RUN", "true").lower() != "false",
        )


settings = Settings.from_env()
