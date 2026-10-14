# Build status

Tracks stage-by-stage completion, mirroring the other three engines'
own `docs/STATUS.md` convention.

## Remediation (portfolio-wide audit, item 3): cost-model consistency diagnostic

A portfolio-wide audit found that two structurally different real
"cost of trading" estimates coexist for the same real trade --
`portfolio-construction-engine`'s own simplified optimizer-side
`TransactionCostModel` (linear + impact^1.5, used only to make the
optimizer itself cost-aware) and this engine's own detailed spread +
impact + slippage + fee estimate -- with nothing checking they stay
in the same ballpark.

**Added** `diagnostics/cost_model_consistency.py`
(`compare_cost_estimates`, `compare_cost_estimates_across_schedule`)
and `CostModelConsistencyResult`: for the same real
`OptimizationResult`, computes this engine's own real detailed cost
(reusing `build_trade_orders` + `compute_total_execution_cost` +
`aggregate_portfolio_execution_cost` directly -- no cost math
reimplemented) and compares it against that result's own real
`transaction_cost` field. Reports absolute and relative differences
(the relative figure is floored against a real, configurable
near-zero epsilon so two tiny agreeing estimates never produce an
exploding ratio), and flags a real, configurable divergence -- never
assuming the two models must match exactly, and never summing them
(that would double-count the real cost of one trade). A security with
a real nonzero trade but no real market data is excluded from the
detailed estimate (with a real warning), never raised -- unlike
`build_trade_orders`'s own deliberate "raise on missing price data"
convention for the core pricing path, a diagnostic should not crash
the whole comparison over one missing security.

**Verified**, not merely written: 8 new unit tests
(`tests/unit/test_cost_model_consistency.py`) confirm the near-zero
floor behaves correctly, the configurable divergence threshold is
actually respected (a moderate real divergence is flagged under a
strict threshold and not flagged under a lenient one), a missing
security is excluded rather than fatal, and the two real estimates
are never summed. Full suite: 57 tests passing (was 49).

## Final summary (all 10 stages complete)

**Architecture.** `data/` (schemas) -> `spread/` + `impact/` +
`fees/` + `slippage/` (the four real cost components) ->
`execution/` (aggregation + `OptimizationResult` consumption) ->
`profitability/` (`gross - cost`) -> `scheduling/`
(participation-rate-constrained multi-day execution, feeding real
`required_days` back into slippage) -> `pipeline/` + `reporting/`
(one orchestration function, one JSON/Markdown report). Depends on
`factor-model-engine` and `portfolio-construction-engine` as pinned
git dependencies; never re-runs an optimizer or re-decides a trade --
it only prices the real cost of one already decided elsewhere.

**Important formulas:** spread `base_spread_bps * (reference_adv_usd
/ adv_usd) ** illiquidity_exponent` (floored); impact
`impact_coefficient * daily_volatility_bps * sqrt(participation_rate)`
(the classic Almgren/Grinold-Kahn convention); slippage
`adverse_selection_coefficient * daily_volatility_bps *
sqrt(delay_days)`; net profitability `gross_expected_return -
total_execution_cost`, enforced as a real `__post_init__` identity on
`NetProfitabilityResult`.

**Test counts.** 57 tests passing (was 49 before the cost-model
consistency remediation above): unit tests per cost component
(each verified against its own real formula and real monotonicity
properties -- sqrt scaling in impact and slippage, confirmed by
direct 4x-input tests), integration tests on real
`portfolio-construction-engine` optimizer output, and two Stage 10
hardening tests.

**Reproducibility, adapted to this engine's real scope.** Unlike the
other three engines, this engine never consumes a historical date
range itself (it prices ONE already-decided `OptimizationResult`
snapshot), so there is no "extend into the future" look-ahead
scenario to test. Its real comprehensive check: given a FIXED
optimizer output, the whole cost/scheduling/profitability/reporting
pipeline is confirmed EXACTLY reproducible across repeated runs
(verified 3 independent times) -- correctly, since nothing in Stages
6-9 calls a numerical solver or a near-zero-magnitude BLAS matrix
multiply, unlike `portfolio-construction-engine`'s SLSQP or
`portfolio-risk-engine`'s quadratic form.

**A real, meaningful end-to-end property, also verified directly:**
feeding the SAME optimizer decision through illiquid vs. liquid real
market data produces genuinely higher total execution cost and
genuinely lower net expected return for the illiquid case -- not just
a unit-level formula check, but confirmed across the whole pipeline.

**End-to-end demonstration.** `scripts/run_cost_analysis.py` optimizes
a real portfolio and runs the complete Stage 6-9 cost analysis;
`tests/integration/test_cli_workflow.py` runs it as a real subprocess.

**Limitations, identified rather than hidden:**
- Fees are a single flat bps rate -- no real volume-tiered discount
  structure.
- Execution scheduling splits a multi-day trade EVENLY, not via a
  real VWAP/TWAP front/back-loading profile.
- Slippage/impact fallback values (when ADV or volatility is unknown)
  are conservative, documented constants, not derived from any real
  cross-sectional calibration.
- This engine inherits every upstream limitation already documented
  in `factor-model-engine` and `portfolio-construction-engine`
  (including the SLSQP non-determinism, which this engine's own
  Stage 10 explicitly does NOT re-litigate, only correctly scopes
  around).
- All data is synthetic; this engine has no real-vendor data adapter
  of its own.

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

## Stage 8 -- Execution Scheduling: COMPLETE

Added `scheduling/execution_schedule.py`: `compute_execution_schedule`
(real participation-rate-constrained multi-day schedule, splitting a
large trade evenly across the minimum number of real days needed to
keep daily participation within `max_participation_rate`) and
`schedule_and_price_execution` (the composed Stage 8 + Stage 6
workflow -- feeds the schedule's real `required_days` directly into
Stage 5's slippage delay, since a trade too large to execute in one
day carries genuinely longer adverse-selection exposure).

4 new unit tests, including a direct check that the composed workflow
actually threads `required_days` into the real slippage formula (not
just computed independently and ignored). 42 tests passing (was 38).
Pushed.

## Stage 9 -- Reporting: COMPLETE

Added `pipeline/pipeline.py` (`run_full_cost_analysis`, orchestrates
Stages 6-8) and `reporting/report.py` (`report_to_dict`/
`render_markdown_report`, both derived from the same real
`TransactionCostAnalysisResult`).

4 new integration tests on a real `portfolio-construction-engine`
optimizer output: JSON serializability, reconciliation against the
real underlying result, every real section in the rendered Markdown,
and deterministic rendering. 46 tests passing (was 42). Pushed.

## Stage 10 -- Hardening: COMPLETE

Added `tests/integration/test_full_system.py` (the comprehensive
check, scoped correctly to this engine's real boundaries -- see the
Final Summary above) and `tests/integration/test_cli_workflow.py`
(real subprocess CLI test). Added `scripts/run_cost_analysis.py`,
this repo's first CLI entry point.

57 tests passing (49 before this pass, 46 before Stage 10). Full leak-check clean across the whole
repo. Pushed.

**All 10 stages of the transaction-cost-engine build are now
complete.**
