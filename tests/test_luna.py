import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from socialflow.luna import identificar_intencao, mesclar_estado, orquestrar
from socialflow.recomendacao import extrair_preferencias


def carro(**extras):
    base = {
        "id": extras.pop("id", "v1"),
        "organization_id": "loja",
        "brand": extras.pop("brand", "Hyundai"),
        "model": extras.pop("model", "HB20"),
        "version": extras.pop("version", "Comfort"),
        "year_manufacture": 2020,
        "year_model": 2021,
        "km": extras.pop("km", 42000),
        "transmission": extras.pop("transmission", "manual"),
        "fuel": "flex",
        "body_type": extras.pop("body_type", "hatch"),
        "price_cents": extras.pop("price_cents", 6890000),
        "status": extras.pop("status", "disponivel"),
        "stock_code": "EST-1",
        "color": "Prata",
        "description": "Unidade demonstrativa.",
    }
    base.update(extras)
    return base


class TestLuna(unittest.TestCase):
    def setUp(self):
        self.org = {"id": "loja", "name": "Lume Veículos"}
        self.config = {
            "trade_name": "Lume Veículos",
            "hours_json": '{"seg":["09:00","18:00"],"sab":["09:00","13:00"]}',
            "address_public": "Avenida Demonstração, 1200",
            "phone": "(11) 4000-0100",
            "email": "contato@lume.demo",
            "description": "",
            "services_json": "[]",
            "assistant_json": "{}",
            "theme_json": "{}",
            "privacy_note": "",
        }
        self.veiculos = [
            carro(id="hb20", brand="Hyundai", model="HB20", price_cents=6890000, transmission="manual"),
            carro(id="argo", brand="Fiat", model="Argo", price_cents=6890000, year_model=2024),
            carro(id="kwid", brand="Renault", model="Kwid", price_cents=6290000, year_model=2025),
            carro(id="pulse", brand="Fiat", model="Pulse", body_type="suv", transmission="cvt", price_cents=9290000, km=28000),
            carro(id="creta", brand="Hyundai", model="Creta", body_type="suv", transmission="automatico", price_cents=7590000, km=22000),
            carro(id="onix", brand="Chevrolet", model="Onix", price_cents=7990000, status="vendido"),
        ]

    def falar(self, mensagem, prefs=None, intencao=None):
        return orquestrar(mensagem, self.veiculos, prefs or {}, self.org, self.config, intencao=intencao)

    def test_intencoes(self):
        self.assertEqual(identificar_intencao("quero um carro até 50 mil"), "busca")
        self.assertEqual(identificar_intencao("quanto fica em 48 vezes"), "simulacao")
        self.assertEqual(identificar_intencao("qual é melhor, Onix ou HB20?"), "comparacao")
        self.assertEqual(identificar_intencao("quero falar com um vendedor"), "atendimento")
        self.assertEqual(identificar_intencao("posso agendar uma visita?"), "agendamento")
        self.assertEqual(identificar_intencao("onde fica a loja?"), "loja")
        self.assertEqual(identificar_intencao("OLA LUNA"), "saudacao")
        self.assertEqual(identificar_intencao("oi, tudo bem?"), "saudacao")
        self.assertEqual(identificar_intencao("obrigado"), "cortesia")
        self.assertEqual(identificar_intencao("qual a capital do Brasil?"), "fora")
        self.assertEqual(identificar_intencao("poderia me ajudar a ver um carro?"), "busca")
        self.assertEqual(identificar_intencao("quero saber sobre os carros automáticos"), "busca")
        self.assertEqual(identificar_intencao("queria saber mais sobre o gol"), "busca")
        self.assertEqual(identificar_intencao("o que voce faz"), "ajuda")

    def test_busca_por_preco_e_contexto(self):
        primeira = self.falar("Quero um SUV até R$ 80 mil")
        self.assertEqual(primeira["intencao"], "busca")
        self.assertEqual(primeira["correspondencia"], "exata")
        self.assertTrue(primeira["sugestoes"])
        segunda = self.falar("Mas quero automático.", primeira["preferencias"])
        self.assertEqual(segunda["preferencias"]["preco_max_centavos"], 8000000)
        self.assertEqual(segunda["preferencias"]["cambio"], "automaticos")
        terceira = self.falar("E com menos de 60 mil quilômetros.", segunda["preferencias"])
        self.assertEqual(terceira["preferencias"]["km_max"], 60000)
        ids = [item["id"] for item in terceira["sugestoes"]]
        self.assertIn("creta", ids)

    def test_veiculo_inexistente(self):
        resposta = self.falar("Tem Ferrari disponível?")
        self.assertEqual(resposta["correspondencia"], "vazia")
        self.assertFalse(resposta["sugestoes"])
        anterior = self.falar("Quanto fica o Kwid com 10 mil de entrada em 48 vezes?")
        repetida = self.falar("Tem Ferrari disponível?", anterior["preferencias"])
        self.assertEqual(repetida["correspondencia"], "vazia")
        self.assertFalse(repetida["sugestoes"])
        self.assertNotIn("kwid", repetida["texto"].lower())

    def test_simulacao_sem_inventar_juros(self):
        resposta = self.falar("Quanto fica um carro de R$ 70 mil em 48 vezes?")
        self.assertEqual(resposta["intencao"], "simulacao")
        self.assertEqual(resposta["simulacao"]["parcelas"], 48)
        self.assertEqual(resposta["simulacao"]["entrada_centavos"], 0)
        self.assertFalse(resposta["simulacao"]["tem_juros"])
        self.assertIn("não uma proposta", resposta["texto"].lower())

    def test_simulacao_com_entrada_antes_da_palavra(self):
        resposta = self.falar("Quanto fica o Kwid com 10 mil de entrada em 48 vezes?")
        self.assertEqual(resposta["intencao"], "simulacao")
        self.assertEqual(resposta["simulacao"]["valor_centavos"], 6290000)
        self.assertEqual(resposta["simulacao"]["entrada_centavos"], 1000000)
        self.assertEqual(resposta["simulacao"]["saldo_centavos"], 5290000)
        self.assertEqual(resposta["simulacao"]["parcelas"], 48)
        self.assertFalse(resposta["simulacao"]["tem_juros"])

    def test_comparacao_e_detalhes(self):
        comparacao = self.falar("Qual é melhor, Kwid ou HB20?")
        self.assertEqual(comparacao["intencao"], "comparacao")
        self.assertEqual(len(comparacao["comparacao"]), 2)
        detalhes = self.falar("Qual o preço?", comparacao["preferencias"], intencao="detalhes")
        self.assertEqual(detalhes["intencao"], "detalhes")
        self.assertTrue(detalhes["sugestoes"])

    def test_saudacao_nao_busca_estoque(self):
        resposta = self.falar("OLA LUNA")
        self.assertEqual(resposta["intencao"], "saudacao")
        self.assertFalse(resposta["sugestoes"])
        self.assertIn("lume", resposta["texto"].lower())
        self.assertNotIn("encontrei", resposta["texto"].lower())

    def test_atendimento_humano(self):
        resposta = self.falar("Quero falar com um vendedor")
        self.assertEqual(resposta["intencao"], "atendimento")
        self.assertEqual(resposta["acao"]["tipo"], "contato")

    def test_extracao_quilometros(self):
        prefs, _ = extrair_preferencias("com menos de 60 mil quilômetros")
        self.assertEqual(prefs["km_max"], 60000)

    def test_mescla_mantem_contexto(self):
        saida = mesclar_estado(
            {"preco_max_centavos": 8000000, "_intencao": "busca"},
            {"cambio": "automaticos"},
        )
        self.assertEqual(saida["preco_max_centavos"], 8000000)
        self.assertEqual(saida["cambio"], "automaticos")
        self.assertEqual(saida["_intencao"], "busca")

    def test_automaticos_nao_somem_por_filtro_antigo(self):
        prefs = {"tipo": "suv", "preco_max_centavos": 5000000, "_intencao": "busca"}
        resposta = self.falar("quero saber sobre os carros automáticos", prefs)
        self.assertEqual(resposta["intencao"], "busca")
        self.assertEqual(resposta["preferencias"]["cambio"], "automaticos")
        self.assertNotEqual(resposta["preferencias"].get("tipo"), "suv")
        self.assertTrue(resposta["sugestoes"])
        ids = {item["id"] for item in resposta["sugestoes"]}
        automaticos = {v["id"] for v in self.veiculos if v["transmission"] in {"automatico", "cvt"}}
        self.assertTrue(ids & automaticos)
        self.assertNotIn("hb20", ids)

    def test_saber_mais_sobre_gol_busca_estoque(self):
        self.veiculos.append(carro(id="gol", brand="Volkswagen", model="Gol", price_cents=4590000))
        resposta = self.falar("queria saber mais sobre o gol")
        self.assertEqual(resposta["intencao"], "busca")
        self.assertTrue(any(item["id"] == "gol" for item in resposta["sugestoes"]))

    def test_fechamento_oferece_consultor(self):
        resposta = self.falar(
            "Consigo comprar um carro com 20 mil de entrada e financiar o restante em 40 vezes?"
        )
        self.assertEqual(resposta["intencao"], "simulacao")
        self.assertEqual(resposta["preferencias"].get("simulacao_entrada_centavos"), 2000000)
        self.assertEqual(resposta["preferencias"].get("simulacao_parcelas"), 40)
        self.assertNotEqual(resposta["preferencias"].get("simulacao_valor_centavos"), 2000000)
        self.assertEqual(resposta["acao"]["tipo"], "contato")
        self.assertIn("consultor", resposta["acao"]["rotulo"].lower())

    def test_simulacao_completa_oferece_consultor(self):
        resposta = self.falar("Quanto fica um carro de R$ 70 mil em 48 vezes?")
        self.assertEqual(resposta["intencao"], "simulacao")
        self.assertTrue(resposta.get("simulacao"))
        self.assertEqual(resposta["acao"]["tipo"], "contato")


if __name__ == "__main__":
    unittest.main()
