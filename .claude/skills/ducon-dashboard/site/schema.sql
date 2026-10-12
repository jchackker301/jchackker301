CREATE TABLE IF NOT EXISTS records (
  table_name TEXT NOT NULL,
  id TEXT NOT NULL,
  data TEXT NOT NULL,
  updated_by TEXT,
  updated_at TEXT,
  PRIMARY KEY (table_name, id)
);
