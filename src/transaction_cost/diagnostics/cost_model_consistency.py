"""Portfolio-wide audit remediation (item 3): a real cost-model
consistency diagnostic. Two structurally different real "cost of
trading" estimates coexist in this portfolio for the exact same real
trade -- ``portfolio-construction-engine``'s own simplified
optimizer-side ``TransactionCostModel`` (a linear-plus-impact^1.5
estimate used only to make the optimizer itself cost-aware, surfaced
on ``OptimizationResult.transaction_cost``), and this engine's own
detailed spread + impact + slippage + fee estimate. Nothing in this
portfolio previously checked that the two stayed in the same ballpark
for the same real trade.

This module adds that check. It never replaces either model, never
assumes they must match exactly (they are two deliberately different
real models, not two implementations of the same formula), and never
adds the two together -- that would double-count the real cost of
one trade.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
from portfolio_construction.data import OptimizationResult

from ..config import CostConsistencyConfig, EngineConfig
from ..data.schemas import CostModelConsistencyResult
from ..execution.total_cost import aggregate_portfolio_execution_cost, compute_total_execution_cost
from ..execution.trade_builder import build_trade_orders


def compare_cost_estimates(
    optimization_result: OptimizationResult,
    current_weights: dict[str, float],
    market_data: dict[str, dict],
    portfolio_value: float,
    engine_cfg: EngineConfig,
) -> CostModelConsistencyResult:
    """Computes this engine's own real detailed cost estimate for the
    exact same trade ``optimization_result`` already describes, then
    compares it against that result's own real
    ``transaction_cost`` field -- both already expressed as a real
    fraction of portfolio value, so no unit conversion is needed
    before comparing them.
    """
    cost_consistency_cfg: CostConsistencyConfig = engine_cfg.cost_consistency
    optimizer_cost_fraction = optimization_result.transaction_cost

    # Pre-filter to securities with real market data BEFORE calling
    # build_trade_orders, which deliberately RAISES on a real nonzero
    # trade with no real price (the correct, established convention
    # for the core pricing path -- see its own docstring). A
    # diagnostic should not crash the whole comparison over one
    # missing security; it excludes that security from this estimate
    # and says so, rather than overriding that function's own real
    # behavior.
    warnings: list[str] = []
    tradable_weights = {sid: w for sid, w in optimization_result.target_weights.items() if sid in market_data}
    missing = sorted(set(optimization_result.target_weights) - set(tradable_weights))
    if missing:
        warnings.append(f"{missing}: no real market data -- excluded from the detailed cost estimate, not fabricated")

    if not tradable_weights:
        detailed_cost_fraction = 0.0
        warnings.append("no real tradable securities with real market data -- detailed cost is 0.0, not fabricated")
    else:
        tradable_result = OptimizationResult(
            as_of=optimization_result.as_of, portfolio_id=optimization_result.portfolio_id, target_weights=tradable_weights,
            expected_return=optimization_result.expected_return, expected_variance=optimization_result.expected_variance,
            turnover=optimization_result.turnover, converged=optimization_result.converged,
        )
        orders = build_trade_orders(tradable_result, current_weights, market_data, portfolio_value)
        if not orders:
            detailed_cost_fraction = 0.0
            warnings.append("no real nonzero trade among the tradable securities -- detailed cost is 0.0, not fabricated")
        else:
            costs = [compute_total_execution_cost(order, engine_cfg) for order in orders]
            detailed_cost_fraction = aggregate_portfolio_execution_cost(orders, costs)

    absolute_difference = abs(optimizer_cost_fraction - detailed_cost_fraction)
    denominator = max(abs(optimizer_cost_fraction), abs(detailed_cost_fraction), cost_consistency_cfg.near_zero_epsilon)
    relative_difference = absolute_difference / denominator
    flagged_as_divergent = relative_difference > cost_consistency_cfg.relative_divergence_threshold

    if flagged_as_divergent:
        warnings.append(
            f"optimizer cost estimate ({optimizer_cost_fraction:.6%}) and detailed cost estimate "
            f"({detailed_cost_fraction:.6%}) diverge by {relative_difference:.1%}, above the configured "
            f"{cost_consistency_cfg.relative_divergence_threshold:.0%} threshold -- a real divergence to "
            "investigate, not necessarily an error in either model"
        )

    return CostModelConsistencyResult(
        portfolio_id=optimization_result.portfolio_id,
        as_of=optimization_result.as_of,
        optimizer_cost_fraction=optimizer_cost_fraction,
        detailed_cost_fraction=detailed_cost_fraction,
        absolute_difference=absolute_difference,
        relative_difference=relative_difference,
        flagged_as_divergent=flagged_as_divergent,
        warnings=tuple(warnings),
    )


def compare_cost_estimates_across_schedule(
    optimization_results: Sequence[OptimizationResult],
    current_weights_by_date: dict[pd.Timestamp, dict[str, float]],
    market_data_by_date: dict[pd.Timestamp, dict[str, dict]],
    portfolio_value: float,
    engine_cfg: EngineConfig,
) -> list[CostModelConsistencyResult]:
    """The same real per-trade comparison, across a real rebalancing
    schedule -- one real result per ``OptimizationResult``, never
    aggregated into a single number (a divergence at one real
    rebalance should never be averaged away by agreement at others).
    """
    results: list[CostModelConsistencyResult] = []
    for result in optimization_results:
        current_weights = current_weights_by_date.get(result.as_of, {})
        market_data = market_data_by_date.get(result.as_of, {})
        results.append(compare_cost_estimates(result, current_weights, market_data, portfolio_value, engine_cfg))
    return results
