"""ETL: TYS-TUB-1 Excel → tabela mto_items."""

import re
import pandas as pd
from sqlalchemy import text
from .column_maps import MTO_MAP
from .utils import clean_str, safe_numeric

CHUNK = 5000


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name=0, dtype=str)
    df.rename(columns={k: v for k, v in MTO_MAP.items() if k in df.columns}, inplace=True)
    df.dropna(subset=["item_3d_name"], inplace=True)

    rows_ok = rows_err = 0
    errors = []
    buffer = []

    for _, row in df.iterrows():
        try:
            buffer.append({
                "project_id":       project_id,
                "isometrico":       clean_str(row.get("isometrico"), 30),
                "spool_number_raw": clean_str(row.get("spool_number_raw"), 50),
                "item_3d_name":     clean_str(row.get("item_3d_name"), 200),
                "item_3d_type":     clean_str(row.get("item_3d_type"), 100),
                "description":      clean_str(row.get("description")),
                "material_spec":    clean_str(row.get("material_spec"), 100),
                "material_code_std": clean_str(row.get("material_code_std"), 150),
                "material_code_alt": clean_str(row.get("material_code_alt"), 150),
                "diameter_nom_mm":  _in_to_mm(clean_str(row.get("diameter_nom_in"))),
                "diameter_sec_mm":  _in_to_mm(clean_str(row.get("diameter_sec_in"))),
                "pipe_length_m":    _mm_to_m(safe_numeric(row.get("pipe_length_mm"))),
                "elevation_m":      _mm_to_m(safe_numeric(row.get("elevation_mm"))),
                "weight_kg":        safe_numeric(row.get("weight_kg")),
                "surface_area_m2":  _mm2_to_m2(safe_numeric(row.get("surface_area_mm2"))),
                "position":         clean_str(row.get("position"), 100),
                "scope":            clean_str(row.get("scope"), 50),
                "zone":             clean_str(row.get("zone"), 100),
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
            errors.append(str(e))

        if len(buffer) >= CHUNK:
            _bulk_insert(buffer, db)
            if progress_cb:
                progress_cb(rows_ok)
            buffer.clear()

    if buffer:
        _bulk_insert(buffer, db)

    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err, "error_samples": errors[:5]}


def _bulk_insert(records: list, db) -> None:
    db.execute(text("""
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
    """), records)


_RE_FRAC = re.compile(r'^(\d+)\s+(\d+)/(\d+)$')
_RE_PLAIN = re.compile(r'^(\d+(?:\.\d+)?)$')


def _in_to_mm(val: str | None) -> float | None:
    if not val:
        return None
    val = val.replace('"', '').strip()
    m = _RE_FRAC.match(val)
    if m:
        return round((int(m.group(1)) + int(m.group(2)) / int(m.group(3))) * 25.4, 2)
    m = _RE_PLAIN.match(val)
    if m:
        return round(float(m.group(1)) * 25.4, 2)
    return None


def _mm_to_m(v: float | None) -> float | None:
    return round(v / 1000, 4) if v is not None else None


def _mm2_to_m2(v: float | None) -> float | None:
    return round(v / 1_000_000, 6) if v is not None else None
