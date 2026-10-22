"""Configuração local. Variáveis de ambiente e arquivo .env opcional."""

import os
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

ADMIN_EMAIL = "marina.costa@lume.demo"
SELLER_EMAIL = "ricardo.nunes@lume.demo"
CONSULTOR_EMAIL = "camila.duarte@lume.demo"
ADMIN_NOME = "Marina Costa"
SELLER_NOME = "Ricardo Nunes"
CONSULTOR_NOME = "Camila Duarte"
SENHA_ADMIN_PADRAO = "Lume-Demo-2026"
SENHA_VENDEDOR_PADRAO = "Lume-Venda-2026"
SENHA_CONSULTOR_PADRAO = "Lume-Consulta-2026"
SLUG_PUBLICO = "lume"


def carregar_env(caminho=None):
    arquivo = Path(caminho or RAIZ / ".env")
    if not arquivo.is_file():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        chave, valor = texto.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        if chave and chave not in os.environ:
            os.environ[chave] = valor


@dataclass
class Config:
    host: str
    port: int
    db_path: Path
    ai_key: str
    ai_base: str
    ai_model: str
    senha_admin: str
    senha_vendedor: str
    limite_login: int = 8
    limite_consultor: int = 30
    limite_formulario: int = 10
    janela_segundos: int = 600
    uploads: Path = None
    senha_consultor: str = SENHA_CONSULTOR_PADRAO
    ai_provider: str = "gemini"

    def __post_init__(self):
        if self.uploads is None:
            self.uploads = self.db_path.parent / "uploads"


def _chave_ia():
    for nome in ("SOCIALFLOW_AI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        valor = (os.environ.get(nome) or "").strip()
        if valor:
            return valor
    return ""


def configuracao_de_ambiente():
    carregar_env()
    db = os.environ.get("SOCIALFLOW_DB", "data/socialflow.sqlite")
    caminho = Path(db)
    if not caminho.is_absolute():
        caminho = RAIZ / caminho
    provedor = (os.environ.get("SOCIALFLOW_AI_PROVIDER") or "gemini").strip().lower()
    if provedor not in {"gemini", "openai"}:
        provedor = "gemini"
    padrao_base = (
        "https://generativelanguage.googleapis.com/v1beta"
        if provedor == "gemini"
        else "https://api.openai.com/v1/chat/completions"
    )
    padrao_modelo = "gemini-3.8-flash" if provedor == "gemini" else "gpt-4o-mini"
    return Config(
        host=os.environ.get("SOCIALFLOW_HOST", "127.0.0.1"),
        port=int(os.environ.get("SOCIALFLOW_PORT", "8080")),
        db_path=caminho,
        ai_key=_chave_ia(),
        ai_base=os.environ.get("SOCIALFLOW_AI_BASE_URL", padrao_base).strip(),
        ai_model=os.environ.get("SOCIALFLOW_AI_MODEL", padrao_modelo).strip(),
        senha_admin=os.environ.get("SOCIALFLOW_ADMIN_PASSWORD", SENHA_ADMIN_PADRAO),
        senha_vendedor=os.environ.get("SOCIALFLOW_SELLER_PASSWORD", SENHA_VENDEDOR_PADRAO),
        senha_consultor=os.environ.get("SOCIALFLOW_CONSULTOR_PASSWORD", SENHA_CONSULTOR_PADRAO),
        ai_provider=provedor,
    )
