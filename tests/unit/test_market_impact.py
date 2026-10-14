import pandas as pd
import pytest

from transaction_cost.config import ImpactConfig
from transaction_cost.data import TradeOrder
from transaction_cost.impact import compute_impact_cost


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order(trade_weight: float, adv_usd=1.0e6, daily_volatility=0.02, portfolio_value=1.0e8) -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=trade_weight, price=100.0, adv_usd=adv_usd, daily_volatility=daily_volatility, portfolio_value=portfolio_value)


def test_impact_matches_the_real_square_root_formula():
    cfg = ImpactConfig(impact_coefficient=0.5)
    order = _order(trade_weight=0.01, adv_usd=1.0e6, daily_volatility=0.02, portfolio_value=1.0e8)
    result = compute_impact_cost(order, cfg)
    participation_rate = order.participation_rate
    expected_bps = 0.5 * (0.02 * 10_000.0) * participation_rate**0.5
    assert result.cost_fraction == pytest.approx(expected_bps / 10_000.0)


def test_impact_increases_with_real_participation_rate():
    cfg = ImpactConfig()
    small_trade = compute_impact_cost(_order(trade_weight=0.001), cfg)
    large_trade = compute_impact_cost(_order(trade_weight=0.05), cfg)
    assert large_trade.cost_fraction > small_trade.cost_fraction


def test_impact_scales_with_real_sqrt_of_participation_not_linearly():
    cfg = ImpactConfig()
    # 4x the trade size -> exactly 2x the impact (sqrt scaling), not 4x
    base = compute_impact_cost(_order(trade_weight=0.01), cfg)
    quadrupled = compute_impact_cost(_order(trade_weight=0.04), cfg)
    assert quadrupled.cost_fraction == pytest.approx(2.0 * base.cost_fraction)


def test_impact_increases_with_real_volatility():
    cfg = ImpactConfig()
    low_vol = compute_impact_cost(_order(trade_weight=0.01, daily_volatility=0.01), cfg)
    high_vol = compute_impact_cost(_order(trade_weight=0.01, daily_volatility=0.05), cfg)
    assert high_vol.cost_fraction > low_vol.cost_fraction


def test_impact_uses_the_conservative_fallback_when_data_is_missing():
    cfg = ImpactConfig(missing_data_impact_bps=100.0)
    result = compute_impact_cost(_order(trade_weight=0.01, adv_usd=None), cfg)
    assert result.cost_fraction == pytest.approx(100.0 / 10_000.0)
    assert result.detail["data_known"] is False
