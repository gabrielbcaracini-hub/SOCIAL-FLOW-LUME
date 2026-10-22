"""Casos de uso. A organização da sessão ou a loja pública limitam toda consulta."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from socialflow import agenda, apresentacao, banco, catalogo, ia, luna, recomendacao, seguranca, semear, validacao
from socialflow.apresentacao import carregar_json, loja_publica, serializar_veiculo, url_imagem
from socialflow.config import SLUG_PUBLICO
from socialflow.dominio import (
    STATUS_AGENDA,
    STATUS_LEAD,
    STATUS_VEICULO,
    pode_agendar,
    pode_recomendar,
    pode_transicionar_veiculo,
    rotulo,
)
from socialflow.erros import ErroHttp
from socialflow.tempo import agora, iso, parse_inicio


@contextmanager
def _conexao(pedido):
    conn = banco.conectar(pedido.config.db_path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def _transacao(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _id():
    return str(uuid.uuid4())


def _auditar(conn, org_id, user_id, acao, entidade, entidade_id):
    conn.execute(
        """
        INSERT INTO audit_log (id, organization_id, user_id, action, entity, entity_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (_id(), org_id, user_id, acao, entidade, entidade_id, iso()),
    )


def _org_publica(conn):
    row = conn.execute("SELECT * FROM organizations WHERE slug = ?", (SLUG_PUBLICO,)).fetchone()
    if not row:
        raise ErroHttp(500, "Loja demonstrativa não configurada.")
    return row


def _configuracao(conn, org_id):
    row = conn.execute(
        "SELECT * FROM business_settings WHERE organization_id = ?", (org_id,)
    ).fetchone()
    if not row:
        raise ErroHttp(500, "Configuração da loja não encontrada.")
    return row


def _contexto_cliente(conn, cookies):
    ctx_id = cookies.get("sf_ctx")
    if not ctx_id:
        return None
    row = conn.execute("SELECT * FROM client_contexts WHERE id = ?", (ctx_id,)).fetchone()
    if not row or row["expires_at"] <= iso():
        return None
    return row


def _exigir_csrf(conn, pedido):
    ctx = _contexto_cliente(conn, pedido.cookies)
    if not ctx or not seguranca.comparar(ctx["csrf_token"], pedido.csrf):
        raise ErroHttp(403, "A solicitação não pôde ser confirmada. Atualize a página.")
    return ctx


def _usuario(conn, cookies):
    sessao = cookies.get("sf_sessao")
    if not sessao:
        return None
    row = conn.execute(
        """
        SELECT u.id, u.organization_id, u.name, u.email, u.role, u.active, s.expires_at
        FROM auth_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.id = ? AND u.active = 1
        """,
        (sessao,),
    ).fetchone()
    if not row or row["expires_at"] <= iso():
        return None
    return row


def _exigir_usuario(conn, pedido):
    usuario = _usuario(conn, pedido.cookies)
    if not usuario:
        raise ErroHttp(401, "É preciso entrar para acessar o painel.")
    return usuario


def _exigir_admin(usuario):
    if usuario["role"] != "admin":
        raise ErroHttp(403, "Somente a administração da loja pode alterar as configurações.")
    return usuario


def _veiculo_org(conn, org_id, veiculo_id):
    row = conn.execute(
        "SELECT * FROM vehicles WHERE id = ? AND organization_id = ?",
        (veiculo_id, org_id),
    ).fetchone()
    if not row:
        raise ErroHttp(404, "Veículo não encontrado nesta loja.")
    return row


def _imagens(conn, ids):
    if not ids:
        return {}
    marcas = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM vehicle_images WHERE vehicle_id IN ({marcas}) ORDER BY sort_order, created_at",
        tuple(ids),
    ).fetchall()
    grupos = {identificador: [] for identificador in ids}
    for row in rows:
        grupos.setdefault(row["vehicle_id"], []).append(row)
    return grupos


def _serial_lista(conn, veiculos, publico=False):
    grupos = _imagens(conn, [v["id"] for v in veiculos])
    return [serializar_veiculo(v, grupos.get(v["id"], []), publico=publico) for v in veiculos]


def _limite(pedido, acao, maximo):
    seguranca.limitar(f"{pedido.ip}|{acao}", maximo, pedido.config.janela_segundos)


def contexto(pedido):
    with _conexao(pedido) as conn:
        cookies = []
        ctx = _contexto_cliente(conn, pedido.cookies)
        if not ctx:
            ctx_id = seguranca.novo_token()
            csrf = seguranca.novo_token()
            momento = agora()
            conn.execute(
                """
                INSERT INTO client_contexts (id, csrf_token, session_id, expires_at, created_at)
                VALUES (?, ?, NULL, ?, ?)
                """,
                (ctx_id, csrf, iso(momento + timedelta(hours=12)), iso(momento)),
            )
            cookies.append(seguranca.cookie("sf_ctx", ctx_id, 12 * 3600))
        else:
            csrf = ctx["csrf_token"]
        org = _org_publica(conn)
        config = _configuracao(conn, org["id"])
        usuario = _usuario(conn, pedido.cookies)
        return {
            "csrf": csrf,
            "loja": loja_publica(org, config),
            "consultor_modo": (
                "gemini" if pedido.config.ai_key and ia.provedor(pedido.config) == "gemini"
                else "generativo_opcional" if pedido.config.ai_key
                else "deterministico"
            ),
            "usuario": None if not usuario else {
                "nome": usuario["name"],
                "email": usuario["email"],
                "papel": usuario["role"],
                "papel_rotulo": rotulo("papel", usuario["role"]),
            },
        }, cookies


def entrar(pedido, corpo):
    _limite(pedido, "login", pedido.config.limite_login)
    if not isinstance(corpo, dict):
        raise ErroHttp(400, "Dados de acesso inválidos.")
    email = validacao.email_obrigatorio(corpo.get("email"))
    senha = corpo.get("senha") if isinstance(corpo.get("senha"), str) else ""
    with _conexao(pedido) as conn:
        ctx = _exigir_csrf(conn, pedido)
        usuario = conn.execute(
            "SELECT * FROM users WHERE email = ? AND active = 1", (email,)
        ).fetchone()
        armazenada = usuario["password_hash"] if usuario else ""
        if not seguranca.verificar_senha(senha, armazenada) or not usuario:
            raise ErroHttp(401, "E-mail ou senha incorretos.")
        with _transacao(conn):
            sessao = seguranca.novo_token()
            csrf = seguranca.novo_token()
            momento = agora()
            conn.execute(
                "INSERT INTO auth_sessions (id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (sessao, usuario["id"], iso(momento + timedelta(hours=12)), iso(momento)),
            )
            conn.execute(
                "UPDATE client_contexts SET csrf_token = ?, session_id = ? WHERE id = ?",
                (csrf, sessao, ctx["id"]),
            )
            _auditar(conn, usuario["organization_id"], usuario["id"], "login", "user", usuario["id"])
        return {
            "csrf": csrf,
            "usuario": {
                "nome": usuario["name"],
                "email": usuario["email"],
                "papel": usuario["role"],
                "papel_rotulo": rotulo("papel", usuario["role"]),
            },
        }, [seguranca.cookie("sf_sessao", sessao, 12 * 3600)]


