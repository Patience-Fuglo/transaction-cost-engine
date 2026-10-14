"""Portfolio-wide audit remediation (item 3): the real cost-model
consistency diagnostic. Compares portfolio-construction-engine's own
simplified optimizer-side cost estimate against this engine's own
detailed estimate for the same real trade -- never assumes they must
match, never sums them, never replaces either model.
"""

import pandas as pd
import pytest
from portfolio_construction.data import OptimizationResult

from transaction_cost.config import CostConsistencyConfig, EngineConfig
from transaction_cost.diagnostics import compare_cost_estimates

AS_OF = pd.Timestamp("2020-06-30")


def _opt_result(transaction_cost: float, target_weights=None):
    return OptimizationResult(
        as_of=AS_OF, portfolio_id="P", target_weights=target_weights or {"A": 0.2, "B": -0.1}, expected_return=0.0,
        expected_variance=0.0, turnover=0.3, converged=True, transaction_cost=transaction_cost,
    )


def _market_data():
    return {"A": {"price": 100.0, "adv_usd": 5_000_000.0, "daily_volatility": 0.015}, "B": {"price": 50.0, "adv_usd": 2_000_000.0, "daily_volatility": 0.02}}


def test_detailed_cost_is_a_real_positive_number_for_a_real_trade():
    result = compare_cost_estimates(_opt_result(0.001), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, EngineConfig())
    assert result.detailed_cost_fraction > 0.0


def test_absolute_and_relative_differences_are_computed_correctly():
    cfg = EngineConfig()
    result = compare_cost_estimates(_opt_result(0.01), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, cfg)
    assert result.absolute_difference == pytest.approx(abs(result.optimizer_cost_fraction - result.detailed_cost_fraction))
    expected_denom = max(abs(result.optimizer_cost_fraction), abs(result.detailed_cost_fraction), cfg.cost_consistency.near_zero_epsilon)
    assert result.relative_difference == pytest.approx(result.absolute_difference / expected_denom)


def test_near_zero_estimates_do_not_blow_up_the_relative_difference():
    """Two real, tiny estimates (effectively agreeing at ~0) must
    never produce an exploding relative difference due to dividing by
    something close to zero.
    """
    result = compare_cost_estimates(_opt_result(1e-9), {"A": 0.0, "B": 0.0}, {}, 1.0e8, EngineConfig())
    assert result.detailed_cost_fraction == 0.0
    assert result.relative_difference < 10.0  # finite and sane, not a huge/inf blow-up


def test_a_small_real_divergence_is_not_flagged():
    cfg = EngineConfig()
    detailed = compare_cost_estimates(_opt_result(0.0), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, cfg).detailed_cost_fraction
    close_result = compare_cost_estimates(_opt_result(detailed * 1.05), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, cfg)
    assert not close_result.flagged_as_divergent


def test_a_large_real_divergence_is_flagged_with_a_real_warning():
    cfg = EngineConfig(cost_consistency=CostConsistencyConfig(relative_divergence_threshold=0.5))
    result = compare_cost_estimates(_opt_result(0.0), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, cfg)  # optimizer says ~0, detailed says real nonzero
    assert result.flagged_as_divergent
    assert any("diverge" in w for w in result.warnings)


def test_divergence_threshold_is_configurable_and_respected():
    detailed = compare_cost_estimates(_opt_result(0.0), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, EngineConfig()).detailed_cost_fraction
    moderate_divergence = _opt_result(detailed * 1.3)

    strict_cfg = EngineConfig(cost_consistency=CostConsistencyConfig(relative_divergence_threshold=0.1))
    lenient_cfg = EngineConfig(cost_consistency=CostConsistencyConfig(relative_divergence_threshold=0.9))

    strict_result = compare_cost_estimates(moderate_divergence, {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, strict_cfg)
    lenient_result = compare_cost_estimates(moderate_divergence, {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, lenient_cfg)

    assert strict_result.flagged_as_divergent
    assert not lenient_result.flagged_as_divergent


def test_no_tradable_security_with_market_data_gives_zero_detailed_cost_not_fatal():
    result = compare_cost_estimates(_opt_result(0.0, target_weights={"C": 0.2}), {"C": 0.0}, _market_data(), 1.0e8, EngineConfig())
    assert result.detailed_cost_fraction == 0.0
    assert any("no real tradable securities" in w for w in result.warnings)


def test_units_are_both_a_fraction_of_portfolio_value_never_summed():
    """The two real estimates must never be added together anywhere
    in this result -- each is reported independently."""
    result = compare_cost_estimates(_opt_result(0.01), {"A": 0.0, "B": 0.0}, _market_data(), 1.0e8, EngineConfig())
    assert result.optimizer_cost_fraction == pytest.approx(0.01)
    assert not hasattr(result, "total_cost_fraction")
