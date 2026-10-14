"""End-to-end: the full Stage 9 orchestration (Stages 6-8) and its
reproducible report, on a real portfolio-construction-engine
optimizer output.
"""

import json

import numpy as np
import pandas as pd
import pytest
from portfolio_construction.config import OptimizerConfig
from portfolio_construction.constraints import GrossLeverageConstraint, MaxPositionWeightConstraint
from portfolio_construction.data import OptimizationInput
from portfolio_construction.optimization import optimize_portfolio

from transaction_cost.config import EngineConfig
from transaction_cost.pipeline import run_full_cost_analysis
from transaction_cost.reporting import render_markdown_report, report_to_dict


@pytest.fixture(scope="module")
def analysis_result():
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

    market_data = {sid: {"price": 100.0, "adv_usd": 5.0e6, "daily_volatility": 0.015} for sid in security_ids}
    return run_full_cost_analysis(opt_result, current_weights, market_data, portfolio_value=1.0e8, cfg=EngineConfig(), portfolio_id="P")


def test_report_to_dict_is_json_serializable(analysis_result):
    json.dumps(report_to_dict(analysis_result))


def test_report_reconciles_with_the_real_underlying_result(analysis_result):
    payload = report_to_dict(analysis_result)
    assert payload["n_trades"] == len(analysis_result.orders)
    assert payload["net_profitability"]["net_expected_return"] == pytest.approx(analysis_result.net_profitability.net_expected_return)


def test_render_markdown_report_contains_every_real_section(analysis_result):
    markdown = render_markdown_report(analysis_result)
    assert "## Trades" in markdown
    assert "## Net Profitability" in markdown
    assert "P" in markdown
    assert "synthetic" in markdown.lower()


def test_report_rendering_is_deterministic(analysis_result):
    first = render_markdown_report(analysis_result)
    second = render_markdown_report(analysis_result)
    assert first == second
    assert report_to_dict(analysis_result) == report_to_dict(analysis_result)