def sair(pedido):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        sessao = pedido.cookies.get("sf_sessao")
        if sessao:
            conn.execute("DELETE FROM auth_sessions WHERE id = ?", (sessao,))
        return {"ok": True}, [seguranca.cookie("sf_sessao", "", 0)]


def veiculos_publicos(pedido):
    filtros = validacao.filtros_publicos(pedido.query)
    with _conexao(pedido) as conn:
        org = _org_publica(conn)
        brutos = [
            dict(row) for row in conn.execute(
                "SELECT * FROM vehicles WHERE organization_id = ?", (org["id"],)
            ).fetchall()
        ]
        filtrados = catalogo.ordenar(catalogo.aplicar_filtros(brutos, filtros), filtros["ordem"])[:60]
        return {"veiculos": _serial_lista(conn, filtrados, publico=True), "total": len(filtrados)}, []


def veiculo_publico(pedido, veiculo_id):
    with _conexao(pedido) as conn:
        org = _org_publica(conn)
        try:
            row = _veiculo_org(conn, org["id"], veiculo_id)
        except ErroHttp:
            raise ErroHttp(404, "Este veículo não está disponível nesta vitrine.")
        if not row["status"] in ("disponivel", "reservado"):
            raise ErroHttp(404, "Este veículo não está disponível nesta vitrine.")
        return {"veiculo": _serial_lista(conn, [dict(row)], publico=True)[0]}, []


def _gravar_lead(conn, org_id, veiculo_id, origem, nome, telefone, email, prefs, resumo, assignee_id=None):
    lead_id = _id()
    momento = iso()
    conn.execute(
        """
        INSERT INTO leads (
            id, organization_id, vehicle_id, origin, contact_name, contact_phone, contact_email,
            consent, preferences_json, status, notes, assignee_id, summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, 'novo', '', ?, ?, ?, ?)
        """,
        (
            lead_id, org_id, veiculo_id, origem, nome, telefone, email,
            json.dumps(prefs, ensure_ascii=False), assignee_id, resumo, momento, momento,
        ),
    )
    _auditar(conn, org_id, None, "criar_lead", "lead", lead_id)
    return lead_id


def criar_lead(pedido, corpo):
    _limite(pedido, "formulario", pedido.config.limite_formulario)
    dados = validacao.payload_lead_publico(corpo)
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        with _transacao(conn):
            origem = "vitrine"
            prefs = {}
            resumo = "Interesse registrado pela vitrine."
            veiculo_id = None
            if dados["sessao_id"]:
                sessao = conn.execute(
                    "SELECT * FROM chat_sessions WHERE id = ? AND organization_id = ?",
                    (dados["sessao_id"], org["id"]),
                ).fetchone()
                if not sessao:
                    raise ErroHttp(400, "Não encontrei a conversa para encaminhar à equipe.")
                prefs = carregar_json(sessao["preference_json"], {})
                ids = []
                ultimo = conn.execute(
                    """
                    SELECT structured_json FROM chat_messages
                    WHERE session_id = ? ORDER BY created_at DESC LIMIT 1
                    """,
                    (sessao["id"],),
                ).fetchone()
                if ultimo:
                    ids = carregar_json(ultimo["structured_json"], {}).get("ids") or []
                codigos = []
                for identificador in ids:
                    row = conn.execute(
                        "SELECT stock_code FROM vehicles WHERE id = ? AND organization_id = ? AND status = 'disponivel'",
                        (identificador, org["id"]),
                    ).fetchone()
                    if row:
                        codigos.append(row["stock_code"])
                resumo = recomendacao.resumo_preferencias(prefs, codigos)
                origem = "assistente"
                if dados["veiculo_id"]:
                    veiculo = _veiculo_org(conn, org["id"], dados["veiculo_id"])
                    if veiculo["status"] not in ("disponivel", "reservado"):
                        raise ErroHttp(409, "Esse veículo não está disponível para interesse.")
                    veiculo_id = veiculo["id"]
                lead_id = _gravar_lead(conn, org["id"], veiculo_id, origem, dados["nome"], dados["telefone"], dados["email"], prefs, resumo)
                conn.execute(
                    "UPDATE chat_sessions SET handoff = 1, lead_id = ?, updated_at = ? WHERE id = ?",
                    (lead_id, iso(), sessao["id"]),
                )
            else:
                assignee_id = None
                if dados["veiculo_id"]:
                    veiculo = _veiculo_org(conn, org["id"], dados["veiculo_id"])
                    if veiculo["status"] not in ("disponivel", "reservado"):
                        raise ErroHttp(409, "Esse veículo não está disponível para interesse.")
                    veiculo_id = veiculo["id"]
                    origem = "detalhe"
                    if not dados["consultor_id"]:
                        raise ErroHttp(
                            400,
                            "Escolha o consultor que vai atender.",
                            {"consultor_id": "Consultor obrigatório."},
                        )
                    consultor = _consultor_vendedor(conn, org["id"], dados["consultor_id"])
                    assignee_id = consultor["id"]
                    resumo = f"Interesse no estoque {veiculo['stock_code']} {veiculo['brand']} {veiculo['model']} {veiculo['version']}."
                    prefs = {"veiculo_id": veiculo_id, "consultor_id": consultor["id"]}
                lead_id = _gravar_lead(
                    conn, org["id"], veiculo_id, origem, dados["nome"], dados["telefone"],
                    dados["email"], prefs, resumo, assignee_id,
                )
        return {"id": lead_id, "status": "novo", "mensagem": "Interesse registrado. A equipe vê o pedido no painel; isso ainda não reserva o veículo."}, []


def _consultor_vendedor(conn, org_id, consultor_id):
    row = conn.execute(
        """
        SELECT id, name FROM users
        WHERE id = ? AND organization_id = ? AND active = 1 AND role = 'vendedor'
        """,
        (consultor_id, org_id),
    ).fetchone()
    if not row:
        raise ErroHttp(
            400,
            "Escolha um consultor da loja.",
            {"consultor_id": "Consultor obrigatório."},
        )
    return row


def consultores_publicos(pedido):
    with _conexao(pedido) as conn:
        org = _org_publica(conn)
        rows = conn.execute(
            """
            SELECT id, name FROM users
            WHERE organization_id = ? AND active = 1 AND role = 'vendedor'
            ORDER BY name
            """,
            (org["id"],),
        ).fetchall()
        return {"consultores": [{"id": row["id"], "nome": row["name"]} for row in rows]}, []


