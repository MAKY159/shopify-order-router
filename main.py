import logging
from dotenv import load_dotenv

load_dotenv()

from src import ShopifyClient, Order, route, Warehouse, EUWarehouseClient, USWarehouseClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    shopify = ShopifyClient()
    clients = {
        Warehouse.EU: EUWarehouseClient(),
        Warehouse.US: USWarehouseClient(),
    }

    for raw in shopify.iter_orders():
        order = Order.from_node(raw)
        destination = route(order)

        if destination == Warehouse.UNKNOWN:
            logger.warning("Order %s skipped — no routable SKUs: %s", order.name, order.skus())
            continue

        try:
            result = clients[destination].send_order(order.to_payload())
            logger.info("Order %s → %s | %s", order.name, destination.value, result)
        except Exception as e:
            logger.error("Order %s failed to dispatch: %s", order.name, e)


if __name__ == "__main__":
    main()
