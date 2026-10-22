"""Validação de entrada. A interface pode ajudar; o servidor decide."""

import re
import unicodedata

from socialflow.dominio import (
    CAMBIOS,
    CAMBIOS_PREFERENCIA,
    COMBUSTIVEIS,
    DIAS,
    ORDENS,
    STATUS_LEAD,
    STATUS_PUBLICOS,
    STATUS_VEICULO,
    TIPOS,
    TIPOS_VISITA,
    USOS,
)
from socialflow.erros import ErroHttp
from socialflow.tempo import agora

_NOME = re.compile(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ' \-]{1,79}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _texto(valor):
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ErroHttp(400, "Um dos campos veio em formato inválido.")
    return unicodedata.normalize("NFC", valor).strip()


def nome_pessoa(valor, campo="nome"):
    texto = _texto(valor)
    if not _NOME.fullmatch(texto):
        raise ErroHttp(
            400,
            "Informe o nome com letras, sem números nem documentos.",
            {campo: "Use apenas letras, espaço, apóstrofo ou hífen."},
        )
    return texto


def email_opcional(valor, campo="email"):
    texto = _texto(valor).lower()
    if not texto:
        return ""
    if len(texto) > 120 or not _EMAIL.fullmatch(texto):
        raise ErroHttp(400, "E-mail inválido.", {campo: "Revise o e-mail."})
    return texto


def email_obrigatorio(valor):
    texto = email_opcional(valor, "email")
    if not texto:
        raise ErroHttp(400, "Informe o e-mail.", {"email": "Campo obrigatório."})
    return texto


def telefone_opcional(valor, campo="telefone"):
    texto = _texto(valor)
    if not texto:
        return ""
    if len(texto) > 20 or re.search(r"[A-Za-z]", texto):
        raise ErroHttp(400, "Telefone inválido.", {campo: "Use DDD e números, sem letras."})
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) < 8 or len(digitos) > 13:
        raise ErroHttp(400, "Telefone inválido.", {campo: "Inclua DDD. Não use CPF."})
    return texto


def exigir_contato(telefone, email):
    if not telefone and not email:
        raise ErroHttp(
            400,
            "Informe telefone ou e-mail para a equipe retornar o contato.",
            {"contato": "Telefone ou e-mail."},
        )


def consentimento(valor):
    if valor is not True:
        raise ErroHttp(
            400,
            "O contato só é registrado com consentimento.",
            {"consentimento": "Marque a autorização de contato."},
        )
    return True


def texto_limitado(valor, minimo, maximo, campo, obrigatorio=True):
    texto = _texto(valor)
    if not texto and not obrigatorio:
        return ""
    if len(texto) < minimo or len(texto) > maximo:
        raise ErroHttp(
            400,
            f"O campo {campo} precisa ter entre {minimo} e {maximo} caracteres.",
            {campo: "Tamanho inválido."},
        )
    return texto


def inteiro(valor, minimo, maximo, campo):
    if isinstance(valor, bool) or isinstance(valor, float):
        raise ErroHttp(400, f"{campo} inválido.", {campo: "Use um número inteiro."})
    if isinstance(valor, str) and re.fullmatch(r"\d{1,9}", valor.strip()):
        valor = int(valor.strip())
    if not isinstance(valor, int):
        raise ErroHttp(400, f"{campo} inválido.", {campo: "Use um número inteiro."})
    if valor < minimo or valor > maximo:
        raise ErroHttp(400, f"{campo} fora da faixa permitida.", {campo: "Valor fora da faixa."})
    return valor


def enumerado(valor, opcoes, campo):
    texto = _texto(valor) if not isinstance(valor, str) else valor.strip()
    if isinstance(valor, str):
        texto = valor.strip()
    if texto not in opcoes:
        raise ErroHttp(400, f"{campo} inválido.", {campo: "Escolha uma opção da lista."})
    return texto


