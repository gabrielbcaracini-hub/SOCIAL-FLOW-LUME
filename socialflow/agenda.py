"""Regras de horário e conflito. A confirmação não é automática."""

from datetime import datetime, time, timedelta

from socialflow.dominio import DIAS, STATUS_OCUPAM
from socialflow.erros import ErroHttp
from socialflow.tempo import TZ, agora


def sobrepoe(inicio_a, fim_a, inicio_b, fim_b):
    return inicio_a < fim_b and fim_a > inicio_b


def validar_janela(inicio, expediente, referencia=None):
    if inicio is None:
        raise ErroHttp(400, "Informe o horário no formato AAAA-MM-DDTHH:MM.", {"inicio": "Horário inválido."})
    if not isinstance(expediente, dict):
        raise ErroHttp(400, "Expediente da loja indisponível.")
    local = inicio.astimezone(TZ).replace(microsecond=0)
    referencia = (referencia or agora()).astimezone(TZ)
    if local <= referencia:
        raise ErroHttp(400, "Escolha um horário futuro.", {"inicio": "Horário no passado."})
    if local.minute != 0 or local.second != 0:
        raise ErroHttp(400, "Os horários são de hora em hora, no minuto zero.", {"inicio": "Use hora cheia."})
    dia = DIAS[local.weekday()]
    faixa = expediente.get(dia)
    if not faixa:
        raise ErroHttp(400, "A loja não atende nesse dia.", {"inicio": "Dia sem expediente."})
    abre = _hora(faixa[0])
    fecha = _hora(faixa[1])
    fim = local + timedelta(hours=1)
    if fim.date() != local.date() or local.time() < abre or fim.time() > fecha:
        raise ErroHttp(400, "Horário fora do expediente da loja.", {"inicio": "Fora do expediente."})
    return local, fim


def _hora(texto):
    hora, minuto = texto.split(":")
    return time(int(hora), int(minuto))


def conflito_ocupado(candidatos, inicio, fim, ignorar_id=None):
    """Conflito real: outro agendamento confirmado ou reagendado do mesmo veículo."""
    for item in candidatos:
        if ignorar_id and item["id"] == ignorar_id:
            continue
        if item["status"] not in STATUS_OCUPAM:
            continue
        if sobrepoe(inicio, fim, item["inicio"], item["fim"]):
            return item
    return None


def contar_outros_pedidos(candidatos, inicio, fim, ignorar_id=None):
    total = 0
    for item in candidatos:
        if ignorar_id and item["id"] == ignorar_id:
            continue
        if item["status"] != "solicitado":
            continue
        if sobrepoe(inicio, fim, item["inicio"], item["fim"]):
            total += 1
    return total
