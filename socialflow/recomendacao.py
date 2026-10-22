"""Consultor determinístico. Só recomenda veículo disponível da organização informada."""

import re
import unicodedata

from socialflow.apresentacao import formatar_km, formatar_reais
from socialflow.catalogo import cambio_compativel
from socialflow.dominio import GRUPO_AUTOMATICO, USO_TIPOS, pode_recomendar, rotulo

CHAVES = (
    "preco_max_centavos",
    "cambio",
    "tipo",
    "km_max",
    "combustivel",
    "uso",
    "ano_min",
    "veiculo_id",
    "modelo",
    "prioridade",
    "simulacao_valor_centavos",
    "simulacao_entrada_centavos",
    "simulacao_parcelas",
)
ORDEM_DURA = ("modelo", "preco_max_centavos", "cambio", "tipo", "km_max", "combustivel", "ano_min")
ASSUNTOS_FORA = ("financi", "parcela", "garantia", "desconto", "entrada", "seguro", "ipva")
_TOKENS = {
    "seda": "sedan",
    "picape": "pickup",
    "automatica": "automatico",
    "automatico": "automatico",
    "automaticos": "automatico",
    "eletrico": "eletrico",
    "hibrido": "hibrido",
    "familia": "familia",
}


def normalizar(texto):
    base = unicodedata.normalize("NFD", (texto or "").casefold())
    sem_acento = "".join(c for c in base if unicodedata.category(c) != "Mn")
    return sem_acento


def _tokens(texto):
    saida = []
    for token in re.findall(r"[a-z0-9]+", normalizar(texto)):
        saida.append(_TOKENS.get(token, token))
    return saida


def _mascarar(texto, padrao):
    return re.sub(padrao, " ", texto)


def extrair_preferencias(mensagem, baixa_km=30000):
    bruto = normalizar(mensagem)
    prefs = {}
    interpretacoes = []
    texto = bruto
    ano = re.search(r"(?:a partir de|ano|desde)\s+((?:19|20)\d{2})", texto)
    if not ano:
        ano = re.search(r"((?:19|20)\d{2})\s+ou mais", texto)
    if ano:
        prefs["ano_min"] = int(ano.group(1))
        texto = texto[: ano.start()] + " " + texto[ano.end() :]
    if "baixa quilometragem" in texto or "pouca km" in texto:
        prefs["km_max"] = int(baixa_km)
        interpretacoes.append(f"Tratei baixa quilometragem como até {formatar_km(baixa_km)}.")
        texto = texto.replace("baixa quilometragem", " ").replace("pouca km", " ")
    km = re.search(r"(\d{1,3})\s*mil\s*(?:km|quilometros)\b", texto)
    if km:
        prefs["km_max"] = int(km.group(1)) * 1000
        texto = _mascarar(texto, r"\d{1,3}\s*mil\s*(?:km|quilometros)\b")
    else:
        km_num = re.search(r"(\d{4,7})\s*km", texto)
        if km_num:
            prefs["km_max"] = int(km_num.group(1))
            texto = _mascarar(texto, r"\d{4,7}\s*km")
    mil = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*mil\b", texto)
    if mil:
        prefs["preco_max_centavos"] = int(float(mil.group(1).replace(",", ".")) * 1000) * 100
        texto = _mascarar(texto, r"\d{1,3}(?:[.,]\d+)?\s*mil\b")
    if "preco_max_centavos" not in prefs:
        moeda = re.search(r"r\$\s*(\d{1,3}(?:\.\d{3})+|\d{4,7})", texto)
        if moeda:
            prefs["preco_max_centavos"] = int(moeda.group(1).replace(".", "")) * 100
        else:
            solto = re.search(r"(?:orcamento|ate)\s+(\d{5,7})\b", texto)
            if not solto:
                solto = re.search(r"\b(\d{5,7})\b", texto)
            if solto:
                prefs["preco_max_centavos"] = int(solto.group(1)) * 100
    tokens = set(_tokens(mensagem))
    if "cvt" in tokens and "automatico" not in tokens and "automaticos" not in tokens:
        prefs["cambio"] = "cvt"
    elif "manual" in tokens:
        prefs["cambio"] = "manual"
    elif "automatizado" in tokens:
        prefs["cambio"] = "automatizado"
    elif "automatico" in tokens or "automaticos" in tokens:
        prefs["cambio"] = "automaticos"
    for tipo in ("hatch", "sedan", "suv", "pickup", "minivan", "esportivo"):
        if tipo in tokens:
            prefs["tipo"] = tipo
            break
    for combustivel in ("flex", "gasolina", "etanol", "diesel", "hibrido", "eletrico"):
        if combustivel in tokens:
            prefs["combustivel"] = combustivel
            break
    for uso in ("familia", "cidade", "trabalho", "viagem"):
        if uso in tokens:
            prefs["uso"] = uso
            break
    return prefs, interpretacoes


