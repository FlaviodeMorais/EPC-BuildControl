"""Helper de bulk insert via execute_values — conexão dedicada do engine."""

from psycopg2.extras import execute_values
from ..database import engine


def bulk_upsert(sql: str, records: list[tuple], chunk_size: int = 5000,
                progress_cb=None) -> tuple[int, list[str]]:
    """
    Insere records em chunks usando execute_values (1 round-trip por chunk).
    Retorna (inserted, errors).
    """
    if not records:
        return 0, []

    raw = engine.raw_connection()
    cur = raw.cursor()
    inserted = 0
    errors = []

    try:
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            try:
                execute_values(cur, sql, chunk, page_size=chunk_size)
                raw.commit()
                inserted += len(chunk)
            except Exception as e:
                raw.rollback()
                errors.append(f"chunk {i}: {str(e)[:300]}")
            if progress_cb:
                progress_cb(inserted)
    finally:
        cur.close()
        raw.close()

    return inserted, errors
