"""Endpoints KPI — indicadores consolidados para dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/kpis", tags=["kpis"])


@router.get("/overview")
def overview(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    spools = db.execute(text("""
        SELECT
            COUNT(*)                                        AS total_spools,
            COUNT(*) FILTER (WHERE status = 'TESTADO')     AS testado,
            COUNT(*) FILTER (WHERE status = 'MONTADO')     AS montado,
            COUNT(*) FILTER (WHERE status = 'EM_CAMPO')    AS em_campo,
            COUNT(*) FILTER (WHERE status = 'FABRICADO')   AS fabricado,
            COUNT(*) FILTER (WHERE status = 'EM_FABRICACAO') AS em_fabricacao,
            COUNT(*) FILTER (WHERE status = 'NAO_INICIADO') AS nao_iniciado,
            COUNT(*) FILTER (WHERE hold = TRUE)             AS em_hold,
            COALESCE(SUM(weight_kg), 0)                    AS peso_total_kg,
            COALESCE(SUM(length_m), 0)                     AS comprimento_total_m,
            COALESCE(SUM(joints_total), 0)                 AS juntas_total,
            COALESCE(SUM(joints_welded), 0)                AS juntas_soldadas,
            COALESCE(SUM(joints_released), 0)              AS juntas_liberadas
        FROM spools WHERE project_id = :pid
    """), {"pid": project_id}).mappings().first()

    joints = db.execute(text("""
        SELECT
            COUNT(*)                                                AS total,
            COUNT(*) FILTER (WHERE status = '30_LIBERADA')         AS liberadas,
            COUNT(*) FILTER (WHERE is_repair = TRUE)               AS reparos,
            COUNT(*) FILTER (WHERE requires_tt = TRUE)             AS com_tt,
            COUNT(*) FILTER (WHERE requires_ut = TRUE)             AS com_ut
        FROM joints WHERE project_id = :pid
    """), {"pid": project_id}).mappings().first()

    return {"spools": dict(spools), "joints": dict(joints)}


@router.get("/by-unit")
def by_unit(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT u.code AS unit, u.sub_unit,
               COUNT(s.id)                                        AS spools,
               COUNT(s.id) FILTER (WHERE s.status = 'FABRICADO') AS fabricado,
               COUNT(s.id) FILTER (WHERE s.status = 'MONTADO')   AS montado,
               COALESCE(SUM(s.weight_kg), 0)                     AS peso_kg,
               COALESCE(SUM(s.joints_total), 0)                  AS juntas,
               COALESCE(SUM(s.joints_released), 0)               AS juntas_lib
        FROM spools s
        JOIN units u ON u.id = s.unit_id
        WHERE s.project_id = :pid
        GROUP BY u.code, u.sub_unit
        ORDER BY u.code, u.sub_unit
    """), {"pid": project_id}).mappings().all()
    return list(rows)


@router.get("/holds")
def holds(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT s.spool_key, s.hold_reason, s.material, s.weight_kg,
               u.code as unit_code, s.status
        FROM spools s
        LEFT JOIN units u ON u.id = s.unit_id
        WHERE s.project_id = :pid AND s.hold = TRUE
        ORDER BY s.spool_key
    """), {"pid": project_id}).mappings().all()
    return list(rows)


@router.get("/s-curve")
def s_curve(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """Curva S acumulada de juntas por semana (fonte: tabela joints)."""
    rows = db.execute(text("""
        WITH weeks AS (
            SELECT generate_series(
                date_trunc('week', MIN(LEAST(dt_corte, dt_acoplamento, dt_soldagem, dt_lib_end))),
                date_trunc('week', GREATEST(MAX(dt_corte), MAX(dt_acoplamento),
                                            MAX(dt_soldagem), MAX(dt_lib_end))),
                '1 week'::interval
            )::date AS semana
            FROM joints WHERE project_id = :pid
              AND LEAST(dt_corte, dt_acoplamento, dt_soldagem, dt_lib_end) IS NOT NULL
        )
        SELECT
            to_char(w.semana, 'YYYY-MM-DD') AS snapshot_dt,
            COUNT(*) FILTER (WHERE j.dt_corte     <= w.semana) AS cortado,
            COUNT(*) FILTER (WHERE j.dt_acoplamento <= w.semana) AS acoplado,
            COUNT(*) FILTER (WHERE j.dt_soldagem  <= w.semana) AS soldado,
            COUNT(*) FILTER (WHERE j.dt_lib_end   <= w.semana) AS liberado
        FROM weeks w
        CROSS JOIN joints j
        WHERE j.project_id = :pid
          AND j.is_repair = FALSE
        GROUP BY w.semana
        ORDER BY w.semana
    """), {"pid": project_id}).mappings().all()
    return list(rows)


@router.get("/valve-availability")
def valve_availability(project_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT availability,
               COUNT(*)                    AS items,
               SUM(qty_planned)            AS qtd_prevista,
               SUM(qty_received)           AS qtd_recebida,
               SUM(weight_planned_kg)      AS peso_previsto,
               SUM(weight_received_kg)     AS peso_recebido
        FROM valves WHERE project_id = :pid
        GROUP BY availability ORDER BY availability
    """), {"pid": project_id}).mappings().all()
    return list(rows)
