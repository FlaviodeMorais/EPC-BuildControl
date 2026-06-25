"""ETL: MAPA_JUNTA xlsb + JUNTAS.csv (Databook) → tabela joints."""

import pandas as pd
from sqlalchemy import text
from .column_maps import JOINTS_EXCEL_MAP, SGER_TO_STATUS
from .utils import clean_str, safe_numeric, delphi_date, normalize_sger

DATE_COLS = [
    "dt_corte","dt_acoplamento","dt_soldagem","dt_vs",
    "dt_lib_end","dt_embarque","dt_prog_mon","dt_pre_mon","dt_montagem",
]


def run_excel(path: str, project_id: int, db) -> dict:
    """Importa arquivo xlsb (MAPA_JUNTA)."""
    try:
        import pyxlsb
        df = pd.read_excel(path, sheet_name="MAPA_JUNTA", engine="pyxlsb", dtype=str)
    except ImportError:
        raise RuntimeError("Instale pyxlsb: pip install pyxlsb")

    df.rename(columns={k: v for k, v in JOINTS_EXCEL_MAP.items() if k in df.columns}, inplace=True)
    return _load(df, project_id, db, source="EXCEL")


def run_csv(path: str, project_id: int, db) -> dict:
    """Importa JUNTAS.csv extraído do Databook Paradox."""
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    # renomear campos Paradox → canônico
    paradox_map = {
        "Isometrico": "isometrico", "Spool": "spool", "Junta": "junta",
        "CBTP": "joint_type", "CBDI": "diameter_mm", "CBESP": "thickness_mm",
        "CBMAT": "material", "CBNI": "insp_level", "CBTT": "requires_tt",
        "ASRAIZ": "welder_root_sin", "ASENCH": "welder_fill_sin",
        "corrida1": "corrida_1", "corrida2": "corrida_2",
        "corrida3": "corrida_3", "corrida4": "corrida_4",
        "HT_NUMBER1": "heat_number_1", "HT_NUMBER2": "heat_number_2",
        "DTSOLD": "dt_soldagem_raw", "DTAJU": "dt_acoplamento_raw",
        "DTVS": "dt_vs_raw",
    }
    df.rename(columns=paradox_map, inplace=True)
    # datas no Databook são float Delphi
    for raw_col, target_col in [
        ("dt_soldagem_raw", "dt_soldagem"),
        ("dt_acoplamento_raw", "dt_acoplamento"),
        ("dt_vs_raw", "dt_vs"),
    ]:
        if raw_col in df.columns:
            df[target_col] = df[raw_col].apply(delphi_date)
    return _load(df, project_id, db, source="DATABOOK")


