from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/welders", tags=["welders"])


@router.get("")
def list_welders(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT w.id, w.sin, w.name, w.company, w.process, w.disqualified,
               COUNT(j.id) total_joints,
               COUNT(j.id) FILTER (WHERE j.is_repair=TRUE) reparos,
               ROUND(COUNT(j.id) FILTER (WHERE j.is_repair=TRUE)::numeric /
                     NULLIF(COUNT(j.id),0)*100,1) repair_rate
        FROM welders w
        LEFT JOIN joints j ON (j.welder_root_id=w.id OR j.welder_fill_id=w.id)
        WHERE w.project_id=:pid
        GROUP BY w.id, w.sin, w.name, w.company, w.process, w.disqualified
        ORDER BY total_joints DESC
    """), {"pid": project_id}).mappings().all()
    return [dict(r) for r in rows]
