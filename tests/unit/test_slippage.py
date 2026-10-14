import pandas as pd
import pytest

from transaction_cost.config import SlippageConfig
from transaction_cost.data import TradeOrder
from transaction_cost.slippage import compute_slippage_cost


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order(daily_volatility=0.02) -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.02, price=100.0, adv_usd=1.0e6, daily_volatility=daily_volatility)


def test_slippage_matches_the_real_formula():
    cfg = SlippageConfig(adverse_selection_coefficient=0.3, default_delay_days=1)
    result = compute_slippage_cost(_order(0.02), cfg)
    expected_bps = 0.3 * (0.02 * 10_000.0) * 1.0
    assert result.cost_fraction == pytest.approx(expected_bps / 10_000.0)


def test_slippage_scales_with_real_sqrt_of_delay():
    cfg = SlippageConfig(adverse_selection_coefficient=0.3)
    one_day = compute_slippage_cost(_order(), cfg, delay_days=1)
    four_days = compute_slippage_cost(_order(), cfg, delay_days=4)
    assert four_days.cost_fraction == pytest.approx(2.0 * one_day.cost_fraction)  # sqrt(4) = 2


def test_slippage_increases_with_real_volatility():
    cfg = SlippageConfig()
    low_vol = compute_slippage_cost(_order(daily_volatility=0.01), cfg)
    high_vol = compute_slippage_cost(_order(daily_volatility=0.05), cfg)
    assert high_vol.cost_fraction > low_vol.cost_fraction


def test_slippage_uses_the_conservative_fallback_when_volatility_is_missing():
    cfg = SlippageConfig(missing_data_slippage_bps=20.0)
    result = compute_slippage_cost(_order(daily_volatility=None), cfg)
    assert result.cost_fraction == pytest.approx(20.0 / 10_000.0)
    assert result.detail["data_known"] is False


def test_slippage_rejects_a_non_positive_delay():
    cfg = SlippageConfig()
    with pytest.raises(ValueError):
        compute_slippage_cost(_order(), cfg, delay_days=0)
