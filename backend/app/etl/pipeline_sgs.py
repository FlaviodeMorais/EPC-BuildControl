"""ETL: SGS-SGM Excel → tabela spools. Pandas vetorizado + execute_values (bulk real)."""

import pandas as pd
import numpy as np
from .column_maps import SGS_MAP, SGER_TO_SPOOL_STATUS
from .utils import delphi_date, normalize_sger, split_spool_key
from .bulk import bulk_upsert

HEADER_ROW = 8
CHUNK = 5000

DATE_COLS = [
    "dt_lib_fab","dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_pintura","dt_embarque","dt_lib_mon",
    "dt_prog_mon","dt_pre_mon","dt_montagem","dt_sth","dt_lavagem",
]

STATUS_ORDER = ["NAO_INICIADO","EM_FABRICACAO","FABRICADO","EM_CAMPO","MONTADO","TESTADO"]
_SO = {s: i for i, s in enumerate(STATUS_ORDER)}


def _norm_status(val):
    return SGER_TO_SPOOL_STATUS.get(normalize_sger(val) or "", "NAO_INICIADO")


def _delphi_series(s: pd.Series) -> pd.Series:
    return s.apply(lambda v: delphi_date(v) if pd.notna(v) and str(v) not in ('', 'nan') else None)


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name="SGS", header=HEADER_ROW, dtype=str)
    df.rename(columns={k: v for k, v in SGS_MAP.items() if k in df.columns}, inplace=True)
    df = df.dropna(subset=["spool_key_raw"]).copy()
    df = df[df["spool_key_raw"].str.strip() != ""]

    # Split spool_key
    split = df["spool_key_raw"].apply(split_spool_key)
    df["isometrico"] = split.apply(lambda t: t[0])
    df["spool"]      = split.apply(lambda t: t[1])
    df = df.dropna(subset=["isometrico", "spool"])
    df = df[df["isometrico"].str.strip() != ""]

    # Status: maior entre sger (fab) e sgermon (montagem)
    s1 = df["sger"].apply(_norm_status) if "sger" in df.columns else pd.Series("NAO_INICIADO", index=df.index)
    s2 = df["sgermon"].apply(_norm_status) if "sgermon" in df.columns else pd.Series("NAO_INICIADO", index=df.index)
    df["status"] = [a if _SO.get(a,0) >= _SO.get(b,0) else b for a, b in zip(s1, s2)]

    # Numéricos
    for col in ["diameter_mm","thickness_mm","length_m","weight_kg","area_m2","pct_fab","pct_mon","joints_total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Hold
    hold_col = df.get("hold", pd.Series("", index=df.index)).fillna("")
    df["hold"] = ~hold_col.astype(str).isin(["0","","nan","None","False"])

    # Datas
    for col in DATE_COLS:
        df[col] = _delphi_series(df[col]) if col in df.columns else None

    # Strings truncadas
    for col, m in [("sger",100),("manufacturer",100),("material",2),("isometrico",30),("spool",10)]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(lambda v, ml=m: str(v)[:ml] if v else None)

    df["project_id"] = project_id
    df["source"] = "SGS"

    COLS = ["project_id","isometrico","spool","sger","status","manufacturer",
            "material","diameter_mm","thickness_mm","length_m","weight_kg","area_m2",
            "hold","pct_fab","pct_mon","joints_total","source"] + DATE_COLS

    for c in COLS:
        if c not in df.columns:
            df[c] = None

    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_UPSERT_SQL, records, chunk_size=CHUNK, progress_cb=progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:3]}


_UPSERT_SQL = """
INSERT INTO spools (
  project_id, isometrico, spool, sger, status, manufacturer,
  material, diameter_mm, thickness_mm, length_m, weight_kg, area_m2,
  hold, pct_fab, pct_mon, joints_total, source,
  dt_lib_fab, dt_corte, dt_acoplamento, dt_soldagem, dt_vs,
  dt_lib_end, dt_pintura, dt_embarque, dt_lib_mon,
  dt_prog_mon, dt_pre_mon, dt_montagem, dt_sth, dt_lavagem
) VALUES %s
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
