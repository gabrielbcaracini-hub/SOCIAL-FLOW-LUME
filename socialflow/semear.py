"""Semeadura fictícia da Lume Veículos. Não há dados de pessoas reais."""

import json
import uuid

from socialflow.config import (
    ADMIN_EMAIL,
    ADMIN_NOME,
    CONSULTOR_EMAIL,
    CONSULTOR_NOME,
    SELLER_EMAIL,
    SELLER_NOME,
    SENHA_CONSULTOR_PADRAO,
    SLUG_PUBLICO,
)
from socialflow.seguranca import hash_senha
from socialflow.tempo import iso, proximo_dia_util

ORG_ID = "11111111-1111-4111-8111-111111111111"

EXPEDIENTE = {
    "seg": ["09:00", "18:00"],
    "ter": ["09:00", "18:00"],
    "qua": ["09:00", "18:00"],
    "qui": ["09:00", "18:00"],
    "sex": ["09:00", "18:00"],
    "sab": ["09:00", "13:00"],
    "dom": None,
}

SERVICOS = [
    {
        "titulo": "Consultoria de escolha",
        "texto": "Ajudamos a comparar carroceria, câmbio, uso e orçamento com o que realmente está no pátio.",
    },
    {
        "titulo": "Atendimento comercial",
        "texto": "Registramos seu interesse, com consentimento, para a equipe retornar sem prometer desconto ou financiamento.",
    },
    {
        "titulo": "Visita e test-drive",
        "texto": "Você pede um horário. A loja confirma, reagenda ou cancela. O pedido ainda não reserva o carro.",
    },
]

