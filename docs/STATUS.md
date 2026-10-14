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

## Stage 4 -- Fees & Commissions: COMPLETE

Added `fees/fee_schedule.py` (`compute_fee_cost`): a simple, flat,
real fee-bps model, independent of trade size (no volume-tiered
discount structure yet -- documented as a real simplification).

3 new unit tests. 22 tests passing (was 19). Pushed.

## Stage 5 -- Execution Delay / Slippage: COMPLETE

Added `slippage/slippage.py` (`compute_slippage_cost`): real
adverse-selection drift during execution (`slippage_bps =
adverse_selection_coefficient * daily_volatility_bps *
sqrt(delay_days)`), one-directional (always a real cost, never a
potential gain) via the adverse-selection coefficient, random-walk
sqrt-time scaling of real volatility. Missing volatility uses an
explicit, conservative fallback.

5 new unit tests, including a direct check that 4x the delay exactly
doubles slippage (real sqrt-time scaling). 27 tests passing (was 22).
Pushed.

## Stage 6 -- Total Execution Cost: COMPLETE

Added `execution/total_cost.py` (`compute_total_execution_cost`,
`aggregate_portfolio_execution_cost`) and `execution/trade_builder.py`
(`build_trade_orders`). `build_trade_orders` consumes
`portfolio-construction-engine`'s own real `OptimizationResult`
directly -- this engine never re-decides a trade, it only prices the
cost of one already decided elsewhere. A security with no real price
data for a real nonzero trade raises, rather than silently defaulting
a price. `aggregate_portfolio_execution_cost` is the real unit
conversion (`cost_fraction * abs(trade_weight)`) from per-trade-value
to per-portfolio-value terms, needed before this can be compared
against a real `gross_expected_return`.

6 new unit tests, including a real genuine cross-repo check: building
trade orders directly from a real `portfolio_construction.data.
OptimizationResult`. 33 tests passing (was 27). Pushed.

## Stage 7 -- Net Profitability: COMPLETE

Added `profitability/net_profitability.py` (`compute_net_profitability`):
this engine's own central question, answered directly --
`net_expected_return = gross_expected_return - total_execution_cost`,
reusing Stage 6's own real portfolio-level cost aggregation. Warns
explicitly when real execution cost consumes all of (or exceeds) a
real positive gross expected return -- "this trade is not worth
making as costed," not silently reported as if it were fine.

4 new unit tests plus a genuine cross-repo integration test:
optimizing a real portfolio with `portfolio-construction-engine`'s
real `optimize_portfolio`, then pricing the real cost of executing it
and computing net profitability -- not a hand-built fixture standing
in for the dependency. 38 tests passing (was 33). Pushed.

## Next up: Stage 8 -- Execution Scheduling

Participation-rate-constrained multi-day execution horizon, feeding
back into impact/slippage for trades too large to execute in one day.
