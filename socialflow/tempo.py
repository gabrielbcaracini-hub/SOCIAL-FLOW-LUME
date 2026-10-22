"""Horário de Brasília com deslocamento fixo UTC−3.

O Python desta máquina não traz a base IANA (tzdata). O Brasil não usa horário
de verão desde 2019, então o deslocamento fixo representa o expediente da loja
sem depender de pacote externo.
"""

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=-3), name="BRT")


def agora():
    return datetime.now(TZ).replace(microsecond=0)


def iso(momento=None):
    momento = momento or agora()
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=TZ)
    return momento.astimezone(TZ).isoformat(timespec="seconds")


def parse_inicio(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None
    texto = valor.strip().replace("Z", "+00:00")
    try:
        momento = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=TZ)
    return momento.astimezone(TZ).replace(microsecond=0)


def proximo_dia_util(weekday, hora, minuto=0, referencia=None):
    """Próxima ocorrência futura do dia da semana, com folga mínima de 2 horas."""
    base = (referencia or agora()).astimezone(TZ)
    dias = (weekday - base.weekday()) % 7
    candidato = (base + timedelta(days=dias)).replace(
        hour=hora, minute=minuto, second=0, microsecond=0
    )
    if candidato <= base + timedelta(hours=2):
        candidato += timedelta(days=7)
    return candidato
