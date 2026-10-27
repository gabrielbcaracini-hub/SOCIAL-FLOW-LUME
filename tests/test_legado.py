import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAIZ = Path(__file__).resolve().parents[1]
TERMOS = re.compile(r"\b(cras|creas|paif|paefi|scfv|rma|cadúnico|bolsa família|smads)\b", re.IGNORECASE)


class TestLegado(unittest.TestCase):
    def test_interface_sem_dominio_antigo(self):
        arquivos = list((RAIZ / "js").glob("*.js")) + list((RAIZ / "css").glob("*.css"))
        arquivos += [RAIZ / nome for nome in ("index.html", "veiculo.html", "painel.html", "privacidade.html")]
        for arquivo in arquivos:
            texto = arquivo.read_text(encoding="utf-8")
            self.assertIsNone(TERMOS.search(texto), arquivo.name)

    def test_pagina_publica_de_privacidade(self):
        self.assertTrue((RAIZ / "privacidade.html").exists())
        self.assertFalse((RAIZ / "js" / "privacidade.js").exists())
        for nome in ("index.html", "veiculo.html", "painel.html"):
            texto = (RAIZ / nome).read_text(encoding="utf-8")
            self.assertIn("/privacidade", texto)
            self.assertIn("Privacidade", texto)

    def test_html_utf8(self):
        bruto = (RAIZ / "index.html").read_bytes()
        texto = bruto.decode("utf-8")
        self.assertIn("Veículos", texto)
        self.assertIn("não", texto.casefold())
        self.assertNotIn("\ufeff", texto)


if __name__ == "__main__":
    unittest.main()
