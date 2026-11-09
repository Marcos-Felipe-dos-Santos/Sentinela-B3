"""BUG-2C-32: a fonte da janela não substitui a inaplicabilidade do método."""

from test_rastreabilidade import _acao, _contexto


def test_janela_ausente_nao_esconde_modelo_banco_fora_do_escopo():
    dados = _acao(modelo_bpp="banco")
    dados.pop("serie_cvm", None)
    r = _contexto(dados)
    for metodo in r["metodos"]:
        if metodo["nome"] in {"Graham", "Lynch"}:
            assert metodo["abstencao"] == "modelo banco fora do escopo do método"