def criar_contato(pedido, corpo):
    _limite(pedido, "formulario", pedido.config.limite_formulario)
    dados = validacao.payload_contato(corpo)
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        with _transacao(conn):
            consultor = _consultor_vendedor(conn, org["id"], dados["consultor_id"])
            veiculo_id = None
            if dados["veiculo_id"]:
                veiculo = _veiculo_org(conn, org["id"], dados["veiculo_id"])
                if veiculo["status"] not in ("disponivel", "reservado"):
                    raise ErroHttp(409, "Esse veículo não está na vitrine.")
                veiculo_id = veiculo["id"]
            lead_id = _gravar_lead(
                conn, org["id"], veiculo_id, "contato", dados["nome"], "", dados["email"],
                {"canal": "contato", "consultor_id": consultor["id"]}, dados["mensagem"],
                consultor["id"],
            )
        return {
            "id": lead_id,
            "status": "novo",
            "mensagem": "Mensagem enviada ao consultor. A equipe vê o contato no painel; isso não reserva o veículo nem confirma a visita.",
        }, []


def criar_agenda(pedido, corpo):
    _limite(pedido, "formulario", pedido.config.limite_formulario)
    dados = validacao.payload_agenda_publico(corpo)
    inicio = parse_inicio(dados["inicio"])
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        config = _configuracao(conn, org["id"])
        expediente = carregar_json(config["hours_json"], {})
        local, fim = agenda.validar_janela(inicio, expediente)
        with _transacao(conn):
            veiculo = _veiculo_org(conn, org["id"], dados["veiculo_id"])
            if not pode_agendar(veiculo["status"]):
                raise ErroHttp(409, "Só agendamos visita para veículo disponível.")
            resumo = f"Pedido de {rotulo('visita', dados['tipo'])} para {veiculo['stock_code']}."
            lead_id = _gravar_lead(
                conn, org["id"], veiculo["id"], "visita", dados["nome"], dados["telefone"],
                dados["email"], {"veiculo_id": veiculo["id"], "tipo": dados["tipo"]}, resumo,
            )
            agenda_id = _id()
            momento = iso()
            conn.execute(
                """
                INSERT INTO appointments (
                    id, organization_id, lead_id, vehicle_id, kind, status, starts_at, ends_at,
                    contact_name, contact_phone, contact_email, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'solicitado', ?, ?, ?, ?, ?, '', ?, ?)
                """,
                (
                    agenda_id, org["id"], lead_id, veiculo["id"], dados["tipo"], iso(local), iso(fim),
                    dados["nome"], dados["telefone"], dados["email"], momento, momento,
                ),
            )
            _auditar(conn, org["id"], None, "solicitar_visita", "appointment", agenda_id)
        return {
            "id": agenda_id,
            "status": "solicitado",
            "mensagem": "Pedido enviado. A equipe precisa confirmar; o horário ainda não está reservado.",
        }, []


def consultor(pedido, corpo):
    _limite(pedido, "consultor", pedido.config.limite_consultor)
    if not isinstance(corpo, dict):
        raise ErroHttp(400, "Mensagem inválida.")
    mensagem = validacao.mensagem_consultor(corpo.get("mensagem"))
    explicitas = validacao.preferencias(corpo.get("preferencias"))
    reiniciar = corpo.get("reiniciar") is True
    sessao_informada = corpo.get("sessao_id") or ""
    if sessao_informada and not isinstance(sessao_informada, str):
        raise ErroHttp(400, "Sessão inválida.")
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        config = _configuracao(conn, org["id"])
        assistente = carregar_json(config["assistant_json"], {})
        extraidas, interpretacoes = recomendacao.extrair_preferencias(
            mensagem, int(assistente.get("baixa_km") or 30000)
        )
        with _transacao(conn):
            sessao = None
            if isinstance(sessao_informada, str) and sessao_informada:
                sessao = conn.execute(
                    "SELECT * FROM chat_sessions WHERE id = ? AND organization_id = ?",
                    (sessao_informada, org["id"]),
                ).fetchone()
            if not sessao:
                sessao_id = _id()
                momento = iso()
                conn.execute(
                    """
                    INSERT INTO chat_sessions (
                        id, organization_id, preference_json, handoff, lead_id, created_at, updated_at
                    ) VALUES (?, ?, '{}', 0, NULL, ?, ?)
                    """,
                    (sessao_id, org["id"], momento, momento),
                )
                sessao = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (sessao_id,)).fetchone()
            anteriores = {} if reiniciar else carregar_json(sessao["preference_json"], {})
            prefs = recomendacao.mesclar(anteriores, extraidas, explicitas, reiniciar=reiniciar)
            veiculos = [
                dict(row) for row in conn.execute(
                    "SELECT * FROM vehicles WHERE organization_id = ?", (org["id"],)
                ).fetchall()
            ]
            resultado = recomendacao.responder(
                veiculos, prefs, org["id"], config["trade_name"],
                assistente.get("max_sugestoes", 3), interpretacoes,
            )
            if recomendacao.pede_assunto_fora(mensagem):
                resultado["texto"] = resultado["texto"] + " " + recomendacao.frase_fora_de_escopo()
                resultado["aviso_escopo"] = True
            else:
                resultado["aviso_escopo"] = False
            por_id = {v["id"]: v for v in veiculos}
            sugestoes = _cards_validos(conn, resultado["sugestoes"], por_id)
            alternativas = _cards_validos(conn, resultado["alternativas"], por_id)
            if len(sugestoes) != len(resultado["sugestoes"]):
                resultado["texto"] = "Não foi possível confirmar todas as sugestões no estoque disponível."
            modo = "deterministico"
            aviso_ia = ""
            if pedido.config.ai_key and sugestoes:
                pacote = []
                for card in sugestoes:
                    bruto = por_id[card["id"]]
                    pacote.append({
                        "id": card["id"],
                        "nome": f"{bruto['brand']} {bruto['model']}",
                        "price_cents": bruto["price_cents"],
                        "motivos": card["motivos"],
                    })
                texto_ia = ia.explicar(pacote, prefs, pedido.config)
                if texto_ia:
                    resultado["texto"] = texto_ia
                    modo = "generativo_explicacao"
                else:
                    aviso_ia = "A explicação generativa não ficou disponível. Mantive a automação determinística."
            foco = _foco_publico(conn, resultado.get("foco"), por_id)
            conn.execute(
                "UPDATE chat_sessions SET preference_json = ?, updated_at = ? WHERE id = ? AND organization_id = ?",
                (json.dumps(prefs, ensure_ascii=False), iso(), sessao["id"], org["id"]),
            )
            conteudo = {
                "exata": "recomendacao",
                "vazia": "sem_correspondencia",
                "incompleta": "incompleta",
            }.get(resultado["correspondencia"], "foco")
            conn.execute(
                """
                INSERT INTO chat_messages (
                    id, organization_id, session_id, role, content, structured_json, created_at
                ) VALUES (?, ?, ?, 'registro', ?, ?, ?)
                """,
                (
                    _id(), org["id"], sessao["id"], conteudo,
                    json.dumps({
                        "ids": [item["id"] for item in sugestoes],
                        "alternativa_ids": [item["id"] for item in alternativas],
                        "filtro_bloqueante": resultado.get("filtro_bloqueante"),
                        "modo": modo,
                    }, ensure_ascii=False),
                    iso(),
                ),
            )
        rotulo_modo = (
            "Texto reescrito por modelo e conferido contra os veículos listados"
            if modo == "generativo_explicacao"
            else "Automação determinística — sem modelo generativo"
        )
        return {
            "sessao_id": sessao["id"],
            "modo": modo,
            "modo_rotulo": rotulo_modo,
            "correspondencia": resultado["correspondencia"],
            "texto": resultado["texto"],
            "sugestoes": sugestoes,
            "alternativas": alternativas,
            "foco": foco,
            "preferencias": resultado["preferencias"],
            "interpretacoes": resultado["interpretacoes"],
            "aviso_escopo": resultado["aviso_escopo"],
            "aviso_ia": aviso_ia,
        }, []


