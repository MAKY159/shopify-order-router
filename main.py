import logging
import sys

from dotenv import load_dotenv
load_dotenv()

from src.config import settings
from src import log
from src import ShopifyClient, Order, route, Warehouse, EUWarehouseClient, USWarehouseClient

log.setup(settings.log_level)
logger = logging.getLogger(__name__)


def main() -> None:
    shopify = ShopifyClient()
    clients = {
        Warehouse.EU: EUWarehouseClient(),
        Warehouse.US: USWarehouseClient(),
    }
    stats = {"routed": 0, "skipped": 0, "failed": 0}

    for raw in shopify.iter_orders():
        tags = {t.lower() for t in raw.get("tags", [])}
        if "routed-to-eu" in tags or "routed-to-us" in tags:
            logger.info("skipping already routed order %s", raw["name"])
            stats["skipped"] += 1
            continue

        order = Order.from_node(raw)
        destination = route(order)

        if destination == Warehouse.UNKNOWN:
            logger.warning("no routable SKUs for order %s: %s", order.name, order.skus())
            stats["skipped"] += 1
            continue

        try:
            clients[destination].send_order(order)
            if not settings.dry_run:
                shopify.mark_routed(order.id, destination.value)
            logger.info("order %s dispatched to %s", order.name, destination.value)
            stats["routed"] += 1
        except Exception as e:
            logger.error("failed to dispatch order %s: %s", order.name, e)
            stats["failed"] += 1

    logger.info("done: %s", stats)

    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
