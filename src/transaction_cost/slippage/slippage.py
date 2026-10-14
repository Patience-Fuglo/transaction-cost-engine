"""Stage 5 -- real adverse-selection slippage during execution: the
real expected cost of price drifting against the trader while an
order is being worked, not a symmetric/zero-mean random-walk
assumption. ``slippage_bps = adverse_selection_coefficient *
daily_volatility_bps * sqrt(delay_days)`` -- random-walk-style
sqrt-time scaling of real volatility, applied one-directionally (a
real cost, never a potential gain) via the adverse-selection
coefficient.
"""

from __future__ import annotations

from ..config import SlippageConfig
from ..data.schemas import CostComponent, TradeOrder


def compute_slippage_cost(order: TradeOrder, cfg: SlippageConfig, delay_days: int | None = None) -> CostComponent:
    delay = delay_days if delay_days is not None else cfg.default_delay_days
    if delay < 1:
        raise ValueError("delay_days must be >= 1")

    if order.daily_volatility is None:
        slippage_bps = cfg.missing_data_slippage_bps
        detail = {"data_known": False, "delay_days": delay}
    else:
        daily_volatility_bps = order.daily_volatility * 10_000.0
        slippage_bps = cfg.adverse_selection_coefficient * daily_volatility_bps * (delay**0.5)
        detail = {"data_known": True, "delay_days": delay, "slippage_bps": slippage_bps}

    cost_fraction = slippage_bps / 10_000.0
    return CostComponent(
        security_id=order.security_id, as_of=order.as_of, component_name="slippage",
        cost_fraction=cost_fraction, detail=detail,
    )