def _cards_validos(conn, itens, por_id):
    if not por_id:
        return []
    org_id = next(iter(por_id.values()))["organization_id"]
    cards = []
    for item in itens:
        bruto = por_id.get(item["id"])
        if not bruto or bruto.get("organization_id") != org_id:
            continue
        if not pode_recomendar(bruto["status"]):
            continue
        card = _serial_lista(conn, [bruto], publico=True)[0]
        card["motivos"] = item.get("motivos") or []
        card["compativel"] = bool(item.get("compativel"))
        card["href"] = "/veiculo?id=" + bruto["id"]
        cards.append(card)
    return cards


def _foco_publico(conn, foco, por_id):
    if not foco:
        return None
    bruto = por_id.get(foco.get("id"))
    if not bruto:
        return {"disponivel": False, "motivos": foco.get("motivos") or [], "href": None}
    if not pode_recomendar(bruto["status"]):
        return {
            "id": bruto["id"],
            "nome": f"{bruto['brand']} {bruto['model']} {bruto['version']}",
            "disponivel": False,
            "status": bruto["status"],
            "status_rotulo": rotulo("status_veiculo", bruto["status"]),
            "motivos": foco.get("motivos") or [],
            "href": None,
        }
    card = _serial_lista(conn, [bruto], publico=True)[0]
    card["motivos"] = foco.get("motivos") or []
    card["compativel"] = bool(foco.get("compativel"))
    card["disponivel"] = True
    card["href"] = "/veiculo?id=" + bruto["id"]
    return card


def luna_assistente(pedido, corpo):
    _limite(pedido, "consultor", pedido.config.limite_consultor)
    if not isinstance(corpo, dict):
        raise ErroHttp(400, "Mensagem inválida.")
    mensagem = validacao.mensagem_consultor(corpo.get("mensagem"))
    intencao = validacao.intencao_luna(corpo.get("intencao"))
    explicitas = validacao.preferencias(corpo.get("preferencias"))
    reiniciar = corpo.get("reiniciar") is True
    sessao_informada = corpo.get("sessao_id") or ""
    if sessao_informada and not isinstance(sessao_informada, str):
        raise ErroHttp(400, "Sessão inválida.")
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        config = _configuracao(conn, org["id"])
        assistente = carregar_json(config["assistant_json"], {})
        limite = max(1, min(int(assistente.get("max_sugestoes") or 3), 5))
        with _transacao(conn):
            sessao = None
            if isinstance(sessao_informada, str) and sessao_informada:
                sessao = conn.execute(
                    "SELECT * FROM chat_sessions WHERE id = ? AND organization_id = ?",
                    (sessao_informada, org["id"]),
                ).fetchone()
            if not sessao:
                sessao_id = _id()
                momento = iso()
                conn.execute(
                    """
                    INSERT INTO chat_sessions (
                        id, organization_id, preference_json, handoff, lead_id, created_at, updated_at
                    ) VALUES (?, ?, '{}', 0, NULL, ?, ?)
                    """,
                    (sessao_id, org["id"], momento, momento),
                )
                sessao = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (sessao_id,)).fetchone()
            anteriores = {} if reiniciar else carregar_json(sessao["preference_json"], {})
            prefs = luna.mesclar_estado(anteriores, explicitas)
            veiculos = [
                dict(row) for row in conn.execute(
                    "SELECT * FROM vehicles WHERE organization_id = ?", (org["id"],)
                ).fetchall()
            ]
            try:
                resultado = luna.orquestrar(
                    mensagem, veiculos, prefs, org, config, intencao=intencao, limite=limite,
                )
            except sqlite3.Error:
                raise ErroHttp(503, "Não consegui consultar o estoque agora. Tente de novo em instantes.")
            por_id = {v["id"]: v for v in veiculos}
            sugestoes = _cards_validos(conn, resultado.get("sugestoes") or [], por_id)
            alternativas = _cards_validos(conn, resultado.get("alternativas") or [], por_id)
            modo = "deterministico"
            aviso_ia = ""
            texto = resultado.get("texto") or "Consultei o estoque da loja."
            if pedido.config.ai_key:
                fatos_ia = {
                    "mensagem": mensagem,
                    "intencao": resultado.get("intencao"),
                    "ids": [item["id"] for item in sugestoes],
                    "veiculos": [
                        {"id": item["id"], "nome": item.get("nome"), "preco": item.get("preco")}
                        for item in sugestoes + alternativas
                    ],
                    "simulacao": resultado.get("simulacao"),
                    "acao": resultado.get("acao"),
                    "loja": {
                        "nome": config["trade_name"],
                        "endereco": config["address_public"],
                    },
                    "preferencias": ia.prefs_publicas(resultado.get("preferencias") or {}),
                }
                if resultado.get("intencao") == "fora":
                    texto_ia = ia.auxiliar_fora(mensagem, fatos_ia, pedido.config)
                    if texto_ia:
                        modo = "generativo_fora"
                else:
                    texto_ia = ia.redigir_luna(texto, fatos_ia, pedido.config)
                    if texto_ia:
                        modo = "generativo"
                if texto_ia:
                    texto = texto_ia
                else:
                    texto = ia.embelezar_luna(texto, resultado.get("intencao") or "")
            else:
                texto = ia.embelezar_luna(texto, resultado.get("intencao") or "")
            prefs_salvas = resultado.get("preferencias") or prefs
            conn.execute(
                "UPDATE chat_sessions SET preference_json = ?, updated_at = ? WHERE id = ? AND organization_id = ?",
                (json.dumps(prefs_salvas, ensure_ascii=False), iso(), sessao["id"], org["id"]),
            )
            conn.execute(
                """
                INSERT INTO chat_messages (
                    id, organization_id, session_id, role, content, structured_json, created_at
                ) VALUES (?, ?, ?, 'registro', ?, ?, ?)
                """,
                (
                    _id(), org["id"], sessao["id"],
                    {
                        "exata": "recomendacao",
                        "vazia": "sem_correspondencia",
                        "incompleta": "incompleta",
                    }.get(resultado.get("correspondencia"), "foco"),
                    json.dumps({
                        "ids": [item["id"] for item in sugestoes],
                        "alternativa_ids": [item["id"] for item in alternativas],
                        "intencao": resultado.get("intencao"),
                        "modo": modo,
                    }, ensure_ascii=False),
                    iso(),
                ),
            )
        return {
            "sessao_id": sessao["id"],
            "modo": modo,
            "modo_rotulo": (
                "Luna com Gemini"
                if modo in {"generativo", "generativo_fora"}
                else "Consulta ao estoque com o script da Luna"
            ),
            "correspondencia": resultado.get("correspondencia"),
            "intencao": resultado.get("intencao"),
            "texto": texto,
            "sugestoes": sugestoes,
            "alternativas": alternativas,
            "comparacao": resultado.get("comparacao"),
            "simulacao": resultado.get("simulacao"),
            "acao": resultado.get("acao"),
            "preferencias": {
                chave: valor for chave, valor in (prefs_salvas or {}).items()
                if not str(chave).startswith("_")
            },
            "aviso_ia": aviso_ia,
        }, []


