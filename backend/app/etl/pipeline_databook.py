"""ETL: CSVs extraídos do Databook Paradox → soldadores, lotes RX,
não-conformidades, rastreabilidade, snapshots de progresso."""

import pandas as pd
from sqlalchemy import text
from .utils import clean_str, safe_numeric, delphi_date, julian_date


# ── SOLDADORES ────────────────────────────────────────────────────────────────

def run_welders(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df.dropna(subset=["SIN"])
    rows_ok = rows_err = 0
    for _, r in df.iterrows():
        try:
            db.execute(text(_WELDER_UPSERT), {
                "project_id":       project_id,
                "sin":              clean_str(r.get("SIN"), 20),
                "name":             clean_str(r.get("NOME"), 100),
                "company":          clean_str(r.get("EMPRESA"), 50),
                "process":          clean_str(r.get("PRSOLD"), 10),
                "p_number":         safe_numeric(r.get("MAT")),
                "f_number":         safe_numeric(r.get("FNUMBER")),
                "diam_min_mm":      safe_numeric(r.get("DMIN")),
                "thickness_max_mm": safe_numeric(r.get("ESPMAX")),
                "positions_qual":   clean_str(r.get("POSQUAL"), 10),
                "dt_qualification": delphi_date(r.get("DTQUALIF")),
                "dt_requalification": delphi_date(r.get("DTREQUALIF")),
                "disqualified":     str(r.get("Desqualificado","0")) not in ("0","","False"),
                "rt_repair_index":  safe_numeric(r.get("IRPER")),
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err}


_WELDER_UPSERT = """
INSERT INTO welders (project_id, sin, name, company, process,
  p_number, f_number, diam_min_mm, thickness_max_mm, positions_qual,
  dt_qualification, dt_requalification, disqualified, rt_repair_index)
VALUES (:project_id, :sin, :name, :company, :process,
  :p_number, :f_number, :diam_min_mm, :thickness_max_mm, :positions_qual,
  :dt_qualification, :dt_requalification, :disqualified, :rt_repair_index)
ON CONFLICT (project_id, sin) DO UPDATE SET
  name = COALESCE(EXCLUDED.name, welders.name),
  rt_repair_index = EXCLUDED.rt_repair_index,
  disqualified = EXCLUDED.disqualified
"""


# ── LOTES RX ──────────────────────────────────────────────────────────────────

def run_rt_lots(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df.dropna(subset=["NUMLO"])
    rows_ok = rows_err = 0
    for _, r in df.iterrows():
        try:
            result_raw = clean_str(r.get("RX1LD"), 1)
            result = {"1": "A", "5": "R"}.get(result_raw, "N")
            db.execute(text(_RT_INSERT), {
                "project_id":  project_id,
                "lot_number":  clean_str(r.get("NUMLO"), 30),
                "isometrico":  clean_str(r.get("ISOMETRICO"), 30),
                "spool":       clean_str(r.get("SPOOL"), 10),
                "junta":       clean_str(r.get("JUNTA"), 10),
                "diameter_mm": safe_numeric(r.get("DI")),
                "thickness_mm": safe_numeric(r.get("ESP")),
                "result":      result,
                "film_lot":    clean_str(r.get("RX1L"), 10),
                "company":     clean_str(r.get("EMPRESA"), 20),
                "status_code": clean_str(r.get("SITU"), 5),
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err}


_RT_INSERT = """
INSERT INTO rt_lots (project_id, lot_number, isometrico, spool, junta,
  diameter_mm, thickness_mm, result, film_lot, company, status_code)
VALUES (:project_id, :lot_number, :isometrico, :spool, :junta,
  :diameter_mm, :thickness_mm, :result::ndt_result, :film_lot,
  :company, :status_code)
ON CONFLICT DO NOTHING
"""


# ── NÃO-CONFORMIDADES ─────────────────────────────────────────────────────────

def run_nonconformances(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    rows_ok = rows_err = 0
    for _, r in df.iterrows():
        try:
            db.execute(text(_INCONF_INSERT), {
                "project_id":     project_id,
                "rnc_number":     clean_str(r.get("RNC"), 20),
                "isometrico_ref": clean_str(r.get("IIS"), 30),
                "junta_ref":      clean_str(r.get("IJU"), 10),
                "spool_ref":      clean_str(r.get("ISP"), 10),
                "system_code":    safe_numeric(r.get("sistema")),
                "operation_code": safe_numeric(r.get("operacao")),
                "description":    clean_str(r.get("descr")),
                "dt_generated":   delphi_date(r.get("dataGeracao")),
                "released":       str(r.get("liberado","0")) not in ("0","","False"),
                "dt_released":    delphi_date(r.get("dataLiberacao")),
                "released_by":    clean_str(r.get("libPorNome"), 100),
                "badge_released": clean_str(r.get("libPorMatricula"), 20),
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err}


_INCONF_INSERT = """
INSERT INTO nonconformances (project_id, rnc_number, system_code, operation_code,
  description, dt_generated, released, dt_released, released_by, badge_released)
VALUES (:project_id, :rnc_number, :system_code, :operation_code,
  :description, :dt_generated, :released, :dt_released,
  :released_by, :badge_released)
ON CONFLICT DO NOTHING
"""


# ── RASTREABILIDADE DE MATERIAL ───────────────────────────────────────────────

def run_material_traceability(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df.dropna(subset=["HT_NUMBER"])
    rows_ok = rows_err = 0
    for _, r in df.iterrows():
        try:
            db.execute(text(_RASTMAT_UPSERT), {
                "project_id":       project_id,
                "heat_number":      clean_str(r.get("HT_NUMBER"), 20),
                "nrir":             clean_str(r.get("NRIR"), 30),
                "nrir_year":        safe_numeric(r.get("NRIR_ano")),
                "supplier":         clean_str(r.get("forncecedor"), 100),
                "contract":         clean_str(r.get("contrato"), 60),
                "fiscal_note":      clean_str(r.get("Ntfiscal"), 60),
                "purchase_order":   clean_str(r.get("NOC"), 60),
                "project_code":     clean_str(r.get("codproj"), 60),
                "description":      clean_str(r.get("descricao")),
                "diam_min_mm":      safe_numeric(r.get("diam_1")),
                "diam_max_mm":      safe_numeric(r.get("diam_2")),
                "certificate_num":  clean_str(r.get("CERTIFICADO"), 30),
                "inspection_result": clean_str(r.get("laudo"), 1),
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err}


_RASTMAT_UPSERT = """
INSERT INTO material_traceability (project_id, heat_number, nrir, nrir_year,
  supplier, contract, fiscal_note, purchase_order, project_code,
  description, diam_min_mm, diam_max_mm, certificate_num, inspection_result)
VALUES (:project_id, :heat_number, :nrir, :nrir_year,
  :supplier, :contract, :fiscal_note, :purchase_order, :project_code,
  :description, :diam_min_mm, :diam_max_mm, :certificate_num, :inspection_result)
ON CONFLICT (project_id, heat_number) DO UPDATE SET
  supplier = COALESCE(EXCLUDED.supplier, material_traceability.supplier),
  certificate_num = COALESCE(EXCLUDED.certificate_num, material_traceability.certificate_num)
"""


# ── SNAPSHOTS DE PROGRESSO ────────────────────────────────────────────────────

def run_progress_snapshots(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    df = df.dropna(subset=["DATA","UNI"])
    rows_ok = rows_err = 0
    for _, r in df.iterrows():
        try:
            snap_date = julian_date(r.get("DATA"))
            if not snap_date:
                continue
            db.execute(text(_RESUMO_UPSERT), {
                "project_id":   project_id,
                "snapshot_dt":  snap_date,
                "unit_code":    clean_str(r.get("UNI"), 10),
                "area_code":    clean_str(r.get("AREA"), 10),
                "sop_code":     clean_str(r.get("SOP"), 25),
                "material":     clean_str(r.get("MAT"), 2),
                "n_total":      safe_numeric(r.get("NTOT")) or 0,
                "p_total":      safe_numeric(r.get("PTOT")) or 0,
                "n_welded":     safe_numeric(r.get("NSOL")) or 0,
                "n_released":   safe_numeric(r.get("NLIB")) or 0,
                "n_hold":       safe_numeric(r.get("NHOLD")) or 0,
                "n_pending_mat": safe_numeric(r.get("NPMAT")) or 0,
                "n_cut":        safe_numeric(r.get("NCORT")) or 0,
                "n_fitup":      safe_numeric(r.get("NAJU")) or 0,
                "n_painted":    safe_numeric(r.get("NPIN")) or 0,
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err}


_RESUMO_UPSERT = """
INSERT INTO progress_snapshots (project_id, snapshot_dt, unit_code, area_code,
  sop_code, material, n_total, p_total, n_welded, n_released, n_hold,
  n_pending_mat, n_cut, n_fitup, n_painted)
VALUES (:project_id, :snapshot_dt, :unit_code, :area_code,
  :sop_code, :material::material_code, :n_total, :p_total, :n_welded,
  :n_released, :n_hold, :n_pending_mat, :n_cut, :n_fitup, :n_painted)
ON CONFLICT (project_id, snapshot_dt, unit_code, area_code, material) DO NOTHING
"""
