"""Stage 6 -- builds real ``TradeOrder``s directly from
``portfolio-construction-engine``'s own ``OptimizationResult`` (the
already-decided target weights) and the pre-trade current weights
that produced its ``turnover`` -- this engine never re-decides a
trade, it only prices the real cost of executing one already decided
elsewhere.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
from portfolio_construction.data import OptimizationResult

from ..data.schemas import TradeOrder


def build_trade_orders(
    result: OptimizationResult,
    current_weights: dict[str, float],
    market_data: dict[str, dict],
    portfolio_value: float = 1.0,
) -> list[TradeOrder]:
    """``market_data`` maps each real security_id to a dict with real
    ``price``, ``adv_usd`` (``None`` if unknown), and
    ``daily_volatility`` (``None`` if unknown) -- this engine does not
    fetch or derive these itself; they come from
    ``factor-model-engine``'s own real market observations. A security
    with no real trade (``target_weight == current_weight``) is
    excluded -- there is nothing real to price the cost of.
    """
    orders: list[TradeOrder] = []
    for security_id, target_weight in result.target_weights.items():
        current_weight = current_weights.get(security_id, 0.0)
        trade_weight = target_weight - current_weight
        if trade_weight == 0.0:
            continue
        data = market_data.get(security_id)
        if data is None or "price" not in data:
            # price is a real, required input -- a security with a
            # real nonzero trade but no real price data is a genuine
            # data problem, never silently defaulted
            raise ValueError(f"{security_id}: has a real nonzero trade but no real price in market_data")
        orders.append(
            TradeOrder(
                security_id=security_id,
                as_of=result.as_of,
                trade_weight=trade_weight,
                price=data["price"],
                adv_usd=data.get("adv_usd"),
                daily_volatility=data.get("daily_volatility"),
                portfolio_value=portfolio_value,
            )
        )
    return orders
