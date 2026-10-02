"""Gera o mapa ticker -> CD_CVM a partir do cadastro oficial da CVM (F1-15).

Caminho oficial: FCA (código de negociação) -> CNPJ -> cadastro da CVM.
Grava `tests/fixtures/cvm_codigos_oficiais.csv` e regenera o bloco `_MANUAL_MAP`
de `cvm_ticker_map.py`. Rodar de novo não produz diff: depois da primeira
execução, o universo de tickers vem da fixture, que guarda também os `fora`.

Rede só de leitura (CVM), e só para o FCA do ano anterior, baixado uma vez para
`outputs/dossie_cache/`. Uso: python scripts/gerar_mapa_cvm.py
"""

from __future__ import annotations

import csv
import io
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.dossie_fase2 import CACHE, cd_oficial, http_get

FIXTURE = ROOT / "tests" / "fixtures" / "cvm_codigos_oficiais.csv"
MAPA = ROOT / "cvm_ticker_map.py"
COLUNAS = ["ticker", "cnpj", "cd_cvm", "situacao"]
BLOCO = re.compile(r"_MANUAL_MAP: dict\[int, str\] = \{.*?\n\}\n", re.DOTALL)


def _ler(arquivo: Path) -> pd.DataFrame:
    return pd.read_csv(arquivo, sep=";", encoding="latin-1", dtype=str)


def fca_ano(ano: int) -> pd.DataFrame:
    arquivo = CACHE / (
        "fca_valor_mobiliario.csv"
        if ano == date.today().year
        else f"fca_valor_mobiliario_{ano}.csv"
    )
    if not arquivo.exists():
        url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip"
        z = zipfile.ZipFile(io.BytesIO(http_get(url).content))
        nome = next(n for n in z.namelist() if "valor_mobiliario" in n)
        arquivo.write_bytes(z.read(nome))
        print(f"FCA {ano} baixado em {date.today().isoformat()}")
    df = _ler(arquivo)
    return df[df["Codigo_Negociacao"].notna()]


def _ativos(fca: pd.DataFrame) -> pd.DataFrame:
    """Código de negociação ativo: sem data de fim (mesma regra do dossiê)."""
    return fca[fca["Data_Fim_Negociacao"].isna()]


def universo_atual() -> dict[str, int]:
    """Ticker -> código no mapa. Com a fixture presente, ela é a fonte (inclui os `fora`)."""
    if FIXTURE.exists():
        linhas = list(csv.DictReader(FIXTURE.open(encoding="utf-8"), delimiter=";"))
        return {r["ticker"]: int(r["cd_cvm"]) if r["cd_cvm"] else 0 for r in linhas}
    from cvm_ticker_map import _TICKER_TO_CVM

    return dict(_TICKER_TO_CVM)


def classificar(universo, cad, fca26, fca25, fca_todos) -> list[dict]:
    linhas = []
    for ticker, cd_mapa in universo.items():
        cnpj, cd = cd_oficial(ticker, cad, _ativos(fca26))
        situacao = "fca_2026"
        if cd is None:
            cnpj, cd = cd_oficial(ticker, cad, _ativos(fca25))
            situacao = "fca_2025"
        if cd is None:
            situacao, cnpj, cd = "fora", "", None
            c = cad[cad["CD_CVM"].astype(int) == cd_mapa] if cd_mapa else cad.iloc[0:0]
            if len(c):
                antigos = fca_todos[
                    fca_todos["CNPJ_Companhia"] == c["CNPJ_CIA"].iloc[0]
                ]
                if any(x[:4] == ticker[:4] for x in antigos["Codigo_Negociacao"]):
                    situacao, cnpj, cd = (
                        "codigo_proprio",
                        c["CNPJ_CIA"].iloc[0],
                        cd_mapa,
                    )
        linhas.append(
            {
                "ticker": ticker,
                "cnpj": cnpj or "",
                "cd_cvm": cd or "",
                "situacao": situacao,
            }
        )
    return linhas


def gravar_fixture(linhas: list[dict]) -> None:
    with FIXTURE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def regenerar_mapa(linhas: list[dict]) -> None:
    mapa = {int(r["cd_cvm"]): r["ticker"] for r in linhas if r["situacao"] != "fora"}
    if len(mapa) != sum(r["situacao"] != "fora" for r in linhas):
        raise SystemExit("CD_CVM repetido entre tickers: o mapa é indexado pelo código")
    corpo = "".join(f'    {cd}: "{t}",\n' for cd, t in mapa.items())
    bloco = f"_MANUAL_MAP: dict[int, str] = {{\n{corpo}}}\n"
    MAPA.write_text(
        BLOCO.sub(lambda _: bloco, MAPA.read_text(encoding="utf-8")), encoding="utf-8"
    )


def main() -> None:
    cad = _ler(CACHE / "cad_cia_aberta.csv")
    ano = date.today().year
    fca26, fca25 = fca_ano(ano), fca_ano(ano - 1)
    fca_todos = pd.concat([fca26, fca25])
    linhas = classificar(universo_atual(), cad, fca26, fca25, fca_todos)
    gravar_fixture(linhas)
    regenerar_mapa(linhas)
    for s in ("fca_2026", "fca_2025", "codigo_proprio", "fora"):
        print(s, [r["ticker"] for r in linhas if r["situacao"] == s])


if __name__ == "__main__":
    main()