ESTOQUE = [
    ("EST-1001", "Toyota", "Corolla", "XEi", 2022, 2023, 45000, "automatico", "flex", "sedan", 118900, "disponivel", "Prata"),
    ("EST-1002", "Honda", "Civic", "EXL", 2021, 2022, 38000, "cvt", "flex", "sedan", 129900, "disponivel", "Cinza"),
    ("EST-1003", "Volkswagen", "Polo", "Track", 2023, 2024, 18000, "manual", "flex", "hatch", 79900, "disponivel", "Branco"),
    ("EST-1004", "Jeep", "Compass", "Longitude", 2022, 2023, 41000, "automatico", "flex", "suv", 154900, "reservado", "Preto"),
    ("EST-1005", "Fiat", "Strada", "Freedom", 2023, 2024, 27000, "manual", "flex", "pickup", 98900, "disponivel", "Branco"),
    ("EST-1006", "Hyundai", "HB20", "Comfort", 2020, 2021, 71000, "manual", "flex", "hatch", 68900, "disponivel", "Prata"),
    ("EST-1007", "Chevrolet", "Onix Plus", "Premier", 2022, 2022, 54000, "automatico", "flex", "sedan", 86900, "vendido", "Vermelho"),
    ("EST-1008", "Toyota", "SW4", "SRX", 2021, 2022, 80000, "automatico", "diesel", "suv", 289900, "disponivel", "Cinza"),
    ("EST-1009", "Renault", "Kwid", "Zen", 2024, 2025, 9000, "manual", "flex", "hatch", 62900, "disponivel", "Branco"),
    ("EST-1010", "BYD", "Dolphin", "Plus", 2024, 2025, 5000, "automatico", "eletrico", "hatch", 149900, "disponivel", "Azul"),
    ("EST-1011", "Volkswagen", "T-Cross", "200 TSI", 2022, 2023, 28000, "automatico", "flex", "suv", 109900, "disponivel", "Prata"),
    ("EST-1012", "Chevrolet", "Tracker", "Premier", 2021, 2022, 36000, "automatico", "flex", "suv", 98900, "disponivel", "Branco"),
    ("EST-1013", "Hyundai", "Creta", "Limited", 2022, 2023, 22000, "automatico", "flex", "suv", 127900, "reservado", "Prata"),
    ("EST-1014", "Honda", "HR-V", "RS e:HEV", 2023, 2024, 12000, "cvt", "hibrido", "suv", 164900, "disponivel", "Bege"),
    ("EST-1015", "Fiat", "Pulse", "Impetus", 2022, 2023, 19000, "cvt", "flex", "suv", 92900, "disponivel", "Vermelho"),
    ("EST-1016", "Toyota", "Hilux", "SRX", 2021, 2022, 74000, "automatico", "diesel", "pickup", 229900, "disponivel", "Branco"),
    ("EST-1017", "Volkswagen", "Nivus", "Highline", 2022, 2023, 24000, "automatico", "flex", "suv", 104900, "disponivel", "Preto"),
    ("EST-1018", "Peugeot", "e-208", "GT", 2023, 2024, 8000, "automatico", "eletrico", "hatch", 149900, "disponivel", "Amarelo"),
    ("EST-1019", "Volkswagen", "Virtus", "Highline", 2022, 2023, 41000, "automatico", "flex", "sedan", 94900, "disponivel", "Branco"),
    ("EST-1020", "Jeep", "Renegade", "Longitude", 2022, 2023, 52000, "automatico", "flex", "suv", 99900, "vendido", "Azul"),
    ("EST-1021", "Fiat", "Toro", "Volcano", 2022, 2023, 33000, "automatico", "diesel", "pickup", 142900, "disponivel", "Branco"),
    ("EST-1022", "Toyota", "Corolla Cross", "XRX", 2023, 2024, 15000, "cvt", "hibrido", "suv", 179900, "disponivel", "Prata"),
    ("EST-1023", "Chevrolet", "Spin", "LTZ", 2022, 2023, 46000, "automatico", "flex", "minivan", 89900, "disponivel", "Prata"),
    ("EST-1024", "Fiat", "Argo", "Drive", 2023, 2024, 18000, "manual", "flex", "hatch", 68900, "disponivel", "Branco"),
    ("EST-1025", "Fiat", "Fastback", "Audace", 2023, 2024, 14000, "cvt", "flex", "suv", 119900, "disponivel", "Cinza"),
    ("EST-1026", "Chevrolet", "Montana", "Premier", 2023, 2024, 16000, "automatico", "flex", "pickup", 124900, "disponivel", "Prata"),
    ("EST-1027", "Nissan", "Kicks", "Exclusive", 2022, 2023, 28000, "cvt", "flex", "suv", 98900, "disponivel", "Branco"),
    ("EST-1028", "Honda", "City Hatch", "Touring", 2022, 2023, 21000, "cvt", "flex", "hatch", 96900, "disponivel", "Cinza"),
    ("EST-1029", "Renault", "Sandero", "Intense", 2020, 2021, 48000, "manual", "flex", "hatch", 59900, "disponivel", "Branco"),
    ("EST-1030", "Jeep", "Commander", "Limited", 2023, 2024, 18000, "automatico", "flex", "suv", 189900, "disponivel", "Preto"),
    ("EST-1031", "Chevrolet", "S10", "LTZ", 2021, 2022, 62000, "automatico", "diesel", "pickup", 189900, "disponivel", "Cinza"),
    ("EST-1032", "Peugeot", "2008", "GT", 2022, 2023, 25000, "automatico", "flex", "suv", 109900, "disponivel", "Laranja"),
    ("EST-1033", "Ford", "Ranger", "XLT", 2020, 2021, 68000, "automatico", "diesel", "pickup", 169900, "disponivel", "Branco"),
    ("EST-1034", "Renault", "Duster", "Iconic", 2022, 2023, 31000, "automatico", "flex", "suv", 89900, "disponivel", "Cinza"),
    ("EST-1035", "Volkswagen", "Taos", "Highline", 2022, 2023, 27000, "automatico", "flex", "suv", 134900, "disponivel", "Prata"),
    ("EST-1036", "Fiat", "Cronos", "Precision", 2023, 2024, 19000, "automatico", "flex", "sedan", 82900, "disponivel", "Vermelho"),
    ("EST-1037", "Honda", "City", "EXL", 2023, 2024, 17000, "cvt", "flex", "sedan", 104900, "disponivel", "Prata"),
    ("EST-1038", "Volkswagen", "Saveiro", "Extreme", 2023, 2024, 22000, "manual", "flex", "pickup", 84900, "disponivel", "Branco"),
    ("EST-1039", "Hyundai", "Tucson", "Limited", 2022, 2023, 35000, "automatico", "flex", "suv", 154900, "disponivel", "Azul"),
    ("EST-1040", "BYD", "Yuan Plus", "Plus", 2023, 2024, 9000, "automatico", "eletrico", "suv", 169900, "disponivel", "Cinza"),
    ("EST-1041", "Citroën", "C4 Cactus", "Feel", 2020, 2021, 44000, "automatico", "flex", "suv", 79900, "disponivel", "Branco"),
]

