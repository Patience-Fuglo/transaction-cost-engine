import pandas as pd
import pytest

from transaction_cost.config import FeeConfig
from transaction_cost.data import TradeOrder
from transaction_cost.fees import compute_fee_cost


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order() -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.02, price=100.0, adv_usd=1.0e6, daily_volatility=0.02)


def test_fee_cost_matches_the_real_flat_rate():
    result = compute_fee_cost(_order(), FeeConfig(fee_bps=2.5))
    assert result.cost_fraction == pytest.approx(2.5 / 10_000.0)


def test_fee_cost_is_independent_of_real_trade_size():
    small = compute_fee_cost(
        TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.001, price=100.0, adv_usd=1.0e6, daily_volatility=0.02),
        FeeConfig(fee_bps=2.0),
    )
    large = compute_fee_cost(
        TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.10, price=100.0, adv_usd=1.0e6, daily_volatility=0.02),
        FeeConfig(fee_bps=2.0),
    )
    assert small.cost_fraction == pytest.approx(large.cost_fraction)  # flat bps rate, same regardless of size


def test_fee_config_rejects_a_negative_rate():
    with pytest.raises(ValueError):
        FeeConfig(fee_bps=-1.0)
