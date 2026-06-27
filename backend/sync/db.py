from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: str) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()


def upsert_transaction(
    conn: sqlite3.Connection,
    *,
    external_id: str,
    fecha: str,
    descripcion: str,
    clasificacion: str,
    tipo: str,
    abono: int,
    gasto: int,
) -> None:
    conn.execute(
        """
        INSERT INTO transactions (
            external_id, fecha, descripcion, clasificacion, tipo, abono, gasto
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            fecha = excluded.fecha,
            descripcion = excluded.descripcion,
            clasificacion = excluded.clasificacion,
            tipo = excluded.tipo,
            abono = excluded.abono,
            gasto = excluded.gasto,
            updated_at = CURRENT_TIMESTAMP
        """,
        (external_id, fecha, descripcion, clasificacion, tipo, abono, gasto),
    )


def delete_missing_transactions(
    conn: sqlite3.Connection,
    *,
    worksheet_name: str,
    current_external_ids: set[str],
) -> int:
    prefix = f"{worksheet_name}:%"

    if not current_external_ids:
        cursor = conn.execute(
            "DELETE FROM transactions WHERE external_id LIKE ?",
            (prefix,),
        )
        return int(cursor.rowcount or 0)

    placeholders = ", ".join("?" for _ in current_external_ids)
    params = [prefix, *sorted(current_external_ids)]

    cursor = conn.execute(
        f"""
        DELETE FROM transactions
        WHERE external_id LIKE ?
          AND external_id NOT IN ({placeholders})
        """,
        params,
    )
    return int(cursor.rowcount or 0)


def count_transactions(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()
    if row is None:
        return 0
    return int(row["total"])