def apagar_consultor(pedido, sessao_id):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        org = _org_publica(conn)
        cur = conn.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND organization_id = ?",
            (sessao_id, org["id"]),
        )
        if cur.rowcount == 0:
            raise ErroHttp(404, "Conversa não encontrada.")
        return {"ok": True}, []


def _contagens(conn, tabela, org_id, opcoes):
    base = {opcao: 0 for opcao in opcoes}
    rows = conn.execute(
        f"SELECT status, COUNT(*) AS n FROM {tabela} WHERE organization_id = ? GROUP BY status",
        (org_id,),
    ).fetchall()
    for row in rows:
        if row["status"] in base:
            base[row["status"]] = row["n"]
    return base


def _dias_resumo(query):
    valores = (query or {}).get("dias") or []
    try:
        n = int(valores[0] if valores else 30)
    except (TypeError, ValueError):
        n = 30
    return n if n in (7, 30, 90) else 30


def _variacao(atual, anterior):
    delta = atual - anterior
    if anterior:
        percentual = round(100 * delta / anterior)
    else:
        percentual = 100 if atual else 0
    return {"atual": atual, "anterior": anterior, "delta": delta, "percentual": percentual}


def _contar(conn, sql, params):
    return conn.execute(sql, params).fetchone()["n"]


def _filtro_lead(usuario):
    if usuario["role"] == "admin":
        return "", []
    return " AND (l.origin NOT IN ('contato', 'detalhe') OR l.assignee_id = ?)", [usuario["id"]]


def _serie_leads(conn, org_id, extra, extra_params, inicio, dias):
    rows = conn.execute(
        f"""
        SELECT substr(l.created_at, 1, 10) AS dia, COUNT(*) AS n
        FROM leads l
        WHERE l.organization_id = ? AND l.created_at >= ?{extra}
        GROUP BY dia
        """,
        tuple([org_id, iso(inicio)] + extra_params),
    ).fetchall()
    por_dia = {row["dia"]: row["n"] for row in rows}
    serie = []
    for i in range(dias):
        momento = inicio + timedelta(days=i)
        chave = momento.date().isoformat()
        serie.append({"dia": chave, "rotulo": momento.strftime("%d/%m"), "total": por_dia.get(chave, 0)})
    return serie


def resumo(pedido):
    with _conexao(pedido) as conn:
        usuario = _exigir_usuario(conn, pedido)
        org_id = usuario["organization_id"]
        dias = _dias_resumo(pedido.query)
        agora_ref = agora()
        inicio = (agora_ref - timedelta(days=dias - 1)).replace(hour=0, minute=0, second=0)
        anterior_inicio = inicio - timedelta(days=dias)
        corte = iso(inicio)
        corte_ant = iso(anterior_inicio)
        extra, extra_params = _filtro_lead(usuario)
        veiculos = _contagens(conn, "vehicles", org_id, STATUS_VEICULO)
        leads = _contagens(conn, "leads", org_id, STATUS_LEAD)
        mais = conn.execute(
            f"""
            SELECT v.id, v.brand, v.model, v.version, v.stock_code,
                   v.year_manufacture, v.year_model, COUNT(l.id) AS total
            FROM leads l
            JOIN vehicles v ON v.id = l.vehicle_id AND v.organization_id = l.organization_id
            WHERE l.organization_id = ?{extra}
            GROUP BY v.id
            ORDER BY total DESC, v.stock_code
            LIMIT 5
            """,
            tuple([org_id] + extra_params),
        ).fetchall()
        fotos = _imagens(conn, [row["id"] for row in mais])
        recentes = conn.execute(
            f"""
            SELECT l.*, v.brand, v.model, v.version, v.stock_code, u.name AS assignee_name
            FROM leads l
            LEFT JOIN vehicles v ON v.id = l.vehicle_id AND v.organization_id = l.organization_id
            LEFT JOIN users u ON u.id = l.assignee_id
            WHERE l.organization_id = ?{extra}
            ORDER BY l.created_at DESC
            LIMIT 6
            """,
            tuple([org_id] + extra_params),
        ).fetchall()
        equipe = conn.execute(
            "SELECT id, name, role FROM users WHERE organization_id = ? AND active = 1 ORDER BY name",
            (org_id,),
        ).fetchall()
        novos_periodo = _contar(
            conn,
            f"SELECT COUNT(*) AS n FROM leads l WHERE l.organization_id = ? AND l.created_at >= ?{extra}",
            tuple([org_id, corte] + extra_params),
        )
        novos_antes = _contar(
            conn,
            f"SELECT COUNT(*) AS n FROM leads l WHERE l.organization_id = ? AND l.created_at >= ? AND l.created_at < ?{extra}",
            tuple([org_id, corte_ant, corte] + extra_params),
        )
        vendidos_periodo = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'vendido' AND updated_at >= ?",
            (org_id, corte),
        )
        vendidos_antes = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'vendido' AND updated_at >= ? AND updated_at < ?",
            (org_id, corte_ant, corte),
        )
        reservados_periodo = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'reservado' AND updated_at >= ?",
            (org_id, corte),
        )
        reservados_antes = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'reservado' AND updated_at >= ? AND updated_at < ?",
            (org_id, corte_ant, corte),
        )
        disponiveis_periodo = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'disponivel' AND created_at >= ?",
            (org_id, corte),
        )
        disponiveis_antes = _contar(
            conn,
            "SELECT COUNT(*) AS n FROM vehicles WHERE organization_id = ? AND status = 'disponivel' AND created_at >= ? AND created_at < ?",
            (org_id, corte_ant, corte),
        )
        return {
            "aviso": "Indicadores calculados dos registros desta base demonstrativa.",
            "periodo": {"dias": dias, "inicio": iso(inicio), "fim": iso(agora_ref)},
            "veiculos": veiculos,
            "leads": leads,
            "agendamentos": _contagens(conn, "appointments", org_id, STATUS_AGENDA),
            "comparativo": {
                "disponivel": _variacao(disponiveis_periodo, disponiveis_antes),
                "reservado": _variacao(reservados_periodo, reservados_antes),
                "vendido": _variacao(vendidos_periodo, vendidos_antes),
                "leads_novos": _variacao(novos_periodo, novos_antes),
            },
            "serie_leads": _serie_leads(conn, org_id, extra, extra_params, inicio, dias),
            "mais_procurados": [
                {
                    "id": row["id"],
                    "titulo": f"{row['brand']} {row['model']} {row['version']}",
                    "nome": f"{row['brand']} {row['model']}",
                    "codigo": row["stock_code"],
                    "ano_fabricacao": row["year_manufacture"],
                    "ano_modelo": row["year_model"],
                    "total": row["total"],
                    "foto": url_imagem(fotos[row["id"]][0]) if fotos.get(row["id"]) else "/assets/marca.jpg",
                }
                for row in mais
            ],
            "leads_recentes": [
                _lead_json(row, row if row["stock_code"] else None)
                for row in recentes
            ],
            "equipe": [
                {"id": row["id"], "nome": row["name"], "papel": row["role"], "papel_rotulo": rotulo("papel", row["role"])}
                for row in equipe
            ],
        }, []


