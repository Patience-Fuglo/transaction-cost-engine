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

**Stages 1–5 of 10 are complete**: schemas, config, dependency wiring,
real spread, market-impact, fee, and slippage models. See
[`docs/STATUS.md`](docs/STATUS.md) for stage-by-stage build status.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python -m pytest tests/ -v
```