def mesclar(anterior, extraido, explicito, reiniciar=False):
    base = {} if reiniciar else (anterior or {})
    saida = {}
    for chave in CHAVES:
        if explicito and explicito.get(chave) not in (None, ""):
            saida[chave] = explicito[chave]
        elif extraido and extraido.get(chave) not in (None, ""):
            saida[chave] = extraido[chave]
        elif base.get(chave) not in (None, ""):
            saida[chave] = base[chave]
    return saida


def preferencias_vazias(prefs):
    ignoradas = {
        "veiculo_id", "prioridade", "simulacao_valor_centavos",
        "simulacao_entrada_centavos", "simulacao_parcelas",
    }
    return not any(prefs.get(chave) not in (None, "") for chave in CHAVES if chave not in ignoradas)


def pede_assunto_fora(mensagem):
    texto = normalizar(mensagem)
    return any(termo in texto for termo in ASSUNTOS_FORA)


def _passa_duro(veiculo, chave, prefs):
    if chave == "modelo":
        return normalizar(veiculo["model"]) == normalizar(prefs[chave])
    if chave == "preco_max_centavos":
        return veiculo["price_cents"] <= prefs[chave]
    if chave == "cambio":
        return cambio_compativel(prefs[chave], veiculo["transmission"])
    if chave == "tipo":
        return veiculo["body_type"] == prefs[chave]
    if chave == "km_max":
        return veiculo["km"] <= prefs[chave]
    if chave == "combustivel":
        return veiculo["fuel"] == prefs[chave]
    if chave == "ano_min":
        return veiculo["year_model"] >= prefs[chave]
    return True


def _filtrar_duros(veiculos, prefs):
    atual = list(veiculos)
    bloqueante = None
    for chave in ORDEM_DURA:
        if prefs.get(chave) in (None, ""):
            continue
        proximo = [v for v in atual if _passa_duro(v, chave, prefs)]
        if not proximo:
            return [], chave
        atual = proximo
    return atual, bloqueante


def _motivos(veiculo, prefs, uso_obrigatorio):
    motivos = []
    if prefs.get("preco_max_centavos"):
        motivos.append(
            f"O preço de {formatar_reais(veiculo['price_cents'])} está dentro do orçamento de {formatar_reais(prefs['preco_max_centavos'])}."
        )
    cambio = prefs.get("cambio")
    if cambio == "automaticos" and veiculo["transmission"] in GRUPO_AUTOMATICO:
        motivos.append(
            f"Câmbio {rotulo('cambio', veiculo['transmission'])}, aceito porque você pediu câmbio automático."
        )
    elif cambio and cambio == veiculo["transmission"]:
        motivos.append(f"Câmbio {rotulo('cambio', veiculo['transmission'])}, como você pediu.")
    if prefs.get("tipo"):
        motivos.append(f"Carroceria {rotulo('tipo', veiculo['body_type'])}.")
    if prefs.get("km_max") is not None:
        motivos.append(f"{formatar_km(veiculo['km'])}, dentro do limite de {formatar_km(prefs['km_max'])}.")
    if prefs.get("combustivel"):
        motivos.append(f"Combustível {rotulo('combustivel', veiculo['fuel'])}.")
    if prefs.get("ano_min"):
        motivos.append(f"Ano do modelo {veiculo['year_model']}, a partir de {prefs['ano_min']}.")
    uso = prefs.get("uso")
    if uso and uso_obrigatorio and veiculo["body_type"] in USO_TIPOS.get(uso, ()):
        motivos.append(
            f"A carroceria {rotulo('tipo', veiculo['body_type'])} combina com uso em {rotulo('uso', uso)}."
        )
    if not motivos:
        motivos.append("Disponível no estoque desta loja com os critérios informados.")
    return motivos


