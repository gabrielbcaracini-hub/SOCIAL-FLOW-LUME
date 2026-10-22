"""Formatação e serialização para a interface. Não decide regra de negócio."""

import json

from socialflow.dominio import aparece_na_vitrine, rotulo


def formatar_reais(centavos):
    valor = int(centavos)
    sinal = "-" if valor < 0 else ""
    inteiro, frac = divmod(abs(valor), 100)
    grupos = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {grupos},{frac:02d}"


def formatar_km(km):
    return f"{int(km):,}".replace(",", ".") + " km"


def carregar_json(texto, padrao):
    if not texto:
        return padrao
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return padrao


def resumo_expediente(horas):
    if not isinstance(horas, dict):
        return ""
    uteis = ["seg", "ter", "qua", "qui", "sex"]
    faixa_util = horas.get("seg")
    if faixa_util and all(horas.get(dia) == faixa_util for dia in uteis):
        texto = f"Segunda a sexta, {faixa_util[0]} às {faixa_util[1]}"
    else:
        partes = []
        for dia in ("seg", "ter", "qua", "qui", "sex", "sab", "dom"):
            faixa = horas.get(dia)
            if faixa:
                partes.append(f"{rotulo('dia', dia)} {faixa[0]}–{faixa[1]}")
        texto = "; ".join(partes)
    sabado = horas.get("sab")
    if sabado and all(horas.get(dia) == faixa_util for dia in uteis):
        texto += f". Sábado, {sabado[0]} às {sabado[1]}"
    if not horas.get("dom"):
        texto += ". Domingo fechado"
    return texto + "."


def url_imagem(imagem):
    caminho = imagem["path"]
    if str(caminho).startswith("/assets/"):
        return caminho
    return "/midia/" + imagem["id"]


def serializar_imagem(imagem):
    return {
        "id": imagem["id"],
        "url": url_imagem(imagem),
        "rotulo": imagem["label"],
        "tipo": imagem["kind"],
    }


def serializar_veiculo(veiculo, imagens, publico=False):
    dados = {
        "id": veiculo["id"],
        "codigo": veiculo["stock_code"],
        "marca": veiculo["brand"],
        "modelo": veiculo["model"],
        "versao": veiculo["version"],
        "ano_fabricacao": veiculo["year_manufacture"],
        "ano_modelo": veiculo["year_model"],
        "km": veiculo["km"],
        "km_rotulo": formatar_km(veiculo["km"]),
        "cambio": veiculo["transmission"],
        "cambio_rotulo": rotulo("cambio", veiculo["transmission"]),
        "combustivel": veiculo["fuel"],
        "combustivel_rotulo": rotulo("combustivel", veiculo["fuel"]),
        "tipo": veiculo["body_type"],
        "tipo_rotulo": rotulo("tipo", veiculo["body_type"]),
        "preco_centavos": veiculo["price_cents"],
        "preco": formatar_reais(veiculo["price_cents"]),
        "status": veiculo["status"],
        "status_rotulo": rotulo("status_veiculo", veiculo["status"]),
        "cor": veiculo["color"],
        "descricao": veiculo["description"],
        "imagens": [serializar_imagem(item) for item in imagens],
        "na_vitrine": aparece_na_vitrine(veiculo["status"]),
    }
    if not publico:
        dados["atualizado_em"] = veiculo["updated_at"]
    return dados


def loja_publica(organizacao, configuracao):
    horas = carregar_json(configuracao["hours_json"], {})
    servicos = carregar_json(configuracao["services_json"], [])
    assistente = carregar_json(configuracao["assistant_json"], {})
    tema = carregar_json(configuracao["theme_json"], {})
    return {
        "nome": configuracao["trade_name"],
        "produto": "SocialFlow Auto",
        "descricao": configuracao["description"],
        "telefone": configuracao["phone"],
        "email": configuracao["email"],
        "endereco": configuracao["address_public"],
        "expediente": horas,
        "horario_resumo": resumo_expediente(horas),
        "servicos": servicos,
        "cor": tema.get("acento", "#d09850"),
        "privacidade": configuracao["privacy_note"],
        "aviso_demonstracao": (
            "Loja fictícia. Veículos, contatos e agendamentos não são reais."
        ),
        "consultor": {
            "max_sugestoes": int(assistente.get("max_sugestoes", 3)),
            "rotulo_modo": assistente.get("rotulo_modo") or "Automação determinística",
        },
        "slug": organizacao["slug"],
    }
