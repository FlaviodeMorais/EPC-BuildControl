"""ETL: MAPA_JUNTA xlsb → tabela joints. Pandas vetorizado + execute_values."""

import pandas as pd
import numpy as np
from .column_maps import JOINTS_EXCEL_MAP, SGER_TO_STATUS
from .utils import delphi_date, normalize_sger
from .bulk import bulk_upsert

CHUNK = 5000
DATE_COLS = ["dt_corte","dt_acoplamento","dt_soldagem","dt_vs","dt_lib_end","dt_embarque","dt_prog_mon","dt_lp","dt_rx","dt_tt"]
RESULT_COLS = ["result_rx","result_lp","result_vs","result_us","result_tt"]


def run_excel(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name="MAPA_JUNTA", engine="pyxlsb", dtype=str, header=7)
    df.rename(columns={k: v for k, v in JOINTS_EXCEL_MAP.items() if k in df.columns}, inplace=True)
    return _load(df, project_id, db, source="EXCEL", progress_cb=progress_cb)


def run_csv(path: str, project_id: int, db) -> dict:
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc, on_bad_lines="skip")
            break
        except UnicodeDecodeError:
            continue
    _PBOM = '\xef\xbb\xbf'
    df.columns = [c.removeprefix(_PBOM).removeprefix('﻿').strip() for c in df.columns]
    paradox_map = {
        "Isometrico":"isometrico","Spool":"spool","Junta":"junta",
        "CBTP":"joint_type","CBDI":"diameter_mm","CBESP":"thickness_mm",
        "CBMAT":"material","CBNI":"insp_level","CBTT":"requires_tt",
        "corrida1":"corrida_1","corrida2":"corrida_2","corrida3":"corrida_3","corrida4":"corrida_4",
        "HT_NUMBER1":"heat_number_1","HT_NUMBER2":"heat_number_2",
        "DTSOLD":"dt_soldagem","DTAJU":"dt_acoplamento","DTVS":"dt_vs",
        "DtLib":"dt_lib_end","DTLP1":"dt_lp","DTRX":"dt_rx","DTTT":"dt_tt",
        "RX1LD":"result_rx","LP1RC":"result_lp","VSL":"result_vs",
        "SGER":"status_raw","IEIS":"ieis","RX_US":"ndt_method",
        "ASRAIZ":"welder_root_sin","ASENCH":"welder_fill_sin",
    }
    df.rename(columns=paradox_map, inplace=True)
    for col in ["dt_soldagem","dt_acoplamento","dt_vs","dt_lib_end","dt_lp","dt_rx","dt_tt"]:
        if col in df.columns:
            df[col] = df[col].apply(delphi_date)
    return _load(df, project_id, db, source="DATABOOK")


def _load(df: pd.DataFrame, project_id: int, db, source: str, progress_cb=None) -> dict:
    df = df.dropna(subset=["isometrico","spool","junta"]).copy()
    df = df[df["isometrico"].str.strip() != ""]
    # Prioriza linha com resultado END preenchido (mantém última após sort)
    result_cols_present = [c for c in RESULT_COLS if c in df.columns]
    if result_cols_present:
        df["_has_result"] = df[result_cols_present].notna().any(axis=1)
        df = df.sort_values("_has_result").drop_duplicates(subset=["isometrico","spool","junta"], keep="last").drop(columns=["_has_result"])
    else:
        df = df.drop_duplicates(subset=["isometrico","spool","junta"])

    # Status
    src = df.get("status_raw", df.get("sger", pd.Series(None, index=df.index)))
    df["status"] = src.apply(lambda v: SGER_TO_STATUS.get(normalize_sger(v), "01_NAO_INICIADA"))

    # is_repair
    df["is_repair"] = df["junta"].fillna("").str.strip().str.upper().str.match(r'^R\d+$')

    # Booleanos
    for col in ["requires_tt","requires_ut"]:
        if col in df.columns:
            df[col] = ~df[col].fillna("0").astype(str).isin(["0","","N","None","False"])
        else:
            df[col] = False

    # Numéricos
    for col in ["diameter_mm","thickness_mm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Datas
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: delphi_date(v) if pd.notna(v) and str(v) not in ('','nan') else None)
        else:
            df[col] = None

    # Strings
    for col, m in [("isometrico",30),("spool",10),("junta",10),("joint_type",5),("material",2),
                   ("insp_level",1),("pressure_class",5),("sth",50),("ieis",20),
                   ("heat_number_1",20),("heat_number_2",20),
                   ("corrida_1",20),("corrida_2",20),("corrida_3",20),("corrida_4",20)]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(lambda v, ml=m: str(v)[:ml] if v else None)
        else:
            df[col] = None

    for col in RESULT_COLS:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(lambda v: str(v)[:1] if v else None)
        else:
            df[col] = None

    df["project_id"] = project_id
    df["source"] = source

    COLS = ["project_id","isometrico","spool","junta","joint_type","diameter_mm",
            "diameter_in","thickness_mm","material","insp_level","pressure_class",
            "requires_tt","requires_ut","is_repair","sth","ieis","status",
            "heat_number_1","heat_number_2","corrida_1","corrida_2","corrida_3","corrida_4",
            "source"] + DATE_COLS + RESULT_COLS

    for c in COLS:
        if c not in df.columns:
            df[c] = None

    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_UPSERT_SQL, records, chunk_size=CHUNK, progress_cb=progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:3]}


_UPSERT_SQL = """
INSERT INTO joints (
  project_id, isometrico, spool, junta, joint_type, diameter_mm,
  diameter_in, thickness_mm, material, insp_level, pressure_class,
  requires_tt, requires_ut, is_repair, sth, ieis, status,
  heat_number_1, heat_number_2, corrida_1, corrida_2, corrida_3, corrida_4,
  source, dt_corte, dt_acoplamento, dt_soldagem, dt_vs, dt_lib_end,
  dt_embarque, dt_prog_mon, dt_lp, dt_rx, dt_tt,
  result_rx, result_lp, result_vs, result_us, result_tt
) VALUES %s
ON CONFLICT (project_id, isometrico, spool, junta) DO UPDATE SET
  status      = EXCLUDED.status,
  material    = COALESCE(EXCLUDED.material, joints.material),
  diameter_mm = COALESCE(EXCLUDED.diameter_mm, joints.diameter_mm),
  requires_tt = EXCLUDED.requires_tt,
  is_repair   = EXCLUDED.is_repair,
  dt_soldagem = COALESCE(EXCLUDED.dt_soldagem, joints.dt_soldagem),
  dt_acoplamento = COALESCE(EXCLUDED.dt_acoplamento, joints.dt_acoplamento),
  dt_lib_end  = COALESCE(EXCLUDED.dt_lib_end, joints.dt_lib_end),
  dt_lp       = COALESCE(EXCLUDED.dt_lp, joints.dt_lp),
  dt_rx       = COALESCE(EXCLUDED.dt_rx, joints.dt_rx),
  dt_tt       = COALESCE(EXCLUDED.dt_tt, joints.dt_tt),
  result_rx   = COALESCE(EXCLUDED.result_rx, joints.result_rx),
  result_lp   = COALESCE(EXCLUDED.result_lp, joints.result_lp),
  result_vs   = COALESCE(EXCLUDED.result_vs, joints.result_vs),
  result_tt   = COALESCE(EXCLUDED.result_tt, joints.result_tt),
  updated_at  = NOW()
"""
