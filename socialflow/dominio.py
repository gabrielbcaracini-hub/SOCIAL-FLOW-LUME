"""Enumerações, rótulos e regras de estado do estoque."""

CAMBIOS = ("manual", "automatico", "cvt", "automatizado")
CAMBIOS_PREFERENCIA = CAMBIOS + ("automaticos",)
COMBUSTIVEIS = ("flex", "gasolina", "etanol", "diesel", "hibrido", "eletrico")
TIPOS = ("hatch", "sedan", "suv", "pickup", "minivan", "esportivo")
STATUS_VEICULO = ("disponivel", "reservado", "vendido", "indisponivel")
STATUS_PUBLICOS = ("disponivel", "reservado")
STATUS_LEAD = ("novo", "contatado", "negociacao", "ganho", "perdido")
STATUS_AGENDA = ("solicitado", "confirmado", "reagendado", "cancelado", "realizado")
STATUS_OCUPAM = ("confirmado", "reagendado")
ORIGENS_LEAD = ("vitrine", "detalhe", "assistente", "visita", "contato")
PAPEIS = ("admin", "vendedor")
TIPOS_VISITA = ("visita", "test_drive")
USOS = ("familia", "cidade", "trabalho", "viagem")
ORDENS = ("preco_asc", "preco_desc", "ano_desc", "km_asc")
DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")

GRUPO_AUTOMATICO = frozenset({"automatico", "cvt", "automatizado"})

USO_TIPOS = {
    "familia": frozenset({"suv", "minivan", "sedan"}),
    "cidade": frozenset({"hatch", "sedan"}),
    "trabalho": frozenset({"pickup", "suv"}),
    "viagem": frozenset({"sedan", "suv"}),
}

TRANSICOES_VEICULO = {
    "disponivel": frozenset({"disponivel", "reservado", "vendido", "indisponivel"}),
    "reservado": frozenset({"reservado", "disponivel", "vendido", "indisponivel"}),
    "vendido": frozenset({"vendido", "disponivel"}),
    "indisponivel": frozenset({"indisponivel", "disponivel"}),
}

ROTULOS = {
    "cambio": {
        "manual": "Manual",
        "automatico": "Automático",
        "cvt": "CVT",
        "automatizado": "Automatizado",
        "automaticos": "Automático (inclui CVT e automatizado)",
    },
    "combustivel": {
        "flex": "Flex",
        "gasolina": "Gasolina",
        "etanol": "Etanol",
        "diesel": "Diesel",
        "hibrido": "Híbrido",
        "eletrico": "Elétrico",
    },
    "tipo": {
        "hatch": "Hatch",
        "sedan": "Sedã",
        "suv": "SUV",
        "pickup": "Picape",
        "minivan": "Minivan",
        "esportivo": "Esportivo",
    },
    "status_veiculo": {
        "disponivel": "Disponível",
        "reservado": "Reservado",
        "vendido": "Vendido",
        "indisponivel": "Indisponível",
    },
    "status_lead": {
        "novo": "Novo",
        "contatado": "Contatado",
        "negociacao": "Negociação",
        "ganho": "Ganho",
        "perdido": "Perdido",
    },
    "status_agenda": {
        "solicitado": "Solicitado",
        "confirmado": "Confirmado",
        "reagendado": "Reagendado",
        "cancelado": "Cancelado",
        "realizado": "Realizado",
    },
    "origem": {
        "vitrine": "Vitrine",
        "detalhe": "Página do veículo",
        "assistente": "Consultor de estoque",
        "visita": "Pedido de visita",
        "contato": "Contato com consultor",
    },
    "visita": {"visita": "Visita à loja", "test_drive": "Test-drive"},
    "uso": {
        "familia": "família",
        "cidade": "cidade",
        "trabalho": "trabalho",
        "viagem": "viagem",
    },
    "papel": {"admin": "Administração", "vendedor": "Vendas"},
    "dia": {
        "seg": "segunda-feira",
        "ter": "terça-feira",
        "qua": "quarta-feira",
        "qui": "quinta-feira",
        "sex": "sexta-feira",
        "sab": "sábado",
        "dom": "domingo",
    },
}


def rotulo(grupo, valor):
    return ROTULOS.get(grupo, {}).get(valor, valor or "")


def pode_transicionar_veiculo(origem, destino):
    return destino in TRANSICOES_VEICULO.get(origem, frozenset())


def aparece_na_vitrine(status):
    return status in STATUS_PUBLICOS


def pode_recomendar(status):
    return status == "disponivel"


def pode_agendar(status):
    return status == "disponivel"
