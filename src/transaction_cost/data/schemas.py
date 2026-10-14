"""Core data schemas for the transaction cost and market impact engine.

This engine never re-runs an optimizer or re-decides a trade -- it
consumes ``portfolio-construction-engine``'s own real
``OptimizationResult`` (the already-decided target weights and
turnover) and ``factor-model-engine``'s own real market data (price,
ADV, volatility). It answers "how much does executing this ALREADY-
DECIDED trade really cost," never "which trade should we make."
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class TradeOrder:
    """One real security's trade, derived from an already-decided
    portfolio change (``target_weight - current_weight``, from
    ``portfolio-construction-engine``'s own ``OptimizationResult``),
    carrying the real reference data its cost model needs.

    ``adv_usd`` is ``None`` (never silently ``0.0``) when real volume
    data is insufficient -- the same convention
    ``factor-model-engine``'s own ``MarketObservation.adv_20d`` uses.
    """

    security_id: str
    as_of: pd.Timestamp
    trade_weight: float  # signed: positive = buy, negative = sell, as a fraction of portfolio value
    price: float
    adv_usd: float | None
    daily_volatility: float | None  # real daily return std, e.g. from a real historical return series
    portfolio_value: float = 1.0  # RESEARCH ASSUMPTION -- normalized to $1 of portfolio value unless a real AUM is supplied

    def __post_init__(self) -> None:
        if self.price <= 0:
            raise ValueError(f"{self.security_id}: price must be positive")
        if self.portfolio_value <= 0:
            raise ValueError(f"{self.security_id}: portfolio_value must be positive")
        if self.adv_usd is not None and self.adv_usd < 0:
            raise ValueError(f"{self.security_id}: adv_usd cannot be negative")
        if self.daily_volatility is not None and self.daily_volatility < 0:
            raise ValueError(f"{self.security_id}: daily_volatility cannot be negative")

    @property
    def trade_value_usd(self) -> float:
        return self.trade_weight * self.portfolio_value

    @property
    def participation_rate(self) -> float | None:
        """Real trade size as a fraction of real average daily volume
        -- ``None`` (never a fabricated number) when ADV is unknown.
        """
        if self.adv_usd is None or self.adv_usd <= 0:
            return None
        return abs(self.trade_value_usd) / self.adv_usd


@dataclass(frozen=True)
class CostComponent:
    """One real cost component (spread, impact, slippage, or fees) for
    one trade, reported as a fraction of REAL trade value -- never a
    dollar figure that would need a separate real-vs-notional
    reconciliation.
    """

    security_id: str
    as_of: pd.Timestamp
    component_name: str
    cost_fraction: float
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.cost_fraction < 0:
            raise ValueError(f"{self.security_id}/{self.component_name}: cost_fraction cannot be negative")


@dataclass(frozen=True)
class TotalExecutionCost:
    security_id: str
    as_of: pd.Timestamp
    spread_cost_fraction: float
    impact_cost_fraction: float
    slippage_cost_fraction: float
    fee_cost_fraction: float
    total_cost_fraction: float
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NetProfitabilityResult:
    """"How much of our expected trading profit survives after real
    execution costs" -- the engine's own central question, answered
    directly: ``net_expected_return = gross_expected_return -
    total_execution_cost``, both real, both in the SAME units
    (fraction of portfolio value) ``portfolio-construction-engine``'s
    own ``OptimizationResult.expected_return`` already uses.
    """

    portfolio_id: str
    as_of: pd.Timestamp
    gross_expected_return: float
    total_execution_cost: float
    net_expected_return: float
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        expected_net = self.gross_expected_return - self.total_execution_cost
        if abs(self.net_expected_return - expected_net) > 1e-9:
            raise ValueError("net_expected_return must equal gross_expected_return - total_execution_cost exactly")


@dataclass(frozen=True)
class ExecutionSchedule:
    """A real, participation-rate-constrained multi-day execution
    plan for one security's trade: trading faster than
    ``max_participation_rate`` of real ADV per day is assumed to incur
    materially higher impact than this engine's single-day cost model
    captures, so a trade requiring more than one real day is spread
    evenly across ``required_days``.
    """

    security_id: str
    as_of: pd.Timestamp
    max_participation_rate: float
    required_days: int
    daily_trade_fraction: float  # fraction of the TOTAL trade executed per day

    def __post_init__(self) -> None:
        if self.required_days < 1:
            raise ValueError(f"{self.security_id}: required_days must be >= 1")
        if not 0 < self.max_participation_rate <= 1:
            raise ValueError(f"{self.security_id}: max_participation_rate must be in (0, 1]")
