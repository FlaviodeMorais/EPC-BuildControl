"""Endpoints de spools — listagem, detalhe e atualização de status."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...api.deps import get_current_user, require_role

router = APIRouter(prefix="/projects/{project_id}/spools", tags=["spools"])


@router.get("")
def list_spools(
    project_id: int,
    status: Optional[str] = None,
    unit_code: Optional[str] = None,
    hold: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = ["s.project_id = :project_id"]
    params: dict = {"project_id": project_id,
                    "offset": (page - 1) * page_size,
                    "limit": page_size}

    if status:
        filters.append("s.status = :status::spool_status")
        params["status"] = status
    if unit_code:
        filters.append("s.unit_id = (SELECT id FROM units WHERE code = :unit_code AND project_id = :project_id LIMIT 1)")
        params["unit_code"] = unit_code
    if hold is not None:
        filters.append("s.hold = :hold")
        params["hold"] = hold
    if search:
        filters.append("s.spool_key ILIKE :search")
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT s.id, s.spool_key, s.status, s.material, s.diameter_mm,
               s.weight_kg, s.joints_total, s.joints_welded, s.joints_released,
               s.hold, s.pct_fab, s.pct_mon, s.dt_embarque, s.dt_montagem
        FROM spools s
        WHERE {where}
        ORDER BY s.spool_key
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(f"SELECT COUNT(*) FROM spools s WHERE {where}"),
                       {k: v for k, v in params.items() if k not in ("limit","offset")}
                       ).scalar()

    return {"total": total, "page": page, "page_size": page_size, "data": list(rows)}


@router.get("/{spool_id}")
def get_spool(
    project_id: int, spool_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    row = db.execute(text("""
        SELECT s.*, u.code as unit_code, u.sub_unit,
               COUNT(j.id) as joint_count_live,
               SUM(CASE WHEN j.status = '30_LIBERADA' THEN 1 ELSE 0 END) as joints_lib_live
        FROM spools s
        LEFT JOIN units u ON u.id = s.unit_id
        LEFT JOIN joints j ON j.spool_id = s.id
        WHERE s.id = :id AND s.project_id = :pid
        GROUP BY s.id, u.code, u.sub_unit
    """), {"id": spool_id, "pid": project_id}).mappings().first()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Spool não encontrado")
    return dict(row)


@router.patch("/{spool_id}")
def update_spool(
    project_id: int, spool_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN", "FIELD_ENGINEER")),
):
    allowed = {"status","hold","hold_reason","dt_embarque","dt_montagem",
               "dt_sth","dt_pintura","dt_dimensional","obs"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        return {"updated": 0}

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = spool_id
    updates["pid"] = project_id
    db.execute(text(f"""
        UPDATE spools SET {set_clause}, updated_at = NOW()
        WHERE id = :id AND project_id = :pid
    """), updates)
    db.commit()
    return {"updated": 1}
