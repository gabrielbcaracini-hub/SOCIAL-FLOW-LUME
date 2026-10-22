"""Erros de negócio traduzidos em respostas HTTP, sem vazar detalhe interno."""


class ErroHttp(Exception):
    def __init__(self, status, mensagem, campos=None):
        super().__init__(mensagem)
        self.status = int(status)
        self.mensagem = mensagem
        self.campos = campos or {}
