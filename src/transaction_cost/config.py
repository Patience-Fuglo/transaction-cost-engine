"""Engine configuration: every ambiguous research decision lives here,
in YAML, with a recommended default and reasoning in
``docs/research_assumptions.md`` -- never hardcoded in source. Same
plain-``@dataclass`` house style as the other engines in this
portfolio.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml


@dataclass(frozen=True)
class RunConfig:
    output_dir: str = "outputs"
    random_seed: int = 1337


@dataclass(frozen=True)
class SpreadConfig:
    # RESEARCH ASSUMPTION -- the half-spread (bps) a security with ADV
    # equal to reference_adv_usd is assumed to trade at
    base_spread_bps: float = 5.0
    # RESEARCH ASSUMPTION -- the real ADV level base_spread_bps is calibrated to
    reference_adv_usd: float = 1.0e7
    # RESEARCH ASSUMPTION -- how fast spread widens as real ADV falls
    # below reference_adv_usd (sqrt scaling: spread ~ 1/sqrt(ADV))
    illiquidity_exponent: float = 0.5
    # RESEARCH ASSUMPTION -- a real floor; spread never estimated below this
    min_spread_bps: float = 1.0
    # RESEARCH ASSUMPTION -- a conservative, explicit fallback when real
    # ADV is unknown -- never silently assumed liquid
    missing_adv_spread_bps: float = 50.0

    def __post_init__(self) -> None:
        if self.base_spread_bps <= 0 or self.reference_adv_usd <= 0:
            raise ValueError("base_spread_bps and reference_adv_usd must be positive")
        if self.illiquidity_exponent < 0:
            raise ValueError("illiquidity_exponent cannot be negative")
        if self.min_spread_bps <= 0:
            raise ValueError("min_spread_bps must be positive")


@dataclass(frozen=True)
class ImpactConfig:
    # RESEARCH ASSUMPTION -- the real "eta" coefficient in the classic
    # square-root impact model: impact_bps = eta * daily_vol_bps * sqrt(participation_rate)
    impact_coefficient: float = 0.5
    # RESEARCH ASSUMPTION -- a conservative, explicit fallback when real
    # ADV or volatility is unknown
    missing_data_impact_bps: float = 100.0

    def __post_init__(self) -> None:
        if self.impact_coefficient <= 0:
            raise ValueError("impact_coefficient must be positive")


@dataclass(frozen=True)
class SlippageConfig:
    # RESEARCH ASSUMPTION -- real adverse-selection drift during
    # execution, as a multiple of daily volatility per sqrt(delay_days)
    adverse_selection_coefficient: float = 0.3
    # RESEARCH ASSUMPTION -- the default real execution delay when the
    # caller doesn't supply one explicitly
    default_delay_days: int = 1
    # RESEARCH ASSUMPTION -- a conservative, explicit fallback when real
    # volatility is unknown
    missing_data_slippage_bps: float = 20.0

    def __post_init__(self) -> None:
        if self.adverse_selection_coefficient < 0:
            raise ValueError("adverse_selection_coefficient cannot be negative")
        if self.default_delay_days < 1:
            raise ValueError("default_delay_days must be >= 1")
        if self.missing_data_slippage_bps < 0:
            raise ValueError("missing_data_slippage_bps cannot be negative")


@dataclass(frozen=True)
class FeeConfig:
    # RESEARCH ASSUMPTION -- a simple flat commission/fee assumption
    fee_bps: float = 1.0

    def __post_init__(self) -> None:
        if self.fee_bps < 0:
            raise ValueError("fee_bps cannot be negative")


@dataclass(frozen=True)
class SchedulingConfig:
    # RESEARCH ASSUMPTION -- the real maximum share of a day's ADV this
    # engine assumes can be traded without materially worse impact
    # than its own single-day cost model captures
    max_participation_rate: float = 0.10

    def __post_init__(self) -> None:
        if not 0 < self.max_participation_rate <= 1:
            raise ValueError("max_participation_rate must be in (0, 1]")


@dataclass(frozen=True)
class CostConsistencyConfig:
    """Portfolio-wide audit remediation (item 3): thresholds for the
    real cost-model consistency diagnostic, which compares
    ``portfolio-construction-engine``'s own simplified optimizer-side
    cost estimate against this engine's own detailed estimate for the
    SAME real trade. Flags a meaningful divergence; never assumes the
    two models must match exactly -- they are two deliberately
    different real models (a simple linear+impact^1.5 estimate used
    to make the optimizer itself cost-aware, vs. a detailed spread +
    impact + slippage + fee estimate), not two implementations of the
    same formula.
    """

    # RESEARCH ASSUMPTION -- the real relative difference
    # (|a-b| / max(|a|, |b|, near_zero_epsilon)) above which the two
    # real cost estimates are flagged as meaningfully divergent
    relative_divergence_threshold: float = 0.50
    # RESEARCH ASSUMPTION -- a real floor used only to keep the
    # relative-difference denominator from blowing up when both real
    # estimates are near zero (a genuinely tiny real trade) -- never
    # used to inflate or hide a real difference between two
    # non-trivial estimates
    near_zero_epsilon: float = 1.0e-6

    def __post_init__(self) -> None:
        if self.relative_divergence_threshold <= 0:
            raise ValueError("relative_divergence_threshold must be positive")
        if self.near_zero_epsilon <= 0:
            raise ValueError("near_zero_epsilon must be positive")


@dataclass(frozen=True)
class EngineConfig:
    run: RunConfig = field(default_factory=RunConfig)
    spread: SpreadConfig = field(default_factory=SpreadConfig)
    impact: ImpactConfig = field(default_factory=ImpactConfig)
    slippage: SlippageConfig = field(default_factory=SlippageConfig)
    fee: FeeConfig = field(default_factory=FeeConfig)
    scheduling: SchedulingConfig = field(default_factory=SchedulingConfig)
    cost_consistency: CostConsistencyConfig = field(default_factory=CostConsistencyConfig)


def load_config(path: str) -> EngineConfig:
    """Load a real YAML config file into a validated EngineConfig.
    Missing sections fall back to each dataclass's own documented
    default -- never a silent empty/zero value."""
    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    return EngineConfig(
        run=RunConfig(**raw.get("run", {})),
        spread=SpreadConfig(**raw.get("spread", {})),
        impact=ImpactConfig(**raw.get("impact", {})),
        slippage=SlippageConfig(**raw.get("slippage", {})),
        fee=FeeConfig(**raw.get("fee", {})),
        scheduling=SchedulingConfig(**raw.get("scheduling", {})),
        cost_consistency=CostConsistencyConfig(**raw.get("cost_consistency", {})),
    )
