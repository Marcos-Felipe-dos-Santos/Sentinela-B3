"""ZIPs oficiais da CVM remontados como existiam em D (F3-3d, DD-62).

A cascata (`CVMProvider`, `CVMFIIProvider`) lê os ZIPs abertos da CVM pelo caminho do
arquivo. Para a análise numa data passada, `zip_cia_em` e `zip_informe_em` escrevem, num
diretório de trabalho, o ZIP do ano no leiaute oficial com só o que existia antes do dia de D,
pelos leitores ponto-no-tempo (`leitura`, F3-3c): o índice de entregas visível em D e, para
cada documento, os números da versão que o leitor escolhe; o resto do caminho da cascata não
muda (regra R2 do F3-3d: ligar o histórico sem mudar método, fórmula ou parâmetro).

Documento que o leitor deixa fora (versão vigente sem números na fonte aberta, conflito da
carga, DD-57) continua no índice e fica sem números: a cascata o vê e se abstém dele, em vez
de voltar a um documento anterior. Os motivos vão no retorno, para os riscos da análise.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import sqlite3
import tempfile
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from sentinela.data.pit import leitura
from sentinela.data.pit.carga_cvm import _COMPOSICAO

_GRUPO = {
    "BPA": "Balanço Patrimonial Ativo",
    "BPP": "Balanço Patrimonial Passivo",
    "DRE": "Demonstração do Resultado",
    "DRA": "Demonstração de Resultado Abrangente",
    "DFC_MD": "Demonstração do Fluxo de Caixa (Método Direto)",
    "DFC_MI": "Demonstração do Fluxo de Caixa (Método Indireto)",
    "DMPL": "Demonstração das Mutações do Patrimônio Líquido",
    "DVA": "Demonstração de Valor Adicionado",
}
_INDICE = ["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", "CD_CVM", "CATEG_DOC", "ID_DOC",
           "DT_RECEB", "LINK_DOC"]  # fmt: skip
_COMPOSICAO_CSV = ["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", *_COMPOSICAO.values()]


@contextmanager
def _gravar(caminho: Path):
    """ZIP escrito num temporário do mesmo diretório e trocado de uma vez (sessões paralelas)."""
    descritor, nome = tempfile.mkstemp(dir=caminho.parent, suffix=".tmp")
    os.close(descritor)
    temporario = Path(nome)
    try:
        with zipfile.ZipFile(temporario, "w", zipfile.ZIP_DEFLATED) as zf:
            yield zf
        temporario.replace(caminho)
    finally:
        temporario.unlink(missing_ok=True)


def _cabecalho(demonstracao: str) -> list[str]:
    tipo = demonstracao.rsplit("_", 1)[0]
    colunas = ["CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA", "CD_CVM", "GRUPO_DFP", "MOEDA",
               "ESCALA_MOEDA", "ORDEM_EXERC"]  # fmt: skip
    if tipo not in ("BPA", "BPP"):
        colunas.append("DT_INI_EXERC")
    colunas.append("DT_FIM_EXERC")
    if tipo == "DMPL":
        colunas.append("COLUNA_DF")
    return [*colunas, "CD_CONTA", "DS_CONTA", "VL_CONTA", "ST_CONTA_FIXA"]


def _grupo(demonstracao: str) -> str:
    tipo, escopo = demonstracao.rsplit("_", 1)
    return f"DF {'Consolidado' if escopo == 'con' else 'Individual'} - {_GRUPO[tipo]}"


def _numero(valor: float | None) -> str:
    return "" if valor is None else f"{valor:.10f}"


def _csv(colunas: list[str], linhas: list[dict]) -> bytes:
    saida = io.StringIO()
    escritor = csv.DictWriter(
        saida, colunas, delimiter=";", lineterminator="\n", extrasaction="ignore"
    )
    escritor.writeheader()
    escritor.writerows(linhas)
    return saida.getvalue().encode("latin-1", errors="replace")


def zip_cia_em(
    conn: sqlite3.Connection,
    documento: str,
    ano: int,
    as_of: datetime,
    destino: Path,
    *,
    modo: str = leitura.ESTRITO,
) -> tuple[Path, dict]:
    """(ZIP `{dfp|itr}_cia_aberta_{ano}.zip` como existia em D, motivos dos documentos fora)."""
    doc = documento.lower()
    dia = leitura._dia(as_of, modo)
    indice = [
        linha | {"LINK_DOC": ""}
        for linha in leitura.entregas(conn, documento, as_of, modo=modo).dados
        if linha["DT_REFER"][:4] == str(ano)
    ]
    nomes = {(r["CNPJ_CIA"], r["DT_REFER"], r["VERSAO"]): r for r in indice}
    _, escolhidos, motivos = leitura._escolha_cia(
        conn, "demonstracoes", documento, None, dia, modo
    )
    membros: dict[str, list[dict]] = {}
    for (
        cnpj, dt_refer, versao, demonstracao, ordem, inicio, fim, coluna, conta, descricao,
        valor, escala, moeda, fixa,
    ) in conn.execute(
        "SELECT cnpj, dt_refer, versao, demonstracao, ordem_exerc, dt_ini_exerc, "
        "dt_fim_exerc, coluna_df, conta, descricao, valor, escala, moeda, conta_fixa "
        "FROM demonstracoes WHERE documento = ? AND substr(dt_refer, 1, 4) = ? "
        "ORDER BY demonstracao, cnpj, dt_refer, versao, ordem_exerc, dt_ini_exerc, "
        "dt_fim_exerc, coluna_df, conta",
        (documento, str(ano)),
    ):  # fmt: skip
        if escolhidos.get((cnpj, dt_refer)) != versao:
            continue
        entrega = nomes.get((cnpj, dt_refer, str(versao)), {})
        membros.setdefault(demonstracao, []).append({
            "CNPJ_CIA": cnpj, "DT_REFER": dt_refer, "VERSAO": versao,
            "DENOM_CIA": entrega.get("DENOM_CIA", ""), "CD_CVM": entrega.get("CD_CVM", ""),
            "GRUPO_DFP": _grupo(demonstracao), "MOEDA": moeda, "ESCALA_MOEDA": escala,
            "ORDEM_EXERC": ordem, "DT_INI_EXERC": inicio, "DT_FIM_EXERC": fim,
            "COLUNA_DF": coluna, "CD_CONTA": conta, "DS_CONTA": descricao,
            "VL_CONTA": _numero(valor), "ST_CONTA_FIXA": fixa,
        })  # fmt: skip
    composicao = [
        linha
        for linha in leitura.composicao(
            conn, documento, as_of, modo=modo
        ).dados.to_dict("records")
        if str(linha["DT_REFER"])[:4] == str(ano)
    ]
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{doc}_cia_aberta_{ano}.zip"
    with _gravar(caminho) as zf:
        zf.writestr(f"{doc}_cia_aberta_{ano}.csv", _csv(_INDICE, indice))
        for demonstracao in sorted(f"{t}_{e}" for t in _GRUPO for e in ("con", "ind")):
            # o arquivo aberto traz as 16 demonstrações, mesmo sem linha
            zf.writestr(
                f"{doc}_cia_aberta_{demonstracao}_{ano}.csv",
                _csv(_cabecalho(demonstracao), membros.get(demonstracao, [])),
            )
        if composicao or _tem_composicao(conn, documento, ano):
            zf.writestr(
                f"{doc}_cia_aberta_composicao_capital_{ano}.csv",
                _csv(_COMPOSICAO_CSV, [_composicao_csv(linha) for linha in composicao]),
            )
    return caminho, {
        chave: motivo for chave, motivo in motivos.items() if chave[1][:4] == str(ano)
    }


def _tem_composicao(conn, documento: str, ano: int) -> bool:
    """O arquivo do ano traz a composição do capital (a CVM a publica desde 2020)."""
    return (
        conn.execute(
            "SELECT 1 FROM composicao_capital WHERE documento = ? AND substr(dt_refer, 1, 4) = ? "
            "LIMIT 1",
            (documento, str(ano)),
        ).fetchone()
        is not None
    )


def _composicao_csv(linha: dict) -> dict:
    saida = {
        c: linha.get(c, "") for c in ("CNPJ_CIA", "DT_REFER", "VERSAO", "DENOM_CIA")
    }
    for coluna in _COMPOSICAO.values():
        valor = linha.get(coluna)
        saida[coluna] = "" if valor is None or math.isnan(valor) else str(int(valor))
    return saida


def zip_informe_em(
    conn: sqlite3.Connection,
    ano: int,
    as_of: datetime,
    destino: Path,
    *,
    modo: str = leitura.ESTRITO,
) -> Path:
    """Remonta o Informe pelo leitor canônico, preservando bloqueios e modo.

    As linhas mantêm o leiaute original; o controle lateral guarda os documentos
    indisponíveis para impedir recuo silencioso no consumidor. Data/modo isolam arquivos.
    """
    dia = leitura._dia(as_of, modo)
    linhas = conn.execute(
        "SELECT cnpj, dt_refer, versao, parte, linha_json FROM fii_informe_linhas "
        "WHERE substr(dt_refer, 1, 4) = ? ORDER BY cnpj, dt_refer, versao, parte, linha_sha256",
        (str(ano),),
    ).fetchall()
    visiveis: set[tuple[str, str, str]] = set()
    motivos: dict[str, dict[str, str]] = {}
    for cnpj in sorted({r[0] for r in linhas}):
        lido = leitura.informe_fii(conn, cnpj, as_of, modo=modo, ano=ano)
        visiveis.update(
            (cnpj, r["Data_Referencia"], r["Versao"]) for r in lido.dados["registros"]
        )
        for (_, referencia), motivo in lido.motivos.items():
            motivos.setdefault(cnpj, {})[referencia] = motivo
    partes: dict[str, list[dict]] = {}
    for cnpj, referencia, versao, parte, texto in linhas:
        if (cnpj, referencia, versao) in visiveis:
            partes.setdefault(parte, []).append(json.loads(texto))
    destino = destino / dia.isoformat() / modo
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"inf_mensal_fii_{ano}.zip"
    with _gravar(caminho) as zf:
        for parte, registros in sorted(partes.items()):
            colunas = list(dict.fromkeys(c for r in registros for c in r))
            zf.writestr(f"inf_mensal_fii_{parte}_{ano}.csv", _csv(colunas, registros))
        zf.writestr(
            "sentinela_informe_pit.json",
            json.dumps({"dia": dia.isoformat(), "modo": modo, "motivos": motivos}, ensure_ascii=False),
        )
    return caminho
