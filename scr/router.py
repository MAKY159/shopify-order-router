from __future__ import annotations

from enum import Enum
from typing import Callable

from .models import Order


class Warehouse(str, Enum):
    EU = "EU"
    US = "US"
    UNKNOWN = "UNKNOWN"


RoutingRule = Callable[[Order], "Warehouse | None"]

_rules: list[RoutingRule] = []


def register(rule: RoutingRule) -> RoutingRule:
    """Register a routing rule. Rules are evaluated in registration order —
    the first rule that returns a non-None value wins."""
    _rules.append(rule)
    return rule


@register
def _eu_rule(order: Order) -> Warehouse | None:
    if any(s.upper().startswith("EU-") for s in order.skus()):
        return Warehouse.EU
    return None


@register
def _us_rule(order: Order) -> Warehouse | None:
    if any(s.upper().startswith("US-") for s in order.skus()):
        return Warehouse.US
    return None


def route(order: Order) -> Warehouse:
    for rule in _rules:
        result = rule(order)
        if result is not None:
            return result
    return Warehouse.UNKNOWN
