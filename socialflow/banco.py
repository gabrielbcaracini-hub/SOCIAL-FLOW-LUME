"""Persistência local: SQLite nos testes e MariaDB/MySQL do XAMPP na loja."""

import re
import sqlite3
from pathlib import Path

from socialflow.config import RAIZ

MIGRACOES = RAIZ / "migrations"
TABELAS_COPIA = (
    "organizations",
    "users",
    "business_settings",
    "vehicles",
    "vehicle_images",
    "leads",
    "appointments",
    "chat_sessions",
    "chat_messages",
    "auth_sessions",
    "client_contexts",
    "audit_log",
)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None
    DictCursor = None

Integridade = sqlite3.IntegrityError
ErroBanco = sqlite3.Error
if pymysql is not None:
    Integridade = (sqlite3.IntegrityError, pymysql.err.IntegrityError)
    ErroBanco = (sqlite3.Error, pymysql.Error)


class CursorMysql:
    def __init__(self, cursor):
        self._cursor = cursor
        self.rowcount = getattr(cursor, "rowcount", -1)
        self.lastrowid = getattr(cursor, "lastrowid", 0)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return list(self._cursor.fetchall())

    def __iter__(self):
        return iter(self._cursor)


class ConexaoMysql:
    driver = "mysql"

    def __init__(self, bruto):
        self._bruto = bruto
        self._bruto.autocommit(True)

    def execute(self, sql, params=()):
        texto = sql.strip()
        upper = texto.upper()
        if upper.startswith("PRAGMA"):
            return CursorMysql(self._bruto.cursor())
        if upper.startswith("BEGIN"):
            self._bruto.autocommit(False)
            cursor = self._bruto.cursor()
            cursor.execute("START TRANSACTION")
            return CursorMysql(cursor)
        if upper == "COMMIT":
            self._bruto.commit()
            self._bruto.autocommit(True)
            return CursorMysql(self._bruto.cursor())
        if upper == "ROLLBACK":
            self._bruto.rollback()
            self._bruto.autocommit(True)
            return CursorMysql(self._bruto.cursor())
        cursor = self._bruto.cursor()
        cursor.execute(texto.replace("?", "%s"), params or ())
        return CursorMysql(cursor)

    def executescript(self, texto):
        _aplicar_script(self, texto)
        return self

    def close(self):
        self._bruto.close()


def _aplicar_script(conn, texto):
    if _driver(conn) == "sqlite":
        conn.executescript(texto)
        return
    for pedaco in texto.split(";"):
        sql = pedaco.strip()
        if not sql or sql.upper().startswith("PRAGMA"):
            continue
        conn.execute(sql)


def _driver(conn):
    return "mysql" if isinstance(conn, ConexaoMysql) else "sqlite"


def _conectar_sqlite(caminho):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _exigir_pymysql():
    if pymysql is None:
        raise RuntimeError(
            "Para usar o MySQL do XAMPP instale o driver com: python -m pip install pymysql"
        )


def _nome_banco(nome):
    if not re.fullmatch(r"[A-Za-z0-9_]+", nome or ""):
        raise RuntimeError("Nome de banco MySQL inválido.")
    return nome


def garantir_database(config):
    _exigir_pymysql()
    nome = _nome_banco(config.mysql_database)
    bruto = pymysql.connect(
        host=config.mysql_host,
        port=int(config.mysql_port),
        user=config.mysql_user,
        password=config.mysql_password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        cursor = bruto.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" % nome
        )
    finally:
        bruto.close()


def _conectar_mysql(config):
    _exigir_pymysql()
    garantir_database(config)
    bruto = pymysql.connect(
        host=config.mysql_host,
        port=int(config.mysql_port),
        user=config.mysql_user,
        password=config.mysql_password,
        database=_nome_banco(config.mysql_database),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    return ConexaoMysql(bruto)


def conectar(destino):
    if getattr(destino, "db_driver", "sqlite") == "mysql":
        return _conectar_mysql(destino)
    caminho = destino.db_path if hasattr(destino, "db_path") else destino
    return _conectar_sqlite(caminho)


def _pasta_migracoes(conn):
    if _driver(conn) == "mysql":
        return MIGRACOES / "mysql"
    return MIGRACOES


def migrar(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id VARCHAR(80) PRIMARY KEY,
            applied_at VARCHAR(40) NOT NULL
        )
        """
        if _driver(conn) == "mysql"
        else """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    from socialflow.tempo import iso

    pasta = _pasta_migracoes(conn)
    for arquivo in sorted(pasta.glob("*.sql")):
        ja = conn.execute(
            "SELECT 1 AS n FROM schema_migrations WHERE id = ?", (arquivo.name,)
        ).fetchone()
        if ja:
            continue
        _aplicar_script(conn, arquivo.read_text(encoding="utf-8"))
        if _driver(conn) == "sqlite":
            conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, ?)",
            (arquivo.name, iso()),
        )


def importar_sqlite_se_vazio(conn, config):
    if _driver(conn) != "mysql":
        return False
    destino = conn.execute("SELECT COUNT(*) AS n FROM organizations").fetchone()["n"]
    if destino:
        return False
    caminho = Path(config.db_path)
    if not caminho.is_file():
        return False
    origem = _conectar_sqlite(caminho)
    try:
        origem_n = origem.execute("SELECT COUNT(*) AS n FROM organizations").fetchone()["n"]
        if not origem_n:
            return False
        conn.execute("SET FOREIGN_KEY_CHECKS=0")
        try:
            for tabela in TABELAS_COPIA:
                colunas = [row[1] for row in origem.execute("PRAGMA table_info(%s)" % tabela)]
                if not colunas:
                    continue
                linhas = origem.execute("SELECT * FROM %s" % tabela).fetchall()
                if not linhas:
                    continue
                marcas = ",".join("?" for _ in colunas)
                sql = "INSERT INTO %s (%s) VALUES (%s)" % (tabela, ",".join(colunas), marcas)
                for linha in linhas:
                    conn.execute(sql, tuple(linha[coluna] for coluna in colunas))
        finally:
            conn.execute("SET FOREIGN_KEY_CHECKS=1")
        return True
    finally:
        origem.close()


def garantir_origem_contato(conn):
    if _driver(conn) != "sqlite":
        return
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
