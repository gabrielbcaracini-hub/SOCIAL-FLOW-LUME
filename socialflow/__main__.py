"""Ponto de entrada: python -m socialflow"""

import sys

from socialflow.config import configuracao_de_ambiente
from socialflow.servidor import preparar_banco, servir


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    config = configuracao_de_ambiente()
    if len(argv) > 1 and argv[1] in {"-h", "--help", "ajuda"}:
        sys.stdout.write(
            "Uso:\n"
            "  python -m socialflow          sobe a vitrine e o painel\n"
            "  python -m socialflow seed     cria o banco se ele ainda não existe\n"
        )
        return 0
    if len(argv) > 1 and argv[1] == "seed":
        preparar_banco(config)
        sys.stdout.write("Banco local pronto em %s\n" % config.db_path)
        return 0
    if len(argv) > 1 and argv[1] not in {"serve", "servir"}:
        sys.stderr.write("Comando desconhecido. Use: python -m socialflow\n")
        return 2
    servir(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
