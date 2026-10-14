"""Stage 10 -- Hardening: the comprehensive check for this engine,
adapted to its real scope. Unlike the other three engines, this
engine never consumes a historical date range itself (it operates on
ONE already-decided ``OptimizationResult`` snapshot), so there is no
"extend into the future" look-ahead scenario to test here. Its real
comprehensive checks are:

1. Given a FIXED optimizer output, is the whole cost/scheduling/
   profitability/reporting pipeline exactly reproducible? (Nothing in
   Stages 6-9 calls a numerical solver or a near-zero-magnitude matrix
   multiply -- unlike portfolio-construction-engine's SLSQP or
   portfolio-risk-engine's BLAS quadratic form -- so this SHOULD hold
   exactly, confirmed directly rather than assumed.)
2. Does real illiquidity/trade size genuinely drive higher costs and
   lower net profitability end to end -- a real, meaningful
   monotonicity property, not just unit-level formula checks.
"""

import numpy as np
import pandas as pd
from portfolio_construction.config import OptimizerConfig
from portfolio_construction.constraints import GrossLeverageConstraint, MaxPositionWeightConstraint
from portfolio_construction.data import OptimizationInput
from portfolio_construction.optimization import optimize_portfolio

from transaction_cost.config import EngineConfig
from transaction_cost.pipeline import run_full_cost_analysis
from transaction_cost.reporting import report_to_dict


def _fixed_optimizer_output():
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
    return opt_result, current_weights


def test_full_pipeline_is_exactly_reproducible_given_a_fixed_optimizer_output():
    opt_result, current_weights = _fixed_optimizer_output()
    market_data = {sid: {"price": 100.0, "adv_usd": 5.0e6, "daily_volatility": 0.015} for sid in opt_result.target_weights}
    cfg = EngineConfig()

    result_a = run_full_cost_analysis(opt_result, current_weights, market_data, 1.0e8, cfg, "P")
    result_b = run_full_cost_analysis(opt_result, current_weights, market_data, 1.0e8, cfg, "P")
    assert report_to_dict(result_a) == report_to_dict(result_b)


def test_real_illiquidity_and_trade_size_drive_higher_cost_and_lower_net_profitability():
    opt_result, current_weights = _fixed_optimizer_output()
    cfg = EngineConfig()

    liquid_market_data = {sid: {"price": 100.0, "adv_usd": 1.0e9, "daily_volatility": 0.01} for sid in opt_result.target_weights}
    illiquid_market_data = {sid: {"price": 100.0, "adv_usd": 1.0e5, "daily_volatility": 0.05} for sid in opt_result.target_weights}

    liquid_result = run_full_cost_analysis(opt_result, current_weights, liquid_market_data, 1.0e8, cfg, "P")
    illiquid_result = run_full_cost_analysis(opt_result, current_weights, illiquid_market_data, 1.0e8, cfg, "P")

    assert illiquid_result.net_profitability.total_execution_cost > liquid_result.net_profitability.total_execution_cost
    assert illiquid_result.net_profitability.net_expected_return < liquid_result.net_profitability.net_expected_return