def _pontuar(veiculo, prefs):
    pontos = 0
    uso = prefs.get("uso")
    if uso and veiculo["body_type"] in USO_TIPOS.get(uso, ()):
        pontos += 30
    orcamento = prefs.get("preco_max_centavos")
    if orcamento:
        pontos += int(10 * veiculo["price_cents"] / orcamento)
    pontos += max(0, 12 - veiculo["km"] // 10000)
    pontos += max(0, min(8, veiculo["year_model"] - 2018))
    return pontos


def _nome(veiculo):
    return f"{veiculo['brand']} {veiculo['model']} {veiculo['version']}".strip()


def avaliar_foco(veiculos, prefs, org_id):
    identificador = prefs.get("veiculo_id")
    if not identificador:
        return None
    veiculo = next((v for v in veiculos if v["id"] == identificador and v["organization_id"] == org_id), None)
    if not veiculo:
        return {"id": identificador, "disponivel": False, "compativel": False, "motivos": ["Não encontrei esse veículo nesta loja."]}
    nome = _nome(veiculo)
    if not pode_recomendar(veiculo["status"]):
        return {
            "id": veiculo["id"],
            "disponivel": False,
            "compativel": False,
            "status": veiculo["status"],
            "motivos": [f"O {nome} não está disponível para recomendação. Status atual: {rotulo('status_veiculo', veiculo['status'])}."],
        }
    duros_ok = all(
        _passa_duro(veiculo, chave, prefs)
        for chave in ORDEM_DURA
        if prefs.get(chave) not in (None, "")
    )
    uso = prefs.get("uso")
    uso_ok = (not uso) or veiculo["body_type"] in USO_TIPOS.get(uso, ())
    compativel = duros_ok and uso_ok
    motivos = _motivos(veiculo, prefs, True) if compativel else []
    if not duros_ok:
        if prefs.get("preco_max_centavos") and veiculo["price_cents"] > prefs["preco_max_centavos"]:
            motivos.append(
                f"Não entra no orçamento: custa {formatar_reais(veiculo['price_cents'])} e o limite informado é {formatar_reais(prefs['preco_max_centavos'])}."
            )
        else:
            motivos.append(f"O {nome} está disponível, mas não atende a todos os filtros informados.")
    elif not uso_ok:
        motivos.append(
            f"A carroceria {rotulo('tipo', veiculo['body_type'])} não é a combinação prevista para uso em {rotulo('uso', uso)}."
        )
    return {
        "id": veiculo["id"],
        "disponivel": True,
        "compativel": compativel,
        "status": veiculo["status"],
        "motivos": motivos,
    }


def responder(veiculos, prefs, org_id, nome_loja, limite=3, interpretacoes=None):
    limite = max(1, min(int(limite or 3), 3))
    proprios = [
        v for v in veiculos
        if v.get("organization_id") == org_id and pode_recomendar(v.get("status"))
    ]
    foco = avaliar_foco(veiculos, prefs, org_id)
    if preferencias_vazias(prefs):
        if foco and foco.get("disponivel") and foco.get("compativel"):
            texto = f"Consultei o estoque da {nome_loja}. O veículo pedido está disponível."
            sugestoes = [{"id": foco["id"], "motivos": foco["motivos"], "compativel": True}]
            correspondencia = "exata"
        elif foco and not foco.get("disponivel"):
            texto = foco["motivos"][0]
            sugestoes = []
            correspondencia = "vazia"
        elif foco:
            texto = f"O veículo está na {nome_loja}, mas não fecha com os critérios informados."
            sugestoes = []
            correspondencia = "vazia"
        else:
            texto = f"Posso consultar só o estoque disponível da {nome_loja}. Diga orçamento, câmbio, tipo de carro, quilometragem ou uso."
            sugestoes = []
            correspondencia = "incompleta"
        return {
            "modo": "deterministico",
            "correspondencia": correspondencia,
            "texto": texto,
            "sugestoes": sugestoes,
            "alternativas": [],
            "foco": foco,
            "preferencias": prefs,
            "filtro_bloqueante": None,
            "interpretacoes": interpretacoes or [],
        }
    compativeis, bloqueante = _filtrar_duros(proprios, prefs)
    alternativas = []
    uso = prefs.get("uso")
    if compativeis and uso:
        do_uso = [v for v in compativeis if v["body_type"] in USO_TIPOS.get(uso, ())]
        if do_uso:
            compativeis = do_uso
        else:
            alternativas = compativeis
            compativeis = []
            bloqueante = bloqueante or "uso"
    elif not compativeis:
        alternativas = []
    prioridade = prefs.get("prioridade")
    if prioridade == "menor_preco":
        chave_ordem = lambda v: (v["price_cents"], v["km"], v["id"])
    elif prioridade == "menor_km":
        chave_ordem = lambda v: (v["km"], v["price_cents"], v["id"])
    elif prioridade == "mais_novo":
        chave_ordem = lambda v: (-v["year_model"], v["km"], v["id"])
    else:
        chave_ordem = lambda v: (-_pontuar(v, prefs), v["price_cents"], v["id"])
    compativeis = sorted(compativeis, key=chave_ordem)[:limite]
    if foco and foco.get("disponivel") and foco.get("compativel"):
        compativeis = [v for v in compativeis if v["id"] != foco["id"]]
        foco_veiculo = next(v for v in proprios if v["id"] == foco["id"])
        compativeis = [foco_veiculo] + compativeis
        compativeis = compativeis[:limite]
    sugestoes = [{"id": v["id"], "motivos": _motivos(v, prefs, bool(uso)), "compativel": True} for v in compativeis]
    alternativas_saida = []
    if not sugestoes and alternativas:
        ordenadas = sorted(alternativas, key=lambda v: (v["price_cents"], v["id"]))[:limite]
        for v in ordenadas:
            motivos = _motivos(v, {k: prefs.get(k) for k in prefs if k != "uso"}, False)
            motivos.insert(0, f"Não combina com o uso em {rotulo('uso', uso)}; entra apenas nos outros filtros.")
            alternativas_saida.append({"id": v["id"], "motivos": motivos, "compativel": False})
    if sugestoes:
        nomes = []
        por_id = {v["id"]: v for v in proprios}
        for item in sugestoes:
            nomes.append(_nome(por_id[item["id"]]))
        texto = f"Na {nome_loja}, encontrei {len(sugestoes)} veículo(s) disponível(is): {', '.join(nomes)}. Cada motivo abaixo sai do cadastro, não de um palpite."
        correspondencia = "exata"
    elif alternativas_saida:
        texto = f"Não há veículo disponível na {nome_loja} que una o uso pedido aos demais filtros. Separei opções que respeitam os outros filtros, fora do uso."
        correspondencia = "vazia"
    elif bloqueante:
        texto = f"Não há veículo disponível na {nome_loja} com todos esses critérios. O filtro que esvaziou a busca foi: {_nome_filtro(bloqueante)}."
        correspondencia = "vazia"
    else:
        texto = f"Não há veículo disponível na {nome_loja} com esses critérios."
        correspondencia = "vazia"
    return {
        "modo": "deterministico",
        "correspondencia": correspondencia,
        "texto": texto,
        "sugestoes": sugestoes,
        "alternativas": alternativas_saida,
        "foco": foco,
        "preferencias": {k: prefs.get(k) for k in CHAVES if prefs.get(k) not in (None, "")},
        "filtro_bloqueante": bloqueante,
        "interpretacoes": interpretacoes or [],
    }


def _nome_filtro(chave):
    return {
        "modelo": "modelo",
        "preco_max_centavos": "orçamento",
        "cambio": "câmbio",
        "tipo": "tipo de carro",
        "km_max": "quilometragem",
        "combustivel": "combustível",
        "ano_min": "ano",
        "uso": "uso",
    }.get(chave, chave)


def frase_fora_de_escopo():
    return (
        "Não há, nesta base, dados de financiamento, desconto, garantia ou seguro. "
        "A consulta usa apenas veículos disponíveis e os atributos cadastrados."
    )


def resumo_preferencias(prefs, codigos_por_id=None):
    partes = []
    if prefs.get("modelo"):
        partes.append("modelo " + str(prefs["modelo"]).title())
    if prefs.get("preco_max_centavos"):
        partes.append("orçamento até " + formatar_reais(prefs["preco_max_centavos"]))
    if prefs.get("cambio"):
        partes.append("câmbio " + rotulo("cambio", prefs["cambio"]))
    if prefs.get("tipo"):
        partes.append("tipo " + rotulo("tipo", prefs["tipo"]))
    if prefs.get("combustivel"):
        partes.append("combustível " + rotulo("combustivel", prefs["combustivel"]))
    if prefs.get("km_max") is not None:
        partes.append("até " + formatar_km(prefs["km_max"]))
    if prefs.get("ano_min"):
        partes.append(f"ano a partir de {prefs['ano_min']}")
    if prefs.get("uso"):
        partes.append("uso em " + rotulo("uso", prefs["uso"]))
    texto = "Preferências: " + (", ".join(partes) if partes else "não informadas") + "."
    if codigos_por_id:
        texto += " Veículos citados: " + ", ".join(codigos_por_id) + "."
    return texto
