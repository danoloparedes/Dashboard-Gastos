import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sync.db import get_connection, init_schema, upsert_transaction, delete_missing_transactions
import api_server
import sync_google_sheet


class TransactionSyncTests(unittest.TestCase):
  def test_manual_create_edit_delete(self):
    with tempfile.TemporaryDirectory() as directory, patch.object(api_server, 'DB_PATH', str(Path(directory) / 'manual.db')):
      row = dict(fecha='2026-10-25', descripcion='Mercado', clasificacion='Comida', tipo='Necesidad', abono=0, gasto=2000)
      identifier = api_server.mutate_transaction('POST', row)
      self.assertEqual(api_server.query_transactions()[0]['id'], identifier)
      self.assertEqual(api_server.mutate_transaction('PUT', {**row, 'id': identifier, 'descripcion': 'Verduras'}), identifier)
      self.assertEqual(api_server.query_transactions()[0]['descripcion'], 'Verduras')
      self.assertEqual(api_server.mutate_transaction('DELETE', {'id': identifier}), identifier)
      self.assertEqual(api_server.query_transactions(), [])
      self.assertIsNone(api_server.mutate_transaction('DELETE', {'id': identifier}))
      for invalid in ({**row, 'fecha': '2026-02-30'}, {**row, 'abono': 50}, {**row, 'gasto': -1}):
        with self.assertRaises(ValueError):
          api_server.mutate_transaction('POST', invalid)

  def test_dashboard_edits_and_deletions_survive_sheet_sync(self):
    with tempfile.TemporaryDirectory() as directory:
      conn = get_connection(str(Path(directory) / 'test.db'))
      try:
        init_schema(conn, str(Path(__file__).parent / 'sync' / 'schema.sql'))
        row = dict(external_id='Gastos:2', fecha='2026-10-25', descripcion='Original', clasificacion='Comida', tipo='Necesidad', abono=0, gasto=100)
        upsert_transaction(conn, **row)
        conn.execute('UPDATE transactions SET descripcion=? WHERE external_id=?', ('Corregido', 'Gastos:2'))
        conn.execute('INSERT INTO sheet_protections VALUES (?)', ('Gastos:2',))
        upsert_transaction(conn, **row)
        self.assertEqual(conn.execute('SELECT descripcion FROM transactions').fetchone()[0], 'Corregido')
        delete_missing_transactions(conn, worksheet_name='Gastos', current_external_ids=set())
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 1)
        conn.execute('DELETE FROM transactions WHERE external_id=?', ('Gastos:2',))
        upsert_transaction(conn, **row)
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0], 0)
      finally:
        conn.close()

  def test_invalid_sheet_row_preserves_existing_data(self):
    with tempfile.TemporaryDirectory() as directory:
      db_path = str(Path(directory) / 'test.db')
      schema_path = str(Path(__file__).parent / 'sync' / 'schema.sql')
      conn = get_connection(db_path)
      init_schema(conn, schema_path)
      row = dict(external_id='Gastos:2', fecha='2026-10-25', descripcion='Conservar', clasificacion='Comida', tipo='Necesidad', abono=0, gasto=100)
      upsert_transaction(conn, **row)
      conn.commit()
      conn.close()
      record = dict(fecha='31/02/2026', descripcion='Mala fecha', clasificacion='Comida', tipo='Necesidad', abono='0', gasto='200')
      with patch.object(sync_google_sheet, 'load_rows', return_value=[record]):
        result = sync_google_sheet.run_sync(db_path, schema_path, 'spreadsheet', 'Gastos', 'unused')
      self.assertEqual(result['skipped'], 1)
      conn = get_connection(db_path)
      self.assertEqual(conn.execute('SELECT descripcion FROM transactions').fetchone()[0], 'Conservar')
      conn.close()

  def test_invalid_headers_do_not_purge_sql(self):
    with tempfile.TemporaryDirectory() as directory:
      db_path = str(Path(directory) / 'test.db')
      schema_path = str(Path(__file__).parent / 'sync' / 'schema.sql')
      with patch.object(sync_google_sheet, 'load_rows', return_value=[{'fecha': '2026-10-25'}]):
        with self.assertRaisesRegex(ValueError, 'La hoja debe tener'):
          sync_google_sheet.run_sync(db_path, schema_path, 'spreadsheet', 'Gastos', 'unused')
      self.assertFalse(Path(db_path).exists())


if __name__ == '__main__':
  unittest.main()
