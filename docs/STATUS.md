# Build status

Tracks stage-by-stage completion, mirroring the other three engines'
own `docs/STATUS.md` convention.

## Stage 1 -- Foundation: COMPLETE

Schemas (`data/schemas.py`): `TradeOrder` (real trade_value_usd/
participation_rate properties), `CostComponent`, `TotalExecutionCost`,
`NetProfitabilityResult` (enforces the real reconciliation identity
`net = gross - cost` in `__post_init__`), `ExecutionSchedule`.
`EngineConfig`/`load_config` (`config.py`) with every real cost-model
coefficient tagged RESEARCH ASSUMPTION. Dependency wiring to
`factor-model-engine` and `portfolio-construction-engine` -- confirmed
resolving cleanly through a fresh venv install. 9 tests passing.
Pushed.

## Stage 2 -- Spread Cost: COMPLETE

Added `spread/spread_cost.py` (`compute_spread_cost`): real sqrt-style
liquidity scaling (`spread_bps = base_spread_bps * (reference_adv_usd
/ adv_usd) ** illiquidity_exponent`, floored at `min_spread_bps`), with
an explicit, conservative fallback (never silently assumed liquid)
when real ADV is unknown. `cost_fraction` reported as a fraction of
TRADE value, the standard real bps-cost convention -- later stages
convert to portfolio-value terms when aggregating.

5 new unit tests, including a direct check against the real sqrt
scaling formula at a specific ADV ratio. 14 tests passing (was 9).
Pushed.

## Stage 3 -- Market Impact: COMPLETE

Added `impact/market_impact.py` (`compute_impact_cost`): the classic,
real square-root impact model (`impact_bps = impact_coefficient *
daily_volatility_bps * sqrt(participation_rate)`, the standard
Almgren/Grinold-Kahn convention). Missing real ADV or volatility uses
an explicit, conservative fallback -- never silently assumed zero
impact.

5 new unit tests, including a direct check that quadrupling trade
size exactly doubles impact (real sqrt scaling, not linear). 19 tests
passing (was 14). Pushed.

## Next up: Stage 4 -- Fees & Commissions

A simple, configurable real fee schedule.
