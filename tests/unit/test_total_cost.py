import pandas as pd
import pytest
from portfolio_construction.data import OptimizationResult

from transaction_cost.config import EngineConfig
from transaction_cost.data import TradeOrder
from transaction_cost.execution import aggregate_portfolio_execution_cost, build_trade_orders, compute_total_execution_cost


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order(trade_weight=0.02) -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=trade_weight, price=100.0, adv_usd=1.0e6, daily_volatility=0.02)


def test_total_cost_sums_all_four_real_components():
    cfg = EngineConfig()
    result = compute_total_execution_cost(_order(), cfg)
    assert result.total_cost_fraction == pytest.approx(
        result.spread_cost_fraction + result.impact_cost_fraction + result.slippage_cost_fraction + result.fee_cost_fraction
    )


def test_total_cost_warns_when_any_component_used_a_real_fallback():
    cfg = EngineConfig()
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.02, price=100.0, adv_usd=None, daily_volatility=None)
    result = compute_total_execution_cost(order, cfg)
    assert len(result.warnings) >= 2  # spread AND impact AND slippage all missing real data


def test_build_trade_orders_computes_the_real_trade_weight_delta():
    opt_result = OptimizationResult(
        as_of=_ts("2020-06-30"), portfolio_id="P", target_weights={"A": 0.6, "B": 0.4},
        expected_return=0.01, expected_variance=0.02, turnover=0.3, converged=True,
    )
    current_weights = {"A": 0.5, "B": 0.5}
    market_data = {"A": {"price": 100.0, "adv_usd": 1.0e6, "daily_volatility": 0.02}, "B": {"price": 50.0, "adv_usd": 2.0e6, "daily_volatility": 0.01}}
    orders = build_trade_orders(opt_result, current_weights, market_data, portfolio_value=1.0e8)
    orders_by_id = {o.security_id: o for o in orders}
    assert orders_by_id["A"].trade_weight == pytest.approx(0.1)
    assert orders_by_id["B"].trade_weight == pytest.approx(-0.1)


def test_build_trade_orders_excludes_a_security_with_no_real_trade():
    opt_result = OptimizationResult(
        as_of=_ts("2020-06-30"), portfolio_id="P", target_weights={"A": 0.5},
        expected_return=0.01, expected_variance=0.02, turnover=0.0, converged=True,
    )
    orders = build_trade_orders(opt_result, {"A": 0.5}, {"A": {"price": 100.0}}, portfolio_value=1.0)
    assert orders == []


def test_build_trade_orders_raises_when_a_real_trade_has_no_real_price():
    opt_result = OptimizationResult(
        as_of=_ts("2020-06-30"), portfolio_id="P", target_weights={"A": 0.5},
        expected_return=0.01, expected_variance=0.02, turnover=0.5, converged=True,
    )
    with pytest.raises(ValueError):
        build_trade_orders(opt_result, {"A": 0.0}, {}, portfolio_value=1.0)


def test_aggregate_portfolio_execution_cost_converts_to_portfolio_value_units():
    cfg = EngineConfig()
    orders = [TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.1, price=100.0, adv_usd=1.0e6, daily_volatility=0.02)]
    costs = [compute_total_execution_cost(orders[0], cfg)]
    portfolio_cost = aggregate_portfolio_execution_cost(orders, costs)
    assert portfolio_cost == pytest.approx(costs[0].total_cost_fraction * 0.1)