def _load(df: pd.DataFrame, project_id: int, db, source: str) -> dict:
    # filtrar linhas sem chave
    df = df.dropna(subset=["isometrico","spool","junta"])
    df = df[df["isometrico"].str.strip() != ""]

    rows_ok = rows_err = 0
    errors = []

    for _, row in df.iterrows():
        try:
            status_code = normalize_sger(row.get("status_raw") or row.get("sger"))
            status = SGER_TO_STATUS.get(status_code, "01_NAO_INICIADA")
            junta_val = clean_str(row.get("junta"), 10) or ""
            is_repair = junta_val.upper().startswith("R") and junta_val[1:].isdigit()

            record = {
                "project_id":      project_id,
                "isometrico":      clean_str(row.get("isometrico"), 30),
                "spool":           clean_str(row.get("spool"), 10),
                "junta":           junta_val,
                "joint_type":      clean_str(row.get("joint_type"), 5),
                "diameter_mm":     safe_numeric(row.get("diameter_mm")),
                "diameter_in":     clean_str(row.get("diameter_in"), 10),
                "thickness_mm":    safe_numeric(row.get("thickness_mm")),
                "material":        clean_str(row.get("material"), 2),
                "insp_level":      clean_str(row.get("insp_level"), 1),
                "pressure_class":  clean_str(row.get("pressure_class"), 5),
                "requires_tt":     str(row.get("requires_tt","0")) not in ("0","","N","None"),
                "requires_ut":     str(row.get("requires_ut","0")) not in ("0","","N","None"),
                "is_repair":       is_repair,
                "sth":             clean_str(row.get("sth"), 50),
                "ieis":            clean_str(row.get("ieis"), 20),
                "status":          status,
                "welder_root_sin": clean_str(row.get("welder_root_sin"), 20),
                "welder_fill_sin": clean_str(row.get("welder_fill_sin"), 20),
                "heat_number_1":   clean_str(row.get("heat_number_1"), 20),
                "heat_number_2":   clean_str(row.get("heat_number_2"), 20),
                "corrida_1":       clean_str(row.get("corrida_1"), 20),
                "corrida_2":       clean_str(row.get("corrida_2"), 20),
                "corrida_3":       clean_str(row.get("corrida_3"), 20),
                "corrida_4":       clean_str(row.get("corrida_4"), 20),
                "source":          source,
            }
            for col in DATE_COLS:
                if col not in record:
                    record[col] = delphi_date(row.get(col)) if source == "DATABOOK" else None

            db.execute(text(_UPSERT_SQL), record)
            rows_ok += 1
        except Exception as e:
            rows_err += 1
            errors.append(str(e))

    db.commit()
    return {"inserted_updated": rows_ok, "errors": rows_err, "error_samples": errors[:5]}


_UPSERT_SQL = """
INSERT INTO joints (
  project_id, isometrico, spool, junta, joint_type, diameter_mm,
  diameter_in, thickness_mm, material, insp_level, pressure_class,
  requires_tt, requires_ut, is_repair, sth, ieis, status,
  welder_root_sin, welder_fill_sin, heat_number_1, heat_number_2,
  corrida_1, corrida_2, corrida_3, corrida_4, source,
  dt_corte, dt_acoplamento, dt_soldagem, dt_vs, dt_lib_end,
  dt_embarque, dt_prog_mon, dt_pre_mon, dt_montagem
)
VALUES (
  :project_id, :isometrico, :spool, :junta, :joint_type::joint_type,
  :diameter_mm, :diameter_in, :thickness_mm, :material::material_code,
  :insp_level::insp_level, :pressure_class, :requires_tt, :requires_ut,
  :is_repair, :sth, :ieis, :status::joint_status,
  :welder_root_sin, :welder_fill_sin, :heat_number_1, :heat_number_2,
  :corrida_1, :corrida_2, :corrida_3, :corrida_4, :source,
  :dt_corte, :dt_acoplamento, :dt_soldagem, :dt_vs, :dt_lib_end,
  :dt_embarque, :dt_prog_mon, :dt_pre_mon, :dt_montagem
)
ON CONFLICT (project_id, isometrico, spool, junta) DO UPDATE SET
  status        = EXCLUDED.status,
  material      = COALESCE(EXCLUDED.material, joints.material),
  diameter_mm   = COALESCE(EXCLUDED.diameter_mm, joints.diameter_mm),
  requires_tt   = EXCLUDED.requires_tt,
  is_repair     = EXCLUDED.is_repair,
  welder_root_sin = COALESCE(EXCLUDED.welder_root_sin, joints.welder_root_sin),
  welder_fill_sin = COALESCE(EXCLUDED.welder_fill_sin, joints.welder_fill_sin),
  heat_number_1 = COALESCE(EXCLUDED.heat_number_1, joints.heat_number_1),
  corrida_1     = COALESCE(EXCLUDED.corrida_1, joints.corrida_1),
  dt_soldagem   = COALESCE(EXCLUDED.dt_soldagem, joints.dt_soldagem),
  dt_lib_end    = COALESCE(EXCLUDED.dt_lib_end, joints.dt_lib_end),
  updated_at    = NOW()
"""
