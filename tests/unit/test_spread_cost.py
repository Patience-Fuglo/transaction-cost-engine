import pandas as pd
import pytest

from transaction_cost.config import SpreadConfig
from transaction_cost.data import TradeOrder
from transaction_cost.spread import compute_spread_cost


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order(adv_usd) -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.02, price=100.0, adv_usd=adv_usd, daily_volatility=0.02)


def test_spread_at_the_reference_adv_matches_base_spread_exactly():
    cfg = SpreadConfig(base_spread_bps=5.0, reference_adv_usd=1.0e7, illiquidity_exponent=0.5)
    result = compute_spread_cost(_order(1.0e7), cfg)
    assert result.cost_fraction == pytest.approx(5.0 / 10_000.0)


def test_spread_widens_as_real_adv_falls():
    cfg = SpreadConfig(base_spread_bps=5.0, reference_adv_usd=1.0e7, illiquidity_exponent=0.5)
    liquid = compute_spread_cost(_order(1.0e8), cfg)
    illiquid = compute_spread_cost(_order(1.0e6), cfg)
    assert illiquid.cost_fraction > liquid.cost_fraction


def test_spread_matches_the_real_sqrt_scaling_formula():
    cfg = SpreadConfig(base_spread_bps=5.0, reference_adv_usd=1.0e7, illiquidity_exponent=0.5)
    # ADV = reference/4 -> spread = base * sqrt(4) = 2 * base
    result = compute_spread_cost(_order(1.0e7 / 4), cfg)
    assert result.cost_fraction == pytest.approx(2.0 * 5.0 / 10_000.0)


def test_spread_is_floored_at_the_real_minimum():
    cfg = SpreadConfig(base_spread_bps=5.0, reference_adv_usd=1.0e7, illiquidity_exponent=0.5, min_spread_bps=3.0)
    result = compute_spread_cost(_order(1.0e12), cfg)  # extremely liquid -- would go below the floor otherwise
    assert result.cost_fraction == pytest.approx(3.0 / 10_000.0)


def test_spread_uses_the_conservative_fallback_when_adv_is_unknown():
    cfg = SpreadConfig(missing_adv_spread_bps=50.0)
    result = compute_spread_cost(_order(None), cfg)
    assert result.cost_fraction == pytest.approx(50.0 / 10_000.0)
    assert result.detail["adv_known"] is False
