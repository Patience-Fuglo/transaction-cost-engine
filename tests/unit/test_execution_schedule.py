import pandas as pd
import pytest

from transaction_cost.config import EngineConfig, SchedulingConfig
from transaction_cost.data import TradeOrder
from transaction_cost.scheduling import compute_execution_schedule, schedule_and_price_execution


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def test_small_trade_requires_a_single_real_day():
    cfg = SchedulingConfig(max_participation_rate=0.10)
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.01, price=100.0, adv_usd=1.0e8, daily_volatility=0.02, portfolio_value=1.0e8)
    # participation_rate = 1e6/1e8 = 0.01 < 0.10
    schedule = compute_execution_schedule(order, cfg)
    assert schedule.required_days == 1
    assert schedule.daily_trade_fraction == pytest.approx(1.0)


def test_large_trade_requires_multiple_real_days():
    cfg = SchedulingConfig(max_participation_rate=0.10)
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.35, price=100.0, adv_usd=1.0e8, daily_volatility=0.02, portfolio_value=1.0e8)
    # participation_rate = 3.5e7/1e8 = 0.35 -> ceil(0.35/0.10) = 4 real days
    schedule = compute_execution_schedule(order, cfg)
    assert schedule.required_days == 4
    assert schedule.daily_trade_fraction == pytest.approx(0.25)


def test_schedule_with_unknown_adv_defaults_to_a_single_day():
    cfg = SchedulingConfig()
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.5, price=100.0, adv_usd=None, daily_volatility=0.02)
    schedule = compute_execution_schedule(order, cfg)
    assert schedule.required_days == 1


def test_schedule_and_price_execution_feeds_required_days_into_real_slippage():
    cfg = EngineConfig(scheduling=SchedulingConfig(max_participation_rate=0.10))
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.35, price=100.0, adv_usd=1.0e8, daily_volatility=0.02, portfolio_value=1.0e8)
    schedule, cost = schedule_and_price_execution(order, cfg)
    assert schedule.required_days == 4
    expected_slippage_bps = cfg.slippage.adverse_selection_coefficient * (0.02 * 10_000.0) * (4**0.5)
    assert cost.slippage_cost_fraction == pytest.approx(expected_slippage_bps / 10_000.0)