def parse_preco_centavos(valor):
    if isinstance(valor, bool) or isinstance(valor, float):
        raise ErroHttp(400, "Envie o preço como texto. Exemplo: 118900,00.", {"preco_reais": "Formato inválido."})
    if isinstance(valor, int):
        if valor < 1 or valor > 5_000_000:
            raise ErroHttp(400, "Preço fora da faixa.", {"preco_reais": "Informe um valor entre 1 e 5000000."})
        return valor * 100
    texto = _texto(valor).replace("R$", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+,\d{2}", texto):
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d+,\d{2}", texto):
        texto = texto.replace(",", ".")
    elif re.fullmatch(r"\d{1,7}", texto):
        texto = texto + ".00"
    else:
        raise ErroHttp(400, "Preço inválido. Use o formato 118900,00.", {"preco_reais": "Formato inválido."})
    reais, _, frac = texto.partition(".")
    centavos = int(reais) * 100 + int(frac)
    if centavos < 100 or centavos > 500_000_000:
        raise ErroHttp(400, "Preço fora da faixa.", {"preco_reais": "Valor não aceito."})
    return centavos


def _hex_para_rgb(cor):
    if re.fullmatch(r"#[0-9a-fA-F]{3}", cor):
        return tuple(int(c * 2, 16) for c in cor[1:])
    if re.fullmatch(r"#[0-9a-fA-F]{6}", cor):
        return tuple(int(cor[i : i + 2], 16) for i in (1, 3, 5))
    return None


def _canal(c):
    valor = c / 255
    if valor <= 0.04045:
        return valor / 12.92
    return ((valor + 0.055) / 1.055) ** 2.4


TEXTO_BOTAO = "#1a1208"


def _luminancia(cor):
    rgb = _hex_para_rgb(cor)
    if not rgb:
        return 0
    r, g, b = (_canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste_com_branco(cor):
    return 1.05 / (_luminancia(cor) + 0.05)


def contraste(cor_a, cor_b):
    claro = max(_luminancia(cor_a), _luminancia(cor_b))
    escuro = min(_luminancia(cor_a), _luminancia(cor_b))
    return (claro + 0.05) / (escuro + 0.05)


def cor_acento(valor):
    texto = _texto(valor)
    if _hex_para_rgb(texto) is None:
        raise ErroHttp(400, "Cor inválida.", {"cor": "Use um hex como #d09850."})
    if contraste_com_branco(texto) < 2.4:
        raise ErroHttp(
            400,
            "Escolha uma cor mais escura para o texto claro manter contraste.",
            {"cor": "Contraste insuficiente com texto branco."},
        )
    if contraste(texto, TEXTO_BOTAO) < 4.5:
        raise ErroHttp(
            400,
            "Escolha um dourado mais claro para o texto escuro do botão.",
            {"cor": "Contraste insuficiente com o texto do botão."},
        )
    return texto.lower()


def preferencias(bruto):
    if bruto is None:
        return {}
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Preferências inválidas.")
    saida = {}
    if bruto.get("preco_max") not in (None, ""):
        saida["preco_max_centavos"] = parse_preco_centavos(bruto.get("preco_max"))
    if bruto.get("cambio"):
        saida["cambio"] = enumerado(bruto.get("cambio"), CAMBIOS_PREFERENCIA, "câmbio")
    if bruto.get("tipo"):
        saida["tipo"] = enumerado(bruto.get("tipo"), TIPOS, "tipo")
    if bruto.get("combustivel"):
        saida["combustivel"] = enumerado(bruto.get("combustivel"), COMBUSTIVEIS, "combustível")
    if bruto.get("uso"):
        saida["uso"] = enumerado(bruto.get("uso"), USOS, "uso")
    if bruto.get("km_max") not in (None, ""):
        saida["km_max"] = inteiro(bruto.get("km_max"), 0, 2_000_000, "quilometragem")
    if bruto.get("ano_min") not in (None, ""):
        saida["ano_min"] = inteiro(bruto.get("ano_min"), 1980, agora().year + 1, "ano")
    if bruto.get("veiculo_id"):
        identificador = _texto(bruto.get("veiculo_id"))
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identificador):
            raise ErroHttp(400, "Veículo inválido.", {"veiculo_id": "Identificador inválido."})
        saida["veiculo_id"] = identificador
    return saida


def filtros_publicos(query):
    def primeiro(nome):
        valores = query.get(nome) or []
        return valores[0] if valores else ""

    bruto = {
        "q": primeiro("q")[:80],
        "marca": primeiro("marca")[:40],
        "cambio": primeiro("cambio"),
        "tipo": primeiro("tipo"),
        "combustivel": primeiro("combustivel"),
        "status": primeiro("status"),
        "ordem": primeiro("ordem") or "preco_asc",
    }
    if primeiro("preco_max"):
        bruto["preco_max"] = primeiro("preco_max")
    if primeiro("km_max"):
        bruto["km_max"] = primeiro("km_max")
    if primeiro("ano_min"):
        bruto["ano_min"] = primeiro("ano_min")
    prefs = preferencias(bruto)
    status = bruto["status"]
    if status and status not in STATUS_PUBLICOS:
        raise ErroHttp(400, "Status de vitrine inválido.", {"status": "Use disponível ou reservado."})
    ordem = bruto["ordem"] or "preco_asc"
    if ordem not in ORDENS:
        raise ErroHttp(400, "Ordenação inválida.", {"ordem": "Escolha uma ordenação da lista."})
    return {
        "q": _texto(bruto["q"]).casefold(),
        "marca": _texto(bruto["marca"]).casefold(),
        "preco_max_centavos": prefs.get("preco_max_centavos"),
        "cambio": prefs.get("cambio", ""),
        "tipo": prefs.get("tipo", ""),
        "combustivel": prefs.get("combustivel", ""),
        "km_max": prefs.get("km_max"),
        "ano_min": prefs.get("ano_min"),
        "status": status,
        "ordem": ordem,
    }


def payload_veiculo(bruto, atual=None):
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Dados do veículo inválidos.")
    ano_limite = agora().year + 1
    dados = {
        "brand": texto_limitado(bruto.get("marca"), 2, 40, "marca"),
        "model": texto_limitado(bruto.get("modelo"), 1, 40, "modelo"),
        "version": texto_limitado(bruto.get("versao"), 1, 40, "versão"),
        "year_manufacture": inteiro(bruto.get("ano_fabricacao"), 1980, ano_limite, "ano de fabricação"),
        "year_model": inteiro(bruto.get("ano_modelo"), 1980, ano_limite, "ano do modelo"),
        "km": inteiro(bruto.get("km"), 0, 2_000_000, "quilometragem"),
        "transmission": enumerado(bruto.get("cambio"), CAMBIOS, "câmbio"),
        "fuel": enumerado(bruto.get("combustivel"), COMBUSTIVEIS, "combustível"),
        "body_type": enumerado(bruto.get("tipo"), TIPOS, "tipo"),
        "price_cents": parse_preco_centavos(bruto.get("preco_reais")),
        "color": texto_limitado(bruto.get("cor"), 3, 30, "cor"),
        "description": texto_limitado(bruto.get("descricao"), 10, 800, "descrição"),
        "stock_code": texto_limitado(bruto.get("codigo"), 3, 20, "código").upper(),
    }
    if not re.fullmatch(r"[A-Z0-9-]{3,20}", dados["stock_code"]):
        raise ErroHttp(400, "Código inválido.", {"codigo": "Use letras, números e hífen."})
    if dados["year_model"] < dados["year_manufacture"]:
        raise ErroHttp(400, "O ano do modelo não pode ser anterior ao de fabricação.", {"ano_modelo": "Ano incoerente."})
    status = bruto.get("status") or (atual["status"] if atual else "disponivel")
    dados["status"] = enumerado(status, STATUS_VEICULO, "status")
    imagem = bruto.get("imagem_base64") or ""
    if imagem and not isinstance(imagem, str):
        raise ErroHttp(400, "Imagem inválida.", {"imagem": "Arquivo inválido."})
    dados["imagem_base64"] = imagem
    return dados


def consultor_informado(valor):
    texto = _texto(valor)
    if not re.fullmatch(r"[A-Za-z0-9-]{8,80}", texto):
        raise ErroHttp(
            400,
            "Escolha o consultor que vai atender.",
            {"consultor_id": "Consultor obrigatório."},
        )
    return texto


def consultor_opcional(valor):
    if not _texto(valor):
        return ""
    return consultor_informado(valor)


def payload_lead_publico(bruto):
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Dados de contato inválidos.")
    consentimento(bruto.get("consentimento"))
    telefone = telefone_opcional(bruto.get("telefone"))
    email = email_opcional(bruto.get("email"))
    exigir_contato(telefone, email)
    veiculo_id = ""
    if bruto.get("veiculo_id"):
        veiculo_id = texto_limitado(bruto.get("veiculo_id"), 8, 80, "veículo")
    sessao_id = ""
    if bruto.get("sessao_id"):
        sessao_id = texto_limitado(bruto.get("sessao_id"), 8, 80, "sessão")
    return {
        "nome": nome_pessoa(bruto.get("nome")),
        "telefone": telefone,
        "email": email,
        "veiculo_id": veiculo_id,
        "sessao_id": sessao_id,
        "consultor_id": consultor_opcional(bruto.get("consultor_id")),
        "reiniciar": bruto.get("reiniciar") is True,
    }


def payload_agenda_publico(bruto):
    dados = payload_lead_publico(bruto)
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Pedido de visita inválido.")
    dados["tipo"] = enumerado(bruto.get("tipo"), TIPOS_VISITA, "tipo de visita")
    dados["inicio"] = texto_limitado(bruto.get("inicio"), 10, 40, "horário")
    if not dados["veiculo_id"]:
        raise ErroHttp(400, "Escolha o veículo da visita.", {"veiculo_id": "Obrigatório."})
    return dados


def payload_configuracao(bruto):
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Configuração inválida.")
    servicos = bruto.get("servicos")
    if not isinstance(servicos, list) or not 1 <= len(servicos) <= 6:
        raise ErroHttp(400, "Informe de 1 a 6 serviços.", {"servicos": "Lista inválida."})
    limpos = []
    for item in servicos:
        if not isinstance(item, dict):
            raise ErroHttp(400, "Serviço inválido.")
        limpos.append({
            "titulo": texto_limitado(item.get("titulo"), 3, 60, "título do serviço"),
            "texto": texto_limitado(item.get("texto"), 10, 280, "texto do serviço"),
        })
    expediente = bruto.get("expediente")
    if not isinstance(expediente, dict):
        raise ErroHttp(400, "Expediente inválido.", {"expediente": "Informe os dias."})
    horas = {}
    for dia in DIAS:
        faixa = expediente.get(dia)
        if faixa in (None, "", False):
            horas[dia] = None
            continue
        if not isinstance(faixa, list) or len(faixa) != 2:
            raise ErroHttp(400, "Faixa de horário inválida.", {"expediente": dia})
        inicio, fim = _texto(faixa[0]), _texto(faixa[1])
        if not re.fullmatch(r"\d{2}:\d{2}", inicio) or not re.fullmatch(r"\d{2}:\d{2}", fim) or inicio >= fim:
            raise ErroHttp(400, "Faixa de horário inválida.", {"expediente": dia})
        horas[dia] = [inicio, fim]
    assistente = bruto.get("consultor") if isinstance(bruto.get("consultor"), dict) else {}
    maximo = inteiro(assistente.get("max_sugestoes", 3), 1, 3, "sugestões")
    return {
        "trade_name": texto_limitado(bruto.get("nome"), 3, 60, "nome da loja"),
        "description": texto_limitado(bruto.get("descricao"), 20, 600, "descrição"),
        "phone": telefone_opcional(bruto.get("telefone"), "telefone da loja") or texto_limitado(bruto.get("telefone"), 8, 20, "telefone da loja"),
        "email": email_obrigatorio(bruto.get("email")),
        "address_public": texto_limitado(bruto.get("endereco"), 8, 160, "endereço demonstrativo"),
        "hours_json": horas,
        "services_json": limpos,
        "assistant_json": {
            "max_sugestoes": maximo,
            "baixa_km": 30000,
            "rotulo_modo": "Automação determinística",
        },
        "theme_json": {"acento": cor_acento(bruto.get("cor") or "#d09850")},
        "privacy_note": texto_limitado(bruto.get("privacidade"), 20, 800, "nota de privacidade"),
    }


def status_lead(valor):
    return enumerado(valor, STATUS_LEAD, "status do lead")


def notas(valor):
    return texto_limitado(valor or "", 0, 1000, "notas", obrigatorio=False)


def payload_contato(bruto):
    if not isinstance(bruto, dict):
        raise ErroHttp(400, "Dados de contato inválidos.")
    consentimento(bruto.get("consentimento"))
    consultor_id = consultor_informado(bruto.get("consultor_id"))
    veiculo_id = ""
    if bruto.get("veiculo_id"):
        veiculo_id = texto_limitado(bruto.get("veiculo_id"), 8, 80, "veículo")
    return {
        "nome": nome_pessoa(bruto.get("nome")),
        "email": email_obrigatorio(bruto.get("email")),
        "mensagem": texto_limitado(bruto.get("mensagem"), 10, 800, "mensagem"),
        "consultor_id": consultor_id,
        "veiculo_id": veiculo_id,
    }


def mensagem_consultor(valor):
    texto = _texto(valor)
    if len(texto) > 500:
        raise ErroHttp(400, "A mensagem pode ter no máximo 500 caracteres.", {"mensagem": "Texto longo demais."})
    return texto


def intencao_luna(valor):
    if valor in (None, ""):
        return None
    texto = _texto(valor)
    permitidas = {
        "busca", "simulacao", "comparacao", "detalhes",
        "atendimento", "agendamento", "loja",
        "saudacao", "cortesia", "ajuda", "fora",
    }
    if texto not in permitidas:
        raise ErroHttp(400, "Intenção inválida.")
    return texto
