"""ETL: SGS-SGM_VALVULAS Excel → tabela valves."""

import pandas as pd
from sqlalchemy import text
from .column_maps import VALVES_MAP
from .utils import clean_str, safe_numeric


def run(path: str, project_id: int, db) -> dict:
    df = pd.read_excel(path, sheet_name=0, header=1, dtype=str)
    df.rename(columns={k: v for k, v in VALVES_MAP.items() if k in df.columns}, inplace=True)
    df.dropna(subset=["valve_id_raw"], inplace=True)

    rows_ok = rows_err = 0
    errors = []

    for _, row in df.iterrows():
        try:
            qty_p = safe_numeric(row.get("qty_planned")) or 0
            qty_r = safe_numeric(row.get("qty_received")) or 0
            if qty_r >= qty_p and qty_p > 0:
                avail = "AVAILABLE"
            elif qty_r > 0:
                avail = "PARTIAL"
            else:
                avail = "MISSING"

            db.execute(text(_UPSERT), {
                "project_id":        project_id,
                "valve_id_raw":      clean_str(row.get("valve_id_raw"), 100),
                "description":       clean_str(row.get("description")),
                "dn_mm":             safe_numeric(row.get("dn_mm")),
                "unit_weight_kg":    safe_numeric(row.get("unit_weight_kg")),
                "qty_planned":       qty_p,
                "qty_received":      qty_r,
                "qty_reserved":      safe_numeric(row.get("qty_reserved")) or 0,
                "qty_issued":        safe_numeric(row.get("qty_issued")) or 0,
                "weight_planned_kg": safe_numeric(row.get("weight_planned_kg")) or 0,
                "weight_received_kg": safe_numeric(row.get("weight_received_kg")) or 0,
                "availability":      avail,
            })
            rows_ok += 1
        except Exception as e:
            rows_err += 1
            errors.append(str(e))

    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err, "error_samples": errors[:5]}


_UPSERT = """
INSERT INTO valves (project_id, valve_id_raw, description, dn_mm, unit_weight_kg,
  qty_planned, qty_received, qty_reserved, qty_issued,
  weight_planned_kg, weight_received_kg, availability)
VALUES (:project_id, :valve_id_raw, :description, :dn_mm, :unit_weight_kg,
  :qty_planned, :qty_received, :qty_reserved, :qty_issued,
  :weight_planned_kg, :weight_received_kg, :availability)
ON CONFLICT DO NOTHING
"""
