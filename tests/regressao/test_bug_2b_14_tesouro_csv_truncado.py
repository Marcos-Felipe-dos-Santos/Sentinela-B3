"""F2B-27 exige cache com aviso se a resposta atual é inválida."""

import os
from datetime import UTC, datetime, timedelta

from sentinela.data.providers import tesouro


def test_csv_truncado_na_rede_preserva_cache(tmp_path, monkeypatch):
    instante = datetime(2026, 10, 19, 18, tzinfo=UTC)
    texto = (
        "Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha\n"
        "Tesouro IPCA+;15/05/2035;15/10/2026;6,84;6,96\n"
    )
    arquivo = tmp_path / "precotaxatesourodireto.csv"
    arquivo.write_text(texto)
    coleta = (instante - timedelta(days=2)).timestamp()
    os.utime(arquivo, (coleta, coleta))

    class Resposta:
        content = (texto.splitlines()[0] + "\nTesouro IPCA+;15/05/2035\n").encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(tesouro.requests, "get", lambda *a, **kw: Resposta())
    snapshot = tesouro.TesouroProvider(tmp_path).baixar(instante)
    assert arquivo.read_text() == texto
    assert snapshot.avisos and "cache" in snapshot.avisos[0]
    assert (
        tesouro.ler_snapshot(snapshot, as_of=instante)[0].taxa_aplicacao.valor == 0.0684
    )
