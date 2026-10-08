"""Cobertura do índice sobre os arquivos oficiais (gate da F2A-1)."""

from __future__ import annotations

import pandas as pd

from sentinela.data.referencia.montagem import (
    fca_mais_recente,
    fiis_em_bolsa,
    linhas_ativas_do_fca,
    normalizar_codigo,
)
from sentinela.data.referencia.registro import Indice


def cobertura(
    indice: Indice, fcas: list[tuple[int, pd.DataFrame]], informe: pd.DataFrame
) -> dict:
    """Mapeáveis e mapeados por grupo. Companhias: pares (CNPJ, código) ativos no FCA; FIIs: listados em bolsa.

    Os tickers ligados pela tabela de correções aparecem em `correcoes`, por classe; os de
    companhia contam como mapeados.
    """
    ativos = linhas_ativas_do_fca(fca_mais_recente(fcas))
    codigos = {
        (linha["CNPJ_Companhia"], normalizar_codigo(linha["Codigo_Negociacao"]))
        for _, linha in ativos.iterrows()
    }
    motivos: dict[str, int] = {}
    for excecao in indice.excecoes:
        motivos[excecao.motivo] = motivos.get(excecao.motivo, 0) + 1
    regras: dict[str, int] = {}
    corrigidos: dict[str, list[str]] = {}
    for registro in indice.registros.values():
        regras[registro.regra] = regras.get(registro.regra, 0) + 1
        if registro.correcao:
            corrigidos.setdefault(registro.classe, []).append(registro.ticker)
    fiis = fiis_em_bolsa(informe)
    return {
        "companhias": {
            "codigos_ativos_no_fca": len(codigos),
            "mapeados": regras.get("fca:codigo_ativo", 0)
            + len(corrigidos.get("STOCK", []))
            + len(corrigidos.get("UNIT", [])),
        },
        "fiis": {
            "listados_em_bolsa": len(fiis),
            "mapeados_pela_juncao": regras.get("fii:informe+cotahist_isin", 0),
            "mapeados_pela_reserva": regras.get("fii:reserva_isin", 0),
        },
        "outros": {
            "bdr": regras.get("cotahist:bdr", 0),
            "unknown": regras.get("cotahist:cota_de_fundo", 0),
        },
        "excecoes_por_motivo": motivos,
        "correcoes": {classe: sorted(t) for classe, t in sorted(corrigidos.items())},
    }
