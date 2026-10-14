"""Stage 3 -- the classic, real square-root market-impact model:
``impact_bps = impact_coefficient * daily_volatility_bps *
sqrt(participation_rate)`` -- the standard industry convention
(Almgren/Grinold-Kahn style), where ``participation_rate`` is the
real trade size as a fraction of real ADV. Missing real ADV or
volatility data uses an explicit, conservative fallback -- never
silently assumed to have no impact.
"""

from __future__ import annotations

from ..config import ImpactConfig
from ..data.schemas import CostComponent, TradeOrder


def compute_impact_cost(order: TradeOrder, cfg: ImpactConfig) -> CostComponent:
    participation_rate = order.participation_rate
    if participation_rate is None or order.daily_volatility is None:
        impact_bps = cfg.missing_data_impact_bps
        detail = {"data_known": False, "impact_bps": impact_bps}
    else:
        daily_volatility_bps = order.daily_volatility * 10_000.0
        impact_bps = cfg.impact_coefficient * daily_volatility_bps * participation_rate**0.5
        detail = {"data_known": True, "participation_rate": participation_rate, "impact_bps": impact_bps}

    cost_fraction = impact_bps / 10_000.0
    return CostComponent(
        security_id=order.security_id, as_of=order.as_of, component_name="impact",
        cost_fraction=cost_fraction, detail=detail,
    )
