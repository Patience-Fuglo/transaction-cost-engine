import pandas as pd
import pytest

from transaction_cost.config import EngineConfig
from transaction_cost.data import TradeOrder
from transaction_cost.execution import compute_total_execution_cost
from transaction_cost.profitability import compute_net_profitability


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s)


def _order(trade_weight=0.05) -> TradeOrder:
    return TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=trade_weight, price=100.0, adv_usd=1.0e6, daily_volatility=0.02)


def test_net_profitability_matches_the_real_reconciliation_identity():
    cfg = EngineConfig()
    order = _order()
    cost = compute_total_execution_cost(order, cfg)
    result = compute_net_profitability("P", _ts("2020-06-30"), 0.05, [order], [cost])
    assert result.net_expected_return == pytest.approx(result.gross_expected_return - result.total_execution_cost)


def test_net_profitability_warns_when_real_cost_consumes_all_profit():
    cfg = EngineConfig()
    # a large, illiquid trade with a tiny real gross expected return
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.5, price=100.0, adv_usd=1.0e5, daily_volatility=0.05)
    cost = compute_total_execution_cost(order, cfg)
    result = compute_net_profitability("P", _ts("2020-06-30"), 0.0001, [order], [cost])
    assert result.net_expected_return < 0
    assert any("not worth making" in w for w in result.warnings)


def test_net_profitability_does_not_warn_when_real_profit_survives():
    cfg = EngineConfig()
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.01, price=100.0, adv_usd=1.0e8, daily_volatility=0.01)
    cost = compute_total_execution_cost(order, cfg)
    result = compute_net_profitability("P", _ts("2020-06-30"), 0.05, [order], [cost])
    assert result.net_expected_return > 0
    assert not any("not worth making" in w for w in result.warnings)


def test_net_profitability_propagates_real_component_fallback_warnings():
    cfg = EngineConfig()
    order = TradeOrder(security_id="A", as_of=_ts("2020-06-30"), trade_weight=0.02, price=100.0, adv_usd=None, daily_volatility=None)
    cost = compute_total_execution_cost(order, cfg)
    result = compute_net_profitability("P", _ts("2020-06-30"), 0.05, [order], [cost])
    assert any("A:" in w for w in result.warnings)
