"""Orquestrador ETL — executa pipelines em sequência e atualiza view."""

from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from . import pipeline_sgs, pipeline_joints, pipeline_databook

# Diretório dos CSVs extraídos do Databook
DATABOOK_CSV_DIR = Path(
    r"C:\Users\MORAIS\Documentos\GitHub\MTO-UGH\extracted_db"
)

SOURCE_FILES = {
    "SGS":     r"C:\Users\MORAIS\Documentos\GitHub\MTO-UGH\SGS-SGM - Toyo 08.10.2015_remanescente.xlsx",
    "JOINTS":  r"C:\Users\MORAIS\Documentos\GitHub\MTO-UGH\01-Situação Geral de juntas_UGH_HC2-16-12-2025_PETROBRAS.xlsb",
}


def run_full(project_id: int, db) -> dict:
    """Executa todos os pipelines e retorna relatório consolidado."""
    started = datetime.now(timezone.utc)
    report = {}

    # 1. Spools (SGS Excel)
    report["sgs"] = _run_step("SGS", pipeline_sgs.run,
                               SOURCE_FILES["SGS"], project_id, db)

    # 2. Juntas (Excel xlsb)
    report["joints_excel"] = _run_step("JOINTS_EXCEL", pipeline_joints.run_excel,
                                        SOURCE_FILES["JOINTS"], project_id, db)

    # 3. Juntas Databook (CSV Paradox)
    report["joints_databook"] = _run_step("JOINTS_DATABOOK", pipeline_joints.run_csv,
                                           str(DATABOOK_CSV_DIR / "JUNTAS.csv"),
                                           project_id, db)

    # 4. Soldadores
    report["welders"] = _run_step("WELDERS", pipeline_databook.run_welders,
                                   str(DATABOOK_CSV_DIR / "SOLD.csv"), project_id, db)

    # 5. Lotes RX
    report["rt_lots"] = _run_step("RT_LOTS", pipeline_databook.run_rt_lots,
                                   str(DATABOOK_CSV_DIR / "LOTERX.csv"), project_id, db)

    # 6. Não-conformidades
    report["ncr"] = _run_step("NCR", pipeline_databook.run_nonconformances,
                               str(DATABOOK_CSV_DIR / "INCONF.csv"), project_id, db)

    # 7. Rastreabilidade de material
    report["traceability"] = _run_step("TRACEABILITY", pipeline_databook.run_material_traceability,
                                        str(DATABOOK_CSV_DIR / "RASTMAT.csv"), project_id, db)

    # 8. Snapshots de progresso (curva S histórica)
    report["snapshots"] = _run_step("SNAPSHOTS", pipeline_databook.run_progress_snapshots,
                                     str(DATABOOK_CSV_DIR / "RESUMO.csv"), project_id, db)

    # 9. Resolver FK: joints.spool_id
    _resolve_joint_spool_fk(project_id, db)

    # 10. Atualizar view materializada
    db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_spool_progress"))
    db.commit()

    report["duration_s"] = (datetime.now(timezone.utc) - started).total_seconds()
    return report


def _run_step(name: str, fn, path: str, project_id: int, db) -> dict:
    if not Path(path).exists():
        return {"status": "SKIPPED", "reason": f"Arquivo não encontrado: {path}"}
    try:
        result = fn(path, project_id, db)
        return {"status": "OK", **result}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def _resolve_joint_spool_fk(project_id: int, db) -> None:
    """Vincula joints.spool_id após spools estarem carregados."""
    db.execute(text("""
        UPDATE joints j
        SET spool_id = s.id
        FROM spools s
        WHERE j.project_id = s.project_id
          AND j.isometrico  = s.isometrico
          AND j.spool        = s.spool
          AND j.project_id   = :pid
          AND j.spool_id IS NULL
    """), {"pid": project_id})
    db.commit()
