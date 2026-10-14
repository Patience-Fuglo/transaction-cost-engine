"""Stage 6 -- aggregates Stages 2-5 into one real per-trade total cost,
and converts a whole portfolio's per-trade (fraction-of-TRADE-value)
costs into one real portfolio-level cost (fraction of PORTFOLIO value)
-- the unit conversion every later stage (net profitability, reporting)
needs: ``portfolio_contribution = cost_fraction * abs(trade_weight)``.
"""

from __future__ import annotations

from typing import Sequence

from ..config import EngineConfig
from ..data.schemas import TotalExecutionCost, TradeOrder
from ..fees import compute_fee_cost
from ..impact import compute_impact_cost
from ..slippage import compute_slippage_cost
from ..spread import compute_spread_cost


def compute_total_execution_cost(order: TradeOrder, cfg: EngineConfig, delay_days: int | None = None) -> TotalExecutionCost:
    spread = compute_spread_cost(order, cfg.spread)
    impact = compute_impact_cost(order, cfg.impact)
    slippage = compute_slippage_cost(order, cfg.slippage, delay_days)
    fee = compute_fee_cost(order, cfg.fee)

    total = spread.cost_fraction + impact.cost_fraction + slippage.cost_fraction + fee.cost_fraction
    warnings = tuple(
        f"{component.component_name}: real data unavailable for {order.security_id}, used a conservative fallback"
        for component in (spread, impact, slippage)
        if component.detail.get("data_known") is False
    )

    return TotalExecutionCost(
        security_id=order.security_id,
        as_of=order.as_of,
        spread_cost_fraction=spread.cost_fraction,
        impact_cost_fraction=impact.cost_fraction,
        slippage_cost_fraction=slippage.cost_fraction,
        fee_cost_fraction=fee.cost_fraction,
        total_cost_fraction=total,
        warnings=warnings,
    )


def aggregate_portfolio_execution_cost(orders: Sequence[TradeOrder], costs: Sequence[TotalExecutionCost]) -> float:
    """Real portfolio-level execution cost, as a fraction of portfolio
    value -- directly comparable to (and subtractable from) a real
    ``gross_expected_return``. Each security's per-trade-value cost
    fraction is scaled by its own real ``abs(trade_weight)`` before
    summing; a security with no real trade (``trade_weight == 0``)
    contributes exactly 0, never a fabricated cost.
    """
    by_security = {cost.security_id: cost for cost in costs}
    return sum(
        by_security[order.security_id].total_cost_fraction * abs(order.trade_weight)
        for order in orders
        if order.security_id in by_security
    )
