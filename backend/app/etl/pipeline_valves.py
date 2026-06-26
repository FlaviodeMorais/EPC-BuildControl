"""ETL: SGS-SGM_VALVULAS Excel → tabela valves. Pandas vetorizado + bulk_upsert."""

import pandas as pd
import numpy as np
from .column_maps import VALVES_MAP
from .bulk import bulk_upsert


def run(path: str, project_id: int, db, progress_cb=None) -> dict:
    df = pd.read_excel(path, sheet_name=0, header=1, dtype=str)
    df.rename(columns={k: v for k, v in VALVES_MAP.items() if k in df.columns}, inplace=True)
    df = df.dropna(subset=["valve_id_raw"]).copy()

    # Numéricos
    for col in ["dn_mm","unit_weight_kg","qty_planned","qty_received",
                "qty_reserved","qty_issued","weight_planned_kg","weight_received_kg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Availability vetorizado
    p = df["qty_planned"].fillna(0)
    r = df["qty_received"].fillna(0)
    df["availability"] = np.where(
        (r >= p) & (p > 0), "AVAILABLE",
        np.where(r > 0, "PARTIAL", "MISSING")
    )

    # Strings
    for col, m in [("valve_id_raw",100),("valve_tag",50)]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None).apply(lambda v, ml=m: str(v)[:ml] if v else None)
    if "description" in df.columns:
        df["description"] = df["description"].where(df["description"].notna(), None)

    df["project_id"] = project_id

    COLS = ["project_id","valve_id_raw","valve_tag","description","dn_mm","unit_weight_kg",
            "qty_planned","qty_received","qty_reserved","qty_issued",
            "weight_planned_kg","weight_received_kg","availability"]
    for c in COLS:
        if c not in df.columns:
            df[c] = None

    records = [tuple(r) for r in df[COLS].replace({np.nan: None}).itertuples(index=False, name=None)]
    inserted, errors = bulk_upsert(_UPSERT, records, chunk_size=5000, progress_cb=progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:5]}


_UPSERT = """
INSERT INTO valves (project_id, valve_id_raw, valve_tag, description, dn_mm, unit_weight_kg,
  qty_planned, qty_received, qty_reserved, qty_issued,
  weight_planned_kg, weight_received_kg, availability)
VALUES %s
ON CONFLICT DO NOTHING
"""
