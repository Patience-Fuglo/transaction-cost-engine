"""Stage 9 -- the end-to-end orchestration: runs Stages 6-8 once, in
dependency order, for one real, already-decided portfolio change.
Every step reuses the exact function that stage already built and
tested -- nothing here re-derives any real computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from portfolio_construction.data import OptimizationResult

from ..config import EngineConfig
from ..data.schemas import ExecutionSchedule, NetProfitabilityResult, TotalExecutionCost, TradeOrder
from ..execution import build_trade_orders
from ..profitability import compute_net_profitability
from ..scheduling import schedule_and_price_execution


@dataclass
class TransactionCostAnalysisResult:
    portfolio_id: str
    as_of: pd.Timestamp
    orders: list[TradeOrder] = field(default_factory=list)
    schedules: list[ExecutionSchedule] = field(default_factory=list)
    costs: list[TotalExecutionCost] = field(default_factory=list)
    net_profitability: NetProfitabilityResult | None = None


def run_full_cost_analysis(
    opt_result: OptimizationResult,
    current_weights: dict[str, float],
    market_data: dict[str, dict],
    portfolio_value: float,
    cfg: EngineConfig,
    portfolio_id: str = "portfolio",
) -> TransactionCostAnalysisResult:
    orders = build_trade_orders(opt_result, current_weights, market_data, portfolio_value)

    schedules: list[ExecutionSchedule] = []
    costs: list[TotalExecutionCost] = []
    for order in orders:
        schedule, cost = schedule_and_price_execution(order, cfg)
        schedules.append(schedule)
        costs.append(cost)

    net_profitability = compute_net_profitability(portfolio_id, opt_result.as_of, opt_result.expected_return, orders, costs)

    return TransactionCostAnalysisResult(
        portfolio_id=portfolio_id,
        as_of=opt_result.as_of,
        orders=orders,
        schedules=schedules,
        costs=costs,
        net_profitability=net_profitability,
    )
