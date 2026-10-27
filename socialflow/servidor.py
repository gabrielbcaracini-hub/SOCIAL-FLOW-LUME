"""Servidor HTTP local. HTML, CSS e JavaScript ficam no projeto; a regra fica aqui."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from socialflow import servicos
from socialflow.config import RAIZ
from socialflow.erros import ErroHttp

PAGINAS = {
    "/": "index.html",
    "/index.html": "index.html",
    "/veiculo": "veiculo.html",
    "/veiculo.html": "veiculo.html",
    "/painel": "painel.html",
    "/painel.html": "painel.html",
    "/privacidade": "privacidade.html",
    "/privacidade.html": "privacidade.html",
}

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".mp4": "video/mp4",
}

HTML_404 = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Página não encontrada · SocialFlow Auto</title>
  <link rel="stylesheet" href="/css/socialflow.css">
</head>
<body>
  <main id="conteudo" class="leitura">
    <h1>Página não encontrada</h1>
    <p>Esse endereço não faz parte da Lume Veículos.</p>
    <p><a href="/">Voltar à vitrine</a></p>
  </main>
</body>
</html>
""".encode("utf-8")


class Pedido:
    def __init__(self, config, metodo, caminho, query, corpo, cookies, ip, csrf):
        self.config = config
        self.metodo = metodo
        self.caminho = caminho
        self.query = query
        self.corpo = corpo
        self.cookies = cookies
        self.ip = ip
        self.csrf = csrf


def _cookies(cabecalho):
    saida = {}
    if not cabecalho:
        return saida
    for parte in cabecalho.split(";"):
        if "=" in parte:
            chave, valor = parte.split("=", 1)
            saida[chave.strip()] = valor.strip()
    return saida


def _intervalo_bytes(cabecalho, total):
    if not cabecalho or total <= 0 or not cabecalho.startswith("bytes="):
        return None
    pedaco = cabecalho[6:].split(",", 1)[0].strip()
    if "-" not in pedaco:
        return None
    inicio_txt, fim_txt = pedaco.split("-", 1)
    try:
        if inicio_txt == "" and fim_txt:
            tamanho = int(fim_txt)
            inicio = max(0, total - tamanho)
            return inicio, total - 1
        inicio = int(inicio_txt) if inicio_txt else 0
        fim = int(fim_txt) if fim_txt else total - 1
    except ValueError:
        return None
    if inicio >= total:
        return None
    inicio = max(0, inicio)
    fim = min(total - 1, max(inicio, fim))
    return inicio, fim


def _arquivo_estatico(caminho):
    if not caminho.startswith(("/css/", "/js/", "/assets/")):
        raise ErroHttp(404, "Não encontrado.")
    if ".." in caminho or "\\" in caminho:
        raise ErroHttp(404, "Não encontrado.")
    relativo = caminho.lstrip("/")
    base = RAIZ.resolve()
    alvo = (base / relativo).resolve()
    alvo.relative_to(base)
    if relativo.split("/")[0] not in {"css", "js", "assets"}:
        raise ErroHttp(404, "Não encontrado.")
    if alvo.suffix.lower() not in TIPOS or not alvo.is_file():
        raise ErroHttp(404, "Não encontrado.")
    return alvo


def bytes_estaticos(caminho):
    if caminho in PAGINAS:
        alvo = RAIZ / PAGINAS[caminho]
        if not alvo.is_file():
            raise ErroHttp(404, "Não encontrado.")
        return alvo.read_bytes(), "text/html; charset=utf-8"
    alvo = _arquivo_estatico(caminho)
    return alvo.read_bytes(), TIPOS[alvo.suffix.lower()]


