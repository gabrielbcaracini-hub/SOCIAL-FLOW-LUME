"""Intenções e ferramentas determinísticas da Luna.

O modelo opcional pode melhorar a redação, mas decisões e dados vêm daqui.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from socialflow.apresentacao import formatar_km, formatar_reais, loja_publica
from socialflow.dominio import pode_recomendar, rotulo
from socialflow import recomendacao

INTENCOES = (
    "busca",
    "simulacao",
    "comparacao",
    "detalhes",
    "atendimento",
    "agendamento",
    "loja",
    "saudacao",
    "cortesia",
    "ajuda",
    "fora",
)
CHAVES_INTERNAS = ("_intencao", "_ultima_sugestao")
MARCAS_CONTEXTO = {
    "luna", "lume", "ai", "ia", "voce", "vc", "tua", "sua",
}
SINAIS_AUTO = (
    "carro", "carros", "veiculo", "veiculos", "suv", "hatch", "sedan", "picape",
    "pickup", "estoque", "modelo", "marca", "preco", "km", "quilometr", "cambio",
    "automatico", "manual", "financi", "parcela", "entrada", "corolla", "onix",
    "hb20", "kwid", "argo", "civic", "creta", "gol", "polo", "pulse", "virtus",
    "tracker", "nivus", "strada", "dolphin", "hilux", "compass", "comprar",
    "test-drive", "visita",
)
SINAIS_FECHAMENTO = (
    "quero comprar", "consigo comprar", "vamos fechar", "fechar negocio",
    "quero esse", "fico com", "quero fechar", "financiar o restante",
    "quero financiar", "fechar a compra", "fechar com voces", "pode reservar",
    "levar o carro", "fechar hoje", "quero fechar negocio",
)
SINAIS_SAUDACAO = (
    "oi", "ola", "oie", "oii", "hey", "eai", "eae", "iai", "hello", "hi",
    "fala", "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom",
    "beleza", "como vai", "como vai voce", "como voce esta", "e ai",
)
SINAIS_AGRADECIMENTO = ("obrigado", "obrigada", "valeu", "agradeco", "muito obrigado")
SINAIS_DESPEDIDA = ("tchau", "ate logo", "ate mais", "falou", "ate breve")
SINAIS_AJUDA = (
    "me ajuda", "pode me ajudar", "preciso de ajuda", "o que voce faz",
    "quem e voce", "quais suas funcoes", "como voce trabalha",
)


def normalizar(texto):
    base = unicodedata.normalize("NFD", (texto or "").casefold())
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def _frase_limpa(mensagem):
    texto = re.sub(r"[^a-z0-9\s]", " ", normalizar(mensagem))
    return re.sub(r"\s+", " ", texto).strip()


def _palavras_uteis(mensagem):
    return [p for p in _frase_limpa(mensagem).split() if p not in MARCAS_CONTEXTO]


def eh_saudacao(mensagem):
    palavras = _palavras_uteis(mensagem)
    if not palavras:
        return bool(_frase_limpa(mensagem))
    frase = " ".join(palavras)
    if frase in SINAIS_SAUDACAO:
        return True
    if palavras[0] not in {"oi", "ola", "oie", "hey", "eai", "eae", "hello", "hi", "fala", "bom", "boa"}:
        return False
    return len(palavras) <= 5 and all(
        p in {
            "oi", "ola", "oie", "hey", "eai", "eae", "hello", "hi", "fala",
            "tudo", "bem", "bom", "boa", "dia", "tarde", "noite", "como", "vai",
        }
        for p in palavras
    )


def eh_cortesia(mensagem):
    frase = " ".join(_palavras_uteis(mensagem))
    return frase in SINAIS_AGRADECIMENTO or frase in SINAIS_DESPEDIDA


def eh_fechamento(mensagem):
    texto = _frase_limpa(mensagem)
    return any(sinal in texto for sinal in SINAIS_FECHAMENTO)


def eh_pedido_ajuda(mensagem):
    texto = _frase_limpa(mensagem)
    if any(sinal in texto for sinal in ("ver um carro", "ver carros", "encontrar", "procurar", "mostrar", "automatico")):
        if parece_automotivo(mensagem):
            return False
    return any(sinal in texto for sinal in SINAIS_AJUDA)


def parece_automotivo(mensagem):
    texto = _frase_limpa(mensagem)
    return any(sinal in texto for sinal in SINAIS_AUTO)


def identificar_intencao(mensagem, intencao_forcada=None, ultima=None):
    if intencao_forcada in INTENCOES:
        return intencao_forcada
    texto = normalizar(mensagem).strip()
    if not texto:
        return ultima if ultima in INTENCOES else "busca"
    if eh_saudacao(mensagem):
        return "saudacao"
    if eh_cortesia(mensagem):
        return "cortesia"
    if eh_pedido_ajuda(mensagem):
        return "ajuda"
    if any(t in texto for t in ("financi", "parcela", "entrada", " vezes", "prestacao", "sem entrada")):
        return "simulacao"
    if any(t in texto for t in ("compar", "qual e melhor", "diferenca entre", "custo-beneficio", "custo beneficio",
                                "maior porta-malas", "mais equipamentos")):
        return "comparacao"
    if any(t in texto for t in ("falar com", "vendedor", "atendente", "atendimento humano", "consultor responsavel")):
        return "atendimento"
    if any(t in texto for t in ("agendar", "test-drive", "test drive", "marcar visita", "fazer uma visita")):
        return "agendamento"
    if any(t in texto for t in ("onde fica", "endereco", "horario", "funcionamento", "como faco para comprar",
                                "formas de pagamento", "forma de pagamento", "aceitam troca", "meu carro usado",
                                "reservar", "reserva esse", "quanto vale meu")):
        return "loja"
    if any(t in texto for t in ("qual o ano", "quantos quilometros", "quilometragem desse", "camera de re",
                                "multimidia", "quantos cavalos", "fotos do interior", "qual combustivel",
                                "qual o preco", "ainda esta disponivel", "ver detalhes", "detalhes desse",
                                "tem camera", "possui multim", "quantos cavalos")):
        return "detalhes"
    if ultima == "simulacao" and re.search(r"\b\d+\s*(?:x|vezes|parcelas)\b", texto):
        return "simulacao"
    if ultima == "comparacao" and (" ou " in texto or " e " in texto):
        return "comparacao"
    if ultima == "detalhes":
        return "detalhes"
    if ultima in {"busca", "simulacao", "comparacao"} and (parece_automotivo(mensagem) or re.search(r"\d", texto)):
        return ultima
    if any(t in texto for t in ("tem ", "existe ", "disponivel", "procuro")):
        return "busca"
    if any(t in texto for t in ("sobre o ", "sobre a ", "sobre os ", "saber mais")):
        return "busca"
    if not parece_automotivo(mensagem):
        return "fora"
    return "busca"


def _nomes(veiculo):
    return [
        normalizar(veiculo.get("brand")),
        normalizar(veiculo.get("model")),
        normalizar(f"{veiculo.get('brand', '')} {veiculo.get('model', '')}"),
        normalizar(f"{veiculo.get('model', '')} {veiculo.get('version', '')}"),
    ]


def localizar_veiculos(mensagem, veiculos, apenas_disponiveis=True):
    texto = normalizar(mensagem)
    palavras = re.findall(r"[a-z0-9-]+", texto)
    encontrados = []
    for veiculo in veiculos:
        if apenas_disponiveis and not pode_recomendar(veiculo.get("status")):
            continue
        nomes = [nome.strip() for nome in _nomes(veiculo) if nome.strip()]
        exato = any(nome in texto for nome in nomes if len(nome) >= 3)
        aproximado = False
        if not exato:
            alvos = set()
            for nome in nomes[:2]:
                alvos.update(p for p in nome.split() if len(p) >= 4)
            aproximado = any(
                SequenceMatcher(None, palavra, alvo).ratio() >= 0.78
                for palavra in palavras if len(palavra) >= 4
                for alvo in alvos
            )
        if exato or aproximado:
            encontrados.append(veiculo)
    unicos = {}
    for item in encontrados:
        unicos[item["id"]] = item
    return list(unicos.values())


GENERICOS_MODELO = {
    "carro", "carros", "veiculo", "veiculos", "suv", "suvs", "hatch", "hatches",
    "sedan", "sedans", "picape", "picapes", "pickup", "minivan", "automatico",
    "automaticos", "manual", "economico", "barato", "novo", "usados", "opcao", "opcoes",
    "saber", "sobre",
}


def _pedido_de_modelo(mensagem, veiculos):
    citados = localizar_veiculos(mensagem, veiculos, apenas_disponiveis=False)
    if citados:
        return citados, None
    texto = normalizar(mensagem)
    achado = re.search(
        r"\b(?:tem|existe|procuro|quero(?:\s+(?:um|uma))?|sobre|saber mais sobre)\s+"
        r"(?:um|uma|o|a|os|as)?\s*"
        r"([a-z][a-z0-9+\-]{1,30}(?:\s+[a-z0-9+\-]{2,20}){0,2})"
        r"(?:\s+disponivel|\s+no estoque|\s+ai|\s*\?|$)",
        texto,
    )
    if not achado:
        return [], None
    nome = re.sub(r"\s+disponivel$", "", achado.group(1).strip())
    primeiro = nome.split()[0]
    if primeiro in GENERICOS_MODELO or primeiro.isdigit():
        return [], None
    return [], nome


def enriquecer_preferencias(mensagem, veiculos, preferencias):
    texto = normalizar(mensagem)
    saida = dict(preferencias or {})
    citados = localizar_veiculos(mensagem, veiculos, apenas_disponiveis=False)
    modelos = {normalizar(v["model"]) for v in citados}
    if len(modelos) == 1:
        saida["modelo"] = next(iter(modelos))
    if any(t in texto for t in ("mais barato", "menor preco", "mais em conta")):
        saida["prioridade"] = "menor_preco"
    elif any(t in texto for t in ("menor quilometragem", "menos rodado", "menos km")):
        saida["prioridade"] = "menor_km"
    elif any(t in texto for t in ("mais novo", "ano mais novo")):
        saida["prioridade"] = "mais_novo"
    elif "economico" in texto:
        saida["prioridade"] = "menor_preco"
    return saida


def _resultado(texto, intencao, **extras):
    base = {
        "modo": "deterministico",
        "correspondencia": "exata",
        "texto": texto,
        "sugestoes": [],
        "alternativas": [],
        "foco": None,
        "preferencias": {},
        "filtro_bloqueante": None,
        "interpretacoes": [],
        "intencao": intencao,
        "acao": None,
        "comparacao": None,
        "simulacao": None,
    }
    base.update(extras)
    return base


def _valor_centavos(texto):
    trecho = normalizar(texto)
    mil = re.search(r"(?:r\$\s*)?(\d{1,3}(?:[.,]\d+)?)\s*mil\b", trecho)
    if mil:
        return int(float(mil.group(1).replace(",", ".")) * 1000) * 100
    moeda = re.search(r"r\$\s*(\d{1,3}(?:\.\d{3})+|\d{4,7})(?:,\d{2})?", trecho)
    if moeda:
        return int(moeda.group(1).replace(".", "")) * 100
    return None


def _extrair_entrada(texto):
    if "sem entrada" in texto:
        return 0
    padroes = (
        r"(?:r\$\s*)?(\d{1,3}(?:[.,]\d+)?)\s*mil(?:\s+reais)?\s+de\s+entrada",
        r"(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*(?:reais\s+)?de\s+entrada",
        r"entrada(?:\s+de|\s*:)\s*(?:r\$\s*)?(\d{1,3}(?:[.,]\d+)?)\s*mil\b",
        r"entrada(?:\s+de|\s*:)\s*(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+|\d{4,7})\b",
    )
    for padrao in padroes:
        achado = re.search(padrao, texto)
        if achado:
            return _valor_centavos(achado.group(0))
    return None


def _extrair_valor_veiculo(texto):
    padroes = (
        r"(?:carro|veiculo|valor)\s+de\s+(.+?)(?:\s+(?:em|com|e|sem)\b|$)",
        r"(?:r\$\s*)?(\d{1,3}(?:[.,]\d+)?)\s*mil\b(?!\s*(?:reais\s+)?de\s+entrada)",
    )
    for padrao in padroes:
        achado = re.search(padrao, texto)
        if not achado:
            continue
        trecho = achado.group(0)
        if "entrada" in trecho:
            continue
        valor = _valor_centavos(trecho)
        if valor is not None:
            return valor
    if re.search(r"\bentrada\b", texto):
        return None
    return _valor_centavos(texto)


def _dados_simulacao(mensagem, prefs, veiculos):
    texto = normalizar(mensagem)
    estado = dict(prefs or {})
    citados = localizar_veiculos(mensagem, veiculos)
    if citados:
        estado["simulacao_valor_centavos"] = citados[0]["price_cents"]
        estado["modelo"] = normalizar(citados[0]["model"])
    valor_entrada = _extrair_entrada(texto)
    if valor_entrada is not None:
        estado["simulacao_entrada_centavos"] = valor_entrada
    if not citados:
        valor = _extrair_valor_veiculo(texto)
        if valor is not None and valor != valor_entrada:
            estado["simulacao_valor_centavos"] = valor
    parcelas = re.search(r"\b(\d{1,3})\s*(?:x|vezes|parcelas)\b", texto)
    if parcelas:
        quantidade = int(parcelas.group(1))
        if 1 <= quantidade <= 120:
            estado["simulacao_parcelas"] = quantidade
    return estado


def simular(mensagem, prefs, veiculos):
    estado = _dados_simulacao(mensagem, prefs, veiculos)
    valor = estado.get("simulacao_valor_centavos")
    entrada = estado.get("simulacao_entrada_centavos", 0)
    parcelas = estado.get("simulacao_parcelas")
    texto_normal = normalizar(mensagem)
    if "quanto preciso dar de entrada" in texto_normal:
        return _resultado(
            "A loja não tem percentual mínimo de entrada cadastrado. Posso calcular um cenário se você informar o valor da entrada.",
            "simulacao", correspondencia="incompleta", preferencias=estado,
        )
    if not valor:
        extra = ""
        if entrada or parcelas:
            partes = []
            if entrada:
                partes.append(f"entrada de {formatar_reais(entrada)}")
            if parcelas:
                partes.append(f"{parcelas} parcelas")
            extra = " Já anotei " + " e ".join(partes) + "."
        return _resultado(
            f"Qual é o veículo ou o valor que você quer simular?{extra}",
            "simulacao", correspondencia="incompleta", preferencias=estado,
        )
    if entrada > valor:
        return _resultado(
            "A entrada não pode ser maior que o valor do veículo. Informe outro valor.",
            "simulacao", correspondencia="incompleta", preferencias=estado,
        )
    if not parcelas:
        return _resultado(
            f"Considerei o valor de {formatar_reais(valor)}. Em quantas parcelas você quer dividir?",
            "simulacao", correspondencia="incompleta", preferencias=estado,
        )
    saldo = valor - entrada
    parcela = round(saldo / parcelas)
    dados = {
        "valor_centavos": valor,
        "valor": formatar_reais(valor),
        "entrada_centavos": entrada,
        "entrada": formatar_reais(entrada),
        "saldo_centavos": saldo,
        "saldo": formatar_reais(saldo),
        "parcelas": parcelas,
        "parcela_centavos": parcela,
        "parcela": formatar_reais(parcela),
        "total": formatar_reais(saldo),
        "tem_juros": False,
    }
    texto = (
        f"Sem aplicar juros: {formatar_reais(valor)} menos {formatar_reais(entrada)} de entrada "
        f"deixa {formatar_reais(saldo)}. Dividido em {parcelas} vezes, dá aproximadamente "
        f"{formatar_reais(parcela)} por parcela. É apenas uma divisão matemática, não uma proposta de financiamento. "
        "Se quiser fechar, um consultor confirma as condições reais da loja."
    )
    return _resultado(texto, "simulacao", preferencias=estado, simulacao=dados)


def comparar(mensagem, veiculos, prefs):
    citados = localizar_veiculos(mensagem, veiculos)
    if len(citados) < 2:
        return _resultado(
            "Diga pelo menos dois modelos disponíveis para eu comparar, por exemplo: “compare Corolla e Civic”.",
            "comparacao", correspondencia="incompleta", preferencias=prefs,
        )
    citados = citados[:3]
    linhas = []
    for v in citados:
        linhas.append({
            "id": v["id"],
            "nome": f"{v['brand']} {v['model']} {v['version']}".strip(),
            "preco": formatar_reais(v["price_cents"]),
            "ano": f"{v['year_manufacture']}/{v['year_model']}",
            "km": formatar_km(v["km"]),
            "cambio": rotulo("cambio", v["transmission"]),
            "combustivel": rotulo("combustivel", v["fuel"]),
            "tipo": rotulo("tipo", v["body_type"]),
        })
    texto_normal = normalizar(mensagem)
    if any(t in texto_normal for t in ("mais barato", "custo-beneficio", "custo beneficio")):
        escolhido = min(citados, key=lambda v: (v["price_cents"], v["km"]))
        criterio = "menor preço cadastrado"
    elif any(t in texto_normal for t in ("menor quilometragem", "menos km", "menos rodado")):
        escolhido = min(citados, key=lambda v: (v["km"], v["price_cents"]))
        criterio = "menor quilometragem cadastrada"
    elif "mais novo" in texto_normal:
        escolhido = max(citados, key=lambda v: (v["year_model"], -v["km"]))
        criterio = "ano-modelo mais novo"
    else:
        escolhido = None
        criterio = ""
    texto = "Comparei somente os dados cadastrados dos veículos disponíveis."
    if escolhido:
        texto += f" Pelo critério de {criterio}, o destaque é {escolhido['brand']} {escolhido['model']}."
    else:
        texto += " Diga se sua prioridade é preço, ano ou quilometragem para eu recomendar uma opção."
    itens = [{"id": v["id"], "motivos": [], "compativel": True} for v in citados]
    return _resultado(texto, "comparacao", preferencias=prefs, sugestoes=itens, comparacao=linhas)


def detalhar(mensagem, veiculos, prefs):
    citados = localizar_veiculos(mensagem, veiculos, apenas_disponiveis=False)
    if not citados and prefs.get("modelo"):
        citados = [v for v in veiculos if normalizar(v["model"]) == prefs["modelo"]]
    if not citados and prefs.get("veiculo_id"):
        citados = [v for v in veiculos if v["id"] == prefs["veiculo_id"]]
    if not citados and prefs.get("_ultima_sugestao"):
        citados = [v for v in veiculos if v["id"] == prefs["_ultima_sugestao"]]
    if not citados:
        return _resultado(
            "Qual veículo você quer consultar? Informe a marca ou o modelo.",
            "detalhes", correspondencia="incompleta", preferencias=prefs,
        )
    v = citados[0]
    nome = f"{v['brand']} {v['model']} {v['version']}".strip()
    if not pode_recomendar(v["status"]):
        return _resultado(
            f"O {nome} não está disponível no momento. O status cadastrado é {rotulo('status_veiculo', v['status'])}.",
            "detalhes", correspondencia="vazia", preferencias=prefs,
        )
    texto_normal = normalizar(mensagem)
    campos_nao_cadastrados = ("camera", "multimidia", "cavalos", "porta-malas", "porta malas",
                              "manutencao", "revisao", "acidente", "documentacao")
    if any(campo in texto_normal for campo in campos_nao_cadastrados):
        texto = f"Não foi possível confirmar essa informação no cadastro do {nome}. Posso encaminhar a pergunta para um consultor."
        acao = {"tipo": "contato", "rotulo": "Falar com um consultor", "veiculo_id": v["id"]}
    else:
        texto = (
            f"{nome}: {v['year_manufacture']}/{v['year_model']}, {formatar_km(v['km'])}, "
            f"câmbio {rotulo('cambio', v['transmission'])}, combustível {rotulo('combustivel', v['fuel'])}, "
            f"{formatar_reais(v['price_cents'])}. Está disponível. Quer abrir a ficha ou simular o valor?"
        )
        acao = {"tipo": "detalhes", "rotulo": "Abrir detalhes", "veiculo_id": v["id"]}
    item = {"id": v["id"], "motivos": [], "compativel": True}
    return _resultado(texto, "detalhes", preferencias=prefs, sugestoes=[item], acao=acao)


def responder_loja(mensagem, organizacao, configuracao, prefs):
    loja = loja_publica(organizacao, configuracao)
    texto = normalizar(mensagem)
    if "horario" in texto or "funcionamento" in texto:
        resposta = loja["horario_resumo"] or "O horário de funcionamento não está cadastrado."
    elif "onde fica" in texto or "endereco" in texto:
        resposta = f"A loja fica em {loja['endereco']}." if loja["endereco"] else "O endereço não está cadastrado."
    elif "reserv" in texto:
        resposta = "A Luna não confirma reservas. Posso registrar seu interesse para a equipe verificar a disponibilidade."
    elif "troca" in texto or "carro usado" in texto:
        resposta = "Não há uma avaliação de usados integrada. Um consultor pode analisar seu carro e explicar as condições."
    elif "pagamento" in texto:
        resposta = "As formas e condições de pagamento não estão cadastradas nesta base. Posso encaminhar você para um consultor."
    else:
        resposta = "Posso explicar o estoque e encaminhar seu interesse. A compra e as condições comerciais são confirmadas pela equipe."
    return _resultado(
        resposta, "loja", preferencias=prefs,
        acao={"tipo": "contato", "rotulo": "Falar com um consultor"},
    )


def responder_atendimento(prefs):
    return _resultado(
        "Claro. Posso abrir o formulário para você falar com um consultor da loja. O contato só será enviado com sua autorização.",
        "atendimento", preferencias=prefs,
        acao={"tipo": "contato", "rotulo": "Falar com um consultor"},
    )


def responder_saudacao(prefs):
    return _resultado(
        "Olá! 😊 Que bom te ver por aqui. Sou a Luna, consultora da Lume Veículos. "
        "Posso te ajudar a encontrar o carro certo no estoque, simular valores ou comparar modelos. O que você procura hoje?",
        "saudacao", correspondencia="foco", preferencias=prefs,
    )


def responder_cortesia(mensagem, prefs):
    frase = " ".join(_palavras_uteis(mensagem))
    if frase in SINAIS_DESPEDIDA:
        texto = "Foi um prazer falar com você. Quando quiser, é só chamar — estou aqui para te ajudar com o estoque da Lume."
    else:
        texto = "Por nada! Se quiser, eu busco outro veículo, simulo o valor ou te encaminho para um consultor."
    return _resultado(texto, "cortesia", correspondencia="foco", preferencias=prefs)


def responder_ajuda(prefs):
    return _resultado(
        "Claro! Posso buscar no estoque, simular valores, comparar modelos, abrir detalhes de um veículo "
        "ou te encaminhar para um consultor. Por onde você prefere começar?",
        "ajuda", correspondencia="foco", preferencias=prefs,
    )


def responder_fora(prefs):
    return _resultado(
        "Essa pergunta foge um pouco do estoque da Lume, mas posso te ajudar do mesmo jeito. "
        "Se quiser, depois te mostro os veículos disponíveis, simulo valores ou te passo para um consultor.",
        "fora", correspondencia="foco", preferencias=prefs,
    )


def responder_agendamento(prefs):
    veiculo_id = prefs.get("veiculo_id") or prefs.get("_ultima_sugestao")
    return _resultado(
        "Posso te levar à ficha do veículo para pedir visita ou test-drive. A equipe ainda confirma o horário — isso não reserva o carro.",
        "agendamento", preferencias=prefs,
        acao={"tipo": "agendamento", "rotulo": "Solicitar visita", "veiculo_id": veiculo_id},
    )


def mesclar_estado(anterior, extraido):
    saida = recomendacao.mesclar(anterior, extraido, {})
    base = anterior or {}
    novo = extraido or {}
    for chave in CHAVES_INTERNAS:
        if novo.get(chave) not in (None, ""):
            saida[chave] = novo[chave]
        elif base.get(chave) not in (None, ""):
            saida[chave] = base[chave]
    return saida


def _abrir_especialidade(intencao, prefs):
    if intencao == "busca":
        return _resultado(
            "Perfeito! 😊 Me conta o orçamento, o tipo de carro ou o modelo que você tem em mente.",
            "busca", correspondencia="incompleta", preferencias=prefs,
        )
    if intencao == "simulacao":
        return _resultado(
            "Vamos simular com calma. Qual veículo ou valor você quer usar? Se quiser, já me diga a entrada e em quantas vezes.",
            "simulacao", correspondencia="incompleta", preferencias=prefs,
        )
    if intencao == "comparacao":
        return _resultado(
            "Boa. Quais modelos você quer comparar? Pode ser, por exemplo: “compare Onix e HB20”.",
            "comparacao", correspondencia="incompleta", preferencias=prefs,
        )
    if intencao == "detalhes":
        if prefs.get("veiculo_id") or prefs.get("_ultima_sugestao") or prefs.get("modelo"):
            return None
        return _resultado(
            "Qual veículo você quer ver? Diga a marca ou o modelo que eu consulto o cadastro.",
            "detalhes", correspondencia="incompleta", preferencias=prefs,
        )
    return None


def _voz_busca(resultado, nome_loja):
    if resultado["correspondencia"] == "exata" and resultado.get("sugestoes"):
        return (
            resultado["texto"].replace(f"Na {nome_loja}, encontrei", f"Encontrei na {nome_loja}")
            + " Se quiser, eu comparo dois deles ou simulo o valor."
        )
    if resultado["correspondencia"] == "vazia":
        return resultado["texto"] + " Se quiser, afrouxamos um filtro ou eu te encaminho para um consultor."
    return resultado["texto"]


def _buscar_por_prioridade(veiculos, prefs, org_id, limite):
    disponiveis = [
        v for v in veiculos
        if v.get("organization_id") == org_id and pode_recomendar(v.get("status"))
    ]
    prioridade = prefs.get("prioridade")
    if prioridade == "menor_km":
        disponiveis.sort(key=lambda v: (v["km"], v["price_cents"], v["id"]))
        criterio = "menor quilometragem"
    elif prioridade == "mais_novo":
        disponiveis.sort(key=lambda v: (-v["year_model"], v["km"], v["id"]))
        criterio = "ano mais novo"
    else:
        disponiveis.sort(key=lambda v: (v["price_cents"], v["km"], v["id"]))
        criterio = "menor preço"
    escolhidos = disponiveis[:limite]
    if not escolhidos:
        return _resultado(
            "Não há veículos disponíveis no estoque neste momento.",
            "busca", correspondencia="vazia", preferencias=prefs,
        )
    itens = [{"id": v["id"], "motivos": [f"Selecionado pelo critério de {criterio} no estoque disponível."], "compativel": True} for v in escolhidos]
    nomes = [f"{v['brand']} {v['model']}" for v in escolhidos]
    return _resultado(
        f"Separei os disponíveis com {criterio}: {', '.join(nomes)}. Os dados vêm do cadastro da loja.",
        "busca", preferencias=prefs, sugestoes=itens,
    )


def _parece_nova_busca(mensagem, extraidas):
    texto = normalizar(mensagem)
    if any(p in texto for p in ("mas ", "e com ", "e quero", "tambem", "ainda quero", "alem")):
        return False
    return any(
        extraidas.get(chave) not in (None, "")
        for chave in ("cambio", "tipo", "modelo", "combustivel")
    )


def buscar(mensagem, veiculos, prefs, org_id, nome_loja, limite=3, interpretacoes=None):
    extraidas, notas = recomendacao.extrair_preferencias(mensagem)
    estado = mesclar_estado(prefs, extraidas)
    if _parece_nova_busca(mensagem, extraidas):
        for chave in recomendacao.ORDEM_DURA:
            if extraidas.get(chave) in (None, ""):
                estado.pop(chave, None)
    estado = enriquecer_preferencias(mensagem, veiculos, estado)
    notas = list(interpretacoes or []) + list(notas or [])
    citados, nome_ausente = _pedido_de_modelo(mensagem, veiculos)
    if nome_ausente:
        for chave in ("modelo", "veiculo_id", "_ultima_sugestao"):
            estado.pop(chave, None)
        return _resultado(
            f"Não encontrei {nome_ausente.title()} no estoque disponível. Posso buscar por tipo, orçamento ou outra marca.",
            "busca", correspondencia="vazia", preferencias=estado,
        )
    if any(t in normalizar(mensagem) for t in ("tem ", "existe ", "disponivel")) and recomendacao.preferencias_vazias(estado):
        if not citados and not estado.get("modelo"):
            return _resultado(
                "Não encontrei esse modelo no estoque disponível. Posso buscar por tipo, orçamento ou outra marca.",
                "busca", correspondencia="vazia", preferencias=estado,
            )
    if recomendacao.preferencias_vazias(estado) and estado.get("prioridade"):
        return _buscar_por_prioridade(veiculos, estado, org_id, limite)
    resultado = recomendacao.responder(veiculos, estado, org_id, nome_loja, limite, notas)
    if resultado["correspondencia"] == "vazia" and not resultado.get("alternativas"):
        herdadas = [
            chave for chave in recomendacao.ORDEM_DURA
            if estado.get(chave) not in (None, "") and extraidas.get(chave) in (None, "")
        ]
        atuais = [
            chave for chave in recomendacao.ORDEM_DURA
            if extraidas.get(chave) not in (None, "")
        ]
        for chave in herdadas + list(reversed(atuais)):
            if estado.get(chave) in (None, ""):
                continue
            reduzidas = dict(estado)
            reduzidas.pop(chave, None)
            proximo = recomendacao.responder(veiculos, reduzidas, org_id, nome_loja, limite, notas)
            if proximo.get("sugestoes"):
                if chave in herdadas:
                    estado = reduzidas
                    resultado = proximo
                    resultado["texto"] = proximo["texto"]
                else:
                    resultado["alternativas"] = proximo["sugestoes"]
                    resultado["texto"] += (
                        f" Separei opções próximas, relaxando o filtro de {recomendacao._nome_filtro(chave)}."
                    )
                break
    resultado["texto"] = _voz_busca(resultado, nome_loja)
    resultado["intencao"] = "busca"
    resultado["preferencias"] = estado
    resultado["interpretacoes"] = notas
    return resultado


def _lembrar_sugestao(resultado):
    prefs = dict(resultado.get("preferencias") or {})
    prefs["_intencao"] = resultado.get("intencao")
    ids = [item.get("id") for item in (resultado.get("sugestoes") or []) if item.get("id")]
    if ids:
        prefs["_ultima_sugestao"] = ids[0]
        prefs["veiculo_id"] = prefs.get("veiculo_id") or ids[0]
    resultado["preferencias"] = prefs
    return resultado


def _acao_consultor(prefs=None):
    acao = {"tipo": "contato", "rotulo": "Conversar com um consultor"}
    veiculo_id = (prefs or {}).get("veiculo_id") or (prefs or {}).get("_ultima_sugestao")
    if veiculo_id:
        acao["veiculo_id"] = veiculo_id
    return acao


def _deve_oferecer_consultor(mensagem, resultado):
    if eh_fechamento(mensagem):
        return True
    if resultado.get("intencao") == "simulacao" and resultado.get("simulacao"):
        return True
    return False


def _com_consultor(resultado, mensagem):
    if not _deve_oferecer_consultor(mensagem, resultado):
        acao = resultado.get("acao")
        if acao and acao.get("tipo") == "contato" and not acao.get("rotulo"):
            acao["rotulo"] = "Conversar com um consultor"
        return resultado
    acao = resultado.get("acao")
    if not acao or acao.get("tipo") != "contato":
        resultado["acao"] = _acao_consultor(resultado.get("preferencias"))
    else:
        acao["rotulo"] = acao.get("rotulo") or "Conversar com um consultor"
        resultado["acao"] = acao
    texto = (resultado.get("texto") or "").rstrip()
    if "consultor" not in texto.lower():
        resultado["texto"] = texto + " Se quiser seguir, clique para conversar com um consultor da loja."
    return resultado


def orquestrar(mensagem, veiculos, prefs, organizacao, configuracao, intencao=None, limite=3):
    estado = dict(prefs or {})
    intencao_atual = identificar_intencao(mensagem, intencao, estado.get("_intencao"))
    nome_loja = configuracao["trade_name"] if configuracao else organizacao.get("name", "a loja")
    if not (mensagem or "").strip():
        abertura = _abrir_especialidade(intencao_atual, estado)
        if abertura:
            return _lembrar_sugestao(abertura)
    if intencao_atual == "simulacao":
        resultado = simular(mensagem, estado, veiculos)
    elif intencao_atual == "comparacao":
        resultado = comparar(mensagem, veiculos, estado)
    elif intencao_atual == "detalhes":
        resultado = detalhar(mensagem, veiculos, estado)
    elif intencao_atual == "atendimento":
        resultado = responder_atendimento(estado)
    elif intencao_atual == "agendamento":
        resultado = responder_agendamento(estado)
    elif intencao_atual == "loja":
        resultado = responder_loja(mensagem, organizacao, configuracao, estado)
    elif intencao_atual == "saudacao":
        resultado = responder_saudacao(estado)
    elif intencao_atual == "cortesia":
        resultado = responder_cortesia(mensagem, estado)
    elif intencao_atual == "ajuda":
        resultado = responder_ajuda(estado)
    elif intencao_atual == "fora":
        resultado = responder_fora(estado)
    else:
        resultado = buscar(mensagem, veiculos, estado, organizacao["id"], nome_loja, limite)
    return _lembrar_sugestao(_com_consultor(resultado, mensagem))
