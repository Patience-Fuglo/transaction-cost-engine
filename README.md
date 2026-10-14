# transaction-cost-engine

Answers: "how much of our expected trading profit survives after
spreads, fees, market impact, and execution delays?" A real spread
model (liquidity-tiered, widening as real ADV falls), a classic
square-root market-impact model, a simple fee schedule, a real
adverse-selection slippage model, participation-rate-constrained
multi-day execution scheduling, and net profitability --
`gross_expected_return - total_execution_cost`.

This engine never re-runs an optimizer or re-decides a trade -- it
consumes `portfolio-construction-engine`'s own real `OptimizationResult`
(the already-decided target weights and turnover) and
`factor-model-engine`'s own real market data (price, ADV, volatility).

**All 10 stages are complete.** Schemas, config, dependency wiring;
real spread (liquidity-tiered), market-impact (classic square-root),
fee, and slippage (adverse-selection) models; total execution cost
aggregation consuming `portfolio-construction-engine`'s own real
`OptimizationResult` directly; net profitability
(`gross - cost`); participation-rate-constrained multi-day execution
scheduling (feeding real `required_days` into slippage); one
reproducible JSON/Markdown report; and a comprehensive hardening pass
confirming exact reproducibility and a real end-to-end illiquidity-
cost relationship, plus a real CLI-chain subprocess test. See
[`docs/STATUS.md`](docs/STATUS.md) for the full stage-by-stage build
history, the final architecture/formula summary, test evidence, and
an honest list of limitations.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m pytest tests/ -v
python scripts/run_cost_analysis.py
```

## Repository layout

```
src/transaction_cost/
  data/schemas.py                       # TradeOrder, CostComponent, TotalExecutionCost,
                                          # NetProfitabilityResult, ExecutionSchedule
  spread/spread_cost.py                     # compute_spread_cost()
  impact/market_impact.py                    # compute_impact_cost()
  fees/fee_schedule.py                        # compute_fee_cost()
  slippage/slippage.py                         # compute_slippage_cost()
  execution/
    total_cost.py                               # compute_total_execution_cost(),
                                                   # aggregate_portfolio_execution_cost()
    trade_builder.py                               # build_trade_orders() -- from a real OptimizationResult
  profitability/net_profitability.py                 # compute_net_profitability()
  scheduling/execution_schedule.py                     # compute_execution_schedule(),
                                                          # schedule_and_price_execution()
  pipeline/pipeline.py                                   # run_full_cost_analysis()
  reporting/report.py                                      # report_to_dict()/render_markdown_report()

tests/
  unit/           # one file per cost component
  integration/     # real OptimizationResult integration, comprehensive hardening
                    # check, real CLI-chain subprocess test

scripts/
  run_cost_analysis.py   # end-to-end: optimize -> price execution -> report
```
