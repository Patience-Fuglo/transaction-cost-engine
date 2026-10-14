import pandas as pd
import pytest

from transaction_cost.data import CostComponent, ExecutionSchedule, NetProfitabilityResult, TradeOrder


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def test_trade_order_trade_value_usd_matches_the_real_formula():
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.05, price=100.0, adv_usd=1.0e6, daily_volatility=0.02, portfolio_value=1.0e8)
    assert order.trade_value_usd == pytest.approx(0.05 * 1.0e8)


def test_trade_order_participation_rate_matches_the_real_formula():
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.01, price=100.0, adv_usd=1.0e6, daily_volatility=0.02, portfolio_value=1.0e8)
    assert order.participation_rate == pytest.approx(abs(0.01 * 1.0e8) / 1.0e6)


def test_trade_order_participation_rate_is_none_without_real_adv():
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.01, price=100.0, adv_usd=None, daily_volatility=0.02)
    assert order.participation_rate is None


def test_trade_order_rejects_non_positive_price():
    with pytest.raises(ValueError):
        TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.01, price=0.0, adv_usd=1.0e6, daily_volatility=0.02)


def test_cost_component_rejects_negative_cost():
    with pytest.raises(ValueError):
        CostComponent(security_id="A", as_of=_ts("2020-06-30"), component_name="spread", cost_fraction=-0.01)


def test_net_profitability_enforces_the_real_reconciliation_identity():
    with pytest.raises(ValueError):
        NetProfitabilityResult(portfolio_id="P", as_of=_ts("2020-06-30"), gross_expected_return=0.05, total_execution_cost=0.01, net_expected_return=0.05)  # should be 0.04


def test_net_profitability_accepts_the_real_correct_identity():
    result = NetProfitabilityResult(portfolio_id="P", as_of=_ts("2020-06-30"), gross_expected_return=0.05, total_execution_cost=0.01, net_expected_return=0.04)
    assert result.net_expected_return == pytest.approx(0.04)


def test_execution_schedule_rejects_an_out_of_range_participation_rate():
    with pytest.raises(ValueError):
        ExecutionSchedule(security_id="A", as_of=_ts("2020-06-30"), max_participation_rate=1.5, required_days=1, daily_trade_fraction=1.0)


def test_execution_schedule_rejects_non_positive_required_days():
    with pytest.raises(ValueError):
        ExecutionSchedule(security_id="A", as_of=_ts("2020-06-30"), max_participation_rate=0.1, required_days=0, daily_trade_fraction=1.0)
