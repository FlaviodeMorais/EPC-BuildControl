"""Upload de arquivos Excel/CSV e disparo do ETL em background."""

import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from ...database import get_db, SessionLocal
from ...api.deps import require_role
from ...etl import orchestrator, pipeline_sgs, pipeline_mto, pipeline_valves, pipeline_joints

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/projects/{project_id}/uploads", tags=["uploads"])

ALLOWED_TYPES = {"MTO", "SGS", "VALVULAS", "JOINTS", "DATABOOK_FULL"}


@router.post("")
def upload_file(
    project_id: int,
    file_type: str = Form(...),
    file: UploadFile = File(...),
    background: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"file_type deve ser um de: {ALLOWED_TYPES}")

    dest = UPLOAD_DIR / f"{project_id}_{file_type}_{file.filename}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    batch = db.execute(text("""
        INSERT INTO upload_batches (project_id, file_type, original_name, status)
        VALUES (:pid, :ft, :fn, 'PENDING') RETURNING id
    """), {"pid": project_id, "ft": file_type, "fn": file.filename}).scalar()
    db.commit()

    background.add_task(_run_etl, batch, project_id, file_type, str(dest))
    return {"batch_id": batch, "status": "PENDING"}


@router.get("")
def list_uploads(project_id: int, db: Session = Depends(get_db), _=Depends(require_role("ADMIN"))):
    rows = db.execute(text("""
        SELECT id, file_type, original_name, status, rows_inserted,
               rows_errored, started_at, completed_at, created_at
        FROM upload_batches WHERE project_id = :pid ORDER BY created_at DESC
    """), {"pid": project_id}).mappings().all()
    return list(rows)


@router.delete("/reset-data")
def reset_project_data(
    project_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("ADMIN")),
):
    """Apaga todos os dados do projeto (spools, joints, mto_items, valves, histórico)."""
    db.execute(text("""
        TRUNCATE TABLE joints, mto_items, spools, valves, upload_batches
        RESTART IDENTITY CASCADE
    """))
    db.commit()
    return {"message": "Dados do projeto removidos com sucesso."}


@router.get("/{batch_id}")
def get_upload(project_id: int, batch_id: int, db: Session = Depends(get_db), _=Depends(require_role("ADMIN"))):
    row = db.execute(text("""
        SELECT * FROM upload_batches WHERE id = :id AND project_id = :pid
    """), {"id": batch_id, "pid": project_id}).mappings().first()
    return dict(row) if row else {}


def _run_etl(batch_id: int, project_id: int, file_type: str, path: str):
    db = SessionLocal()
    try:
        db.execute(text("UPDATE upload_batches SET status='RUNNING', started_at=NOW() WHERE id=:id"),
                   {"id": batch_id})
        db.commit()

        if file_type == "SGS":
            report = pipeline_sgs.run(path, project_id, db)
        elif file_type == "MTO":
            report = pipeline_mto.run(path, project_id, db)
        elif file_type == "VALVULAS":
            report = pipeline_valves.run(path, project_id, db)
        elif file_type == "JOINTS":
            report = pipeline_joints.run_excel(path, project_id, db)
        elif file_type == "DATABOOK_FULL":
            report = orchestrator.run_full(project_id, db)
        else:
            report = {"inserted_updated": 0, "errors": 0}

        db.execute(text("""
            UPDATE upload_batches
            SET status='COMPLETED', completed_at=NOW(),
                rows_inserted=:ri, rows_errored=:re, error_log=:log
            WHERE id=:id
        """), {
            "id": batch_id,
            "ri": report.get("inserted_updated", 0),
            "re": report.get("errors", 0),
            "log": str(report.get("error_samples", [])),
        })
        db.commit()
    except Exception as e:
        db.execute(text("""
            UPDATE upload_batches
            SET status='FAILED', completed_at=NOW(), error_log=:err WHERE id=:id
        """), {"id": batch_id, "err": str(e)})
        db.commit()
    finally:
        db.close()
