"""Levantamento das fontes oficiais da Fase 2A (F2A-16).

Confere nos arquivos reais os fatos de que os itens da fila dependem e grava o
resultado em `outputs/levantamento_fase2a.json` (fora do git). O texto que interpreta
os números está em `docs/decisoes/fontes-fase2a.md`.

Rede só de leitura (CVM, B3, Banco Central, yfinance), com cache em
`outputs/levantamento_cache/`. Não importa `config`, não usa token da brapi, não lê
`.env`, a carteira nem o banco. A amostra vem dos mapas públicos do código.

Uso: python scripts/levantamento_fase2a.py [--secao 1 2 ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from sentinela.data.providers import b3_cotahist as cot  # noqa: E402

CACHE = RAIZ / "outputs" / "levantamento_cache"
SAIDA = RAIZ / "outputs" / "levantamento_fase2a.json"
UA = {"User-Agent": "Mozilla/5.0 (Sentinela levantamento F2A-16; leitura)"}
ANO_DFP = 2025
ANO_FCA = 2026
MESES_COTAHIST = ((2026, 7), (2026, 8), (2026, 9))
CVM = "https://dados.cvm.gov.br/dados"
BCB = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
CODIGOS_OFICIAIS = RAIZ / "tests" / "fixtures" / "cvm_codigos_oficiais.csv"
DOSSIE = RAIZ / "docs" / "decisoes" / "dossie-fase2.md"


# ── utilidades ────────────────────────────────────────────────────────────────


def baixar(url: str, nome: str) -> Path:
    """Baixa para o cache uma vez (leitura); reaproveita o arquivo se já existe."""
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / nome
    if not destino.exists():
        resp = requests.get(url, timeout=300, headers=UA)
        resp.raise_for_status()
        destino.write_bytes(resp.content)
    return destino


def csv_do_zip(zip_path: Path, nome: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        return pd.read_csv(zf.open(nome), sep=";", encoding="latin-1", dtype=str)


def dfp() -> Path:
    return baixar(
        f"{CVM}/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ANO_DFP}.zip",
        f"dfp_{ANO_DFP}.zip",
    )


def dem(zip_path: Path, tipo: str) -> pd.DataFrame:
    df = csv_do_zip(zip_path, f"dfp_cia_aberta_{tipo}_{ANO_DFP}.csv")
    if "ORDEM_EXERC" in df:
        df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
    return df


def valor(df: pd.DataFrame, cd: str, conta: str) -> float | None:
    x = df[(df["CD_CVM"] == cd) & (df["CD_CONTA"] == conta)]
    if x.empty:
        return None
    v = float(x["VL_CONTA"].iloc[0])
    escala = 1000 if str(x["ESCALA_MOEDA"].iloc[0]).upper() == "MIL" else 1
    return v * escala


def codigos_oficiais() -> dict[str, str]:
    with CODIGOS_OFICIAIS.open(encoding="utf-8") as f:
        return {
            r["ticker"]: r["cd_cvm"].zfill(6)
            for r in csv.DictReader(f, delimiter=";")
            if r["situacao"] != "fora"
        }


def cotacoes() -> pd.DataFrame:
    """Mercado à vista de jul a set/2026 (65 pregões)."""
    pkl = CACHE / "cotahist_vista.pkl"
    if pkl.exists():
        return pd.read_pickle(pkl)
    registros = []
    for ano, mes in MESES_COTAHIST:
        zip_path = baixar(
            cot.URL_MENSAL.format(ano=ano, mes=mes), f"COTAHIST_M{mes:02d}{ano}.ZIP"
        )
        registros += [c.__dict__ for c in cot.ler_zip(zip_path)]
    df = pd.DataFrame(registros)
    df.to_pickle(pkl)
    return df


def fca_valor_mobiliario() -> pd.DataFrame:
    p = baixar(
        f"{CVM}/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ANO_FCA}.zip",
        f"fca_{ANO_FCA}.zip",
    )
    return csv_do_zip(p, f"fca_cia_aberta_valor_mobiliario_{ANO_FCA}.csv")


def classe_do_papel(row) -> str:
    """Grupo usado só no levantamento: ação, unit, FII, outro fundo, BDR, outro."""
    if row.codbdi == "12" and row.especificacao.startswith("CI"):
        return "fii"
    if row.codbdi in ("14", "13") and row.especificacao.startswith("CI"):
        return "outro_fundo"
    if row.codbdi in ("34", "35", "36") and not row.especificacao.startswith("UNT"):
        return "bdr"
    if row.especificacao.startswith("UNT"):
        return "unit"
    if row.codbdi in ("02", "07", "08"):
        return "acao"
    return "outro"


# ── 1. FCA ────────────────────────────────────────────────────────────────────


def secao_1() -> dict:
    vm = fca_valor_mobiliario()
    cotas = cotacoes()
    negociados = set(cotas["codigo_negociacao"])
    cod = vm["Codigo_Negociacao"].dropna().str.strip().str.upper()
    formato = re.compile(r"^[A-Z][A-Z0-9]{3}\d{1,2}$")
    fora = cod[~cod.str.match(formato)]
    units = vm[vm["Valor_Mobiliario"] == "Units"]
    ativos = vm[
        vm["Data_Fim_Negociacao"].isna()
        & (vm["Mercado"] == "Bolsa")
        & vm["Valor_Mobiliario"].isin(
            ["Ações Ordinárias", "Ações Preferenciais", "Units"]
        )
        & vm["Codigo_Negociacao"].fillna("").str.strip().str.upper().str.match(formato)
    ]
    ativos = ativos.assign(cod=ativos["Codigo_Negociacao"].str.strip().str.upper())
    sem_cotacao = ativos[~ativos["cod"].isin(negociados)]
    cod_units = units["Codigo_Negociacao"].fillna("").str.strip().str.upper()
    publicos = set(_tickers_publicos())
    return {
        "colunas": list(vm.columns),
        "valores_valor_mobiliario": vm["Valor_Mobiliario"].value_counts().to_dict(),
        "mercados": vm["Mercado"].value_counts().to_dict(),
        "tem_coluna_isin": any("ISIN" in c.upper() for c in vm.columns),
        "units": {
            "linhas": len(units),
            "com_composicao_preenchida": int(
                units["Composicao_BDR_Unit"].notna().sum()
            ),
            "com_codigo_negociacao": int(units["Codigo_Negociacao"].notna().sum()),
            "sem_codigo_negociacao": units[cod_units == ""][
                "Nome_Empresarial"
            ].tolist(),
            "codigo_fora_do_formato": units[
                (cod_units != "") & ~cod_units.str.match(formato)
            ][["Nome_Empresarial", "Codigo_Negociacao"]].values.tolist(),
            "exemplos_composicao": units["Composicao_BDR_Unit"]
            .dropna()
            .head(8)
            .tolist(),
        },
        "codigos_fora_do_formato": {
            "total": int(len(fora)),
            "de_total_codigos": int(len(cod)),
            "regra": "quatro caracteres alfanuméricos (o primeiro, letra) e um ou dois dígitos, após maiúsculas e sem espaços",
            "amostra": sorted(fora.unique())[:25],
            "csn_4030": vm[vm["Codigo_Negociacao"] == "4030"][
                "Nome_Empresarial"
            ].tolist(),
        },
        "sem_data_fim_e_sem_cotacao_no_cotahist": {
            "ativos_sem_data_fim_no_formato": int(len(ativos)),
            "sem_cotacao_jul_set_2026": int(len(sem_cotacao)),
            "dos_mapas_publicos": sorted(set(sem_cotacao["cod"]) & publicos),
            "amostra": sorted(set(sem_cotacao["cod"]))[:25],
        },
    }


def _tickers_publicos() -> list[str]:
    from cvm_fii_map import FII_CNPJ_MAP
    from cvm_ticker_map import _TICKER_TO_CVM

    return sorted(set(_TICKER_TO_CVM) | set(FII_CNPJ_MAP))


# ── 2. Escala da Composição do Capital ────────────────────────────────────────


def _tickers_dossie() -> set[str]:
    """Tickers que a tabela da seção 1 do dossiê marca com escala em milhares."""
    milhares = set()
    for linha in DOSSIE.read_text(encoding="utf-8").splitlines():
        partes = [p.strip() for p in linha.strip("|").split("|")]
        if len(partes) == 7 and re.fullmatch(r"[A-Z]{4}\d{1,2}", partes[0]):
            if partes[6] == "sim":
                milhares.add(partes[0])
    return milhares


def _acoes_cc(cc: pd.DataFrame, cnpj: str) -> float | None:
    x = (
        cc[cc["CNPJ_CIA"] == cnpj]
        .assign(_v=lambda d: pd.to_numeric(d["VERSAO"]))
        .sort_values("_v")
    )
    if x.empty:
        return None
    r = x.iloc[-1]
    tesouraria = pd.to_numeric(r["QT_ACAO_TOTAL_TESOURO"])
    tesouraria = 0.0 if pd.isna(tesouraria) else float(tesouraria)
    total = float(r["QT_ACAO_TOTAL_CAP_INTEGR"]) - tesouraria
    return total


def secao_2() -> dict:
    z = dfp()
    dre = dem(z, "DRE_con")
    cc = csv_do_zip(z, f"dfp_cia_aberta_composicao_capital_{ANO_DFP}.csv")
    bpp = dem(z, "BPP_con")
    cnpj_de = dict(zip(bpp["CD_CVM"], bpp["CNPJ_CIA"], strict=False))
    milhares_dossie = _tickers_dossie()
    from cvm_ticker_map import _TICKER_TO_CVM

    oficiais = codigos_oficiais()
    tickers = sorted(t for t in _TICKER_TO_CVM if t in oficiais)

    linhas_399 = dre[dre["CD_CONTA"].str.startswith("3.99")]
    escala_399 = linhas_399["ESCALA_MOEDA"].value_counts().to_dict()
    exemplo_itub = valor_bruto(dre, oficiais.get("ITUB4", ""), "3.99.01")

    motivos: dict[str, str] = {}

    def avalia(cd: str) -> dict | None:
        cnpj = cnpj_de.get(cd)
        acoes = _acoes_cc(cc, cnpj) if cnpj else None
        luc_tot = valor(dre, cd, "3.11") or valor(dre, cd, "3.09")
        luc_ctrl = valor(dre, cd, "3.11.01") or valor(dre, cd, "3.09.01") or luc_tot
        lpa = valor_bruto(dre, cd, "3.99.01.01") or valor_bruto(dre, cd, "3.99.01.02")
        motivo = None
        if not cnpj or acoes is None:
            motivo = "sem linha de Composição do Capital"
        elif not luc_ctrl:
            motivo = "sem lucro (3.11.01, 3.09.01, 3.11, 3.09)"
        elif luc_ctrl <= 0:
            motivo = "lucro dos controladores <= 0"
        elif not lpa:
            motivo = "sem LPA básico em 3.99.01.01 nem em 3.99.01.02"
        elif lpa <= 0:
            motivo = "LPA básico <= 0"
        elif acoes <= 0:
            motivo = "total de ações <= 0"
        if motivo:
            motivos[cd] = motivo
            return None
        melhor = min(
            (1, 1000),
            key=lambda s: abs(math.log(luc_ctrl / (acoes * s) / lpa)),
        )
        implicito = luc_ctrl / (acoes * melhor)
        ajuste_total = None
        if luc_tot and luc_tot > 0 and luc_tot != luc_ctrl:
            ajuste_total = abs(math.log(luc_tot / (acoes * melhor) / lpa))
        return {
            "escala": melhor,
            "razao_lpa_calculado_sobre_divulgado": implicito / lpa,
            "erro_controladora": abs(math.log(implicito / lpa)),
            "erro_lucro_total": ajuste_total,
        }

    do_mapa = {}
    motivo_por_ticker = {}
    for t in tickers:
        cd = oficiais.get(t)
        if cd:
            r = avalia(cd)
            if r:
                do_mapa[t] = r
            else:
                motivo_por_ticker[t] = motivos[cd]

    motivos.clear()
    universo = {}
    for cd in cnpj_de:
        r = avalia(cd)
        if r:
            universo[cd] = r

    def resumo(d: dict) -> dict:
        razoes = sorted(v["razao_lpa_calculado_sobre_divulgado"] for v in d.values())
        if not razoes:
            return {"n": 0}
        q = lambda p: razoes[min(len(razoes) - 1, int(p * len(razoes)))]  # noqa: E731
        fora = lambda a, b: sum(not (a <= r <= b) for r in razoes)  # noqa: E731
        return {
            "n": len(d),
            "razao_min_max": [round(razoes[0], 3), round(razoes[-1], 3)],
            "fora_de_0_8_a_1_25": fora(0.8, 1.25),
            "fora_de_0_5_a_2": fora(0.5, 2),
            "fora_de_0_1_a_10": fora(0.1, 10),
            "piores_cinco_codigos_cvm": [
                [k, round(v["razao_lpa_calculado_sobre_divulgado"], 3), v["escala"]]
                for k, v in sorted(
                    d.items(),
                    key=lambda kv: (
                        -abs(math.log(kv[1]["razao_lpa_calculado_sobre_divulgado"]))
                    ),
                )[:5]
            ],
            "separacao_das_escalas": "as duas hipóteses diferem por 1.000; a escolha só é ambígua com razão perto de 1/31,6 ou 31,6 (raiz de 1.000)",
            "escala_1000": sorted(k for k, v in d.items() if v["escala"] == 1000),
            "n_escala_1000": sum(v["escala"] == 1000 for v in d.values()),
            "razao_p10_p50_p90": [round(q(0.1), 3), round(q(0.5), 3), round(q(0.9), 3)],
            "dentro_de_10pct": sum(0.9 <= r <= 1.1 for r in razoes),
            "com_lucro_total_diferente_do_dos_controladores": sum(
                v["erro_lucro_total"] is not None for v in d.values()
            ),
            "controladora_estritamente_mais_proxima": sum(
                1
                for v in d.values()
                if v["erro_lucro_total"] is not None
                and v["erro_controladora"] < v["erro_lucro_total"]
            ),
        }

    inferidas = {t for t, v in do_mapa.items() if v["escala"] == 1000}
    n_empresas = bpp["CD_CVM"].nunique()
    return {
        "regra": "escala (1 ou 1000) que aproxima lucro atribuído aos controladores ÷ ações (ON+PN−tesouraria) do LPA básico divulgado (3.99.01.01, ou 3.99.01.02 se não houver)",
        "composicao_capital_tem_coluna_de_escala": any(
            "ESCALA" in c for c in cc.columns
        ),
        "colunas_composicao_capital": list(cc.columns),
        "acoes_do_mapa": {
            "tickers": len(tickers),
            "avaliados": len(do_mapa),
            "nao_avaliados": dict(sorted(motivo_por_ticker.items())),
            **resumo(do_mapa),
        },
        "dossie_marcados_em_milhares_na_tabela": sorted(milhares_dossie),
        "confronto_com_o_dossie": {
            "so_na_regra_nova": sorted(inferidas - milhares_dossie),
            "so_no_dossie": sorted((milhares_dossie & set(do_mapa)) - inferidas),
            "ambos": sorted(inferidas & milhares_dossie),
        },
        "universo_dfp": {
            "empresas_com_dre": int(n_empresas),
            "motivos_de_exclusao": pd.Series(list(motivos.values()))
            .value_counts()
            .to_dict(),
            **resumo(universo),
        },
        "linha_3_99_escala_moeda": escala_399,
        "exemplo_lpa_basico_itub4_valor_bruto": exemplo_itub,
        "lpa_por_especie": linhas_399.groupby(["CD_CONTA"])["DS_CONTA"]
        .agg(lambda s: s.value_counts().index[0])
        .head(14)
        .to_dict(),
        "empresas_com_lucro_controladora_3_11_01": int(
            dre[dre["CD_CONTA"] == "3.11.01"]["CD_CVM"].nunique()
        ),
        "empresas_com_pl_nao_controladores_2_03_09": int(
            bpp[bpp["CD_CONTA"] == "2.03.09"]["CD_CVM"].nunique()
        ),
        "empresas_com_pl_2_03": int(bpp[bpp["CD_CONTA"] == "2.03"]["CD_CVM"].nunique()),
    }


def valor_bruto(df: pd.DataFrame, cd: str, conta: str) -> float | None:
    """Valor sem aplicar a escala monetária (LPA já vem em R$ por ação)."""
    x = df[(df["CD_CVM"] == cd) & (df["CD_CONTA"] == conta)]
    return float(x["VL_CONTA"].iloc[0]) if not x.empty else None


# ── 3. DFP e ITR ──────────────────────────────────────────────────────────────


def _frequencia(df: pd.DataFrame, prefixo: str, limite: int = 12) -> list[list]:
    d = df[
        df["CD_CONTA"].str.startswith(prefixo)
        & (pd.to_numeric(df["VL_CONTA"], errors="coerce").fillna(0) != 0)
    ]
    g = d.groupby("CD_CONTA").agg(
        empresas=("CD_CVM", "nunique"),
        descricao=("DS_CONTA", lambda s: s.value_counts().index[0]),
    )
    return [
        [c, int(r.empresas), r.descricao]
        for c, r in g.sort_values("empresas", ascending=False).head(limite).iterrows()
    ]


def _arrendamento_fora(bpp: pd.DataFrame) -> dict:
    """Linhas de arrendamento com valor fora do grupo de empréstimos (2.01.04 e 2.02.01)."""
    valores = pd.to_numeric(bpp["VL_CONTA"], errors="coerce").fillna(0)
    achadas = bpp[
        bpp["DS_CONTA"].str.contains("arrend|leasing", case=False, na=False)
        & ~bpp["CD_CONTA"].str.startswith(("2.01.04", "2.02.01"))
        & (valores != 0)
    ]
    return {
        "empresas": int(achadas["CD_CVM"].nunique()),
        "contas_mais_comuns": achadas.groupby("CD_CONTA")["CD_CVM"]
        .nunique()
        .sort_values(ascending=False)
        .head(5)
        .to_dict(),
    }


def secao_3() -> dict:
    z = dfp()
    bpa, bpp, dva = dem(z, "BPA_con"), dem(z, "BPP_con"), dem(z, "DVA_con")
    total = int(bpp["CD_CVM"].nunique())
    itr_zip = baixar(
        f"{CVM}/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ANO_FCA}.zip",
        f"itr_{ANO_FCA}.zip",
    )
    itr_dre = csv_do_zip(itr_zip, f"itr_cia_aberta_DRE_con_{ANO_FCA}.csv")
    itr_cc = csv_do_zip(itr_zip, f"itr_cia_aberta_composicao_capital_{ANO_FCA}.csv")
    primeiro = itr_dre[
        (itr_dre["DT_REFER"] == "2026-03-31") & (itr_dre["CD_CONTA"] == "3.11")
    ]
    por_empresa_1t = primeiro.groupby("CD_CVM")["DT_INI_EXERC"].nunique()
    ref = itr_dre[itr_dre["DT_REFER"] == "2026-06-30"]
    periodos = (
        ref[ref["CD_CONTA"] == "3.11"]
        .groupby("CD_CVM")
        .agg(inicios=("DT_INI_EXERC", "nunique"))
    )
    return {
        "empresas_dfp_consolidado": total,
        "criterio_de_contagem": "empresas com a conta e VL_CONTA diferente de zero",
        "passivo_emprestimos_circulante": _frequencia(bpp, "2.01.04"),
        "passivo_emprestimos_nao_circulante": _frequencia(bpp, "2.02.01"),
        "ativo_caixa_e_aplicacoes": [
            x for x in _frequencia(bpa, "1.01.0", 40) if x[0] in ("1.01.01", "1.01.02")
        ],
        "arrendamento_fora_de_2_x_04": _arrendamento_fora(bpp),
        "dva_depreciacao_amortizacao": _frequencia(dva, "7.04.01", 3),
        "dva_dividendos_e_jcp": [
            x
            for x in _frequencia(dva, "7.08.04", 6)
            if x[0] in ("7.08.04.01", "7.08.04.02")
        ],
        "dva_descricoes_de_7_04_01": dva[dva["CD_CONTA"] == "7.04.01"]["DS_CONTA"]
        .value_counts()
        .head(4)
        .to_dict(),
        "itr": {
            "arquivo": f"itr_cia_aberta_{ANO_FCA}.zip",
            "datas_de_referencia": itr_dre["DT_REFER"].value_counts().to_dict(),
            "colunas_dre": list(itr_dre.columns),
            "empresas_no_1o_tri": int(len(por_empresa_1t)),
            "empresas_com_2_periodos_distintos_no_1o_tri": int(
                (por_empresa_1t == 2).sum()
            ),
            "empresas_no_2o_tri": int(len(periodos)),
            "empresas_com_4_periodos_distintos_no_2o_tri": int(
                (periodos["inicios"] == 4).sum()
            ),
            "empresas_com_2_periodos_no_2o_tri": int((periodos["inicios"] == 2).sum()),
            "composicao_capital_no_itr": {
                "linhas": int(len(itr_cc)),
                "colunas": list(itr_cc.columns),
            },
            "terceiro_trimestre": "não observado: o ITR 2026 só tem 31/03 e 30/06",
        },
    }


# ── 4. Bancos e seguradoras ───────────────────────────────────────────────────


def secao_4() -> dict:
    z = dfp()
    bpp, dre = dem(z, "BPP_con"), dem(z, "DRE_con")
    cad = pd.read_csv(
        baixar(f"{CVM}/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv", "cad_cia_aberta.csv"),
        sep=";",
        encoding="latin-1",
        dtype=str,
    )
    setores = cad["SETOR_ATIV"].value_counts()
    financeiros = setores[
        setores.index.str.contains(
            "Banc|Segur|Intermedia|Cr.dito Imob", case=False, na=False, regex=True
        )
    ].to_dict()
    oficiais = codigos_oficiais()
    bancos = {}
    for t in ("BBAS3", "ITUB4", "BBDC4"):
        cd = oficiais[t]
        b = bpp[bpp["CD_CVM"] == cd]
        d = dre[dre["CD_CVM"] == cd]
        bancos[t] = {
            "pl": b[
                b["DS_CONTA"].str.contains("Patrimônio Líquido Consolidado", na=False)
            ][["CD_CONTA", "DS_CONTA"]].values.tolist(),
            "conta_2_03": b[b["CD_CONTA"] == "2.03"]["DS_CONTA"].tolist(),
            "lucro": d[
                d["DS_CONTA"].str.contains(
                    "Lucro.*Consolidado do Período|Lucro/Prejuízo Consolidado",
                    na=False,
                    regex=True,
                )
            ][["CD_CONTA", "DS_CONTA"]].values.tolist(),
            "lucro_controladora": d[
                d["DS_CONTA"].str.contains("Controladora", na=False)
            ][["CD_CONTA", "DS_CONTA"]].values.tolist(),
            "conta_3_11": d[d["CD_CONTA"] == "3.11"]["DS_CONTA"].tolist(),
        }
    # em quantos bancos do cadastro a conta 2.03 não é o patrimônio líquido
    cds_bancos = set(
        cad[(cad["SETOR_ATIV"] == "Bancos") & (cad["SIT"] == "ATIVO")][
            "CD_CVM"
        ].str.zfill(6)
    ) & set(bpp["CD_CVM"])
    pl_em_2_03 = sum(
        1
        for cd in cds_bancos
        if bpp[(bpp["CD_CVM"] == cd) & (bpp["CD_CONTA"] == "2.03")]["DS_CONTA"]
        .str.contains("Patrim", na=False)
        .any()
    )
    codigo_pl = {}
    for cd in cds_bancos:
        achou = bpp[
            (bpp["CD_CVM"] == cd)
            & bpp["DS_CONTA"].str.contains("Patrimônio Líquido Consolidado", na=False)
        ]["CD_CONTA"]
        codigo_pl[achou.iloc[0] if len(achou) else "sem linha"] = (
            codigo_pl.get(achou.iloc[0] if len(achou) else "sem linha", 0) + 1
        )
    codigo_lucro = {}
    for cd in cds_bancos:
        achou = dre[
            (dre["CD_CVM"] == cd)
            & dre["DS_CONTA"].str.contains("Atribu.*Controladora", na=False, regex=True)
        ]["CD_CONTA"]
        chave = achou.iloc[0] if len(achou) else "sem linha"
        codigo_lucro[chave] = codigo_lucro.get(chave, 0) + 1
    return {
        "conta_do_pl_consolidado_nos_bancos_ativos": codigo_pl,
        "conta_do_lucro_da_controladora_nos_bancos_ativos": codigo_lucro,
        "setor_ativ_financeiros": financeiros,
        "bancos_ativos_com_dfp": len(cds_bancos),
        "bancos_cuja_conta_2_03_e_patrimonio_liquido": pl_em_2_03,
        "tres_bancos_do_mapa": bancos,
        "conta_usada_pela_v1_para_pl": "2.03 (cvm_provider._CONTAS) e para lucro 3.11",
    }


# ── 5. IF.data ────────────────────────────────────────────────────────────────


def _ifdata(path: str) -> list[dict]:
    resp = requests.get(f"{BCB}/{path}", timeout=90, headers=UA)
    resp.raise_for_status()
    return resp.json().get("value", [])


def _valores(am: str, tipo: int, rel: str, extra: str = "") -> list[dict]:
    caminho = (
        f"IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
        f"?@AnoMes={am}&@TipoInstituicao={tipo}&@Relatorio='{rel}'{extra}&$format=json"
    )
    return _ifdata(caminho)


def secao_5() -> dict:
    am = "202512"
    cadastro = _ifdata(
        f"IfDataCadastro(AnoMes=@AnoMes)?@AnoMes={am}&$filter=CnpjInstituicaoLider eq '00000000'&$format=json"
    )
    nomes = {}
    for am_teste in ("202412", "202509", "202512"):
        nomes[am_teste] = {}
        for rel in range(1, 31):
            v = _valores(am_teste, 1, str(rel), "&$top=1")
            if v:
                nomes[am_teste][rel] = v[0]["NomeRelatorio"]
    prud = next(x["CodInst"] for x in cadastro if "PRUDENCIAL" in x["NomeInstituicao"])
    capital = _valores(am, 1, "5", f"&$filter=CodInst eq '{prud}'")
    resumo = _valores(am, 1, "1", f"&$filter=CodInst eq '{prud}'")
    return {
        "chamada_de_controle": f"IfDataValores, AnoMes={am}, TipoInstituicao=1, Relatorio=1, CodInst={prud}: {len(resumo)} linhas",
        "resumo_banco_do_brasil_prudencial": {
            x["NomeColuna"]: x["Saldo"] for x in resumo
        },
        "cadastro_por_cnpj_lider": [
            [x["CodInst"], x["NomeInstituicao"], x["Td"], x["CnpjInstituicaoLider"]]
            for x in cadastro
        ],
        "relatorios_por_data": nomes,
        "relatorio_de_capital": {
            "numero": 5,
            "indice_de_basileia": [
                x["NomeColuna"].replace("\n", " ")
                for x in capital
                if "Basileia" in x["NomeColuna"]
            ],
            "valor_basileia": [
                x["Saldo"] for x in capital if "Basileia" in x["NomeColuna"]
            ],
        },
        "relatorios_com_risco_no_nome": sorted(
            {
                f"{am}/{n}"
                for am, rels in nomes.items()
                for n, nome in rels.items()
                if "risco" in nome.lower()
            }
        ),
        "relatorios_sem_resposta_de_1_a_30": {
            am: [n for n in range(1, 31) if n not in rels] for am, rels in nomes.items()
        },
        "como_achar_a_instituicao": "IfDataCadastro filtra CnpjInstituicaoLider (os 8 primeiros dígitos do CNPJ); o CodInst do conglomerado prudencial (Td=C, nome com PRUDENCIAL) é o que tem os relatórios de capital",
    }


# ── 6. COTAHIST ───────────────────────────────────────────────────────────────


def secao_6() -> dict:
    ano, mes = MESES_COTAHIST[-1]
    url = cot.URL_MENSAL.format(ano=ano, mes=mes)
    zip_path = baixar(url, f"COTAHIST_M{mes:02d}{ano}.ZIP")
    with zipfile.ZipFile(zip_path) as zf:
        nome = zf.namelist()[0]
        linhas = zf.read(nome).decode("latin-1").splitlines()
    tipos = pd.Series([ln[:2] for ln in linhas]).value_counts().to_dict()
    todas = pd.DataFrame(
        [
            c.__dict__
            for c in cot.ler_zip(
                zip_path,
                mercados=(
                    "010",
                    "020",
                    "030",
                    "050",
                    "060",
                    "070",
                    "080",
                    "012",
                    "013",
                    "017",
                ),
            )
        ]
    )
    vista = todas[todas["tipo_mercado"] == "010"].copy()
    vista["grupo"] = vista.apply(classe_do_papel, axis=1)
    unicos = vista.drop_duplicates("codigo_negociacao")
    por_grupo = {
        g: unicos[unicos["grupo"] == g]["especificacao"]
        .value_counts()
        .head(8)
        .to_dict()
        for g in ("acao", "unit", "fii", "outro_fundo", "bdr")
    }
    z = baixar(
        f"{CVM}/FI/CAD/DADOS/registro_fundo_classe.zip", "registro_fundo_classe.zip"
    )
    classes = csv_do_zip(z, "registro_classe.csv")
    return {
        "url": url,
        "arquivo": nome,
        "bytes_zip": zip_path.stat().st_size,
        "linhas_por_tipo_de_registro": tipos,
        "registros_01": int(tipos.get("01", 0)),
        "registros_01_mercado_a_vista": int(len(vista)),
        "codigos_a_vista_no_mes": int(unicos["codigo_negociacao"].nunique()),
        "datas_no_mes": int(vista["data"].nunique()),
        "ativos_por_grupo": unicos["grupo"].value_counts().to_dict(),
        "codbdi_por_grupo": unicos.groupby("grupo")["codbdi"]
        .agg(lambda s: s.value_counts().head(4).to_dict())
        .to_dict(),
        "especi_por_grupo": por_grupo,
        "especi_units": unicos[unicos["especificacao"].str.startswith("UNT")][
            "especificacao"
        ]
        .value_counts()
        .to_dict(),
        "etf_oficial": {
            "fonte": "registro_classe.csv (CVM, dados abertos de fundos), coluna Tipo_Classe",
            "tipos_de_classe": classes["Tipo_Classe"].value_counts().to_dict(),
            "classes_fiim_exemplos": classes[
                classes["Tipo_Classe"].str.endswith("FIIM", na=False)
            ]["Denominacao_Social"]
            .head(4)
            .tolist(),
            "chave_para_juntar": "o COTAHIST traz ISIN e o registro traz CNPJ_Classe, sem ISIN: a junção exige uma terceira fonte (por exemplo, o ISIN do cadastro de instrumentos da B3) — não determinada aqui",
        },
        "etf_conhecidos_codbdi": unicos[
            unicos["codigo_negociacao"].isin(["BOVA11", "IVVB11", "SMAL11", "GOLD11"])
        ][["codigo_negociacao", "codbdi", "especificacao"]].values.tolist(),
    }


# ── 7. Informe Mensal de FII ──────────────────────────────────────────────────


def secao_7() -> dict:
    from cvm_fii_map import FII_CNPJ_MAP

    z = baixar(
        f"{CVM}/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ANO_FCA}.zip",
        f"inf_mensal_fii_{ANO_FCA}.zip",
    )
    geral = csv_do_zip(z, f"inf_mensal_fii_geral_{ANO_FCA}.csv")
    geral = (
        geral.assign(_v=pd.to_numeric(geral["Versao"]))
        .sort_values(["Data_Referencia", "_v"])
        .drop_duplicates("CNPJ_Fundo_Classe", keep="last")
    )
    cotas = cotacoes()
    vista = cotas[cotas["tipo_mercado"] == "010"].copy()
    vista["grupo"] = vista.apply(classe_do_papel, axis=1)
    fiis = vista[vista["grupo"] == "fii"].drop_duplicates("codigo_negociacao")
    por_isin = set(geral["Codigo_ISIN"].dropna())
    casados = fiis[fiis["isin"].isin(por_isin)]
    sem_informe = fiis[~fiis["isin"].isin(por_isin)]
    reserva_ok = fiis.apply(
        lambda r: r["codigo_negociacao"] == r["isin"][2:6] + "11", axis=1
    )
    quatro_letras = fiis.apply(
        lambda r: r["codigo_negociacao"][:4] == r["isin"][2:6], axis=1
    )
    mapa = pd.DataFrame(
        [
            (t, cnpj, cnpj in set(geral["CNPJ_Fundo_Classe"]))
            for t, cnpj in FII_CNPJ_MAP.items()
        ],
        columns=["ticker", "cnpj", "no_informe"],
    )
    mapa["negociado"] = mapa["ticker"].isin(set(fiis["codigo_negociacao"]))
    return {
        "arquivo": f"inf_mensal_fii_geral_{ANO_FCA}.csv",
        "colunas_de_identificacao": [
            "CNPJ_Fundo_Classe",
            "Codigo_ISIN",
            "Segmento_Atuacao",
            "Mercado_Negociacao_Bolsa",
            "Entidade_Administradora_BVMF",
            "Tipo_Fundo_Classe",
        ],
        "fundos_no_informe": int(len(geral)),
        "negociados_em_bolsa_no_informe": int(
            (geral["Mercado_Negociacao_Bolsa"] == "S").sum()
        ),
        "segmentos": geral["Segmento_Atuacao"].value_counts().head(12).to_dict(),
        "segmento_vazio": int(geral["Segmento_Atuacao"].isna().sum()),
        "fiis_no_cotahist_a_vista": int(len(fiis)),
        "juncao_por_isin": {
            "casam": int(len(casados)),
            "nao_casam": int(len(sem_informe)),
            "cobertura": round(len(casados) / max(1, len(fiis)), 4),
            "nao_casam_amostra": sorted(sem_informe["codigo_negociacao"])[:15],
        },
        "regra_do_isin_reserva": {
            "descricao": "ticker = 4 letras do ISIN (posições 3 a 6) + 11",
            "quatro_letras_concordam": int(quatro_letras.sum()),
            "concorda_com_o_cotahist": int(reserva_ok.sum()),
            "de": int(len(fiis)),
        },
        "mapa_manual": {
            "tickers": int(len(mapa)),
            "cnpj_no_informe": int(mapa["no_informe"].sum()),
            "negociados_no_cotahist": int(mapa["negociado"].sum()),
            "fora_dos_listados_em_bolsa": sorted(mapa[~mapa["negociado"]]["ticker"]),
            "cnpj_fora_do_informe": sorted(mapa[~mapa["no_informe"]]["ticker"]),
        },
    }


# ── 8. Representação do DY e do ROE ───────────────────────────────────────────


def secao_8() -> dict:
    import yfinance as yf

    z = dfp()
    dre, bpp = dem(z, "DRE_con"), dem(z, "BPP_con")
    oficiais = codigos_oficiais()
    amostra = [
        "PETR4",
        "VALE3",
        "WEGE3",
        "ITUB4",
        "BBAS3",
        "BBDC4",
        "ABEV3",
        "KLBN11",
        "SUZB3",
        "RENT3",
    ]
    linhas = []
    for t in amostra:
        cd = oficiais.get(t)
        tk = yf.Ticker(t + ".SA")
        info = tk.info
        hist = tk.history(period="1y", auto_adjust=False)
        if hist.empty:
            continue
        preco = float(hist["Close"].iloc[-1])
        dy_12m = float(hist["Dividends"].sum()) / preco
        pl = next(
            (
                valor(bpp, cd, c)
                for c in ("2.03", "2.07", "2.08")
                if "Patrim"
                in " ".join(
                    bpp[(bpp["CD_CVM"] == cd) & (bpp["CD_CONTA"] == c)]["DS_CONTA"]
                )
            ),
            None,
        )
        lucro = next(
            (valor(dre, cd, c) for c in ("3.11", "3.09") if valor(dre, cd, c)), None
        )
        linhas.append(
            {
                "ticker": t,
                "dividendYield_yf": info.get("dividendYield"),
                "trailingAnnualDividendYield_yf": info.get(
                    "trailingAnnualDividendYield"
                ),
                "proventos_12m_sobre_preco": round(dy_12m, 4),
                "returnOnEquity_yf": info.get("returnOnEquity"),
                "lucro_sobre_pl_dfp": round(lucro / pl, 4) if lucro and pl else None,
            }
        )
    return {
        "yfinance": yf.__version__,
        "amostra": linhas,
        "leitura": "dividendYield vem em percentual (6.74 = 6,74%) e trailingAnnualDividendYield em fração; compare com proventos_12m_sobre_preco",
        "brapi": "não determinado: a documentação pública é renderizada por JavaScript e não expõe os campos no HTML; a chamada sem token devolve só cotação, sem os campos fundamentalistas",
        "informe_mensal": "Percentual_Dividend_Yield_Mes é o rendimento do mês em %, só registro",
    }


# ── 9. Liquidez ───────────────────────────────────────────────────────────────


def _liquidez(df: pd.DataFrame, datas: list) -> pd.DataFrame:
    janela = df[df["data"].isin(datas)]
    n = len(datas)
    linhas = []
    for cod, g in janela.groupby("codigo_negociacao"):
        por_dia = g.groupby("data").agg(
            vol=("volume_financeiro", "sum"), neg=("negocios", "sum")
        )
        por_dia = por_dia.reindex(datas, fill_value=0)
        linhas.append(
            {
                "codigo": cod,
                "grupo": g["grupo"].iloc[0],
                "mediana_volume": float(por_dia["vol"].median()),
                "mediana_negocios": float(por_dia["neg"].median()),
                "presenca": float((por_dia["neg"] > 0).sum() / n),
            }
        )
    return pd.DataFrame(linhas)


def secao_9() -> dict:
    cotas = cotacoes()
    vista = cotas[cotas["tipo_mercado"] == "010"].copy()
    vista["grupo"] = vista.apply(classe_do_papel, axis=1)
    vista = vista[vista["grupo"].isin(["acao", "unit", "fii"])]
    datas = sorted(vista["data"].unique())
    saida: dict = {"pregoes_disponiveis": len(datas), "ultimo_pregao": str(datas[-1])}
    for janela in (21, 63):
        liq = _liquidez(vista, datas[-janela:])
        bloco = {}
        for grupo, g in liq.groupby("grupo"):
            vols = g["mediana_volume"]
            bloco[grupo] = {
                "ativos": int(len(g)),
                "mediana_do_volume_mediano": round(float(vols.median()), 0),
                "p25_p75_do_volume_mediano": [
                    round(float(vols.quantile(0.25)), 0),
                    round(float(vols.quantile(0.75)), 0),
                ],
                "mediana_de_negocios": round(float(g["mediana_negocios"].median()), 1),
                "abaixo_de_volume_diario": {
                    str(lim): int((vols < lim).sum())
                    for lim in (100_000, 500_000, 1_000_000, 5_000_000)
                },
                "abaixo_de_presenca": {
                    str(lim): int((g["presenca"] < lim).sum())
                    for lim in (0.80, 0.90, 0.95)
                },
            }
        saida[f"janela_{janela}_pregoes"] = bloco
    saida["definicao"] = (
        "volume financeiro e negócios por dia somados por código; dias sem negócio contam como zero; presença = dias com negócio ÷ pregões da janela; só ativos com ao menos um negócio na janela; mercado à vista"
    )
    return saida


SECOES = {
    1: secao_1,
    2: secao_2,
    3: secao_3,
    4: secao_4,
    5: secao_5,
    6: secao_6,
    7: secao_7,
    8: secao_8,
    9: secao_9,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--secao", type=int, nargs="*", help="números das perguntas (padrão: todas)"
    )
    args = ap.parse_args(argv)
    resultado = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    resultado["gerado_em"] = date.today().isoformat()
    for n in args.secao or sorted(SECOES):
        resultado[f"pergunta_{n}"] = SECOES[n]()
        print(f"pergunta {n}: ok")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
