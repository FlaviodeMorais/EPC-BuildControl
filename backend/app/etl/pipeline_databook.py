"""ETL: CSVs Databook Paradox → soldadores, lotes RX, NCR, rastreabilidade, snapshots."""

import pandas as pd
import numpy as np
from .utils import clean_str, safe_numeric, delphi_date, julian_date
from .bulk import bulk_upsert

CHUNK = 5000


_PSEUDO_BOM = '\xef\xbb\xbf'  # UTF-8 BOM double-encoded as Latin-1 then re-encoded as UTF-8


def _strip_bom(s: str) -> str:
    return s.removeprefix(_PSEUDO_BOM).removeprefix('﻿').strip()


def _read(path: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc, on_bad_lines="skip")
            df.columns = [_strip_bom(c) for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível decodificar: {path}")


def _str(df, col, maxlen=None):
    s = df[col].where(df[col].notna(), None) if col in df.columns else pd.Series(None, index=df.index)
    return s.apply(lambda v, m=maxlen: str(v)[:m] if v and m else (str(v) if v else None))


def _num(df, col):
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(np.nan, index=df.index)


def _date_delphi(df, col):
    """Converte coluna: tenta ordinal Python (Paradox CSV) ou Delphi (xlsx)."""
    from datetime import date as _date
    def _parse(v):
        try:
            n = int(float(v))
            if n <= 0: return None
            # Valores > 600000 são ordinals Python (2014 ≈ 735000); < 100000 são Delphi
            return _date.fromordinal(n) if n > 600000 else delphi_date(n)
        except (TypeError, ValueError, OverflowError):
            return None
    return df[col].apply(_parse) if col in df.columns else pd.Series(None, index=df.index)


# ── SOLDADORES ────────────────────────────────────────────────────────────────

def run_welders(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).dropna(subset=["SIN"]).copy()

    df["project_id"]        = project_id
    df["sin"]               = _str(df, "SIN", 20)
    df["name"]              = _str(df, "NOME", 100)
    df["company"]           = _str(df, "EMPRESA", 50)
    df["process"]           = _str(df, "PRSOLD", 10)
    df["p_number"]          = _num(df, "MAT")
    df["f_number"]          = _num(df, "FNUMBER")
    df["diam_min_mm"]       = _num(df, "DMIN")
    df["thickness_max_mm"]  = _num(df, "ESPMAX")
    df["positions_qual"]    = _str(df, "POSQUAL", 10)
    df["dt_qualification"]  = _date_delphi(df, "DTQUALIF")
    df["dt_requalification"]= _date_delphi(df, "DTREQUALIF")
    df["disqualified"]      = df.get("Desqualificado", pd.Series("0", index=df.index)).fillna("0").apply(
        lambda v: str(v) not in ("0","","False"))
    df["rt_repair_index"]   = _num(df, "IRPER")

    COLS = ["project_id","sin","name","company","process","p_number","f_number",
            "diam_min_mm","thickness_max_mm","positions_qual","dt_qualification",
            "dt_requalification","disqualified","rt_repair_index"]
    df = df.drop_duplicates(subset=["sin"])
    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_WELDER_UPSERT, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors)}


_WELDER_UPSERT = """
INSERT INTO welders (project_id, sin, name, company, process, p_number, f_number,
  diam_min_mm, thickness_max_mm, positions_qual, dt_qualification,
  dt_requalification, disqualified, rt_repair_index)
VALUES %s
ON CONFLICT (project_id, sin) DO UPDATE SET
  name = COALESCE(EXCLUDED.name, welders.name),
  rt_repair_index = EXCLUDED.rt_repair_index,
  disqualified = EXCLUDED.disqualified
"""


# ── LOTES RX ──────────────────────────────────────────────────────────────────

def run_rt_lots(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).dropna(subset=["NUMLO"]).copy()

    df["project_id"]  = project_id
    df["lot_number"]  = _str(df, "NUMLO", 30)
    df["isometrico"]  = _str(df, "ISOMETRICO", 30)
    df["spool"]       = _str(df, "SPOOL", 10)
    df["junta"]       = _str(df, "JUNTA", 10)
    df["diameter_mm"] = _num(df, "DI")
    df["thickness_mm"]= _num(df, "ESP")
    df["result"]      = df.get("RX1LD", pd.Series("", index=df.index)).fillna("").map(
        {"1": "A", "5": "R"}).fillna("N")
    df["film_lot"]    = _str(df, "RX1L", 10)
    df["company"]     = _str(df, "EMPRESA", 20)
    df["status_code"] = _str(df, "SITU", 5)

    COLS = ["project_id","lot_number","isometrico","spool","junta",
            "diameter_mm","thickness_mm","result","film_lot","company","status_code"]
    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_RT_INSERT, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors)}


_RT_INSERT = """
INSERT INTO rt_lots (project_id, lot_number, isometrico, spool, junta,
  diameter_mm, thickness_mm, result, film_lot, company, status_code)
VALUES %s
ON CONFLICT DO NOTHING
"""


