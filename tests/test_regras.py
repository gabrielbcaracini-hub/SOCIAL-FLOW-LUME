import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from socialflow.agenda import conflito_ocupado, sobrepoe, validar_janela
from socialflow.apresentacao import formatar_reais
from socialflow.dominio import aparece_na_vitrine, pode_agendar, pode_recomendar, pode_transicionar_veiculo
from socialflow.erros import ErroHttp
from socialflow.recomendacao import extrair_preferencias, mesclar, responder
from socialflow.tempo import TZ, agora
from socialflow.validacao import contraste_com_branco, cor_acento, parse_preco_centavos, preferencias


def carro(**extras):
    base = {
        "id": "v1",
        "organization_id": "loja",
        "brand": "Toyota",
        "model": "Corolla",
        "version": "XEi",
        "year_manufacture": 2022,
        "year_model": 2023,
        "km": 45000,
        "transmission": "automatico",
        "fuel": "flex",
        "body_type": "sedan",
        "price_cents": 11890000,
        "status": "disponivel",
        "stock_code": "EST-1",
        "color": "Prata",
        "description": "Unidade demonstrativa.",
    }
    base.update(extras)
    return base


class TestRegras(unittest.TestCase):
    def test_preco_e_moeda(self):
        self.assertEqual(parse_preco_centavos("118.900,00"), 11890000)
        self.assertEqual(parse_preco_centavos("79900,50"), 7990050)
        self.assertEqual(parse_preco_centavos(62900), 6290000)
        self.assertEqual(formatar_reais(11890000), "R$ 118.900,00")

    def test_contraste_rejeita_cor_clara(self):
        self.assertGreaterEqual(contraste_com_branco("#8a5a2b"), 4.5)
        self.assertEqual(cor_acento("#d09850"), "#d09850")
        with self.assertRaises(ErroHttp):
            cor_acento("#f4f0e8")
        with self.assertRaises(ErroHttp):
            cor_acento("#8a5a2b")

    def test_status(self):
        self.assertTrue(pode_recomendar("disponivel"))
        self.assertFalse(pode_recomendar("reservado"))
        self.assertFalse(pode_recomendar("vendido"))
        self.assertTrue(aparece_na_vitrine("reservado"))
        self.assertFalse(aparece_na_vitrine("vendido"))
        self.assertTrue(pode_agendar("disponivel"))
        self.assertFalse(pode_agendar("reservado"))
        self.assertFalse(pode_transicionar_veiculo("vendido", "reservado"))
        self.assertTrue(pode_transicionar_veiculo("disponivel", "vendido"))

    def test_extracao_nao_confunde_km_com_orcamento(self):
        prefs, _ = extrair_preferencias("até 50 mil km e orçamento de 90 mil")
        self.assertEqual(prefs["km_max"], 50000)
        self.assertEqual(prefs["preco_max_centavos"], 9000000)

    def test_extracao_cambio_e_tipo(self):
        prefs, notas = extrair_preferencias("SUV automático até 150 mil, baixa quilometragem, para família")
        self.assertEqual(prefs["tipo"], "suv")
        self.assertEqual(prefs["cambio"], "automaticos")
        self.assertEqual(prefs["preco_max_centavos"], 15000000)
        self.assertEqual(prefs["km_max"], 30000)
        self.assertEqual(prefs["uso"], "familia")
        self.assertTrue(notas)

    def test_preferencia_explicita_ignora_chave_estranha(self):
        limpas = preferencias({"cambio": "manual", "status": "vendido", "organization_id": "outra"})
        self.assertEqual(limpas, {"cambio": "manual"})

    def test_mescla_prioriza_formulario(self):
        saida = mesclar(
            {"tipo": "suv"},
            {"tipo": "hatch", "cambio": "manual"},
            {"tipo": "sedan"},
        )
        self.assertEqual(saida["tipo"], "sedan")
        self.assertEqual(saida["cambio"], "manual")

    def test_recomendacao_isola_loja_e_status(self):
        veiculos = [
            carro(id="ok", stock_code="EST-OK"),
            carro(id="vendido", status="vendido", price_cents=8000000, stock_code="EST-V"),
            carro(id="reservado", status="reservado", stock_code="EST-R"),
            carro(id="outra", organization_id="outra", price_cents=1000000, stock_code="EST-X"),
        ]
        resposta = responder(
            veiculos,
            {"preco_max_centavos": 14000000, "cambio": "automaticos", "tipo": "sedan"},
            "loja",
            "Lume Veículos",
        )
        ids = [item["id"] for item in resposta["sugestoes"]]
        self.assertEqual(ids, ["ok"])
        self.assertNotIn("vendido", ids)
        self.assertNotIn("outra", ids)
        self.assertTrue(resposta["sugestoes"][0]["motivos"])

    def test_sem_correspondencia_e_honesta(self):
        resposta = responder(
            [carro(body_type="pickup", fuel="flex", id="strada")],
            {"tipo": "pickup", "combustivel": "diesel"},
            "loja",
            "Lume Veículos",
        )
        self.assertEqual(resposta["correspondencia"], "vazia")
        self.assertEqual(resposta["sugestoes"], [])
        self.assertIn("combustível", resposta["texto"])

    def test_uso_nao_esconde_que_filtrou(self):
        hatches = [
            carro(id="h1", body_type="hatch", price_cents=6000000, transmission="manual"),
        ]
        resposta = responder(hatches, {"preco_max_centavos": 7000000, "uso": "familia"}, "loja", "Lume")
        self.assertEqual(resposta["sugestoes"], [])
        self.assertEqual(len(resposta["alternativas"]), 1)
        self.assertIn("uso", resposta["alternativas"][0]["motivos"][0].lower())

    def test_foco_vendido_nao_vira_sugestao(self):
        resposta = responder(
            [carro(id="vendido", status="vendido")],
            {"veiculo_id": "vendido"},
            "loja",
            "Lume",
        )
        self.assertEqual(resposta["sugestoes"], [])
        self.assertFalse(resposta["foco"]["disponivel"])

    def test_janela_e_conflito(self):
        expediente = {"seg": ["09:00", "18:00"], "ter": ["09:00", "18:00"], "qua": ["09:00", "18:00"],
                      "qui": ["09:00", "18:00"], "sex": ["09:00", "18:00"], "sab": ["09:00", "13:00"], "dom": None}
        futuro = (agora() + timedelta(days=10)).replace(hour=11, minute=0, second=0, microsecond=0)
        while futuro.weekday() == 6:
            futuro += timedelta(days=1)
        inicio, fim = validar_janela(futuro, expediente, referencia=agora())
        self.assertEqual(int((fim - inicio).total_seconds()), 3600)
        domingo = futuro + timedelta(days=(6 - futuro.weekday()) % 7)
        domingo = domingo.replace(hour=11)
        with self.assertRaises(ErroHttp):
            validar_janela(domingo, expediente, referencia=agora())
        passado = agora() - timedelta(days=1)
        with self.assertRaises(ErroHttp):
            validar_janela(passado.replace(minute=0, second=0, microsecond=0), expediente)
        a = futuro
        b = futuro + timedelta(hours=1)
        self.assertTrue(sobrepoe(a, b, a, b))
        ocupado = conflito_ocupado(
            [{"id": "1", "status": "confirmado", "inicio": a, "fim": b}],
            a, b, ignorar_id=None,
        )
        self.assertIsNotNone(ocupado)
        self.assertIsNone(conflito_ocupado(
            [{"id": "1", "status": "solicitado", "inicio": a, "fim": b}],
            a, b, None,
        ))

    def test_garantir_estoque_nao_apaga_lead(self):
        import tempfile

        from socialflow import banco, semear
        from socialflow.config import SENHA_ADMIN_PADRAO, SENHA_CONSULTOR_PADRAO, SENHA_VENDEDOR_PADRAO

        with tempfile.TemporaryDirectory() as pasta:
            conn = banco.conectar(Path(pasta) / "t.sqlite")
            try:
                banco.migrar(conn)
                self.assertTrue(semear.semear(
                    conn, SENHA_ADMIN_PADRAO, SENHA_VENDEDOR_PADRAO, SENHA_CONSULTOR_PADRAO,
                ))
                total = conn.execute("SELECT COUNT(*) AS n FROM vehicles").fetchone()["n"]
                self.assertEqual(total, len(semear.ESTOQUE))
                self.assertGreaterEqual(total, 18)
                leads = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
                self.assertGreaterEqual(leads, 1)
                vid = conn.execute(
                    "SELECT id FROM vehicles WHERE stock_code = 'EST-1024'"
                ).fetchone()["id"]
                conn.execute("DELETE FROM vehicle_images WHERE vehicle_id = ?", (vid,))
                conn.execute("DELETE FROM vehicles WHERE id = ?", (vid,))
                conn.execute(
                    "UPDATE business_settings SET theme_json = ? WHERE organization_id = ?",
                    ('{"acento": "#8a5a2b"}', semear.ORG_ID),
                )
                self.assertEqual(semear.garantir_estoque(conn), 1)
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) AS n FROM vehicles").fetchone()["n"], total,
                )
                self.assertEqual(
                    conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"], leads,
                )
                tema = conn.execute(
                    "SELECT theme_json FROM business_settings WHERE organization_id = ?",
                    (semear.ORG_ID,),
                ).fetchone()["theme_json"]
                self.assertIn("#d09850", tema)
                conn.execute(
                    "UPDATE business_settings SET theme_json = ? WHERE organization_id = ?",
                    ('{"acento": "#9a6b2e"}', semear.ORG_ID),
                )
                self.assertEqual(semear.garantir_estoque(conn), 0)
                tema = conn.execute(
                    "SELECT theme_json FROM business_settings WHERE organization_id = ?",
                    (semear.ORG_ID,),
                ).fetchone()["theme_json"]
                self.assertIn("#9a6b2e", tema)
                self.assertNotIn("#d09850", tema)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