def _despachar(pedido):
    metodo, caminho = pedido.metodo, pedido.caminho
    if metodo == "GET" and caminho == "/api/saude":
        return {"ok": True}, [], 200
    if metodo == "GET" and caminho == "/api/contexto":
        payload, cookies = servicos.contexto(pedido)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/entrar":
        payload, cookies = servicos.entrar(pedido, pedido.corpo)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/sair":
        payload, cookies = servicos.sair(pedido)
        return payload, cookies, 200
    if metodo == "GET" and caminho == "/api/publico/veiculos":
        payload, cookies = servicos.veiculos_publicos(pedido)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/publico/leads":
        payload, cookies = servicos.criar_lead(pedido, pedido.corpo)
        return payload, cookies, 201
    if metodo == "GET" and caminho == "/api/publico/consultores":
        payload, cookies = servicos.consultores_publicos(pedido)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/publico/contatos":
        payload, cookies = servicos.criar_contato(pedido, pedido.corpo)
        return payload, cookies, 201
    if metodo == "POST" and caminho == "/api/publico/agendamentos":
        payload, cookies = servicos.criar_agenda(pedido, pedido.corpo)
        return payload, cookies, 201
    if metodo == "POST" and caminho == "/api/publico/consultor":
        payload, cookies = servicos.consultor(pedido, pedido.corpo)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/publico/luna":
        payload, cookies = servicos.luna_assistente(pedido, pedido.corpo)
        return payload, cookies, 200
    if metodo == "GET" and caminho == "/api/admin/resumo":
        payload, cookies = servicos.resumo(pedido)
        return payload, cookies, 200
    if metodo == "GET" and caminho == "/api/admin/veiculos":
        payload, cookies = servicos.listar_veiculos_admin(pedido)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/admin/veiculos":
        payload, cookies = servicos.criar_veiculo(pedido, pedido.corpo)
        return payload, cookies, 201
    if metodo == "GET" and caminho == "/api/admin/leads":
        payload, cookies = servicos.listar_leads(pedido)
        return payload, cookies, 200
    if metodo == "GET" and caminho == "/api/admin/agendamentos":
        payload, cookies = servicos.listar_agenda(pedido)
        return payload, cookies, 200
    if metodo == "GET" and caminho == "/api/admin/configuracoes":
        payload, cookies = servicos.obter_config(pedido)
        return payload, cookies, 200
    if metodo == "PUT" and caminho == "/api/admin/configuracoes":
        payload, cookies = servicos.salvar_config(pedido, pedido.corpo)
        return payload, cookies, 200
    if metodo == "POST" and caminho == "/api/admin/restaurar-demonstracao":
        payload, cookies = servicos.restaurar(pedido)
        return payload, cookies, 200
    partes = caminho.strip("/").split("/")
    if len(partes) == 4 and partes[:3] == ["api", "publico", "veiculos"] and metodo == "GET":
        payload, cookies = servicos.veiculo_publico(pedido, partes[3])
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "publico", "consultor"] and metodo == "DELETE":
        payload, cookies = servicos.apagar_consultor(pedido, partes[3])
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "publico", "luna"] and metodo == "DELETE":
        payload, cookies = servicos.apagar_consultor(pedido, partes[3])
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "admin", "veiculos"] and metodo == "GET":
        with servicos._conexao(pedido) as conn:
            servicos._exigir_usuario(conn, pedido)
            usuario = servicos._usuario(conn, pedido.cookies)
            row = servicos._veiculo_org(conn, usuario["organization_id"], partes[3])
            payload = {"veiculo": servicos._serial_lista(conn, [dict(row)], publico=False)[0]}
        return payload, [], 200
    if len(partes) == 4 and partes[:3] == ["api", "admin", "veiculos"] and metodo == "PUT":
        payload, cookies = servicos.atualizar_veiculo(pedido, partes[3], pedido.corpo)
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "admin", "veiculos"] and metodo == "DELETE":
        payload, cookies = servicos.excluir_veiculo(pedido, partes[3])
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "admin", "leads"] and metodo == "PATCH":
        payload, cookies = servicos.atualizar_lead(pedido, partes[3], pedido.corpo)
        return payload, cookies, 200
    if len(partes) == 4 and partes[:3] == ["api", "admin", "leads"] and metodo == "DELETE":
        payload, cookies = servicos.excluir_lead(pedido, partes[3])
        return payload, cookies, 200
    if len(partes) == 5 and partes[:3] == ["api", "admin", "agendamentos"] and metodo == "POST":
        payload, cookies = servicos.transicao_agenda(pedido, partes[3], partes[4], pedido.corpo)
        return payload, cookies, 200
    if len(partes) == 2 and partes[0] == "midia" and metodo == "GET":
        return servicos.ler_midia(pedido, partes[1])
    raise ErroHttp(404, "Recurso não encontrado.")


CABECALHOS_PADRAO = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: blob:; media-src 'self'; "
        "style-src 'self'; script-src 'self'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def responder_api(pedido):
    try:
        if pedido.metodo == "GET" and pedido.caminho.startswith("/midia/"):
            partes = pedido.caminho.rstrip("/").split("/")
            identificador = partes[2] if len(partes) > 2 else ""
            conteudo, tipo = servicos.ler_midia(pedido, identificador)
            return 200, conteudo, tipo, []
        payload, cookies, status = _despachar(pedido)
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return status, corpo, "application/json; charset=utf-8", cookies
    except ErroHttp as erro:
        corpo = json.dumps({"erro": erro.mensagem, "campos": erro.campos}, ensure_ascii=False).encode("utf-8")
        return erro.status, corpo, "application/json; charset=utf-8", []
    except Exception:
        sys.stderr.write("erro interno\n")
        corpo = json.dumps({"erro": "Não foi possível concluir a operação."}, ensure_ascii=False).encode("utf-8")
        return 500, corpo, "application/json; charset=utf-8", []


