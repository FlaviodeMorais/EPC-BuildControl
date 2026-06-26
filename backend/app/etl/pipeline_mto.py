"""ETL: TYS-TUB-1 Excel → tabela mto_items."""

import re
import pandas as pd
import numpy as np
from .column_maps import MTO_MAP
from .bulk import bulk_upsert

CHUNK = 5000
_RE_FRAC  = re.compile(r'^(\d+)\s+(\d+)/(\d+)$')
_RE_PLAIN = re.compile(r'^(\d+(?:\.\d+)?)$')


def _in_to_mm(val):
    if not val:
        return None
    val = str(val).replace('"', '').strip()
    m = _RE_FRAC.match(val)
    if m:
        return round((int(m.group(1)) + int(m.group(2)) / int(m.group(3))) * 25.4, 2)
    m = _RE_PLAIN.match(val)
    return round(float(m.group(1)) * 25.4, 2) if m else None


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name=0, dtype=str)
    df.rename(columns={k: v for k, v in MTO_MAP.items() if k in df.columns}, inplace=True)
    df = df.dropna(subset=["material_code_alt"]).copy()

    for src, dst, factor in [
        ("pipe_length_mm", "pipe_length_m",    1/1000),
        ("elevation_mm",   "elevation_m",       1/1000),
        ("surface_area_mm2","surface_area_m2",  1/1_000_000),
    ]:
        df[dst] = pd.to_numeric(df[src], errors="coerce") * factor if src in df.columns else None

    if "weight_kg" in df.columns:
        df["weight_kg"] = pd.to_numeric(df["weight_kg"], errors="coerce")

    df["diameter_nom_mm"] = df["diameter_nom_in"].apply(_in_to_mm) if "diameter_nom_in" in df.columns else None

    for col, m in [
        ("line_tag",100), ("item_3d_type",100),
        ("isometrico",30), ("spool_number_raw",50), ("iso_text",200),
        ("material_spec",100), ("material_code_std",150), ("material_code_alt",150),
        ("position",100),
    ]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(
                lambda v, ml=m: str(v)[:ml] if v else None)
        else:
            df[col] = None

    df["description"] = df["description"].where(df["description"].notna(), None) if "description" in df.columns else None
    df["project_id"] = project_id

    COLS = [
        "project_id", "line_tag", "item_3d_type",
        "diameter_nom_mm", "pipe_length_m", "description",
        "material_spec", "material_code_std", "material_code_alt",
        "position", "elevation_m", "weight_kg", "surface_area_m2",
        "isometrico", "iso_text", "spool_number_raw",
    ]
    for c in COLS:
        if c not in df.columns:
            df[c] = None

    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_INSERT_SQL, records, chunk_size=CHUNK, progress_cb=progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:5]}


_INSERT_SQL = """
INSERT INTO mto_items (
  project_id, line_tag, item_3d_type,
  diameter_nom_mm, pipe_length_m, description,
  material_spec, material_code_std, material_code_alt,
  position, elevation_m, weight_kg, surface_area_m2,
  isometrico, iso_text, spool_number_raw)
VALUES %s
ON CONFLICT (project_id, material_code_alt, isometrico, spool_number_raw)
DO UPDATE SET
  line_tag        = EXCLUDED.line_tag,
  item_3d_type    = EXCLUDED.item_3d_type,
  diameter_nom_mm = EXCLUDED.diameter_nom_mm,
  pipe_length_m   = EXCLUDED.pipe_length_m,
  description     = EXCLUDED.description,
  material_spec   = EXCLUDED.material_spec,
  material_code_std = EXCLUDED.material_code_std,
  position        = EXCLUDED.position,
  elevation_m     = EXCLUDED.elevation_m,
  weight_kg       = EXCLUDED.weight_kg,
  surface_area_m2 = EXCLUDED.surface_area_m2,
  iso_text        = EXCLUDED.iso_text
"""
