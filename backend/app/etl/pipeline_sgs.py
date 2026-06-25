"""ETL: SGS-SGM Excel → tabela spools."""

import pandas as pd
from sqlalchemy import text
from .column_maps import SGS_MAP, SGER_TO_STATUS
from .utils import clean_str, safe_numeric, delphi_date, split_spool_key, normalize_sger

HEADER_ROW = 7   # linha 8 no Excel (0-indexed = 7)
DATE_COLS = [
    "dt_lib_fab","dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_pintura","dt_embarque","dt_lib_mon",
    "dt_prog_mon","dt_pre_mon","dt_montagem","dt_sth","dt_lavagem",
]
NUMERIC_COLS = ["diameter_mm","thickness_mm","length_m","area_m2","weight_kg",
                "pct_fab","pct_mon","joints_total"]


def run(path: str, project_id: int, db) -> dict:
    df = pd.read_excel(path, sheet_name="SGS", header=HEADER_ROW, dtype=str)
    df.rename(columns={k: v for k, v in SGS_MAP.items() if k in df.columns}, inplace=True)
    df.dropna(subset=["spool_key_raw"], inplace=True)

    rows_ok = rows_err = 0
    errors = []

    for _, row in df.iterrows():
        try:
            iso, spool = split_spool_key(row.get("spool_key_raw"))
            if not iso or not spool:
                continue

            status_raw = normalize_sger(row.get("sger"))
            status = SGER_TO_STATUS.get(status_raw, "NAO_INICIADO")

            record = {
                "project_id":    project_id,
                "isometrico":    iso,
                "spool":         spool,
                "unit_code":     clean_str(row.get("unit_code"), 10),
                "sub_unit":      clean_str(row.get("sub_unit"), 10),
                "line_tag":      clean_str(row.get("line_tag"), 100),
                "manufacturer":  clean_str(row.get("manufacturer"), 100),
                "material":      clean_str(row.get("material"), 2),
                "diameter_mm":   safe_numeric(row.get("diameter_mm")),
                "thickness_mm":  safe_numeric(row.get("thickness_mm")),
                "length_m":      safe_numeric(row.get("length_m")),
                "weight_kg":     safe_numeric(row.get("weight_kg")),
                "area_m2":       safe_numeric(row.get("area_m2")),
                "hold":          clean_str(row.get("hold")) not in (None, "", "0"),
                "pct_fab":       safe_numeric(row.get("pct_fab")),
                "pct_mon":       safe_numeric(row.get("pct_mon")),
                "joints_total":  safe_numeric(row.get("joints_total")),
                "sger":          clean_str(row.get("sger"), 100),
                "status":        status,
                "source":        "SGS",
            }
            for col in DATE_COLS:
                record[col] = delphi_date(row.get(col))

            db.execute(text(_UPSERT_SQL), record)
            rows_ok += 1
        except Exception as e:
            rows_err += 1
            errors.append(str(e))

    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err, "error_samples": errors[:5]}


_UPSERT_SQL = """
INSERT INTO spools (
  project_id, isometrico, spool, sger, status, manufacturer,
  material, diameter_mm, thickness_mm, length_m, weight_kg, area_m2,
  hold, pct_fab, pct_mon, joints_total, source,
  dt_lib_fab, dt_corte, dt_acoplamento, dt_soldagem, dt_vs,
  dt_lib_end, dt_pintura, dt_embarque, dt_lib_mon,
  dt_prog_mon, dt_pre_mon, dt_montagem, dt_sth, dt_lavagem
)
VALUES (
  :project_id, :isometrico, :spool, :sger, :status::spool_status,
  :manufacturer, :material::material_code, :diameter_mm, :thickness_mm,
  :length_m, :weight_kg, :area_m2, :hold, :pct_fab, :pct_mon,
  :joints_total, :source,
  :dt_lib_fab, :dt_corte, :dt_acoplamento, :dt_soldagem, :dt_vs,
  :dt_lib_end, :dt_pintura, :dt_embarque, :dt_lib_mon,
  :dt_prog_mon, :dt_pre_mon, :dt_montagem, :dt_sth, :dt_lavagem
)
ON CONFLICT (project_id, isometrico, spool) DO UPDATE SET
  sger          = EXCLUDED.sger,
  status        = EXCLUDED.status,
  manufacturer  = EXCLUDED.manufacturer,
  material      = COALESCE(EXCLUDED.material, spools.material),
  diameter_mm   = COALESCE(EXCLUDED.diameter_mm, spools.diameter_mm),
  weight_kg     = COALESCE(EXCLUDED.weight_kg, spools.weight_kg),
  hold          = EXCLUDED.hold,
  pct_fab       = EXCLUDED.pct_fab,
  pct_mon       = EXCLUDED.pct_mon,
  joints_total  = COALESCE(EXCLUDED.joints_total, spools.joints_total),
  -- nunca sobrescreve datas reais com nulo
  dt_soldagem   = COALESCE(EXCLUDED.dt_soldagem, spools.dt_soldagem),
  dt_lib_end    = COALESCE(EXCLUDED.dt_lib_end, spools.dt_lib_end),
  dt_embarque   = COALESCE(EXCLUDED.dt_embarque, spools.dt_embarque),
  updated_at    = NOW()
"""
