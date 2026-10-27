"""Senha, sessão, CSRF, limite de tentativas e imagem."""

import base64
import hashlib
import secrets
import threading
import time

from socialflow.erros import ErroHttp

_LIMITE = threading.Lock()
_EVENTOS = {}
_DUMMY = None


def hash_senha(senha):
    sal = secrets.token_bytes(16)
    n, r, p = 2**14, 8, 1
    derivado = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, dklen=32)
    return f"scrypt${n}${r}${p}${sal.hex()}${derivado.hex()}"


def _dummy():
    global _DUMMY
    if _DUMMY is None:
        _DUMMY = hash_senha("placeholder-local-nao-usado")
    return _DUMMY


def verificar_senha(senha, armazenada):
    referencia = armazenada or _dummy()
    try:
        esquema, n, r, p, sal_hex, hash_hex = referencia.split("$")
        if esquema != "scrypt":
            return False
        calculado = hashlib.scrypt(
            senha.encode("utf-8"),
            salt=bytes.fromhex(sal_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        ok = secrets.compare_digest(calculado, bytes.fromhex(hash_hex))
    except (ValueError, TypeError):
        ok = False
    if not armazenada:
        return False
    return ok


def novo_token():
    return secrets.token_urlsafe(32)


def comparar(esperado, recebido):
    if not esperado or not recebido:
        return False
    return secrets.compare_digest(str(esperado), str(recebido))


def reiniciar_limites():
    with _LIMITE:
        _EVENTOS.clear()


def limitar(chave, maximo, janela_segundos):
    agora_mono = time.monotonic()
    with _LIMITE:
        eventos = [t for t in _EVENTOS.get(chave, []) if agora_mono - t < janela_segundos]
        if len(eventos) >= maximo:
            _EVENTOS[chave] = eventos
            raise ErroHttp(429, "Muitas tentativas. Espere um pouco e tente novamente.")
        eventos.append(agora_mono)
        _EVENTOS[chave] = eventos


def decodificar_imagem(conteudo_b64):
    if not isinstance(conteudo_b64, str) or not conteudo_b64.strip():
        raise ErroHttp(400, "Imagem inválida.", {"imagem": "Arquivo ausente."})
    try:
        bruto = base64.b64decode(conteudo_b64, validate=True)
    except (ValueError, TypeError):
        raise ErroHttp(400, "Imagem inválida.", {"imagem": "Não foi possível ler o arquivo."})
    if len(bruto) > 1_500_000:
        raise ErroHttp(400, "A imagem pode ter no máximo 1,5 MB.", {"imagem": "Arquivo grande demais."})
    if bruto.startswith(b"\x89PNG\r\n\x1a\n"):
        return bruto, "png"
    if bruto.startswith(b"\xff\xd8\xff"):
        return bruto, "jpg"
    if len(bruto) >= 12 and bruto.startswith(b"RIFF") and bruto[8:12] == b"WEBP":
        return bruto, "webp"
    raise ErroHttp(400, "Envie uma imagem PNG, JPEG ou WebP.", {"imagem": "Tipo não aceito."})


def cookie(nome, valor, max_age, seguro=False):
    marca = f"{nome}={valor}; HttpOnly; SameSite=Lax; Path=/; Max-Age={max_age}"
    if seguro:
        marca += "; Secure"
    return marca
