"""ETL: TUB.csv (Paradox) → enriquece tabela spools com datas, contagens e status."""

import pandas as pd
import numpy as np
from .utils import delphi_date
from .bulk import bulk_upsert

CHUNK = 5000
_PBOM = '\xef\xbb\xbf'

_DATE_COLS = [
    ("DTCORT","dt_corte"),("AJUDAT","dt_acoplamento"),("SOLDAT","dt_soldagem"),
    ("VSDAT","dt_vs"),("LIBDAT","dt_lib_end"),("DTLIBFAB","dt_lib_fab"),
    ("DTLIBMON","dt_lib_mon"),("DTPREMON","dt_pre_mon"),("DTPROGMON","dt_prog_mon"),
    ("DTEMBARQUE","dt_embarque"),("DtSitFab","dt_sit_fab"),("DtSitMon","dt_sit_mon"),
]


def _read(path: str) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc, on_bad_lines="skip")
            df.columns = [c.removeprefix(_PBOM).removeprefix('﻿').strip() for c in df.columns]
            return df
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível decodificar: {path}")


def _ordinal_or_delphi(v):
    try:
        n = int(float(v))
        if n <= 0: return None
        from datetime import date
        return date.fromordinal(n) if n > 600000 else delphi_date(n)
    except (TypeError, ValueError, OverflowError):
        return None


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = _read(path).dropna(subset=["ISOMETRICO", "SPOOL"]).copy()
    df = df.drop_duplicates(subset=["ISOMETRICO", "SPOOL"])

    df["project_id"] = project_id
    df["isometrico"] = df["ISOMETRICO"].str.strip()
    df["spool"] = df["SPOOL"].str.strip()

    for src, dst in _DATE_COLS:
        df[dst] = df[src].apply(_ordinal_or_delphi) if src in df.columns else None

    for col in ["DIAMETRO","COMP","AREA","ESP","PESO",
                "PROGFAB","PROGMON","TJS","TJSS","TJSM","TJSA"]:
        if col in df.columns:
            df[col.lower()] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col.lower()] = None

    for col, m in [("LINHA",100),("fluido",50),("ESPEC",100),("STH",50),
                   ("sop",30),("MAT",2),("sger",5),("sgermon",5),("MONTADORA",100)]:
        df[col.lower()] = df[col].where(df[col].notna(), None).apply(
            lambda v, ml=m: str(v)[:ml] if v else None) if col in df.columns else None

    COLS = ["project_id","isometrico","spool",
            "diametro","comp","area","esp","peso","progfab","progmon",
            "tjs","tjss","tjsm","tjsa",
            "linha","fluido","espec","sth","sop","mat","sger","sgermon","montadora",
            "dt_corte","dt_acoplamento","dt_soldagem","dt_vs","dt_lib_end",
            "dt_lib_fab","dt_lib_mon","dt_pre_mon","dt_prog_mon","dt_embarque",
            "dt_sit_fab","dt_sit_mon"]

    for c in COLS:
        if c not in df.columns:
            df[c] = None

    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_SQL, records, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:5]}


_SQL = """
INSERT INTO tub_status (
  project_id, isometrico, spool,
  diameter_mm, length_m, area_m2, thickness_mm, weight_kg, pct_fab, pct_mon,
  joints_total, joints_welded, joints_mounted, joints_coupled,
  line_tag, fluid, spec, sth, sop, material, sger, sgermon, manufacturer,
  dt_corte, dt_acoplamento, dt_soldagem, dt_vs, dt_lib_end,
  dt_lib_fab, dt_lib_mon, dt_pre_mon, dt_prog_mon, dt_embarque,
  dt_sit_fab, dt_sit_mon
) VALUES %s
ON CONFLICT (project_id, isometrico, spool) DO UPDATE SET
  pct_fab      = EXCLUDED.pct_fab,
  pct_mon      = EXCLUDED.pct_mon,
  joints_total = EXCLUDED.joints_total,
  joints_welded= EXCLUDED.joints_welded,
  sger         = EXCLUDED.sger,
  sgermon      = EXCLUDED.sgermon,
  dt_soldagem  = COALESCE(EXCLUDED.dt_soldagem, tub_status.dt_soldagem),
  dt_lib_end   = COALESCE(EXCLUDED.dt_lib_end, tub_status.dt_lib_end),
  dt_sit_fab   = EXCLUDED.dt_sit_fab,
  dt_sit_mon   = EXCLUDED.dt_sit_mon,
  updated_at   = NOW()
"""
