"""ETL: SGS-SGM Excel → tabela spools. Bulk insert via executemany."""

import pandas as pd
from sqlalchemy import text
from .column_maps import SGS_MAP, SGER_TO_STATUS
from .utils import clean_str, safe_numeric, delphi_date, split_spool_key, normalize_sger

HEADER_ROW = 8
CHUNK = 2000
DATE_COLS = [
    "dt_lib_fab","dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_pintura","dt_embarque","dt_lib_mon",
    "dt_prog_mon","dt_pre_mon","dt_montagem","dt_sth","dt_lavagem",
]


def run(path: str, project_id: int, db) -> dict:
    df = pd.read_excel(path, sheet_name="SGS", header=HEADER_ROW, dtype=str)
    df.rename(columns={k: v for k, v in SGS_MAP.items() if k in df.columns}, inplace=True)
    df.dropna(subset=["spool_key_raw"], inplace=True)

    records = []
    errors = []

    for _, row in df.iterrows():
        try:
            iso, spool = split_spool_key(row.get("spool_key_raw"))
            if not iso or not spool:
                continue
            status_raw = normalize_sger(row.get("sger"))
            status = SGER_TO_STATUS.get(status_raw, "NAO_INICIADO")
            rec = {
                "project_id":   project_id,
                "isometrico":   iso,
                "spool":        spool,
                "sger":         clean_str(row.get("sger"), 100),
                "status":       status,
                "manufacturer": clean_str(row.get("manufacturer"), 100),
                "material":     clean_str(row.get("material"), 2),
                "diameter_mm":  safe_numeric(row.get("diameter_mm")),
                "thickness_mm": safe_numeric(row.get("thickness_mm")),
                "length_m":     safe_numeric(row.get("length_m")),
                "weight_kg":    safe_numeric(row.get("weight_kg")),
                "area_m2":      safe_numeric(row.get("area_m2")),
                "hold":         clean_str(row.get("hold")) not in (None, "", "0"),
                "pct_fab":      safe_numeric(row.get("pct_fab")),
                "pct_mon":      safe_numeric(row.get("pct_mon")),
                "joints_total": safe_numeric(row.get("joints_total")),
                "source":       "SGS",
            }
            for col in DATE_COLS:
                rec[col] = delphi_date(row.get(col))
            records.append(rec)
        except Exception as e:
            errors.append(str(e))

    # Bulk upsert em chunks
    for i in range(0, len(records), CHUNK):
        db.execute(text(_UPSERT_SQL), records[i:i+CHUNK])
    db.commit()

    return {"inserted_updated": len(records), "errors": len(errors), "error_samples": errors[:3]}


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
