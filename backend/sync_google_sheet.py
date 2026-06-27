from __future__ import annotations

import argparse
import os
import unicodedata
from datetime import datetime
from pathlib import Path

import gspread
from dotenv import load_dotenv

try:
    from db import count_transactions, delete_missing_transactions, get_connection, init_schema, upsert_transaction
except ModuleNotFoundError:
    from sync.db import count_transactions, delete_missing_transactions, get_connection, init_schema, upsert_transaction


HEADER_MAP = {
    "fecha": "fecha",
    "descripcion": "descripcion",
    "descripsion": "descripcion",
    "descripcion": "descripcion",
    "clasificacion": "clasificacion",
    "classificacion": "clasificacion",
    "tipo": "tipo",
    "abono": "abono",
    "gasto": "gasto",
}


def normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = "".join(ch for ch in value if ch.isalnum())
    return value


def normalize_headers(row: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_key, raw_value in row.items():
        if raw_key is None:
            continue
        normalized = normalize_text(str(raw_key))
        canonical = HEADER_MAP.get(normalized)
        if canonical:
            out[canonical] = str(raw_value or "").strip()
    return out


def parse_date(value: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError("Fecha vacia")

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(f"Formato de fecha no soportado: {text}")


def parse_money(value: str) -> int:
    text = (value or "").strip()
    if not text:
        return 0

    cleaned = text.replace("$", "").replace(" ", "")

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(".", "").replace(",", "")

    try:
        return int(round(float(cleaned)))
    except ValueError:
        return 0


def load_rows(spreadsheet_id: str, worksheet_name: str, credentials_file: str) -> list[dict[str, str]]:
    client = gspread.service_account(filename=credentials_file)
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    return worksheet.get_all_records(default_blank="")


def run_sync(db_path: str, schema_path: str, spreadsheet_id: str, worksheet_name: str, credentials_file: str) -> dict:
    records = load_rows(spreadsheet_id, worksheet_name, credentials_file)

    conn = get_connection(db_path)
    init_schema(conn, schema_path)

    imported = 0
    skipped = 0
    current_external_ids: set[str] = set()

    for index, record in enumerate(records, start=2):
        row = normalize_headers(record)

        required = ["fecha", "descripcion", "clasificacion", "tipo", "abono", "gasto"]
        if any(key not in row for key in required):
            skipped += 1
            continue

        try:
            fecha = parse_date(row["fecha"])
        except ValueError:
            skipped += 1
            continue

        descripcion = row["descripcion"].strip() or "Sin descripcion"
        clasificacion = row["clasificacion"].strip()
        tipo = row["tipo"].strip()
        abono = parse_money(row["abono"])
        gasto = parse_money(row["gasto"])

        external_id = f"{worksheet_name}:{index}"
        current_external_ids.add(external_id)

        upsert_transaction(
            conn,
            external_id=external_id,
            fecha=fecha,
            descripcion=descripcion,
            clasificacion=clasificacion,
            tipo=tipo,
            abono=abono,
            gasto=gasto,
        )
        imported += 1

    deleted = delete_missing_transactions(
        conn,
        worksheet_name=worksheet_name,
        current_external_ids=current_external_ids,
    )

    conn.commit()
    total = count_transactions(conn)
    conn.close()

    print(f"Filas procesadas: {len(records)}")
    print(f"Filas importadas/actualizadas: {imported}")
    print(f"Filas omitidas: {skipped}")
    print(f"Filas eliminadas en BD (ya no existen en Sheets): {deleted}")
    print(f"Total en BD: {total}")

    return {
        "processed": len(records),
        "imported": imported,
        "skipped": skipped,
        "deleted": deleted,
        "total": total,
    }


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    if (script_dir / ".env").exists():
        project_root = script_dir
    elif (script_dir.parent / ".env").exists():
        project_root = script_dir.parent
    else:
        project_root = script_dir

    load_dotenv(project_root / ".env", override=True)

    parser = argparse.ArgumentParser(description="Sincroniza Google Sheets a SQLite")
    parser.add_argument("--db-path", default=os.getenv("SQLITE_DB_PATH", "./data/gastos.db"))
    parser.add_argument("--spreadsheet-id", default=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", ""))
    parser.add_argument("--worksheet", default=os.getenv("GOOGLE_SHEETS_WORKSHEET", "Gastos"))
    parser.add_argument("--credentials-file", default=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./service-account.json"))
    args = parser.parse_args()

    if not args.spreadsheet_id:
        raise SystemExit("Falta GOOGLE_SHEETS_SPREADSHEET_ID")

    credentials_path = Path(args.credentials_file)
    if not credentials_path.is_absolute():
        credentials_path = (project_root / credentials_path).resolve()

    if not credentials_path.exists():
        alt_path = (project_root / "sync" / "service-account.json").resolve()
        if alt_path.exists():
            credentials_path = alt_path

    if not credentials_path.exists():
        raise SystemExit(f"No existe archivo de credenciales: {credentials_path}")

    db_path = Path(args.db_path)
    if not db_path.is_absolute():
        db_path = (project_root / db_path).resolve()

    schema_path = (project_root / "sync" / "schema.sql").resolve()

    run_sync(
        db_path=str(db_path),
        schema_path=str(schema_path),
        spreadsheet_id=args.spreadsheet_id,
        worksheet_name=args.worksheet,
        credentials_file=str(credentials_path),
    )


if __name__ == "__main__":
    main()
