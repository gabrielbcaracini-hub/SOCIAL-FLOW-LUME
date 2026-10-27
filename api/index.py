"""Função serverless da Vercel. Reutiliza as regras de socialflow.servidor."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from socialflow.config import configuracao_de_ambiente
from socialflow.erros import ErroHttp
from socialflow.servidor import (
    CABECALHOS_PADRAO,
    Pedido,
    _cookies,
    bytes_estaticos,
    preparar_banco,
    responder_api,
)

_CONFIG = None


def _config():
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = configuracao_de_ambiente()
        try:
            preparar_banco(_CONFIG)
        except Exception:
            sys.stderr.write("aviso: banco não preparado neste arranque\n")
    return _CONFIG


def _caminho(handler):
    partes = urlsplit(handler.path)
    query = parse_qs(partes.query, keep_blank_values=False)
    bruto = (query.get("sf_path") or [None])[0]
    if not bruto:
        bruto = handler.headers.get("x-invoke-path") or partes.path
    caminho = unquote(bruto.split("?", 1)[0])
    if len(caminho) > 1 and caminho.endswith("/"):
        caminho = caminho[:-1]
    return caminho, query


def _corpo(handler, caminho):
    if handler.command == "GET":
        return {}
    try:
        tamanho = int(handler.headers.get("Content-Length", "0") or 0)
    except ValueError:
        raise ErroHttp(400, "Cabeçalho inválido.")
    limite = 2_000_000 if caminho.startswith("/api/admin/veiculos") else 100_000
    if tamanho < 0 or tamanho > limite:
        raise ErroHttp(413, "Conteúdo grande demais.")
    bruto = handler.rfile.read(tamanho) if tamanho else b""
    if not bruto:
        return {}
    try:
        dados = json.loads(bruto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ErroHttp(400, "JSON inválido.")
    if not isinstance(dados, dict):
        raise ErroHttp(400, "O corpo precisa ser um objeto JSON.")
    return dados


def _ip(handler):
    encaminhado = handler.headers.get("x-forwarded-for") or ""
    if encaminhado:
        return encaminhado.split(",")[0].strip()
    return "0.0.0.0"


class handler(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        return

    def do_GET(self):
        self._executar()

    def do_POST(self):
        self._executar()

    def do_PUT(self):
        self._executar()

    def do_PATCH(self):
        self._executar()

    def do_DELETE(self):
        self._executar()

    def _executar(self):
        config = _config()
        caminho, query = _caminho(self)
        if self.command == "GET" and not caminho.startswith("/api/") and not caminho.startswith("/midia/"):
            try:
                conteudo, tipo = bytes_estaticos(caminho if caminho != "" else "/")
                self._enviar(200, conteudo, tipo, [])
                return
            except ErroHttp:
                pass
        try:
            corpo = _corpo(self, caminho)
        except ErroHttp as erro:
            saida = json.dumps({"erro": erro.mensagem, "campos": erro.campos}, ensure_ascii=False).encode("utf-8")
            self._enviar(erro.status, saida, "application/json; charset=utf-8", [])
            return
        pedido = Pedido(
            config,
            self.command,
            caminho,
            query,
            corpo,
            _cookies(self.headers.get("Cookie")),
            _ip(self),
            self.headers.get("X-CSRF-Token", ""),
        )
        status, conteudo, tipo, cookies = responder_api(pedido)
        self._enviar(status, conteudo, tipo, cookies)

    def _enviar(self, status, corpo, tipo, cookies):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        for chave, valor in CABECALHOS_PADRAO.items():
            self.send_header(chave, valor)
        for item in cookies or []:
            self.send_header("Set-Cookie", item)
        self.end_headers()
        self.wfile.write(corpo)


# Mantém o módulo importável em testes sem disparar o handler.
os.environ.setdefault("SOCIALFLOW_VERCEL_HANDLER", "1")