def listar_veiculos_admin(pedido):
    with _conexao(pedido) as conn:
        usuario = _exigir_usuario(conn, pedido)
        rows = [
            dict(row) for row in conn.execute(
                "SELECT * FROM vehicles WHERE organization_id = ? ORDER BY updated_at DESC",
                (usuario["organization_id"],),
            ).fetchall()
        ]
        return {"veiculos": _serial_lista(conn, rows, publico=False)}, []


def _salvar_imagem(pedido, conn, org_id, veiculo_id, conteudo_b64):
    if not conteudo_b64:
        return
    bruto, extensao = seguranca.decodificar_imagem(conteudo_b64)
    nome = f"{_id()}.{extensao}"
    pasta = pedido.config.uploads.resolve()
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = (pasta / nome).resolve()
    alvo.relative_to(pasta)
    alvo.write_bytes(bruto)
    conn.execute(
        "UPDATE vehicle_images SET sort_order = sort_order + 1 WHERE vehicle_id = ?",
        (veiculo_id,),
    )
    conn.execute(
        """
        INSERT INTO vehicle_images (
            id, organization_id, vehicle_id, kind, label, path, sort_order, created_at
        ) VALUES (?, ?, ?, 'upload', ?, ?, 0, ?)
        """,
        (_id(), org_id, veiculo_id, "Foto enviada pela loja", nome, iso()),
    )


def _inserir_placeholder(conn, org_id, veiculo_id, tipo):
    conn.execute(
        """
        INSERT INTO vehicle_images (
            id, organization_id, vehicle_id, kind, label, path, sort_order, created_at
        ) VALUES (?, ?, ?, 'placeholder', ?, ?, 1, ?)
        """,
        (
            _id(), org_id, veiculo_id,
            f"Ilustração demonstrativa de {rotulo('tipo', tipo).lower()}. Não é fotografia deste veículo.",
            f"/assets/ilustracoes/{tipo}.svg",
            iso(),
        ),
    )


