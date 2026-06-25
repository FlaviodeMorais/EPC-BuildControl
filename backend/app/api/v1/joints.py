"""Endpoints de juntas — listagem por spool e detalhe individual."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/joints", tags=["joints"])


@router.get("")
def list_joints(
    project_id: int,
    spool_id: Optional[int] = None,
    status: Optional[str] = None,
    material: Optional[str] = None,
    is_repair: Optional[bool] = None,
    requires_tt: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = ["j.project_id = :project_id"]
    params: dict = {"project_id": project_id,
                    "offset": (page - 1) * page_size,
                    "limit": page_size}

    if spool_id:
        filters.append("j.spool_id = :spool_id")
        params["spool_id"] = spool_id
    if status:
        filters.append("j.status = :status::joint_status")
        params["status"] = status
    if material:
        filters.append("j.material = :material::material_code")
        params["material"] = material
    if is_repair is not None:
        filters.append("j.is_repair = :is_repair")
        params["is_repair"] = is_repair
    if requires_tt is not None:
        filters.append("j.requires_tt = :requires_tt")
        params["requires_tt"] = requires_tt
    if search:
        filters.append("j.joint_key ILIKE :search")
        params["search"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT j.id, j.joint_key, j.joint_type, j.diameter_mm, j.material,
               j.status, j.is_repair, j.requires_tt, j.requires_ut,
               j.dt_soldagem, j.dt_lib_end, j.result_rx, j.result_lp,
               w1.sin as welder_root, w2.sin as welder_fill
        FROM joints j
        LEFT JOIN welders w1 ON w1.id = j.welder_root_id
        LEFT JOIN welders w2 ON w2.id = j.welder_fill_id
        WHERE {where}
        ORDER BY j.joint_key
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(text(f"SELECT COUNT(*) FROM joints j WHERE {where}"),
                       {k: v for k, v in params.items() if k not in ("limit","offset")}
                       ).scalar()

    return {"total": total, "page": page, "page_size": page_size, "data": list(rows)}


@router.get("/{joint_id}")
def get_joint(
    project_id: int, joint_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    row = db.execute(text("""
        SELECT j.*,
               w1.name as welder_root_name, w1.sin as welder_root_sin,
               w2.name as welder_fill_name, w2.sin as welder_fill_sin,
               mt.supplier, mt.certificate_num
        FROM joints j
        LEFT JOIN welders w1 ON w1.id = j.welder_root_id
        LEFT JOIN welders w2 ON w2.id = j.welder_fill_id
        LEFT JOIN material_traceability mt ON mt.heat_number = j.heat_number_1
                                          AND mt.project_id = j.project_id
        WHERE j.id = :id AND j.project_id = :pid
    """), {"id": joint_id, "pid": project_id}).mappings().first()

    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "Junta não encontrada")

    rt = db.execute(text("""
        SELECT lot_number, result, dt_exam, film_lot, company
        FROM rt_lots WHERE joint_id = :id ORDER BY dt_exam
    """), {"id": joint_id}).mappings().all()

    return {**dict(row), "rt_lots": list(rt)}
