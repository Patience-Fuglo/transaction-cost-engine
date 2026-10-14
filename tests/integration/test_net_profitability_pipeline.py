"""End-to-end: optimize a real portfolio with portfolio-construction-
engine, then price the real cost of executing it and compute net
profitability -- a genuine cross-repo integration proof, not a
hand-built fixture standing in for the dependency.
"""

import numpy as np
import pandas as pd
import pytest
from portfolio_construction.config import OptimizerConfig
from portfolio_construction.constraints import GrossLeverageConstraint, MaxPositionWeightConstraint
from portfolio_construction.data import OptimizationInput
from portfolio_construction.optimization import optimize_portfolio

from transaction_cost.config import EngineConfig
from transaction_cost.execution import build_trade_orders, compute_total_execution_cost
from transaction_cost.profitability import compute_net_profitability


def test_net_profitability_on_a_real_optimizer_output():
    security_ids = ["A", "B", "C", "D", "E"]
    covariance = pd.DataFrame(np.diag([0.02, 0.03, 0.025, 0.04, 0.035]), index=security_ids, columns=security_ids)
    expected_returns = {"A": 0.02, "B": 0.01, "C": 0.015, "D": 0.005, "E": 0.012}
    current_weights = {sid: 0.2 for sid in security_ids}

    opt_input = OptimizationInput(
        as_of=pd.Timestamp("2020-06-30"), security_ids=tuple(security_ids), expected_returns=expected_returns,
        covariance=covariance, current_weights=current_weights,
    )
    constraints = [MaxPositionWeightConstraint(max_weight=0.4, long_only=True), GrossLeverageConstraint(max_gross_leverage=1.0)]
    opt_result = optimize_portfolio(opt_input, "mean_variance", constraints, OptimizerConfig())
    assert opt_result.converged

    market_data = {sid: {"price": 100.0, "adv_usd": 5.0e6, "daily_volatility": 0.015} for sid in security_ids}
    orders = build_trade_orders(opt_result, current_weights, market_data, portfolio_value=1.0e8)
    assert len(orders) > 0  # the optimizer should have real trades to execute

    cost_cfg = EngineConfig()
    costs = [compute_total_execution_cost(order, cost_cfg) for order in orders]
    net = compute_net_profitability("P", opt_result.as_of, opt_result.expected_return, orders, costs)

    assert net.net_expected_return == pytest.approx(net.gross_expected_return - net.total_execution_cost)
    assert net.total_execution_cost >= 0
