"""Utilitários compartilhados pelos pipelines ETL."""

from datetime import date, timedelta
from typing import Any
import re
import pandas as pd


DELPHI_EPOCH = date(1899, 12, 30)
JULIAN_OFFSET = 1721425  # dias entre Julian Day 0 e ordinal Python


def delphi_date(value: Any) -> date | None:
    """Converte float/int Delphi (dias desde 30/12/1899) para date."""
    try:
        v = float(value)
        if v <= 0 or v == -32768:
            return None
        return DELPHI_EPOCH + timedelta(days=v)
    except (TypeError, ValueError):
        return None


def julian_date(value: Any) -> date | None:
    """Converte Julian Day Number (Paradox) para date."""
    try:
        v = int(value)
        if v <= 0:
            return None
        return date.fromordinal(v - JULIAN_OFFSET)
    except (TypeError, ValueError, OverflowError):
        return None


def safe_numeric(value: Any, sentinel: int = -32768) -> float | None:
    """Retorna None para valores nulos/sentinela Paradox."""
    try:
        v = float(value)
        return None if v == sentinel else v
    except (TypeError, ValueError):
        return None


def clean_str(value: Any, max_len: int = None) -> str | None:
    """Strip + None para strings vazias."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len] if max_len else s


def normalize_sger(raw: Any) -> str | None:
    """Extrai código numérico do campo sger (ex: '01 - NAO INICIADA' → '01')."""
    s = clean_str(raw)
    if not s:
        return None
    m = re.match(r'^(\d{2})', s)
    return m.group(1) if m else None


def split_spool_key(spool_key: Any) -> tuple[str, str] | tuple[None, None]:
    """Separa 'ISOM-001' em (isometrico, spool). Último segmento = spool."""
    s = clean_str(spool_key)
    if not s:
        return None, None
    parts = s.rsplit('-', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return s, None


def parse_diameter_in(value: Any) -> float | None:
    """Converte '1 1/2\"' ou '6' para float em polegadas."""
    s = clean_str(value)
    if not s:
        return None
    s = s.replace('"', '').strip()
    if ' ' in s:
        parts = s.split()
        try:
            whole = float(parts[0])
            if '/' in parts[1]:
                n, d = parts[1].split('/')
                return whole + float(n) / float(d)
        except (ValueError, IndexError):
            pass
    try:
        return float(s)
    except ValueError:
        return None


def in_to_mm(inches: float | None) -> float | None:
    return round(inches * 25.4, 2) if inches is not None else None
