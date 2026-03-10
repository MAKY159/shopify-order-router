from enum import Enum

from .models import Order


class Warehouse(str, Enum):
    EU = "EU"
    US = "US"
    UNKNOWN = "UNKNOWN"


def route(order: Order) -> Warehouse:
    skus = order.skus()
    if any(s.upper().startswith("EU-") for s in skus):
        return Warehouse.EU
    if any(s.upper().startswith("US-") for s in skus):
        return Warehouse.US
    return Warehouse.UNKNOWN
