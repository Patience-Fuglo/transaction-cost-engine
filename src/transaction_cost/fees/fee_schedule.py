"""Stage 4 -- a real, simple flat fee/commission model: ``fee_bps`` of
real trade value, configurable, with no real volume-tiered discount
structure yet (a documented simplification -- real broker fee
schedules often tier by volume; this v1 keeps a single flat rate).
"""

from __future__ import annotations

from ..config import FeeConfig
from ..data.schemas import CostComponent, TradeOrder


def compute_fee_cost(order: TradeOrder, cfg: FeeConfig) -> CostComponent:
    cost_fraction = cfg.fee_bps / 10_000.0
    return CostComponent(
        security_id=order.security_id, as_of=order.as_of, component_name="fee",
        cost_fraction=cost_fraction, detail={"fee_bps": cfg.fee_bps},
    )
