"""ETL: MAPA_JUNTA xlsb → tabela joints. Vectorized pandas + bulk upsert."""

import pandas as pd
import numpy as np
from sqlalchemy import text
from .column_maps import JOINTS_EXCEL_MAP, SGER_TO_STATUS
from .utils import clean_str, safe_numeric, delphi_date, normalize_sger

CHUNK = 3000
DATE_COLS = [
    "dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_embarque","dt_prog_mon",
]


def run_excel(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name="MAPA_JUNTA", engine="pyxlsb", dtype=str, header=7)
    df.rename(columns={k: v for k, v in JOINTS_EXCEL_MAP.items() if k in df.columns}, inplace=True)
    return _load(df, project_id, db, source="EXCEL", progress_cb=progress_cb)


def run_csv(path: str, project_id: int, db) -> dict:
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    paradox_map = {
        "Isometrico": "isometrico", "Spool": "spool", "Junta": "junta",
        "CBTP": "joint_type", "CBDI": "diameter_mm", "CBESP": "thickness_mm",
        "CBMAT": "material", "CBNI": "insp_level", "CBTT": "requires_tt",
        "corrida1": "corrida_1", "corrida2": "corrida_2",
        "corrida3": "corrida_3", "corrida4": "corrida_4",
        "HT_NUMBER1": "heat_number_1", "HT_NUMBER2": "heat_number_2",
        "DTSOLD": "dt_soldagem", "DTAJU": "dt_acoplamento", "DTVS": "dt_vs",
    }
    df.rename(columns=paradox_map, inplace=True)
    for col in ["dt_soldagem", "dt_acoplamento", "dt_vs"]:
        if col in df.columns:
            df[col] = df[col].apply(delphi_date)
    return _load(df, project_id, db, source="DATABOOK")


def _load(df: pd.DataFrame, project_id: int, db, source: str, progress_cb=None) -> dict:
    df = df.dropna(subset=["isometrico", "spool", "junta"]).copy()
    df = df[df["isometrico"].str.strip() != ""]

    # Status vectorizado
    status_src = df.get("status_raw", df.get("sger", pd.Series(None, index=df.index)))
    df["status"] = status_src.apply(
        lambda v: SGER_TO_STATUS.get(normalize_sger(v), "01_NAO_INICIADA")
    )

    # is_repair vectorizado
    junta_col = df["junta"].fillna("").str.strip()
    df["is_repair"] = junta_col.str.upper().str.match(r'^R\d+$')

    # Booleanos
    for col in ["requires_tt", "requires_ut"]:
        if col in df.columns:
            df[col] = ~df[col].fillna("0").astype(str).isin(["0","","N","None","False"])
        else:
            df[col] = False

    # Numéricos
    for col in ["diameter_mm", "thickness_mm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Datas
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: delphi_date(str(v)) if pd.notna(v) and str(v) not in ('','nan') else None)
        else:
            df[col] = None

    # String cols
    str_cols = {
        "isometrico":30,"spool":10,"junta":10,"joint_type":5,
        "material":2,"insp_level":1,"pressure_class":5,"sth":50,"ieis":20,
        "heat_number_1":20,"heat_number_2":20,
        "corrida_1":20,"corrida_2":20,"corrida_3":20,"corrida_4":20,
    }
    for col, maxlen in str_cols.items():
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(
                lambda v, m=maxlen: str(v)[:m] if v is not None else None
            )
        else:
            df[col] = None

    df["project_id"] = project_id
    df["source"] = source

    cols = [
        "project_id","isometrico","spool","junta","joint_type","diameter_mm",
        "diameter_in","thickness_mm","material","insp_level","pressure_class",
        "requires_tt","requires_ut","is_repair","sth","ieis","status",
        "heat_number_1","heat_number_2","corrida_1","corrida_2","corrida_3","corrida_4",
        "source",
    ] + DATE_COLS

    for c in cols:
        if c not in df.columns:
            df[c] = None

    records = df[cols].replace({np.nan: None}).to_dict("records")
    errors = []
    inserted = 0

    for i in range(0, len(records), CHUNK):
        chunk = records[i:i+CHUNK]
        try:
            db.execute(text(_UPSERT_SQL), chunk)
            db.commit()
            inserted += len(chunk)
        except Exception as e:
            db.rollback()
            errors.append(f"chunk {i}: {str(e)[:200]}")
        if progress_cb:
            progress_cb(inserted)

    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:3]}


_UPSERT_SQL = """
INSERT INTO joints (
  project_id, isometrico, spool, junta, joint_type, diameter_mm,
  diameter_in, thickness_mm, material, insp_level, pressure_class,
  requires_tt, requires_ut, is_repair, sth, ieis, status,
  heat_number_1, heat_number_2, corrida_1, corrida_2, corrida_3, corrida_4,
  source, dt_corte, dt_acoplamento, dt_soldagem, dt_vs, dt_lib_end,
  dt_embarque, dt_prog_mon
) VALUES (
  :project_id, :isometrico, :spool, :junta, CAST(:joint_type AS joint_type),
  :diameter_mm, :diameter_in, :thickness_mm, CAST(:material AS material_code),
  CAST(:insp_level AS insp_level), :pressure_class, :requires_tt, :requires_ut,
  :is_repair, :sth, :ieis, CAST(:status AS joint_status),
  :heat_number_1, :heat_number_2, :corrida_1, :corrida_2, :corrida_3, :corrida_4,
  :source, :dt_corte, :dt_acoplamento, :dt_soldagem, :dt_vs, :dt_lib_end,
  :dt_embarque, :dt_prog_mon
)
ON CONFLICT (project_id, isometrico, spool, junta) DO UPDATE SET
  status       = EXCLUDED.status,
  material     = COALESCE(EXCLUDED.material, joints.material),
  diameter_mm  = COALESCE(EXCLUDED.diameter_mm, joints.diameter_mm),
  requires_tt  = EXCLUDED.requires_tt,
  is_repair    = EXCLUDED.is_repair,
  heat_number_1= COALESCE(EXCLUDED.heat_number_1, joints.heat_number_1),
  corrida_1    = COALESCE(EXCLUDED.corrida_1, joints.corrida_1),
  dt_soldagem  = COALESCE(EXCLUDED.dt_soldagem, joints.dt_soldagem),
  dt_lib_end   = COALESCE(EXCLUDED.dt_lib_end, joints.dt_lib_end),
  updated_at   = NOW()
"""
