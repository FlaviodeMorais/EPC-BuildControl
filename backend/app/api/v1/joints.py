"""Endpoints de juntas — listagem e detalhe com JOINs."""

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
    isometrico: Optional[str] = None,
    spool: Optional[str] = None,
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
                    "offset": (page - 1) * page_size, "limit": page_size}

    if spool_id:
        filters.append("j.spool_id = :spool_id"); params["spool_id"] = spool_id
    if isometrico:
        filters.append("j.isometrico ILIKE :iso"); params["iso"] = f"%{isometrico}%"
    if spool:
        filters.append("j.spool = :spool"); params["spool"] = spool
    if status:
        filters.append("j.status = :status"); params["status"] = status
    if material:
        filters.append("j.material = :material"); params["material"] = material
    if is_repair is not None:
        filters.append("j.is_repair = :is_repair"); params["is_repair"] = is_repair
    if requires_tt is not None:
        filters.append("j.requires_tt = :requires_tt"); params["requires_tt"] = requires_tt
    if search:
        filters.append("(j.joint_key ILIKE :s OR j.isometrico ILIKE :s OR j.junta ILIKE :s)")
        params["s"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT j.id, j.isometrico, j.spool, j.junta, j.joint_key,
               j.joint_type, j.diameter_mm, j.material, j.insp_level,
               j.status, j.is_repair, j.requires_tt, j.requires_ut,
               j.proc_raiz, j.proc_ench, j.manufacturer,
               j.dt_corte, j.dt_acoplamento, j.dt_soldagem,
               j.dt_vs, j.dt_tt, j.dt_lib_end,
               j.lp_result_acab AS result_lp, j.result_rx, j.result_du,
               j.heat_number_1, j.heat_number_2,
               COALESCE(w1.name, j.welder_root_sin) AS welder_root,
               COALESCE(w2.name, j.welder_fill_sin) AS welder_fill
        FROM joints j
        LEFT JOIN welders w1 ON w1.id = j.welder_root_id
        LEFT JOIN welders w2 ON w2.id = j.welder_fill_id
        WHERE {where}
        ORDER BY j.isometrico, j.spool, j.junta
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(
        text(f"SELECT COUNT(*) FROM joints j WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")}
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
               COALESCE(w1.name, j.welder_root_sin) AS welder_root_name,
               w1.company AS welder_root_company, j.proc_raiz,
               COALESCE(w2.name, j.welder_fill_sin) AS welder_fill_name,
               w2.company AS welder_fill_company, j.proc_ench,
               mt.supplier, mt.certificate_num, mt.inspection_result AS mat_laudo
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

    # RX lots via chave natural (isometrico+spool+junta)
    rt = db.execute(text("""
        SELECT lot_number, result, film_lot, company, status_code
        FROM rt_lots
        WHERE project_id = :pid AND isometrico = :iso
          AND spool = :sp AND junta = :ju
        ORDER BY lot_number
    """), {"pid": project_id, "iso": row["isometrico"],
           "sp": row["spool"], "ju": row["junta"]}).mappings().all()

    return {**dict(row), "rt_lots": list(rt)}
