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

    def _clean_str(v, maxlen):
        if not v: return None
        s = str(v)
        # material_code_std: /prefixo/CODIGO → extrai CODIGO (após segunda /)
        # Pipe Name e demais: remove / inicial
        return s[:maxlen]

    def _clean_code_std(v):
        """Remove prefixo /xxx/ mantendo só o código: /M1_SCH40/C4B0010F01 → C4B0010F01"""
        if not v: return None
        s = str(v).strip()
        if s.startswith('/'):
            parts = s[1:].split('/', 1)
            return parts[1][:150] if len(parts) > 1 else parts[0][:150]
        return s[:150]

    def _strip_leading_slash(v, maxlen):
        if not v: return None
        s = str(v).strip().lstrip('/')
        return s[:maxlen] or None

    for col, m in [
        ("line_tag",100), ("item_3d_type",100),
        ("isometrico",30), ("spool_number_raw",50), ("iso_text",200),
        ("material_spec",100), ("material_code_alt",150),
        ("position",100),
    ]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(
                lambda v, ml=m: _strip_leading_slash(v, ml))
        else:
            df[col] = None

    if "material_code_std" in df.columns:
        df["material_code_std"] = df["material_code_std"].where(
            df["material_code_std"].notna(), None).apply(_clean_code_std)
    else:
        df["material_code_std"] = None

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

    df = df.drop_duplicates(subset=["material_code_alt", "isometrico", "spool_number_raw"])
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
