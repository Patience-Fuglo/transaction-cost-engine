"""Stage 2 -- a real, liquidity-tiered half-spread cost model: real
spread widens as real ADV falls below a reference level
(``spread_bps = base_spread_bps * (reference_adv_usd / adv_usd) **
illiquidity_exponent``, a standard, documented sqrt-style liquidity
scaling, floored at ``min_spread_bps``). When real ADV is unknown, an
explicit, conservative fallback is used and flagged -- never silently
assumed liquid.

``cost_fraction`` is reported as a fraction of TRADE value (the
standard real convention for quoting spread cost in bps), not of
portfolio value -- later stages convert to portfolio-value terms when
aggregating across securities.
"""

from __future__ import annotations

from ..config import SpreadConfig
from ..data.schemas import CostComponent, TradeOrder


def compute_spread_cost(order: TradeOrder, cfg: SpreadConfig) -> CostComponent:
    if order.adv_usd is None or order.adv_usd <= 0:
        spread_bps = cfg.missing_adv_spread_bps
        detail = {"adv_known": False, "spread_bps": spread_bps}
    else:
        raw_spread_bps = cfg.base_spread_bps * (cfg.reference_adv_usd / order.adv_usd) ** cfg.illiquidity_exponent
        spread_bps = max(raw_spread_bps, cfg.min_spread_bps)
        detail = {"adv_known": True, "spread_bps": spread_bps}

    cost_fraction = spread_bps / 10_000.0
    return CostComponent(
        security_id=order.security_id, as_of=order.as_of, component_name="spread",
        cost_fraction=cost_fraction, detail=detail,
    )
