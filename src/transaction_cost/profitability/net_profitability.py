"""Stage 7 -- this engine's own central question, answered directly:
how much of a real expected trading profit survives after real
execution costs. Reuses Stage 6's own real portfolio-level cost
aggregation -- never a separately re-derived cost figure.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from ..data.schemas import NetProfitabilityResult, TotalExecutionCost, TradeOrder
from ..execution.total_cost import aggregate_portfolio_execution_cost


def compute_net_profitability(
    portfolio_id: str,
    as_of: pd.Timestamp,
    gross_expected_return: float,
    orders: Sequence[TradeOrder],
    costs: Sequence[TotalExecutionCost],
) -> NetProfitabilityResult:
    total_cost = aggregate_portfolio_execution_cost(orders, costs)
    net_expected_return = gross_expected_return - total_cost

    warnings: list[str] = []
    if gross_expected_return > 0 and total_cost >= gross_expected_return:
        warnings.append(
            f"real execution cost ({total_cost:.4%}) consumes all of (or exceeds) the real gross expected "
            f"return ({gross_expected_return:.4%}) -- this trade is not worth making as costed"
        )
    for cost in costs:
        if cost.warnings:
            warnings.extend(f"{cost.security_id}: {w}" for w in cost.warnings)

    return NetProfitabilityResult(
        portfolio_id=portfolio_id,
        as_of=as_of,
        gross_expected_return=gross_expected_return,
        total_execution_cost=total_cost,
        net_expected_return=net_expected_return,
        warnings=tuple(warnings),
    )
