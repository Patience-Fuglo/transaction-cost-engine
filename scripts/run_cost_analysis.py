#!/usr/bin/env python3
"""End-to-end CLI: optimizes a small real portfolio with
portfolio-construction-engine, then runs this engine's full Stage
6-9 transaction cost analysis and writes one reproducible JSON +
Markdown report.

Usage:
    python scripts/run_cost_analysis.py [--adv-usd 5000000] [--daily-volatility 0.015] [--output-dir outputs/reports]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from portfolio_construction.config import OptimizerConfig
from portfolio_construction.constraints import GrossLeverageConstraint, MaxPositionWeightConstraint
from portfolio_construction.data import OptimizationInput
from portfolio_construction.optimization import optimize_portfolio

from transaction_cost.config import EngineConfig
from transaction_cost.pipeline import run_full_cost_analysis
from transaction_cost.reporting import render_markdown_report, report_to_dict


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adv-usd", type=float, default=5.0e6)
    parser.add_argument("--daily-volatility", type=float, default=0.015)
    parser.add_argument("--portfolio-value", type=float, default=1.0e8)
    parser.add_argument("--output-dir", default="outputs/reports")
    args = parser.parse_args()

    security_ids = ["A", "B", "C", "D", "E"]
    covariance = pd.DataFrame(np.diag([0.02, 0.03, 0.025, 0.04, 0.035]), index=security_ids, columns=security_ids)
    expected_returns = {"A": 0.02, "B": 0.01, "C": 0.015, "D": 0.005, "E": 0.012}
    current_weights = {sid: 0.2 for sid in security_ids}

    opt_input = OptimizationInput(
        as_of=pd.Timestamp("2020-06-30"), security_ids=tuple(security_ids), expected_returns=expected_returns,
        covariance=covariance, current_weights=current_weights,
    )
    constraints = [MaxPositionWeightConstraint(max_weight=0.4, long_only=True), GrossLeverageConstraint(max_gross_leverage=1.0)]
    opt_result = optimize_portfolio(opt_input, "mean_variance", constraints, OptimizerConfig())

    market_data = {sid: {"price": 100.0, "adv_usd": args.adv_usd, "daily_volatility": args.daily_volatility} for sid in security_ids}
    cfg = EngineConfig()
    result = run_full_cost_analysis(opt_result, current_weights, market_data, args.portfolio_value, cfg, "portfolio")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "cost_report_portfolio.json"
    md_path = out_dir / "cost_report_portfolio.md"

    with open(json_path, "w") as f:
        json.dump(report_to_dict(result), f, indent=2, sort_keys=True)
        f.write("\n")
    with open(md_path, "w") as f:
        f.write(render_markdown_report(result))

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"{len(result.orders)} real trades priced")
    net = result.net_profitability
    print(f"gross expected return: {net.gross_expected_return:.4%}  total execution cost: {net.total_execution_cost:.4%}  net: {net.net_expected_return:.4%}")
    for w in net.warnings:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
