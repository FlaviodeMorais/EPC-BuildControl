"""Endpoints MTO — itens do modelo 3D."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/mto-items", tags=["mto"])


@router.get("")
def list_mto(
    project_id: int,
    item_3d_type: Optional[str] = None,
    isometrico: Optional[str] = None,
    scope: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = ["project_id = :project_id"]
    params: dict = {"project_id": project_id,
                    "offset": (page - 1) * page_size,
                    "limit": page_size}

    if item_3d_type:
        filters.append("item_3d_type ILIKE :type")
        params["type"] = f"%{item_3d_type}%"
    if isometrico:
        filters.append("isometrico ILIKE :iso")
        params["iso"] = f"%{isometrico}%"
    if scope:
        filters.append("scope = :scope")
        params["scope"] = scope
    if search:
        filters.append(
            "(description ILIKE :s OR material_code_std ILIKE :s OR material_code_alt ILIKE :s OR isometrico ILIKE :s)"
        )
        params["s"] = f"%{search}%"

    where = " AND ".join(filters)
    rows = db.execute(text(f"""
        SELECT id, material_code_alt, item_3d_type, description,
               material_code_std, material_spec, diameter_nom_mm, weight_kg,
               isometrico, spool_number_raw, scope, zone
        FROM mto_items WHERE {where}
        ORDER BY isometrico, item_3d_name
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    total = db.execute(
        text(f"SELECT COUNT(*) FROM mto_items WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    ).scalar()

    return {"total": total, "page": page, "page_size": page_size, "data": list(rows)}
