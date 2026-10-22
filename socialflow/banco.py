"""SQLite com migrações versionadas e chaves estrangeiras ligadas."""

import sqlite3
from pathlib import Path

from socialflow.config import RAIZ

MIGRACOES = RAIZ / "migrations"


def conectar(caminho):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrar(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    for arquivo in sorted(MIGRACOES.glob("*.sql")):
        ja = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE id = ?", (arquivo.name,)
        ).fetchone()
        if ja:
            continue
        conn.executescript(arquivo.read_text(encoding="utf-8"))
        conn.execute("PRAGMA foreign_keys = ON")
        from socialflow.tempo import iso

        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, ?)",
            (arquivo.name, iso()),
        )


def garantir_origem_contato(conn):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'leads'"
    ).fetchone()
    if not row or "contato" in (row[0] or ""):
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            CREATE TABLE leads_nova (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL REFERENCES organizations(id),
                vehicle_id TEXT REFERENCES vehicles(id) ON DELETE SET NULL,
                origin TEXT NOT NULL CHECK (origin IN ('vitrine', 'detalhe', 'assistente', 'visita', 'contato')),
                contact_name TEXT NOT NULL,
                contact_phone TEXT NOT NULL DEFAULT '',
                contact_email TEXT NOT NULL DEFAULT '',
                consent INTEGER NOT NULL CHECK (consent = 1),
                preferences_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL CHECK (status IN ('novo', 'contatado', 'negociacao', 'ganho', 'perdido')),
                notes TEXT NOT NULL DEFAULT '',
                assignee_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO leads_nova (
                id, organization_id, vehicle_id, origin, contact_name, contact_phone, contact_email,
                consent, preferences_json, status, notes, assignee_id, summary, created_at, updated_at
            )
            SELECT
                id, organization_id, vehicle_id, origin, contact_name, contact_phone, contact_email,
                consent, preferences_json, status, notes, assignee_id, summary, created_at, updated_at
            FROM leads
            """
        )
        conn.execute("DROP TABLE leads")
        conn.execute("ALTER TABLE leads_nova RENAME TO leads")
        conn.execute("CREATE INDEX idx_leads_org_status ON leads(organization_id, status)")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Integridade do banco após ajustar a origem do contato.")