def preparar_banco(config):
    from socialflow import banco, semear

    config.uploads.mkdir(parents=True, exist_ok=True)
    if config.db_driver == "sqlite":
        config.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = banco.conectar(config)
    try:
        banco.migrar(conn)
        if config.db_driver == "mysql":
            copiou = banco.importar_sqlite_se_vazio(conn, config)
            if copiou:
                sys.stdout.write(
                    "Banco do XAMPP recebeu os dados locais da loja (%s).\n" % config.mysql_database
                )
                sys.stdout.flush()
        else:
            banco.garantir_origem_contato(conn)
        semear.semear(conn, config.senha_admin, config.senha_vendedor, config.senha_consultor)
        semear.garantir_consultor(conn, config.senha_consultor)
        semear.garantir_estoque(conn)
        semear.aplicar_fotos(conn)
    finally:
        conn.close()


def fabrica(config):
    class Tratador(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, formato, *args):
            sys.stderr.write("%s %s\n" % (self.command, self.path.split("?", 1)[0]))

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
            try:
                partes = urlsplit(self.path)
                caminho = unquote(partes.path)
                if len(caminho) > 1 and caminho.endswith("/"):
                    caminho = caminho[:-1]
                if self.command == "GET" and caminho in PAGINAS:
                    self._arquivo(RAIZ / PAGINAS[caminho], "text/html; charset=utf-8")
                    return
                if self.command == "GET" and caminho.startswith(("/css/", "/js/", "/assets/")):
                    self._arquivo(_arquivo_estatico(caminho), TIPOS[(_arquivo_estatico(caminho)).suffix.lower()])
                    return
                corpo = self._ler_corpo(caminho)
                pedido = Pedido(
                    config, self.command, caminho,
                    parse_qs(partes.query, keep_blank_values=False),
                    corpo, _cookies(self.headers.get("Cookie")),
                    self.client_address[0], self.headers.get("X-CSRF-Token", ""),
                )
                status, conteudo, tipo, cookies = responder_api(pedido)
                self._bytes(status, conteudo, tipo, cookies)
            except ErroHttp as erro:
                corpo = json.dumps({"erro": erro.mensagem, "campos": erro.campos}, ensure_ascii=False).encode("utf-8")
                self._bytes(erro.status, corpo, "application/json; charset=utf-8")

        def _ler_corpo(self, caminho):
            if self.command == "GET":
                return {}
            try:
                tamanho = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                raise ErroHttp(400, "Cabeçalho inválido.")
            limite = 2_000_000 if caminho.startswith("/api/admin/veiculos") else 100_000
            if tamanho < 0 or tamanho > limite:
                raise ErroHttp(413, "Conteúdo grande demais.")
            bruto = self.rfile.read(tamanho) if tamanho else b""
            if not bruto:
                return {}
            try:
                dados = json.loads(bruto.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ErroHttp(400, "JSON inválido.")
            if not isinstance(dados, dict):
                raise ErroHttp(400, "O corpo precisa ser um objeto JSON.")
            return dados

        def _arquivo(self, caminho, tipo):
            if not caminho.is_file():
                self._bytes(404, HTML_404, "text/html; charset=utf-8")
                return
            bruto = caminho.read_bytes()
            extras = {}
            if tipo.startswith("video/"):
                extras["Accept-Ranges"] = "bytes"
                faixa = _intervalo_bytes(self.headers.get("Range"), len(bruto))
                if faixa:
                    inicio, fim = faixa
                    extras["Content-Range"] = "bytes %s-%s/%s" % (inicio, fim, len(bruto))
                    self._bytes(206, bruto[inicio:fim + 1], tipo, extras=extras)
                    return
            self._bytes(200, bruto, tipo, extras=extras)

        def _bytes(self, status, corpo, tipo, cookies=None, extras=None):
            try:
                self.send_response(status)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                for chave, valor in CABECALHOS_PADRAO.items():
                    self.send_header(chave, valor)
                self.send_header("Connection", "close")
                for chave, valor in (extras or {}).items():
                    self.send_header(chave, valor)
                for item in cookies or []:
                    self.send_header("Set-Cookie", item)
                self.end_headers()
                self.wfile.write(corpo)
            except (BrokenPipeError, ConnectionAbortedError):
                return

    return Tratador


def criar_servidor(config):
    preparar_banco(config)
    return ThreadingHTTPServer((config.host, config.port), fabrica(config))


def servir(config):
    try:
        httpd = criar_servidor(config)
    except OSError:
        sys.stderr.write("Não foi possível abrir a porta %s. Ela pode estar em uso.\n" % config.port)
        raise SystemExit(1)
    endereco = "http://%s:%s" % (config.host, httpd.server_address[1])
    sys.stdout.write("SocialFlow Auto em %s\n" % endereco)
    sys.stdout.write("Ambiente local. Nenhuma publicação externa foi feita.\n")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nServidor encerrado.\n")
    finally:
        httpd.server_close()
