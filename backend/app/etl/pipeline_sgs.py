"""ETL: SGS-SGM Excel → tabela spools. Vectorized pandas + bulk upsert."""

import pandas as pd
import numpy as np
from sqlalchemy import text
from .column_maps import SGS_MAP, SGER_TO_SPOOL_STATUS
from .utils import clean_str, safe_numeric, delphi_date, split_spool_key, normalize_sger

HEADER_ROW = 8
CHUNK = 3000
DATE_COLS = [
    "dt_lib_fab","dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_pintura","dt_embarque","dt_lib_mon",
    "dt_prog_mon","dt_pre_mon","dt_montagem","dt_sth","dt_lavagem",
]


def _delphi_vec(series: pd.Series) -> pd.Series:
    """Converte coluna de datas Delphi/Excel para date string ou None."""
    def _cvt(v):
        if pd.isna(v) or v in ('', 'nan', 'None'):
            return None
        return delphi_date(str(v))
    return series.apply(_cvt)


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name="SGS", header=HEADER_ROW, dtype=str)
    df.rename(columns={k: v for k, v in SGS_MAP.items() if k in df.columns}, inplace=True)
    df = df.dropna(subset=["spool_key_raw"]).copy()
    df = df[df["spool_key_raw"].str.strip() != ""]

    # Split spool_key vectorizado
    split = df["spool_key_raw"].apply(lambda x: split_spool_key(x))
    df["isometrico"] = split.apply(lambda t: t[0])
    df["spool"]      = split.apply(lambda t: t[1])
    df = df.dropna(subset=["isometrico", "spool"])
    df = df[df["isometrico"].str.strip() != ""]

    # Status vectorizado — usa sger (fab) e sgermon (montagem), avança para o mais alto
    STATUS_ORDER = ["NAO_INICIADO","EM_FABRICACAO","FABRICADO","EM_CAMPO","MONTADO","TESTADO"]
    def _spool_status(row):
        s1 = SGER_TO_SPOOL_STATUS.get(normalize_sger(row.get("sger")) or "", "NAO_INICIADO")
        s2 = SGER_TO_SPOOL_STATUS.get(normalize_sger(row.get("sgermon")) or "", "NAO_INICIADO")
        return s1 if STATUS_ORDER.index(s1) >= STATUS_ORDER.index(s2) else s2
    df["status"] = df.apply(_spool_status, axis=1)

    # Campos numéricos
    for col in ["diameter_mm","thickness_mm","length_m","weight_kg","area_m2","pct_fab","pct_mon","joints_total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Hold
    df["hold"] = df.get("hold", pd.Series(False, index=df.index)).apply(
        lambda v: str(v).strip() not in ("0","","nan","None","False")
    )

    # Datas
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = _delphi_vec(df[col])
        else:
            df[col] = None

    # String cols — truncate
    for col, maxlen in [("sger",100),("manufacturer",100),("material",2),("isometrico",30),("spool",10)]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(
                lambda v, m=maxlen: str(v)[:m] if v is not None else None
            )

    df["project_id"] = project_id
    df["source"] = "SGS"

    cols = [
        "project_id","isometrico","spool","sger","status","manufacturer",
        "material","diameter_mm","thickness_mm","length_m","weight_kg","area_m2",
        "hold","pct_fab","pct_mon","joints_total","source",
    ] + DATE_COLS

    # Garante que todas colunas existam
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
INSERT INTO spools (
  project_id, isometrico, spool, sger, status, manufacturer,
  material, diameter_mm, thickness_mm, length_m, weight_kg, area_m2,
  hold, pct_fab, pct_mon, joints_total, source,
  dt_lib_fab, dt_corte, dt_acoplamento, dt_soldagem, dt_vs,
  dt_lib_end, dt_pintura, dt_embarque, dt_lib_mon,
  dt_prog_mon, dt_pre_mon, dt_montagem, dt_sth, dt_lavagem
) VALUES (
  :project_id, :isometrico, :spool, :sger, CAST(:status AS spool_status),
  :manufacturer, CAST(:material AS material_code), :diameter_mm, :thickness_mm,
  :length_m, :weight_kg, :area_m2, :hold, :pct_fab, :pct_mon,
  :joints_total, :source,
  :dt_lib_fab, :dt_corte, :dt_acoplamento, :dt_soldagem, :dt_vs,
  :dt_lib_end, :dt_pintura, :dt_embarque, :dt_lib_mon,
  :dt_prog_mon, :dt_pre_mon, :dt_montagem, :dt_sth, :dt_lavagem
)
ON CONFLICT (project_id, isometrico, spool) DO UPDATE SET
  sger         = EXCLUDED.sger,
  status       = EXCLUDED.status,
  manufacturer = EXCLUDED.manufacturer,
  material     = COALESCE(EXCLUDED.material, spools.material),
  diameter_mm  = COALESCE(EXCLUDED.diameter_mm, spools.diameter_mm),
  weight_kg    = COALESCE(EXCLUDED.weight_kg, spools.weight_kg),
  hold         = EXCLUDED.hold,
  pct_fab      = EXCLUDED.pct_fab,
  pct_mon      = EXCLUDED.pct_mon,
  joints_total = COALESCE(EXCLUDED.joints_total, spools.joints_total),
  dt_soldagem  = COALESCE(EXCLUDED.dt_soldagem, spools.dt_soldagem),
  dt_lib_end   = COALESCE(EXCLUDED.dt_lib_end, spools.dt_lib_end),
  dt_embarque  = COALESCE(EXCLUDED.dt_embarque, spools.dt_embarque),
  updated_at   = NOW()
"""
