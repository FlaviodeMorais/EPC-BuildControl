from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/ncr", tags=["ncr"])


@router.get("")
def list_ncr(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT n.id, n.rnc_number, n.description, n.dt_generated, n.released, n.dt_released,
               n.released_by, n.operation_code, n.system_code
        FROM nonconformances n
        WHERE n.project_id=:pid
        ORDER BY n.dt_generated DESC NULLS LAST
        LIMIT 500
    """), {"pid": project_id}).mappings().all()
    return [dict(r) for r in rows]
