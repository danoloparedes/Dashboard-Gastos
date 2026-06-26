from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


def resolve_db_path(raw_path: str | None = None) -> Path:
  base_dir = Path(__file__).resolve().parents[1]
  load_dotenv(base_dir / '.env')

  raw = raw_path or os.getenv('SQLITE_DB_PATH', './data/gastos.db')
  path = Path(raw)
  if not path.is_absolute():
    path = (base_dir / path).resolve()
  return path


def main() -> None:
  parser = argparse.ArgumentParser(description='Inspect SQLite database used by dashboard')
  parser.add_argument('--db-path', default=None, help='Optional custom path to a SQLite file')
  args = parser.parse_args()

  db_path = resolve_db_path(args.db_path)
  print(f'DB path: {db_path}')

  if not db_path.exists():
    print('DB file does not exist yet.')
    return

  conn = sqlite3.connect(db_path)
  conn.row_factory = sqlite3.Row

  tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
  ).fetchall()

  if not tables:
    print('No tables found.')
    conn.close()
    return

  print('Tables:')
  for row in tables:
    table_name = row['name']
    total_row = conn.execute(f'SELECT COUNT(*) AS total FROM "{table_name}"').fetchone()
    print(f"- {table_name} (rows={int(total_row['total'])})")

  if any(row['name'] == 'transactions' for row in tables):
    total_row = conn.execute('SELECT COUNT(*) AS total FROM transactions').fetchone()
    print(f"transactions count: {int(total_row['total'])}")

    sample = conn.execute(
      """
      SELECT fecha, descripcion, clasificacion, tipo, abono, gasto
      FROM transactions
      ORDER BY fecha DESC, id DESC
      LIMIT 15
      """
    ).fetchall()

    print('Last rows (max 15):')
    for row in sample:
      print(
        f"{row['fecha']} | {row['descripcion']} | {row['clasificacion']} | {row['tipo']} | "
        f"abono={int(row['abono'] or 0)} | gasto={int(row['gasto'] or 0)}"
      )

  if any(row['name'] == 'gastos' for row in tables):
    sample = conn.execute(
      """
      SELECT fecha, descripcion, clasificacion, tipo, abono, gasto
      FROM gastos
      ORDER BY id DESC
      LIMIT 10
      """
    ).fetchall()

    print('Last rows from gastos (max 10):')
    for row in sample:
      print(
        f"{row['fecha']} | {row['descripcion']} | {row['clasificacion']} | {row['tipo']} | "
        f"abono={int(row['abono'] or 0)} | gasto={int(row['gasto'] or 0)}"
      )

  conn.close()


if __name__ == '__main__':
  main()
