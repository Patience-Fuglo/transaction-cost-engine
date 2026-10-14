"""Stage 9 -- renders a real ``TransactionCostAnalysisResult`` into a
reproducible report: a JSON-serializable dict, and a professional
Markdown document. Both derived from the SAME object -- never
recomputed separately, so they can't silently disagree. Mirrors the
other three engines' own reporting convention.
"""

from __future__ import annotations

from ..pipeline import TransactionCostAnalysisResult


def report_to_dict(result: TransactionCostAnalysisResult) -> dict:
    net = result.net_profitability
    return {
        "portfolio_id": result.portfolio_id,
        "as_of": str(result.as_of.date()),
        "n_trades": len(result.orders),
        "trades": [
            {
                "security_id": order.security_id,
                "trade_weight": order.trade_weight,
                "required_days": schedule.required_days,
                "total_cost_fraction": cost.total_cost_fraction,
                "spread": cost.spread_cost_fraction,
                "impact": cost.impact_cost_fraction,
                "slippage": cost.slippage_cost_fraction,
                "fee": cost.fee_cost_fraction,
            }
            for order, schedule, cost in zip(result.orders, result.schedules, result.costs)
        ],
        "net_profitability": {
            "gross_expected_return": net.gross_expected_return,
            "total_execution_cost": net.total_execution_cost,
            "net_expected_return": net.net_expected_return,
            "warnings": list(net.warnings),
        } if net else None,
    }


def render_markdown_report(result: TransactionCostAnalysisResult) -> str:
    payload = report_to_dict(result)
    lines: list[str] = []
    lines.append("# Transaction Cost Engine -- Research Report")
    lines.append("")
    lines.append(f"**Portfolio:** `{payload['portfolio_id']}`  **As of:** {payload['as_of']}  **Trades:** {payload['n_trades']}")
    lines.append("")
    lines.append("All data in this report is synthetic and non-proprietary.")
    lines.append("")

    lines.append("## Trades")
    lines.append("| Security | Trade Weight | Days | Spread | Impact | Slippage | Fee | Total |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for t in payload["trades"]:
        lines.append(
            f"| {t['security_id']} | {t['trade_weight']:.4f} | {t['required_days']} | "
            f"{t['spread']:.4%} | {t['impact']:.4%} | {t['slippage']:.4%} | {t['fee']:.4%} | {t['total_cost_fraction']:.4%} |"
        )
    lines.append("")

    if payload["net_profitability"]:
        net = payload["net_profitability"]
        lines.append("## Net Profitability")
        lines.append(f"- Gross expected return: {net['gross_expected_return']:.4%}")
        lines.append(f"- Total execution cost: {net['total_execution_cost']:.4%}")
        lines.append(f"- Net expected return: {net['net_expected_return']:.4%}")
        if net["warnings"]:
            lines.append("")
            lines.append("Warnings:")
            for w in net["warnings"]:
                lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)
