"""Filtros e ordenação do catálogo. Funções puras, usadas pela API."""

from socialflow.dominio import GRUPO_AUTOMATICO, STATUS_PUBLICOS


def cambio_compativel(pedido, real):
    if not pedido:
        return True
    if pedido == "automaticos":
        return real in GRUPO_AUTOMATICO
    return pedido == real


def passa_filtros(veiculo, filtros):
    if filtros.get("status"):
        if veiculo["status"] != filtros["status"]:
            return False
    elif veiculo["status"] not in STATUS_PUBLICOS:
        return False
    if filtros.get("marca") and filtros["marca"] not in veiculo["brand"].casefold():
        return False
    if filtros.get("q"):
        bloco = " ".join([
            veiculo["brand"], veiculo["model"], veiculo["version"], veiculo["stock_code"],
        ]).casefold()
        if filtros["q"] not in bloco:
            return False
    if filtros.get("preco_max_centavos") is not None and veiculo["price_cents"] > filtros["preco_max_centavos"]:
        return False
    if not cambio_compativel(filtros.get("cambio") or "", veiculo["transmission"]):
        return False
    if filtros.get("tipo") and veiculo["body_type"] != filtros["tipo"]:
        return False
    if filtros.get("combustivel") and veiculo["fuel"] != filtros["combustivel"]:
        return False
    if filtros.get("km_max") is not None and veiculo["km"] > filtros["km_max"]:
        return False
    if filtros.get("ano_min") is not None and veiculo["year_model"] < filtros["ano_min"]:
        return False
    return True


def aplicar_filtros(veiculos, filtros):
    return [veiculo for veiculo in veiculos if passa_filtros(veiculo, filtros)]


def ordenar(veiculos, ordem):
    if ordem == "preco_desc":
        chave = lambda v: (-v["price_cents"], v["stock_code"])
    elif ordem == "ano_desc":
        chave = lambda v: (-v["year_model"], v["price_cents"], v["stock_code"])
    elif ordem == "km_asc":
        chave = lambda v: (v["km"], v["price_cents"], v["stock_code"])
    else:
        chave = lambda v: (v["price_cents"], v["stock_code"])
    return sorted(veiculos, key=chave)