# Fotos reais em assets/veiculos/. Créditos e a diferença de ano/versão: data/creditos-fotos.md
# A vitrine mostra a frente parada. Os outros ângulos entram no hover.
FOTOS = {
    "EST-1001": [
        ("corolla.jpg", "Toyota Corolla, frente"),
        ("corolla-traseira.jpg", "Toyota Corolla, traseira"),
        ("corolla-interior.jpg", "Toyota Corolla, interior"),
    ],
    "EST-1002": [
        ("civic.jpg", "Honda Civic, frente"),
        ("civic-traseira.jpg", "Honda Civic, traseira"),
        ("civic-interior.jpg", "Honda Civic, interior"),
    ],
    "EST-1003": [
        ("polo.jpg", "Volkswagen Polo, frente"),
        ("polo-traseira.jpg", "Volkswagen Polo, traseira"),
        ("polo-interior.jpg", "Volkswagen Polo, interior"),
    ],
    "EST-1004": [
        ("compass.jpg", "Jeep Compass, frente"),
        ("compass-traseira.jpg", "Jeep Compass, traseira"),
        ("compass-interior.jpg", "Jeep Compass, interior"),
    ],
    "EST-1005": [
        ("strada.jpg", "Fiat Strada, frente"),
        ("strada-traseira.jpg", "Fiat Strada, traseira"),
    ],
    "EST-1006": [
        ("hb20.png", "Hyundai HB20, frente"),
        ("hb20-traseira.jpg", "Hyundai HB20, traseira"),
        ("hb20-interior.jpg", "Hyundai HB20, interior"),
    ],
    "EST-1007": [
        ("onix-plus.png", "Chevrolet Onix Plus, frente"),
    ],
    "EST-1008": [
        ("sw4.jpg", "Toyota SW4, frente"),
        ("sw4-traseira.jpg", "Toyota SW4, traseira"),
        ("sw4-interior.jpg", "Toyota SW4, interior"),
    ],
    "EST-1009": [
        ("kwid.png", "Renault Kwid, frente"),
        ("kwid-traseira.jpg", "Renault Kwid, traseira"),
    ],
    "EST-1010": [
        ("dolphin.jpg", "BYD Dolphin, frente"),
        ("dolphin-traseira.jpg", "BYD Dolphin, traseira"),
        ("dolphin-interior.jpg", "BYD Dolphin, interior"),
    ],
    "EST-1011": [
        ("tcross.jpg", "Volkswagen T-Cross, frente"),
        ("tcross-traseira.jpg", "Volkswagen T-Cross, traseira"),
    ],
    "EST-1012": [
        ("tracker.jpg", "Chevrolet Tracker, frente"),
        ("tracker-traseira.jpg", "Chevrolet Tracker, traseira"),
        ("tracker-interior.jpg", "Chevrolet Tracker, interior"),
    ],
    "EST-1013": [
        ("creta.jpg", "Hyundai Creta, frente"),
        ("creta-traseira.jpg", "Hyundai Creta, traseira"),
        ("creta-interior.jpg", "Hyundai Creta, interior"),
    ],
    "EST-1014": [
        ("hrv.jpg", "Honda HR-V, frente"),
        ("hrv-traseira.jpg", "Honda HR-V, traseira"),
        ("hrv-interior.jpg", "Honda HR-V, interior"),
    ],
    "EST-1015": [
        ("pulse.jpg", "Fiat Pulse, frente"),
        ("pulse-traseira.jpg", "Fiat Pulse, traseira"),
        ("pulse-interior.jpg", "Fiat Pulse, interior"),
    ],
    "EST-1016": [
        ("hilux.jpg", "Toyota Hilux, frente"),
        ("hilux-traseira.jpg", "Toyota Hilux, traseira"),
    ],
    "EST-1017": [
        ("nivus.jpg", "Volkswagen Nivus, frente"),
        ("nivus-traseira.jpg", "Volkswagen Nivus, traseira"),
    ],
    "EST-1018": [
        ("peugeot208.jpg", "Peugeot e-208, frente"),
        ("peugeot208-traseira.jpg", "Peugeot e-208, traseira"),
        ("peugeot208-interior.jpg", "Peugeot 208, interior"),
    ],
    "EST-1019": [
        ("virtus.jpg", "Volkswagen Virtus, frente"),
        ("virtus-traseira.jpg", "Volkswagen Virtus, traseira"),
        ("virtus-interior.jpg", "Volkswagen Virtus, interior"),
    ],
    "EST-1020": [
        ("renegade.jpg", "Jeep Renegade, frente"),
        ("renegade-traseira.jpg", "Jeep Renegade, traseira"),
    ],
    "EST-1021": [
        ("toro.jpg", "Fiat Toro, frente"),
        ("toro-traseira.jpg", "Fiat Toro, traseira"),
    ],
    "EST-1022": [
        ("cross.jpg", "Toyota Corolla Cross, frente"),
        ("cross-traseira.jpg", "Toyota Corolla Cross, traseira"),
        ("cross-interior.jpg", "Toyota Corolla Cross, interior"),
    ],
    "EST-1023": [
        ("spin.jpg", "Chevrolet Spin, frente"),
        ("spin-traseira.jpg", "Chevrolet Spin, traseira"),
    ],
    "EST-1024": [
        ("argo.jpg", "Fiat Argo, frente"),
        ("argo-traseira.jpg", "Fiat Argo, traseira"),
        ("argo-interior.jpg", "Fiat Argo, interior"),
    ],
    "EST-1025": [
        ("fastback.jpg", "Fiat Fastback, frente"),
        ("fastback-traseira.jpg", "Fiat Fastback, traseira"),
        ("fastback-interior.jpg", "Fiat Fastback, interior"),
    ],
    "EST-1026": [
        ("montana.jpg", "Chevrolet Montana, frente"),
        ("montana-traseira.jpg", "Chevrolet Montana, traseira"),
        ("montana-interior.jpg", "Chevrolet Montana, interior"),
    ],
    "EST-1027": [
        ("kicks.jpg", "Nissan Kicks, frente"),
        ("kicks-traseira.jpg", "Nissan Kicks, traseira"),
        ("kicks-interior.jpg", "Nissan Kicks, interior"),
    ],
    "EST-1028": [
        ("cityhatch.jpg", "Honda City Hatch, frente"),
        ("cityhatch-traseira.jpg", "Honda City Hatch, traseira"),
        ("cityhatch-interior.jpg", "Honda City Hatch, interior"),
    ],
    "EST-1029": [
        ("sandero.jpg", "Renault Sandero, frente"),
        ("sandero-traseira.jpg", "Renault Sandero, traseira"),
    ],
    "EST-1030": [
        ("commander.jpg", "Jeep Commander, frente"),
        ("commander-traseira.jpg", "Jeep Commander, traseira"),
    ],
    "EST-1031": [
        ("s10.jpg", "Chevrolet S10, frente"),
        ("s10-traseira.jpg", "Chevrolet S10, traseira"),
    ],
    "EST-1032": [
        ("peugeot2008.jpg", "Peugeot 2008, frente"),
        ("peugeot2008-traseira.jpg", "Peugeot 2008, traseira"),
    ],
    "EST-1033": [
        ("ranger.jpg", "Ford Ranger, frente"),
        ("ranger-traseira.jpg", "Ford Ranger, traseira"),
    ],
    "EST-1034": [
        ("duster.jpg", "Renault Duster, frente"),
        ("duster-traseira.jpg", "Renault Duster, traseira"),
        ("duster-interior.jpg", "Renault Duster, interior"),
    ],
    "EST-1035": [
        ("taos.jpg", "Volkswagen Taos, frente"),
        ("taos-traseira.jpg", "Volkswagen Taos, traseira"),
    ],
    "EST-1036": [
        ("cronos.jpg", "Fiat Cronos, frente"),
        ("cronos-traseira.jpg", "Fiat Cronos, traseira"),
    ],
    "EST-1037": [
        ("city.jpg", "Honda City, frente"),
        ("city-traseira.jpg", "Honda City, traseira"),
    ],
    "EST-1038": [
        ("saveiro.jpg", "Volkswagen Saveiro, frente"),
        ("saveiro-traseira.jpg", "Volkswagen Saveiro, traseira"),
    ],
    "EST-1039": [
        ("tucson.jpg", "Hyundai Tucson, frente"),
        ("tucson-traseira.jpg", "Hyundai Tucson, traseira"),
        ("tucson-interior.jpg", "Hyundai Tucson, interior"),
    ],
    "EST-1040": [
        ("atto3.jpg", "BYD Yuan Plus, frente"),
        ("atto3-traseira.jpg", "BYD Yuan Plus, traseira"),
    ],
    "EST-1041": [
        ("cactus.jpg", "Citroën C4 Cactus, frente"),
        ("cactus-traseira.jpg", "Citroën C4 Cactus, traseira"),
    ],
}


