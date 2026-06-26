"""ETL: TYS-TUB-1 Excel → tabela mto_items. Vectorized pandas."""

import re
import pandas as pd
import numpy as np
from sqlalchemy import text
from .column_maps import MTO_MAP

CHUNK = 5000
_RE_FRAC  = re.compile(r'^(\d+)\s+(\d+)/(\d+)$')
_RE_PLAIN = re.compile(r'^(\d+(?:\.\d+)?)$')


def _in_to_mm(val: str | None) -> float | None:
    if not val:
        return None
    val = val.replace('"', '').strip()
    m = _RE_FRAC.match(val)
    if m:
        return round((int(m.group(1)) + int(m.group(2)) / int(m.group(3))) * 25.4, 2)
    m = _RE_PLAIN.match(val)
    return round(float(m.group(1)) * 25.4, 2) if m else None


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name=0, dtype=str)
    df.rename(columns={k: v for k, v in MTO_MAP.items() if k in df.columns}, inplace=True)
    df = df.dropna(subset=["item_3d_name"]).copy()

    # Numéricos vectorizados
    num_cols = {"pipe_length_mm": ("pipe_length_m", 1/1000),
                "elevation_mm":   ("elevation_m",   1/1000),
                "surface_area_mm2": ("surface_area_m2", 1/1_000_000)}
    for src, (dst, factor) in num_cols.items():
        if src in df.columns:
            df[dst] = pd.to_numeric(df[src], errors="coerce") * factor
        else:
            df[dst] = None

    if "weight_kg" in df.columns:
        df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")

    # Diâmetros: polegadas → mm
    for col_in, col_out in [("diameter_nom_in","diameter_nom_mm"),("diameter_sec_in","diameter_sec_mm")]:
        if col_in in df.columns:
            df[col_out] = df[col_in].apply(_in_to_mm)
        else:
            df[col_out] = None

    # String truncation vectorizada
    str_cols = {
        "isometrico":30,"spool_number_raw":50,"item_3d_name":200,
        "item_3d_type":100,"material_spec":100,"material_code_std":150,
        "material_code_alt":150,"position":100,"scope":50,"zone":100,
    }
    for col, maxlen in str_cols.items():
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(
                lambda v, m=maxlen: str(v)[:m] if v is not None else None
            )
        else:
            df[col] = None

    # description sem truncate
    if "description" in df.columns:
        df["description"] = df["description"].where(df["description"].notna(), None)
    else:
        df["description"] = None

    df["project_id"] = project_id

    cols = [
        "project_id","isometrico","spool_number_raw","item_3d_name","item_3d_type",
        "description","material_spec","material_code_std","material_code_alt",
        "diameter_nom_mm","diameter_sec_mm","pipe_length_m","elevation_m",
        "weight_kg","surface_area_m2","position","scope","zone",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    records = df[cols].replace({np.nan: None}).to_dict("records")
    errors = []

    for i in range(0, len(records), CHUNK):
        chunk = records[i:i+CHUNK]
        try:
            db.execute(text(_INSERT_SQL), chunk)
            db.commit()
        except Exception as e:
            db.rollback()
            errors.append(f"chunk {i}: {e}")
        if progress_cb:
            progress_cb(min(i + CHUNK, len(records)))

    return {"inserted_updated": len(records), "errors": len(errors), "error_samples": errors[:5]}


_INSERT_SQL = """
INSERT INTO mto_items (project_id, isometrico, spool_number_raw,
  item_3d_name, item_3d_type, description, material_spec,
  material_code_std, material_code_alt, diameter_nom_mm, diameter_sec_mm,
  pipe_length_m, elevation_m, weight_kg, surface_area_m2,
  position, scope, zone)
VALUES (:project_id, :isometrico, :spool_number_raw,
  :item_3d_name, :item_3d_type, :description, :material_spec,
  :material_code_std, :material_code_alt, :diameter_nom_mm, :diameter_sec_mm,
  :pipe_length_m, :elevation_m, :weight_kg, :surface_area_m2,
  :position, :scope, :zone)
ON CONFLICT DO NOTHING
"""