def criar_veiculo(pedido, corpo):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        dados = validacao.payload_veiculo(corpo)
        try:
            with _transacao(conn):
                vid = _id()
                momento = iso()
                imagem = dados.pop("imagem_base64")
                conn.execute(
                    """
                    INSERT INTO vehicles (
                        id, organization_id, brand, model, version, year_manufacture, year_model, km,
                        transmission, fuel, body_type, price_cents, status, color, description, stock_code,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        vid, usuario["organization_id"], dados["brand"], dados["model"], dados["version"],
                        dados["year_manufacture"], dados["year_model"], dados["km"], dados["transmission"],
                        dados["fuel"], dados["body_type"], dados["price_cents"], dados["status"],
                        dados["color"], dados["description"], dados["stock_code"], momento, momento,
                    ),
                )
                _inserir_placeholder(conn, usuario["organization_id"], vid, dados["body_type"])
                _salvar_imagem(pedido, conn, usuario["organization_id"], vid, imagem)
                _auditar(conn, usuario["organization_id"], usuario["id"], "criar_veiculo", "vehicle", vid)
        except sqlite3.IntegrityError as exc:
            raise ErroHttp(409, _mensagem_integridade(exc))
        row = _veiculo_org(conn, usuario["organization_id"], vid)
        return {"veiculo": _serial_lista(conn, [dict(row)], publico=False)[0]}, []


def atualizar_veiculo(pedido, veiculo_id, corpo):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        atual = _veiculo_org(conn, usuario["organization_id"], veiculo_id)
        dados = validacao.payload_veiculo(corpo, atual)
        if not pode_transicionar_veiculo(atual["status"], dados["status"]):
            raise ErroHttp(409, "Essa troca de status não é permitida.")
        try:
            with _transacao(conn):
                imagem = dados.pop("imagem_base64")
                conn.execute(
                    """
                    UPDATE vehicles SET
                        brand = ?, model = ?, version = ?, year_manufacture = ?, year_model = ?, km = ?,
                        transmission = ?, fuel = ?, body_type = ?, price_cents = ?, status = ?, color = ?,
                        description = ?, stock_code = ?, updated_at = ?
                    WHERE id = ? AND organization_id = ?
                    """,
                    (
                        dados["brand"], dados["model"], dados["version"], dados["year_manufacture"],
                        dados["year_model"], dados["km"], dados["transmission"], dados["fuel"],
                        dados["body_type"], dados["price_cents"], dados["status"], dados["color"],
                        dados["description"], dados["stock_code"], iso(), veiculo_id, usuario["organization_id"],
                    ),
                )
                _salvar_imagem(pedido, conn, usuario["organization_id"], veiculo_id, imagem)
                _auditar(conn, usuario["organization_id"], usuario["id"], "atualizar_veiculo", "vehicle", veiculo_id)
        except sqlite3.IntegrityError as exc:
            raise ErroHttp(409, _mensagem_integridade(exc))
        row = _veiculo_org(conn, usuario["organization_id"], veiculo_id)
        return {"veiculo": _serial_lista(conn, [dict(row)], publico=False)[0]}, []


def excluir_veiculo(pedido, veiculo_id):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        _veiculo_org(conn, usuario["organization_id"], veiculo_id)
        ocupado = conn.execute(
            "SELECT COUNT(*) AS n FROM appointments WHERE vehicle_id = ? AND organization_id = ?",
            (veiculo_id, usuario["organization_id"]),
        ).fetchone()["n"]
        if ocupado:
            raise ErroHttp(409, "Há visitas neste veículo. Altere o status em vez de excluir.")
        uploads = conn.execute(
            "SELECT path FROM vehicle_images WHERE vehicle_id = ? AND kind = 'upload'",
            (veiculo_id,),
        ).fetchall()
        try:
            with _transacao(conn):
                conn.execute(
                    "DELETE FROM vehicles WHERE id = ? AND organization_id = ?",
                    (veiculo_id, usuario["organization_id"]),
                )
                _auditar(conn, usuario["organization_id"], usuario["id"], "excluir_veiculo", "vehicle", veiculo_id)
        except sqlite3.IntegrityError as exc:
            raise ErroHttp(409, _mensagem_integridade(exc))
        _apagar_arquivos(pedido, [row["path"] for row in uploads])
        return {"ok": True}, []


def _mensagem_integridade(exc):
    texto = str(exc).lower()
    if "stock_code" in texto:
        return "Já existe um veículo com esse código nesta loja."
    return "Não foi possível gravar por uma regra de integridade dos dados."


def _apagar_arquivos(pedido, nomes):
    base = pedido.config.uploads.resolve()
    for nome in nomes:
        alvo = (base / Path(nome).name).resolve()
        try:
            alvo.relative_to(base)
        except ValueError:
            continue
        if alvo.is_file():
            alvo.unlink()


def _lead_json(row, veiculo):
    return {
        "id": row["id"],
        "origem": row["origin"],
        "origem_rotulo": rotulo("origem", row["origin"]),
        "nome": row["contact_name"],
        "telefone": row["contact_phone"],
        "email": row["contact_email"],
        "status": row["status"],
        "status_rotulo": rotulo("status_lead", row["status"]),
        "notas": row["notes"],
        "responsavel_id": row["assignee_id"],
        "resumo": row["summary"],
        "veiculo_id": row["vehicle_id"],
        "veiculo": None if not veiculo else f"{veiculo['brand']} {veiculo['model']} {veiculo['version']}",
        "codigo": None if not veiculo else veiculo["stock_code"],
        "criado_em": row["created_at"],
        "responsavel_nome": row["assignee_name"] or "",
    }


_ORIGENS_DO_CONSULTOR = ("contato", "detalhe")


def _lead_visivel(usuario, row):
    if usuario["role"] == "admin":
        return True
    if row["origin"] not in _ORIGENS_DO_CONSULTOR:
        return True
    return row["assignee_id"] == usuario["id"]


def listar_leads(pedido):
    with _conexao(pedido) as conn:
        usuario = _exigir_usuario(conn, pedido)
        consulta = """
            SELECT l.*, v.brand, v.model, v.version, v.stock_code, u.name AS assignee_name
            FROM leads l
            LEFT JOIN vehicles v ON v.id = l.vehicle_id AND v.organization_id = l.organization_id
            LEFT JOIN users u ON u.id = l.assignee_id
            WHERE l.organization_id = ?
        """
        params = [usuario["organization_id"]]
        if usuario["role"] != "admin":
            consulta += " AND (l.origin NOT IN ('contato', 'detalhe') OR l.assignee_id = ?)"
            params.append(usuario["id"])
        consulta += " ORDER BY l.created_at DESC"
        rows = conn.execute(consulta, tuple(params)).fetchall()
        saida = []
        for row in rows:
            veiculo = None
            if row["stock_code"]:
                veiculo = row
            saida.append(_lead_json(row, veiculo))
        return {"leads": saida}, []


def atualizar_lead(pedido, lead_id, corpo):
    if not isinstance(corpo, dict):
        raise ErroHttp(400, "Lead inválido.")
    status = validacao.status_lead(corpo.get("status"))
    notas = validacao.notas(corpo.get("notas"))
    responsavel = corpo.get("responsavel_id") or ""
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        row = conn.execute(
            "SELECT * FROM leads WHERE id = ? AND organization_id = ?",
            (lead_id, usuario["organization_id"]),
        ).fetchone()
        if not row or not _lead_visivel(usuario, row):
            raise ErroHttp(404, "Lead não encontrado nesta loja.")
        responsavel_id = None
        if responsavel:
            pessoa = conn.execute(
                "SELECT id FROM users WHERE id = ? AND organization_id = ? AND active = 1",
                (responsavel, usuario["organization_id"]),
            ).fetchone()
            if not pessoa:
                raise ErroHttp(400, "Responsável não pertence a esta loja.")
            responsavel_id = pessoa["id"]
        if usuario["role"] != "admin" and row["origin"] in _ORIGENS_DO_CONSULTOR:
            responsavel_id = row["assignee_id"]
        with _transacao(conn):
            conn.execute(
                """
                UPDATE leads SET status = ?, notes = ?, assignee_id = ?, updated_at = ?
                WHERE id = ? AND organization_id = ?
                """,
                (status, notas, responsavel_id, iso(), lead_id, usuario["organization_id"]),
            )
            _auditar(conn, usuario["organization_id"], usuario["id"], "atualizar_lead", "lead", lead_id)
        return {"ok": True}, []


def excluir_lead(pedido, lead_id):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        row = conn.execute(
            "SELECT * FROM leads WHERE id = ? AND organization_id = ?",
            (lead_id, usuario["organization_id"]),
        ).fetchone()
        if not row or not _lead_visivel(usuario, row):
            raise ErroHttp(404, "Lead não encontrado nesta loja.")
        with _transacao(conn):
            conn.execute(
                """
                UPDATE appointments
                SET contact_name = 'Contato removido', contact_phone = '', contact_email = '', notes = ''
                WHERE lead_id = ? AND organization_id = ?
                """,
                (lead_id, usuario["organization_id"]),
            )
            conn.execute(
                "DELETE FROM chat_sessions WHERE lead_id = ? AND organization_id = ?",
                (lead_id, usuario["organization_id"]),
            )
            conn.execute(
                "DELETE FROM leads WHERE id = ? AND organization_id = ?",
                (lead_id, usuario["organization_id"]),
            )
            _auditar(conn, usuario["organization_id"], usuario["id"], "excluir_lead", "lead", lead_id)
        return {"ok": True}, []


def _agenda_json(conn, row):
    inicio = parse_inicio(row["starts_at"])
    fim = parse_inicio(row["ends_at"])
    intervalos = []
    outros = conn.execute(
        "SELECT * FROM appointments WHERE organization_id = ? AND vehicle_id = ?",
        (row["organization_id"], row["vehicle_id"]),
    ).fetchall()
    for item in outros:
        intervalos.append({
            "id": item["id"],
            "status": item["status"],
            "inicio": parse_inicio(item["starts_at"]),
            "fim": parse_inicio(item["ends_at"]),
        })
    return {
        "id": row["id"],
        "tipo": row["kind"],
        "tipo_rotulo": rotulo("visita", row["kind"]),
        "status": row["status"],
        "status_rotulo": rotulo("status_agenda", row["status"]),
        "inicio": row["starts_at"],
        "fim": row["ends_at"],
        "nome": row["contact_name"],
        "telefone": row["contact_phone"],
        "email": row["contact_email"],
        "notas": row["notes"],
        "veiculo_id": row["vehicle_id"],
        "veiculo": f"{row['brand']} {row['model']} {row['version']}",
        "codigo": row["stock_code"],
        "lead_id": row["lead_id"],
        "outros_pedidos": agenda.contar_outros_pedidos(intervalos, inicio, fim, row["id"]) if inicio and fim else 0,
    }


def listar_agenda(pedido):
    with _conexao(pedido) as conn:
        usuario = _exigir_usuario(conn, pedido)
        rows = conn.execute(
            """
            SELECT a.*, v.brand, v.model, v.version, v.stock_code
            FROM appointments a
            JOIN vehicles v ON v.id = a.vehicle_id AND v.organization_id = a.organization_id
            WHERE a.organization_id = ?
            ORDER BY a.starts_at
            """,
            (usuario["organization_id"],),
        ).fetchall()
        return {"agendamentos": [_agenda_json(conn, row) for row in rows]}, []


def transicao_agenda(pedido, agenda_id, acao, corpo):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_usuario(conn, pedido)
        with _transacao(conn):
            row = conn.execute(
                "SELECT * FROM appointments WHERE id = ? AND organization_id = ?",
                (agenda_id, usuario["organization_id"]),
            ).fetchone()
            if not row:
                raise ErroHttp(404, "Agendamento não encontrado nesta loja.")
            config = _configuracao(conn, usuario["organization_id"])
            expediente = carregar_json(config["hours_json"], {})
            if acao == "cancelar":
                if row["status"] in ("cancelado", "realizado"):
                    raise ErroHttp(409, "Esse agendamento não pode ser cancelado.")
                conn.execute(
                    "UPDATE appointments SET status = 'cancelado', updated_at = ? WHERE id = ?",
                    (iso(), agenda_id),
                )
            elif acao == "realizar":
                if row["status"] not in ("confirmado", "reagendado"):
                    raise ErroHttp(409, "Só uma visita confirmada pode ser marcada como realizada.")
                conn.execute(
                    "UPDATE appointments SET status = 'realizado', updated_at = ? WHERE id = ?",
                    (iso(), agenda_id),
                )
            elif acao in ("confirmar", "reagendar"):
                if acao == "confirmar" and row["status"] != "solicitado":
                    raise ErroHttp(409, "Só um pedido solicitado pode ser confirmado.")
                if acao == "reagendar" and row["status"] not in ("solicitado", "confirmado", "reagendado"):
                    raise ErroHttp(409, "Esse agendamento não pode ser reagendado.")
                inicio = parse_inicio(row["starts_at"])
                if acao == "reagendar":
                    if not isinstance(corpo, dict):
                        raise ErroHttp(400, "Informe o novo horário.")
                    inicio = parse_inicio(corpo.get("inicio"))
                local, fim = agenda.validar_janela(inicio, expediente)
                intervalos = []
                for item in conn.execute(
                    "SELECT * FROM appointments WHERE organization_id = ? AND vehicle_id = ?",
                    (usuario["organization_id"], row["vehicle_id"]),
                ).fetchall():
                    intervalos.append({
                        "id": item["id"],
                        "status": item["status"],
                        "inicio": parse_inicio(item["starts_at"]),
                        "fim": parse_inicio(item["ends_at"]),
                    })
                if agenda.conflito_ocupado(intervalos, local, fim, agenda_id):
                    raise ErroHttp(409, "Já existe visita confirmada deste veículo nesse horário.")
                novo_status = "confirmado" if acao == "confirmar" else "reagendado"
                conn.execute(
                    """
                    UPDATE appointments
                    SET status = ?, starts_at = ?, ends_at = ?, updated_at = ?
                    WHERE id = ? AND organization_id = ?
                    """,
                    (novo_status, iso(local), iso(fim), iso(), agenda_id, usuario["organization_id"]),
                )
            else:
                raise ErroHttp(404, "Ação de agenda desconhecida.")
            _auditar(conn, usuario["organization_id"], usuario["id"], acao + "_visita", "appointment", agenda_id)
        return {"ok": True, "mensagem": "Agenda atualizada. A confirmação depende desta ação da equipe."}, []


def obter_config(pedido):
    with _conexao(pedido) as conn:
        usuario = _exigir_usuario(conn, pedido)
        _exigir_admin(usuario)
        org = conn.execute(
            "SELECT * FROM organizations WHERE id = ?", (usuario["organization_id"],)
        ).fetchone()
        config = _configuracao(conn, usuario["organization_id"])
        return {"loja": loja_publica(org, config)}, []


def salvar_config(pedido, corpo):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_admin(_exigir_usuario(conn, pedido))
        dados = validacao.payload_configuracao(corpo)
        with _transacao(conn):
            conn.execute(
                """
                UPDATE business_settings SET
                    trade_name = ?, description = ?, phone = ?, email = ?, address_public = ?,
                    hours_json = ?, services_json = ?, assistant_json = ?, theme_json = ?,
                    privacy_note = ?, updated_at = ?
                WHERE organization_id = ?
                """,
                (
                    dados["trade_name"], dados["description"], dados["phone"], dados["email"],
                    dados["address_public"], json.dumps(dados["hours_json"], ensure_ascii=False),
                    json.dumps(dados["services_json"], ensure_ascii=False),
                    json.dumps(dados["assistant_json"], ensure_ascii=False),
                    json.dumps(dados["theme_json"], ensure_ascii=False),
                    dados["privacy_note"], iso(), usuario["organization_id"],
                ),
            )
            _auditar(conn, usuario["organization_id"], usuario["id"], "atualizar_config", "settings", usuario["organization_id"])
        return {"ok": True}, []


def restaurar(pedido):
    with _conexao(pedido) as conn:
        _exigir_csrf(conn, pedido)
        usuario = _exigir_admin(_exigir_usuario(conn, pedido))
        if usuario["organization_id"] != semear.ORG_ID:
            raise ErroHttp(403, "A restauração demonstrativa vale só para a loja Lume.")
        nomes = semear.restaurar_operacao(conn)
        _auditar(conn, usuario["organization_id"], usuario["id"], "restaurar_demo", "organization", usuario["organization_id"])
        _apagar_arquivos(pedido, nomes)
        return {"ok": True, "mensagem": "Demonstração restaurada nesta loja."}, []


def ler_midia(pedido, imagem_id):
    with _conexao(pedido) as conn:
        row = conn.execute(
            """
            SELECT i.*, v.status, v.organization_id AS org_veiculo
            FROM vehicle_images i
            JOIN vehicles v ON v.id = i.vehicle_id
            WHERE i.id = ?
            """,
            (imagem_id,),
        ).fetchone()
        if not row or row["kind"] != "upload":
            raise ErroHttp(404, "Imagem não encontrada.")
        usuario = _usuario(conn, pedido.cookies)
        publico = row["status"] in ("disponivel", "reservado")
        mesma_loja = usuario and usuario["organization_id"] == row["organization_id"]
        if not publico and not mesma_loja:
            raise ErroHttp(404, "Imagem não encontrada.")
        base = pedido.config.uploads.resolve()
        alvo = (base / Path(row["path"]).name).resolve()
        try:
            alvo.relative_to(base)
        except ValueError:
            raise ErroHttp(404, "Imagem não encontrada.")
        if not alvo.is_file():
            raise ErroHttp(404, "Imagem não encontrada.")
        tipo = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(
            alvo.suffix.lower().lstrip("."), "application/octet-stream"
        )
        return alvo.read_bytes(), tipo