def _id():
    return str(uuid.uuid4())


def semear(conn, senha_admin, senha_vendedor, senha_consultor=None):
    senha_consultor = senha_consultor or SENHA_CONSULTOR_PADRAO
    existe = conn.execute("SELECT COUNT(*) AS n FROM organizations").fetchone()["n"]
    if existe:
        return False
    conn.execute("BEGIN IMMEDIATE")
    try:
        momento = iso()
        conn.execute(
            "INSERT INTO organizations (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (ORG_ID, "Lume Veículos", SLUG_PUBLICO, momento, momento),
        )
        for email, nome, papel, senha in (
            (ADMIN_EMAIL, ADMIN_NOME, "admin", senha_admin),
            (SELLER_EMAIL, SELLER_NOME, "vendedor", senha_vendedor),
            (CONSULTOR_EMAIL, CONSULTOR_NOME, "vendedor", senha_consultor),
        ):
            conn.execute(
                """
                INSERT INTO users (
                    id, organization_id, name, email, password_hash, role, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (_id(), ORG_ID, nome, email, hash_senha(senha), papel, momento, momento),
            )
        conn.execute(
            """
            INSERT INTO business_settings (
                organization_id, trade_name, description, phone, email, address_public,
                hours_json, services_json, assistant_json, theme_json, privacy_note, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ORG_ID,
                "Lume Veículos",
                "Revenda fictícia de demonstração. Oferece consultoria de escolha, atendimento comercial e agendamento de visita ou test-drive.",
                "(11) 4000-0100",
                "contato@lume.demo",
                "Avenida Demonstração, 1200, Setor Comercial, Cidade Exemplo/SP",
                json.dumps(EXPEDIENTE, ensure_ascii=False),
                json.dumps(SERVICOS, ensure_ascii=False),
                json.dumps({"max_sugestoes": 3, "baixa_km": 30000, "rotulo_modo": "Automação determinística"}, ensure_ascii=False),
                json.dumps({"acento": "#d09850"}, ensure_ascii=False),
                "Os contatos desta vitrine são fictícios e só existem neste ambiente de demonstração. Não coletamos CPF, endereço residencial nem dados de saúde.",
                momento,
            ),
        )
        _inserir_operacao(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return True


def restaurar_operacao(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        imagens = conn.execute(
            "SELECT path, kind FROM vehicle_images WHERE organization_id = ? AND kind = 'upload'",
            (ORG_ID,),
        ).fetchall()
        for tabela in ("chat_messages", "chat_sessions", "appointments", "leads", "vehicle_images", "vehicles"):
            conn.execute(f"DELETE FROM {tabela} WHERE organization_id = ?", (ORG_ID,))
        _inserir_operacao(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return [item["path"] for item in imagens]


def _gravar_veiculo(conn, item, momento):
    codigo, marca, modelo, versao, fab, ano, km, cambio, combustivel, tipo, preco, status, cor = item
    vid = _id()
    conn.execute(
        """
        INSERT INTO vehicles (
            id, organization_id, brand, model, version, year_manufacture, year_model, km,
            transmission, fuel, body_type, price_cents, status, color, description, stock_code,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vid, ORG_ID, marca, modelo, versao, fab, ano, km, cambio, combustivel, tipo,
            preco * 100, status, cor,
            f"Unidade demonstrativa {codigo}. {marca} {modelo} {versao}, cor {cor}. Atributos fictícios para a vitrine, sem garantia ou financiamento.",
            codigo, momento, momento,
        ),
    )
    return vid


def _inserir_operacao(conn):
    momento = iso()
    ids = {}
    for item in ESTOQUE:
        codigo = item[0]
        vid = _gravar_veiculo(conn, item, momento)
        ids[codigo] = vid
        for ordem, (arquivo, rotulo) in enumerate(FOTOS[codigo]):
            conn.execute(
                """
                INSERT INTO vehicle_images (
                    id, organization_id, vehicle_id, kind, label, path, sort_order, created_at
                ) VALUES (?, ?, ?, 'placeholder', ?, ?, ?, ?)
                """,
                (_id(), ORG_ID, vid, rotulo, f"/assets/veiculos/{arquivo}", ordem, momento),
            )
    lead_corolla = _id()
    lead_civic = _id()
    lead_strada = _id()
    for lead_id, veiculo, origem, nome, telefone, email, status, resumo in (
        (lead_corolla, ids["EST-1001"], "vitrine", "Ana Martins", "(11) 90000-0001", "ana.martins@exemplo.demo", "novo", "Interesse demonstrativo no Corolla."),
        (lead_civic, ids["EST-1002"], "assistente", "Bruno Almeida", "(11) 90000-0002", "bruno.almeida@exemplo.demo", "contatado", "Preferências: câmbio automático, tipo sedã."),
        (lead_strada, ids["EST-1005"], "visita", "Carla Dias", "(11) 90000-0003", "carla.dias@exemplo.demo", "novo", "Pedido demonstrativo de test-drive da Strada."),
    ):
        conn.execute(
            """
            INSERT INTO leads (
                id, organization_id, vehicle_id, origin, contact_name, contact_phone, contact_email,
                consent, preferences_json, status, notes, assignee_id, summary, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, '{}', ?, '', NULL, ?, ?, ?)
            """,
            (lead_id, ORG_ID, veiculo, origem, nome, telefone, email, status, resumo, momento, momento),
        )
    visita = proximo_dia_util(1, 10)
    pedido = proximo_dia_util(3, 15)
    from datetime import timedelta

    conn.execute(
        """
        INSERT INTO appointments (
            id, organization_id, lead_id, vehicle_id, kind, status, starts_at, ends_at,
            contact_name, contact_phone, contact_email, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'visita', 'confirmado', ?, ?, ?, ?, ?, '', ?, ?)
        """,
        (_id(), ORG_ID, lead_corolla, ids["EST-1001"], iso(visita), iso(visita + timedelta(hours=1)),
         "Ana Martins", "(11) 90000-0001", "ana.martins@exemplo.demo", momento, momento),
    )
    conn.execute(
        """
        INSERT INTO appointments (
            id, organization_id, lead_id, vehicle_id, kind, status, starts_at, ends_at,
            contact_name, contact_phone, contact_email, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'test_drive', 'solicitado', ?, ?, ?, ?, ?, '', ?, ?)
        """,
        (_id(), ORG_ID, lead_strada, ids["EST-1005"], iso(pedido), iso(pedido + timedelta(hours=1)),
         "Carla Dias", "(11) 90000-0003", "carla.dias@exemplo.demo", momento, momento),
    )


def garantir_consultor(conn, senha):
    org = conn.execute("SELECT id FROM organizations WHERE id = ?", (ORG_ID,)).fetchone()
    if not org:
        return False
    existe = conn.execute(
        "SELECT 1 FROM users WHERE email = ?", (CONSULTOR_EMAIL,)
    ).fetchone()
    if existe:
        return False
    momento = iso()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """
            INSERT INTO users (
                id, organization_id, name, email, password_hash, role, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'vendedor', 1, ?, ?)
            """,
            (_id(), ORG_ID, CONSULTOR_NOME, CONSULTOR_EMAIL, hash_senha(senha or SENHA_CONSULTOR_PADRAO), momento, momento),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return True


def aplicar_fotos(conn):
    momento = iso()
    conn.execute("BEGIN IMMEDIATE")
    try:
        for codigo, angulos in FOTOS.items():
            veiculo = conn.execute(
                "SELECT id FROM vehicles WHERE organization_id = ? AND stock_code = ?",
                (ORG_ID, codigo),
            ).fetchone()
            if not veiculo:
                continue
            conn.execute(
                """
                DELETE FROM vehicle_images
                WHERE vehicle_id = ? AND organization_id = ? AND kind = 'placeholder'
                """,
                (veiculo["id"], ORG_ID),
            )
            for ordem, (arquivo, rotulo) in enumerate(angulos):
                conn.execute(
                    """
                    INSERT INTO vehicle_images (
                        id, organization_id, vehicle_id, kind, label, path, sort_order, created_at
                    ) VALUES (?, ?, ?, 'placeholder', ?, ?, ?, ?)
                    """,
                    (
                        _id(), ORG_ID, veiculo["id"], rotulo,
                        f"/assets/veiculos/{arquivo}", ordem, momento,
                    ),
                )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def garantir_estoque(conn):
    """Inclui códigos do catálogo que ainda não estão no banco. Não apaga leads."""
    org = conn.execute("SELECT id FROM organizations WHERE id = ?", (ORG_ID,)).fetchone()
    if not org:
        return 0
    momento = iso()
    conn.execute("BEGIN IMMEDIATE")
    try:
        novos = 0
        for item in ESTOQUE:
            codigo = item[0]
            existe = conn.execute(
                "SELECT 1 FROM vehicles WHERE organization_id = ? AND stock_code = ?",
                (ORG_ID, codigo),
            ).fetchone()
            if existe:
                continue
            _gravar_veiculo(conn, item, momento)
            novos += 1
        row = conn.execute(
            "SELECT theme_json FROM business_settings WHERE organization_id = ?",
            (ORG_ID,),
        ).fetchone()
        if row:
            tema = json.loads(row["theme_json"] or "{}")
            if str(tema.get("acento", "")).lower() == "#8a5a2b":
                tema["acento"] = "#d09850"
                conn.execute(
                    "UPDATE business_settings SET theme_json = ?, updated_at = ? WHERE organization_id = ?",
                    (json.dumps(tema, ensure_ascii=False), momento, ORG_ID),
                )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return novos
