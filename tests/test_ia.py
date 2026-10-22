import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from socialflow import ia


class TestIaGemini(unittest.TestCase):
    def test_provedor_gemini_por_padrao_do_modelo(self):
        config = SimpleNamespace(ai_provider="gemini", ai_base="", ai_model="gemini-3.8-flash")
        self.assertEqual(ia.provedor(config), "gemini")

    def test_montar_corpo_gemini_usa_system_instruction(self):
        corpo = ia.montar_corpo_gemini([
            {"role": "system", "content": "Seja a Luna."},
            {"role": "user", "content": "{\"texto_base\":\"oi\"}"},
        ], temperatura=0.4)
        self.assertEqual(corpo["system_instruction"]["parts"][0]["text"], "Seja a Luna.")
        self.assertEqual(corpo["contents"][0]["role"], "user")
        self.assertEqual(corpo["generationConfig"]["responseMimeType"], "application/json")

    def test_extrair_texto_gemini(self):
        envelope = {
            "candidates": [{
                "content": {"parts": [{"text": "{\"texto\":\"Encontrei o Kwid no estoque.\"}"}]}
            }]
        }
        self.assertIn("Kwid", ia.extrair_texto_gemini(envelope))

    def test_redigir_luna_sem_chave_nao_chama_rede(self):
        config = SimpleNamespace(ai_key="", ai_provider="gemini", ai_base="", ai_model="gemini-3.8-flash")
        self.assertIsNone(ia.redigir_luna("Encontrei um hatch no estoque.", {"mensagem": "hatch"}, config))

    def test_embelezar_luna_adiciona_emoji(self):
        texto = ia.embelezar_luna("Encontrei três automáticos no estoque.", "busca")
        self.assertIn("🚗", texto)
        self.assertEqual(ia.embelezar_luna("Já respondi 😊", "busca"), "Já respondi 😊")

    def test_url_generate_gemini(self):
        url = ia._url_generate("gemini-3.8-flash", ia.GEMINI_BASE)
        self.assertTrue(url.startswith("https://generativelanguage.googleapis.com/"))
        self.assertIn("generateContent", url)
        self.assertTrue(ia.url_permitida(url))


if __name__ == "__main__":
    unittest.main()
