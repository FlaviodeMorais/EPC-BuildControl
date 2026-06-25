"""Endpoints de válvulas."""

import math
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...api.deps import get_current_user, require_role

router = APIRouter(prefix="/projects/{project_id}/valves", tags=["valves"])

NUMERIC_COLS = {"dn_mm","unit_weight_kg","qty_planned","qty_received",
                "qty_reserved","qty_issued","weight_planned_kg","weight_received_kg"}


def _safe(v):
    if isinstance(v, Decimal):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    return v


def _row(r: dict) -> dict:
    return {k: (_safe(v) if k in NUMERIC_COLS else v) for k, v in r.items()}


@router.get("")
def list_valves(
    project_id: int,
    availability: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = ["project_id = :pid"]
    params: dict = {"pid": project_id}
    if availability:
        filters.append("availability = :avail")
        params["avail"] = availability

    rows = db.execute(text(f"""
        SELECT id, valve_id_raw, description,
               dn_mm, unit_weight_kg,
               qty_planned, qty_received,
               qty_reserved, qty_issued,
               weight_planned_kg, weight_received_kg,
               availability
        FROM valves WHERE {' AND '.join(filters)}
        ORDER BY availability, dn_mm NULLS LAST, valve_id_raw
    """), params).mappings().all()
    return [_row(dict(r)) for r in rows]


@router.patch("/{valve_id}")
def update_valve(
    project_id: int, valve_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    allowed = {"qty_received", "qty_reserved", "qty_issued", "availability"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        return {"updated": 0}

    if "qty_received" in updates:
        planned = db.execute(
            text("SELECT qty_planned FROM valves WHERE id = :id"), {"id": valve_id}
        ).scalar() or 0
        recv = updates["qty_received"]
        updates["availability"] = "AVAILABLE" if recv >= planned else ("PARTIAL" if recv > 0 else "MISSING")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = valve_id
    updates["pid"] = project_id
    db.execute(text(f"UPDATE valves SET {set_clause}, updated_at = NOW() WHERE id = :id AND project_id = :pid"),
               updates)
    db.commit()
    return {"updated": 1}
