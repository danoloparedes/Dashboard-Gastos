CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT NOT NULL UNIQUE,
  fecha TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  clasificacion TEXT,
  tipo TEXT,
  abono INTEGER NOT NULL DEFAULT 0,
  gasto INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_fecha ON transactions(fecha);
CREATE INDEX IF NOT EXISTS idx_transactions_tipo ON transactions(tipo);
CREATE INDEX IF NOT EXISTS idx_transactions_clasificacion ON transactions(clasificacion);
