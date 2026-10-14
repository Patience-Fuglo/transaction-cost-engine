"""Stage 8 -- a real, participation-rate-constrained multi-day
execution schedule: a trade whose real participation rate exceeds
``max_participation_rate`` is split EVENLY across the real minimum
number of days needed to keep each day's participation within that
limit. Even splitting is a documented simplification -- a real VWAP/
TWAP algorithm might front- or back-load execution; this engine's own
single-day impact/spread model doesn't capture that distinction.

``required_days`` feeds directly back into Stage 5's slippage delay
(``compute_total_execution_cost``'s own ``delay_days`` parameter) --
a trade that takes longer to execute has longer real exposure to
adverse-selection drift.
"""

from __future__ import annotations

import math

from ..config import EngineConfig, SchedulingConfig
from ..data.schemas import ExecutionSchedule, TotalExecutionCost, TradeOrder
from ..execution.total_cost import compute_total_execution_cost


def compute_execution_schedule(order: TradeOrder, cfg: SchedulingConfig) -> ExecutionSchedule:
    participation_rate = order.participation_rate
    if participation_rate is None or participation_rate <= cfg.max_participation_rate:
        required_days = 1
    else:
        required_days = math.ceil(participation_rate / cfg.max_participation_rate)

    return ExecutionSchedule(
        security_id=order.security_id,
        as_of=order.as_of,
        max_participation_rate=cfg.max_participation_rate,
        required_days=required_days,
        daily_trade_fraction=1.0 / required_days,
    )


def schedule_and_price_execution(order: TradeOrder, cfg: EngineConfig) -> tuple[ExecutionSchedule, TotalExecutionCost]:
    """The real, composed Stage 8 + Stage 6 workflow: compute the real
    schedule first, then price the trade's total execution cost using
    THAT schedule's own ``required_days`` as the real slippage delay
    -- a trade too large to execute in one day carries a real, longer
    adverse-selection exposure, not the same single-day delay a small
    trade would.
    """
    schedule = compute_execution_schedule(order, cfg.scheduling)
    cost = compute_total_execution_cost(order, cfg, delay_days=schedule.required_days)
    return schedule, cost