# ── NÃO-CONFORMIDADES ─────────────────────────────────────────────────────────

def run_nonconformances(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).copy()

    df["project_id"]     = project_id
    df["rnc_number"]     = _str(df, "RNC", 20)
    df["system_code"]    = _num(df, "sistema")
    df["operation_code"] = _num(df, "operacao")
    df["description"]    = _str(df, "descr")
    df["dt_generated"]   = _date_delphi(df, "dataGeracao")
    df["released"]       = df.get("liberado", pd.Series("0", index=df.index)).fillna("0").apply(
        lambda v: str(v) not in ("0","","False"))
    df["dt_released"]    = _date_delphi(df, "dataLiberacao")
    df["released_by"]    = _str(df, "libPorNome", 100)
    df["badge_released"] = _str(df, "libPorMatricula", 20)

    COLS = ["project_id","rnc_number","system_code","operation_code","description",
            "dt_generated","released","dt_released","released_by","badge_released"]
    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_INCONF_INSERT, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors)}


_INCONF_INSERT = """
INSERT INTO nonconformances (project_id, rnc_number, system_code, operation_code,
  description, dt_generated, released, dt_released, released_by, badge_released)
VALUES %s
ON CONFLICT DO NOTHING
"""


# ── RASTREABILIDADE DE MATERIAL ───────────────────────────────────────────────

def run_material_traceability(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).dropna(subset=["HT_NUMBER"]).copy()

    df["project_id"]         = project_id
    df["heat_number"]        = _str(df, "HT_NUMBER", 20)
    df["nrir"]               = _str(df, "NRIR", 30)
    df["nrir_year"]          = _num(df, "NRIR_ano")
    df["supplier"]           = _str(df, "forncecedor", 100)
    df["contract"]           = _str(df, "contrato", 60)
    df["fiscal_note"]        = _str(df, "Ntfiscal", 60)
    df["purchase_order"]     = _str(df, "NOC", 60)
    df["project_code"]       = _str(df, "codproj", 60)
    df["description"]        = _str(df, "descricao")
    df["diam_min_mm"]        = _num(df, "diam_1")
    df["diam_max_mm"]        = _num(df, "diam_2")
    df["certificate_num"]    = _str(df, "CERTIFICADO", 30)
    df["inspection_result"]  = _str(df, "laudo", 1)

    COLS = ["project_id","heat_number","nrir","nrir_year","supplier","contract",
            "fiscal_note","purchase_order","project_code","description",
            "diam_min_mm","diam_max_mm","certificate_num","inspection_result"]
    df = df.drop_duplicates(subset=["heat_number"])
    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_RASTMAT_UPSERT, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors)}


_RASTMAT_UPSERT = """
INSERT INTO material_traceability (project_id, heat_number, nrir, nrir_year,
  supplier, contract, fiscal_note, purchase_order, project_code,
  description, diam_min_mm, diam_max_mm, certificate_num, inspection_result)
VALUES %s
ON CONFLICT (project_id, heat_number) DO UPDATE SET
  supplier = COALESCE(EXCLUDED.supplier, material_traceability.supplier),
  certificate_num = COALESCE(EXCLUDED.certificate_num, material_traceability.certificate_num)
"""


# ── SNAPSHOTS DE PROGRESSO ────────────────────────────────────────────────────

def run_progress_snapshots(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).dropna(subset=["DATA","UNI"]).copy()

    df["project_id"]   = project_id
    df["snapshot_dt"] = pd.to_datetime(df["DATA"], errors="coerce").dt.date
    df["snapshot_dt"] = df["snapshot_dt"].where(df["snapshot_dt"].notna(), df["DATA"].apply(julian_date))
    df = df.dropna(subset=["snapshot_dt"])
    df["unit_code"]    = _str(df, "UNI", 10)
    df["area_code"]    = _str(df, "AREA", 10)
    df["sop_code"]     = _str(df, "SOP", 25)
    df["material"]     = _str(df, "MAT", 2)
    for col, src in [("n_total","NTOT"),("p_total","PTOT"),("n_welded","NSOL"),
                     ("n_released","NLIB"),("n_hold","NHOLD"),("n_pending_mat","NPMAT"),
                     ("n_cut","NCORT"),("n_fitup","NAJU"),("n_painted","NPIN")]:
        df[col] = _num(df, src).fillna(0)

    COLS = ["project_id","snapshot_dt","unit_code","area_code","sop_code","material",
            "n_total","p_total","n_welded","n_released","n_hold",
            "n_pending_mat","n_cut","n_fitup","n_painted"]
    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_RESUMO_UPSERT, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors)}


_RESUMO_UPSERT = """
INSERT INTO progress_snapshots (project_id, snapshot_dt, unit_code, area_code,
  sop_code, material, n_total, p_total, n_welded, n_released, n_hold,
  n_pending_mat, n_cut, n_fitup, n_painted)
VALUES %s
ON CONFLICT (project_id, snapshot_dt, unit_code, area_code, material) DO NOTHING
"""
