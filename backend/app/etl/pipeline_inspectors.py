"""ETL: INSP.DB (Paradox) → inspectors | BMSRX/TT/US.DB → inspection_reports."""

import numpy as np
from .paradox_reader import parse
from .bulk import bulk_upsert

CHUNK = 2000


def run_inspectors(path: str, project_id: int, db, progress_cb=None) -> dict:
    _, recs = parse(path)

    rows = []
    for r in recs:
        quali = (r.get('QUALI') or '').strip()
        nome = (r.get('NOME') or '').strip()
        if not quali and not nome:
            continue
        rows.append((
            project_id,
            _s(r.get('INSP'), 20),
            quali[:10] if quali else None,
            nome[:100] if nome else None,
            _s(r.get('EMPRESA'), 50),
            None, None, None,
            _s(r.get('CERTIFICADORA'), 100),
            _s(r.get('MetodoMedFerrita'), 20),
        ))

    inserted, errors = bulk_upsert(_INSP_SQL, rows, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:3]}


def run_inspection_reports(path: str, report_type: str, project_id: int,
                           db, progress_cb=None) -> dict:
    _, recs = parse(path)

    # Mapeia campos por tipo de ensaio
    if report_type == 'RX':
        result_col, lot_col, num_col = 'RX1L', 'RX1RC', 'PLRX'
    elif report_type == 'TT':
        result_col, lot_col, num_col = 'ASTTL', 'ASTTREC', 'PLTT'
    else:  # US
        result_col, lot_col, num_col = 'RX1L', 'RX1RC', 'PLUS'

    rows = []
    for r in recs:
        iso = _clean_iso(r.get('Isometrico') or r.get('isometrico'))
        if not iso:
            continue
        spool = _s(r.get('Spool') or r.get('spool'), 10)
        junta = _s(r.get('Junta') or r.get('junta'), 10)
        rows.append((
            project_id,
            report_type,
            _s(r.get(num_col), 30),
            iso,
            spool,
            junta,
            _num(r.get('CBDI')),
            _s(r.get(lot_col), 10),
            _s(r.get(result_col), 1),
            _s(r.get('AP'), 10),
            _num(r.get('CBESP')),
            _s(r.get('MAT'), 5),
            None,
        ))

    inserted, errors = bulk_upsert(_REPORT_SQL, rows, CHUNK, progress_cb)
    return {"inserted_updated": inserted, "errors": len(errors), "error_samples": errors[:3]}


def _s(v, maxlen=None):
    if v is None: return None
    s = str(v).strip()
    s = ''.join(c for c in s if ord(c) >= 32)
    return s[:maxlen] if maxlen else s or None


def _num(v):
    if v is None: return None
    try: return float(v) if abs(float(v)) < 1e10 else None
    except: return None


def _clean_iso(v):
    if not v: return None
    s = str(v).strip()
    s = ''.join(c for c in s if ord(c) >= 32)
    # Remove prefixo lixo (char antes de 4710/4730/6100)
    for prefix in ('4710', '4730', '6100', 'B065'):
        idx = s.find(prefix)
        if idx > 0:
            s = s[idx:]
            break
    return s[:30] or None


_INSP_SQL = """
INSERT INTO inspectors (project_id, badge, quali_code, name, company,
  dt_entry, dt_exit, dt_validity, certifier, method)
VALUES %s
ON CONFLICT (project_id, quali_code) DO UPDATE SET
  name      = COALESCE(EXCLUDED.name, inspectors.name),
  company   = COALESCE(EXCLUDED.company, inspectors.company),
  certifier = COALESCE(EXCLUDED.certifier, inspectors.certifier)
"""

_REPORT_SQL = """
INSERT INTO inspection_reports (project_id, report_type, report_num,
  isometrico, spool, junta, diameter_mm, lot_ref, result, inspector,
  thickness, material, report_date)
VALUES %s
ON CONFLICT (project_id, report_type, isometrico, spool, junta, report_num)
DO UPDATE SET result = COALESCE(EXCLUDED.result, inspection_reports.result)
"""
