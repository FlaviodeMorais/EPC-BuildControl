"""Endpoints de válvulas."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...api.deps import get_current_user, require_role

router = APIRouter(prefix="/projects/{project_id}/valves", tags=["valves"])


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
               dn_mm::float, unit_weight_kg::float,
               qty_planned::float, qty_received::float,
               qty_reserved::float, qty_issued::float,
               weight_planned_kg::float, weight_received_kg::float,
               availability
        FROM valves WHERE {' AND '.join(filters)}
        ORDER BY availability, dn_mm, valve_id_raw
    """), params).mappings().all()
    return [dict(r) for r in rows]


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

    # Recalcula availability se qtd atualizada
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
