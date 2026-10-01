"""Dossiê de decisão da Fase 2 (F0-6).

Gera `docs/decisoes/dossie-fase2.md` com a amostra dos mapas atuais (50 ações e
30 FIIs) e `outputs/dossie-carteira.md` (fora do git) com o mesmo recorte de
cobertura, classe e bancos aplicado à carteira local.

Somente leitura de rede (CVM, Banco Central, Tesouro Direto, yfinance); não altera
módulos de produção. As fórmulas dos métodos são recalculadas aqui para variar
taxas, e o `ValuationEngine` real é usado só com `get_selic_atual` substituída.

Uso: python scripts/dossie_fase2.py [caminho/do/banco.db]
Sem argumento, a carteira vem de `sentinela_v6.db` na raiz do repositório.
Cache bruto em outputs/dossie_cache/ (ignorado pelo git).
"""

from __future__ import annotations

import io
import json
import statistics
import sys
import time
import warnings
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

import yfinance as yf  # noqa: E402

from config import MACRO, _normalizar_dy  # noqa: E402
from cvm_fii_map import FII_CNPJ_MAP  # noqa: E402
from cvm_provider import CVMProvider  # noqa: E402
from cvm_ticker_map import _TICKER_TO_CVM  # noqa: E402
from sentinela.services.asset_classifier import AssetClassifier  # noqa: E402
from valuation_engine import ValuationEngine  # noqa: E402

CACHE = ROOT / "outputs" / "dossie_cache"
CACHE.mkdir(parents=True, exist_ok=True)
HOJE = date.today()
ANOS = list(range(HOJE.year - 5, HOJE.year))  # 2021..2025 em 2026
SELIC_GRID = sorted(
    {round(0.10 + 0.005 * i, 4) for i in range(11)} | {0.1375}
)  # 10% a 15% e a Selic de 13,75%
PREMIOS = [0.04, 0.05, 0.07]
CLASSIFIER = AssetClassifier()
UA = {"User-Agent": "Mozilla/5.0 (Sentinela dossie F0-6; leitura)"}


# ── utilidades ────────────────────────────────────────────────────────────────


def pct(x, casas=1):
    return "n/d" if x is None or x != x else f"{x * 100:.{casas}f}%"


def num(x, casas=2):
    return "n/d" if x is None or x != x else f"{x:,.{casas}f}"


def med(valores):
    v = [x for x in valores if x is not None and x == x]
    return statistics.median(v) if v else None


def tabela(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(out)


def http_get(url, tentativas=3, **kw):
    ultimo = None
    for i in range(tentativas):
        try:
            r = requests.get(url, timeout=90, headers=UA, **kw)
            if r.status_code == 200:
                return r
            ultimo = f"HTTP {r.status_code}"
        except Exception as exc:
            ultimo = str(exc)[:120]
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"{url[:90]} -> {ultimo}")


def cache_json(nome, fabrica):
    f = CACHE / f"{nome}.json"
    if f.exists():
        return json.loads(f.read_text())
    valor = fabrica()
    f.write_text(json.dumps(valor, default=str))
    return valor


def secao(titulo, fn, falhas):
    try:
        return fn()
    except Exception as exc:  # a seção vira aviso no documento, não derruba o script
        falhas.append(f"{titulo}: {type(exc).__name__}: {str(exc)[:200]}")
        return f"_Seção indisponível nesta execução: {type(exc).__name__}: {str(exc)[:200]}_"


# ── dados: CVM ────────────────────────────────────────────────────────────────


def cadastro_cvm():
    f = CACHE / "cad_cia_aberta.csv"
    if not f.exists():
        f.write_bytes(
            http_get(
                "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
            ).content
        )
    return pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)


def composicao_capital():
    """Última versão da Composição do Capital por CNPJ, entre os DFP baixados."""
    prov = CVMProvider()
    quadros = []
    for ano in ANOS:
        with zipfile.ZipFile(prov.baixar_dfp(ano)) as z:
            nome = [n for n in z.namelist() if "composicao_capital" in n][0]
            quadros.append(
                pd.read_csv(z.open(nome), sep=";", encoding="latin-1", dtype=str)
            )
    df = pd.concat(quadros)
    for c in df.columns:
        if c.startswith("QT_"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["VERSAO"] = pd.to_numeric(df["VERSAO"], errors="coerce")
    df = (
        df.sort_values(["CNPJ_CIA", "DT_REFER", "VERSAO"])
        .groupby(["CNPJ_CIA", "DT_REFER"])
        .tail(1)
    )
    return df.sort_values("DT_REFER").groupby("CNPJ_CIA").tail(1).set_index("CNPJ_CIA")


def fca_valores():
    f = CACHE / "fca_valor_mobiliario.csv"
    if not f.exists():
        z = zipfile.ZipFile(
            io.BytesIO(
                http_get(
                    f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{HOJE.year}.zip"
                ).content
            )
        )
        nome = [n for n in z.namelist() if "valor_mobiliario" in n][0]
        f.write_bytes(z.read(nome))
    df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    return df[df["Codigo_Negociacao"].notna()]


def fii_geral():
    f = CACHE / "fii_geral.csv"
    if not f.exists():
        z = zipfile.ZipFile(
            io.BytesIO(
                http_get(
                    f"https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{HOJE.year}.zip"
                ).content
            )
        )
        nome = [n for n in z.namelist() if "geral" in n][0]
        f.write_bytes(z.read(nome))
    df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str)
    df = df.sort_values("Data_Referencia").groupby("CNPJ_Fundo_Classe").tail(1)
    return df


def indicadores_cvm(cd_cvm):
    return cache_json(
        f"cvm_ind_{cd_cvm}",
        lambda: {
            str(k): v
            for k, v in CVMProvider().calcular_indicadores(cd_cvm, anos=5).items()
        },
    )


# ── dados: mercado ────────────────────────────────────────────────────────────


def mercado(ticker):
    def buscar():
        tk = yf.Ticker(f"{ticker}.SA")
        info = tk.info or {}
        hist = tk.history(period="6y", auto_adjust=False)
        divs = tk.dividends
        time.sleep(0.4)
        return {
            "preco": float(hist["Close"].iloc[-1]) if len(hist) else None,
            "shares": info.get("sharesOutstanding"),
            "dy_info": info.get("dividendYield"),
            "pvp": info.get("priceToBook"),
            "pl": info.get("trailingPE"),
            "roe": info.get("returnOnEquity"),
            "quote_type": info.get("quoteType"),
            "divs": {str(k.date()): float(v) for k, v in divs.items()},
            "ex_div_12m": float(
                divs[divs.index >= (divs.index.max() - pd.Timedelta(days=365))].sum()
            )
            if len(divs)
            else 0.0,
        }

    try:
        return cache_json(f"yf_{ticker}", buscar)
    except Exception as exc:
        return {"erro": str(exc)[:100]}


def macro():
    """Selic, NTN-B e IPCA do MacroContext; detecta fallback pelos avisos que o próprio config registra."""
    import logging

    avisos = []

    class Coletor(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING:
                avisos.append(record.getMessage())

    h = Coletor()
    logging.getLogger().addHandler(h)
    try:
        selic, ntnb, ipca = MACRO.selic, MACRO.ntnb_longa, MACRO.ipca_12m
    finally:
        logging.getLogger().removeHandler(h)
    return {
        "selic": selic,
        "ntnb": ntnb,
        "ipca": ipca,
        "ntnb_aviso": next((a for a in avisos if "NTN-B" in a), None),
        "ipca_aviso": next((a for a in avisos if "IPCA" in a), None),
        "ntnb_fallback": any("NTN-B" in a for a in avisos),
        "ipca_fallback": any("IPCA" in a for a in avisos),
    }


_MACRO_CACHE: dict = {}


def macro_cache():
    if not _MACRO_CACHE:
        _MACRO_CACHE.update(macro())
    return _MACRO_CACHE


def div12m(m):
    """Proventos por ação nos 12 meses até hoje (não até o último pagamento)."""
    corte = (pd.Timestamp(HOJE) - pd.Timedelta(days=365)).date().isoformat()
    return sum(v for dt, v in (m.get("divs") or {}).items() if dt >= corte)


# ── E-1: ações da CVM × sharesOutstanding ─────────────────────────────────────


def cd_oficial(ticker, cad, fca):
    """CD_CVM oficial do ticker: FCA (código de negociação) -> CNPJ -> cadastro da CVM."""
    f = fca[fca["Codigo_Negociacao"] == ticker]
    if f.empty:
        return None, None
    cnpj = f["CNPJ_Companhia"].iloc[0]
    c = cad[cad["CNPJ_CIA"] == cnpj]
    if c.empty:
        return cnpj, None
    ativo = c[c["SIT"].fillna("").str.upper().str.contains("ATIVO")]
    c = ativo if len(ativo) else c
    return cnpj, int(c["CD_CVM"].iloc[0])


def dados_acoes(cad, cap, fca):
    linhas = {}
    for ticker, cd_manual in _TICKER_TO_CVM.items():
        cnpj, cd = cd_oficial(ticker, cad, fca)
        c = cad[cad["CNPJ_CIA"] == cnpj] if cnpj else cad.iloc[0:0]
        reg = cap.loc[cnpj] if cnpj in cap.index else None
        m = mercado(ticker)
        ind = indicadores_cvm(cd) if cd else {}
        total, escala_mil = None, False
        if reg is not None:
            tes = (reg["QT_ACAO_ORDIN_TESOURO"] or 0) + (
                reg["QT_ACAO_PREF_TESOURO"] or 0
            )
            total = (
                (reg["QT_ACAO_ORDIN_CAP_INTEGR"] or 0)
                + (reg["QT_ACAO_PREF_CAP_INTEGR"] or 0)
                - tes
            )
            ysh = m.get("shares") if "erro" not in m else None
            # o CSV não traz a escala da quantidade (armadilha 10): fator ~1000 contra o yfinance = documento em milhares
            if total and ysh and 100 < ysh / total < 5000:
                total, escala_mil = total * 1000, True
        linhas[ticker] = {
            "cd": cd,
            "cd_manual": cd_manual,
            "cnpj": cnpj,
            "setor": c["SETOR_ATIV"].iloc[0] if len(c) else None,
            "nome_oficial": c["DENOM_SOCIAL"].iloc[0] if len(c) else None,
            "cap": reg,
            "total": total,
            "escala_mil": escala_mil,
            "m": m,
            "ind": ind,
        }
    return linhas


def secao_mapa(acoes, cad, fca_todos):
    certas, sem_negociacao, erradas = 0, [], []
    for t, d in acoes.items():
        if d["cd"] is not None and d["cd"] == d["cd_manual"]:
            certas += 1
            continue
        c = cad[cad["CD_CVM"].astype(int) == d["cd_manual"]]
        nome_mapa = (
            c["DENOM_SOCIAL"].iloc[0] if len(c) else "(código inexistente no cadastro)"
        )
        # o código do mapa pertence a uma empresa que já teve este ticker (qualquer data no FCA)?
        tickers_mapa = set()
        if len(c):
            tickers_mapa = set(
                fca_todos[fca_todos["CNPJ_Companhia"] == c["CNPJ_CIA"].iloc[0]][
                    "Codigo_Negociacao"
                ]
            )
        linha = [t, d["cd_manual"], nome_mapa, d["cd"], d["nome_oficial"] or "n/d"]
        if d["cd"] is None or any(x[:4] == t[:4] for x in tickers_mapa):
            sem_negociacao.append(linha)
        else:
            erradas.append(linha)
    cab = [
        "Ticker",
        "CD_CVM no mapa",
        "Empresa a que esse código pertence",
        "CD_CVM oficial",
        "Empresa oficial do ticker",
    ]
    texto = (
        f"Para cada um dos {len(acoes)} tickers do mapa manual (`cvm_ticker_map.py`), comparei o `CD_CVM` do mapa com o oficial "
        f"(código de negociação ativo no FCA → CNPJ → cadastro da CVM). Resultado: **{certas} batem**; **{len(sem_negociacao)}** têm o "
        f"ticker sem negociação ativa no FCA (troca de código, incorporação ou saída da bolsa) ou com o código da empresa certa: não dá para afirmar erro, e o nome da empresa do código deve ser julgado à mão; "
        f"**{len(erradas)} apontam para outra empresa** ou para código inexistente. Na V1 isso atribui os fundamentos da CVM (lucro, PL, ROE) "
        f"de uma empresa a outro ticker, sem alerta: o resultado sai com a mesma cara de dado oficial. Esta falha não está na auditoria "
        f"de 9/9 (o E-1 trata do escopo das ações, não do código da empresa).\n\n"
        f"**Código do mapa de outra empresa ({len(erradas)}):**\n\n"
        + tabela(cab, erradas)
    )
    if sem_negociacao:
        texto += (
            f"\n\n**Sem negociação ativa no FCA, a julgar pelo nome ({len(sem_negociacao)}):**\n\n"
            + tabela(cab, sem_negociacao)
        )
    return (
        texto
        + "\n\nTodo o restante deste dossiê usa o **mapeamento oficial** (FCA), e não o mapa manual, para não propagar o erro."
    )


def secao_e1(acoes):
    difs = []
    for t, d in acoes.items():
        m, total = d["m"], d["total"]
        if "erro" in m or not m.get("shares") or not total:
            continue
        reg, ind = d["cap"], d["ind"]
        on, pn = reg["QT_ACAO_ORDIN_CAP_INTEGR"], reg["QT_ACAO_PREF_CAP_INTEGR"]
        yf_sh = m["shares"]
        dif = yf_sh / total - 1
        duas = bool(on and pn and min(on, pn) / (on + pn) > 0.02)  # ignora golden share
        ano = max(ind) if ind else None
        lucro = ind[ano].get("lucro_liquido") if ano else None
        efeito = (
            (total / yf_sh - 1) if lucro and yf_sh else None
        )  # LPA com yfinance ÷ LPA com ações totais − 1 = total/yf − 1
        difs.append((t, dif, duas, efeito, total, yf_sh, d["escala_mil"]))
    n = len(difs)
    maiores = [x for x in difs if abs(x[1]) > 0.05]
    duas = [x for x in difs if x[2]]
    mil = [x for x in difs if x[6]]
    linhas = [
        [
            t,
            num(tot / 1e6, 0),
            num(y / 1e6, 0),
            pct(dif),
            "sim" if dc else "não",
            pct(ef),
            "sim" if sm else "não",
        ]
        for t, dif, dc, ef, tot, y, sm in sorted(maiores, key=lambda x: -abs(x[1]))
    ]
    return (
        f"Amostra: {n} das {len(acoes)} ações com Composição do Capital da CVM e `sharesOutstanding` do yfinance. Ações da CVM = ON + PN − "
        f"tesouraria. **Escala (armadilha 10):** o CSV não traz coluna de escala e **{len(mil)} empresas** informam a quantidade em milhares "
        f"(fator ≈ 1000 contra o yfinance); aqui elas foram multiplicadas por 1000 antes de comparar. Sem esse ajuste a divergência dessas empresas seria de ~100.000%.\n\n"
        f"- A escala é inferida (razão yfinance/CVM entre 100 e 5000), e o yfinance é o objeto do teste: empresas com divergência acima de 5% "
        f"**sem** reescala ({', '.join(x[0] for x in maiores if not x[6]) or 'nenhuma'}) podem ter escala em milhares não detectada; para elas, "
        f"LPA e VPA das seções seguintes podem estar errados por fator 1000.\n"
        f"- Divergência acima de 5% (já na escala corrigida): **{len(maiores)} de {n}** ({pct(len(maiores) / n if n else None, 0)}).\n"
        f"- Empresas com ON e PN (a menor classe com mais de 2% do total, para não contar golden share): **{len(duas)}**; destas, {len([x for x in duas if x in maiores])} divergem mais de 5%.\n"
        f"- Efeito no LPA, VPA e P/L: lucro e PL da CVM são da companhia inteira; dividir pelas ações de uma classe só muda LPA e VPA por "
        f"`ações totais ÷ ações da classe` e o P/L na proporção inversa. A coluna *Efeito* é `LPA com yfinance ÷ LPA com ações totais − 1`: "
        f"positivo = LPA inflado, negativo = LPA subestimado.\n\n"
        + tabela(
            [
                "Ticker",
                "Ações CVM (mi)",
                "Ações yfinance (mi)",
                "Divergência",
                "ON+PN",
                "Efeito no LPA/VPA",
                "Escala em milhares (inferida, não lida)",
            ],
            linhas,
        )
    )


# ── Taxas, Gordon, cinco anos ─────────────────────────────────────────────────


def entrada_acao(t, d, ano=None):
    m, ind = d["m"], d["ind"]
    shares = d.get("total")
    if "erro" in m or not ind or not shares or not m.get("preco"):
        return None
    ano = ano or max(ind)
    lucro, pl_cvm = ind[ano].get("lucro_liquido"), ind[ano].get("patrimonio_liquido")
    if not lucro or not pl_cvm:
        return None
    p = m["preco"]
    lpa, vpa = lucro / shares, pl_cvm / shares
    dy_raw = m.get("dy_info") or 0
    return {
        "ticker": t,
        "preco_atual": p,
        "roe": lucro / pl_cvm,
        "pl": p / lpa if lpa else 0,
        "pvp": p / vpa if vpa else 0,
        "dy": dy_raw,
    }


def rotulo(rec):
    """Agrupa o rótulo legado da V1 (trocado no F2C-4) no vocabulário vigente."""
    if rec.startswith("COMPRA"):
        return "sinal positivo"
    if rec.startswith("VENDA"):
        return "sinal negativo"
    if rec.startswith("ALTO RISCO"):
        return "alto risco"
    return "neutro/outros"


def processar(entrada, selic):
    with patch("valuation_engine.get_selic_atual", return_value=selic):
        return ValuationEngine().processar(dict(entrada))


def metodos_de(res):
    out = {}
    for parte in (res.get("metodos_usados") or "").split(", "):
        if ": R$" in parte:
            nome, v = parte.split(": R$")
            out[nome] = float(v)
    return out


def secao_taxas(acoes):
    entradas = {t: e for t, d in acoes.items() if (e := entrada_acao(t, d))}
    linhas = []
    for s in SELIC_GRID:
        por_metodo, fv_up, classes = (
            {"Graham": [], "Bazin": [], "Lynch": [], "Gordon": []},
            [],
            {},
        )
        for t, e in entradas.items():
            r = processar(e, s)
            if not r:
                continue
            for nome, v in metodos_de(r).items():
                por_metodo[nome].append(v / e["preco_atual"] - 1)
            if metodos_de(r):
                fv_up.append(r["upside"] / 100)
            rot = rotulo(r["recomendacao"])
            classes[rot] = classes.get(rot, 0) + 1
        linhas.append(
            [pct(s, 2)]
            + [
                f"{pct(med(por_metodo[n]))} (n={len(por_metodo[n])})"
                for n in ("Graham", "Bazin", "Lynch", "Gordon")
            ]
            + [
                f"{pct(med(fv_up))} (n={len(fv_up)})",
                sum(len(v) for v in por_metodo.values())
                and ", ".join(f"{k} {v}" for k, v in sorted(classes.items())),
            ]
        )
    mc = macro_cache()
    k_linhas = []
    for prem in PREMIOS:
        k_real = mc["ntnb"] + prem
        k_nom = (1 + k_real) * (1 + mc["ipca"]) - 1
        k_linhas.append(
            [
                pct(prem, 0),
                pct(k_real, 2),
                pct(k_nom, 2),
                pct(MACRO.selic + MACRO.GORDON_PREMIO_RISCO, 2),
            ]
        )
    return (
        f"Entradas: {len(entradas)} ações com CVM oficial (último DFP, ações da Composição do Capital na escala corrigida; preço da própria ticker, aproximação para duas classes), yfinance (preço, DY) e o `ValuationEngine` real, com "
        f"`get_selic_atual` substituída por cada valor da grade (mesma ideia da fixture do F0-2). **Mediana do upside implícito de cada método** (n = ações em que o método calcula; o upside final conta só as ações com pelo menos um método).\n\n"
        + tabela(
            [
                "Selic",
                "Graham",
                "Bazin",
                "Lynch",
                "Gordon",
                "Upside final",
                "Classificação (agrupada)",
            ],
            linhas,
        )
        + "\n\nLeitura: o Graham e o Lynch não dependem da Selic (colunas constantes); Bazin e Gordon andam com ela, e o "
        "upside final acompanha o ciclo — a nota muda sem que o negócio mude (armadilha 5). A coluna Lynch tem poucos casos e valores "
        "extremos: trate como sinal de problema de insumo (DY e preço do yfinance misturados com LPA da CVM), não como resultado. "
        "Os rótulos da V1 aparecem agrupados (sinal positivo, neutro, sinal negativo); o upside é saída mecânica do método, não recomendação.\n\n"
        + f"**Taxa real.** NTN-B longa = {pct(mc['ntnb'], 2)}"
        + (
            f" (**valor de fallback do código**: {mc['ntnb_aviso'][:140]})"
            if mc["ntnb_fallback"]
            else " (Tesouro Direto)"
        )
        + f", IPCA 12m = {pct(mc['ipca'], 2)}"
        + (
            f" (fallback do código: {mc['ipca_aviso'][:100]})"
            if mc["ipca_fallback"]
            else " (BCB SGS 433)"
        )
        + f", Selic = {pct(mc['selic'], 2)}.\n\n"
        + tabela(
            [
                "Prêmio",
                "k real (NTN-B + prêmio)",
                "k nominal equivalente",
                "k atual (Selic + 7%)",
            ],
            k_linhas,
        )
    ), entradas


def gordon_variantes(entradas):
    mc = macro_cache()
    ipca = mc["ipca"]
    resumo, razoes = {}, {}
    elegiveis = 0
    for t, e in entradas.items():
        dy, conf = _normalizar_dy(float(e["dy"] or 0))
        if not (conf and dy > MACRO.GORDON_DY_MIN and e["roe"] > MACRO.GORDON_ROE_MIN):
            continue
        p, lpa = e["preco_atual"], e["preco_atual"] / e["pl"] if e["pl"] > 0 else 0
        payout = min(dy * p / lpa, MACRO.GORDON_PAYOUT_MAX) if lpa > 0 else 0.5
        g = min(e["roe"] * (1 - payout), MACRO.GORDON_G_MAX)
        div = dy * p
        elegiveis += 1

        def val(k, gg):
            return div * (1 + gg) / (k - gg) / p - 1 if k > gg else None

        atual = val(mc["selic"] + MACRO.GORDON_PREMIO_RISCO, g)
        resumo.setdefault("atual", []).append(atual)
        for prem in PREMIOS:
            k_real = mc["ntnb"] + prem
            k_nom = (1 + k_real) * (1 + ipca) - 1
            misto = val(k_real, g)  # k real, g nominal (erro F-6)
            a_ = val(k_real, g - ipca)  # k e g reais (g deflacionado)
            b_ = val(k_nom, g)  # tudo nominal
            resumo.setdefault(f"misto{prem}", []).append(misto)
            resumo.setdefault(f"A{prem}", []).append(a_)
            resumo.setdefault(f"B{prem}", []).append(b_)
            if misto is not None and b_ is not None:
                razoes.setdefault(f"isolado{prem}", []).append((1 + misto) / (1 + b_))
            if misto is not None and atual is not None:
                razoes.setdefault(f"vs_atual{prem}", []).append(
                    (1 + misto) / (1 + atual)
                )
    linhas = [
        [
            "Regime atual: k = Selic + 7%, g nominal",
            elegiveis,
            pct(med(resumo.get("atual", []))) if resumo.get("atual") else "n/d",
            sum(1 for v in resumo.get("atual", []) if v is None),
        ]
    ]
    for prem in PREMIOS:
        for rot, chave in (
            ("Misto (k real, g nominal) — o erro da armadilha 1", "misto"),
            ("Opção A: k e g reais (g − IPCA)", "A"),
            ("Opção B: tudo nominal (k = (1+k real)(1+IPCA) − 1)", "B"),
        ):
            v = resumo.get(f"{chave}{prem}", [])
            linhas.append(
                [
                    f"{rot}; prêmio {pct(prem, 0)}",
                    elegiveis,
                    pct(med(v)) if v else "n/d",
                    sum(1 for x in v if x is None),
                ]
            )
    iso = [med(razoes.get(f"isolado{prem}", [])) for prem in PREMIOS]
    iso = [x for x in iso if x]
    vsa = [med(razoes.get(f"vs_atual{prem}", [])) for prem in PREMIOS]
    vsa = [x for x in vsa if x]
    fator_iso = (min(iso), max(iso)) if iso else None
    razao_linhas = [
        [
            pct(prem, 0),
            f"{med(razoes.get(f'isolado{prem}', [])):.2f}×"
            if razoes.get(f"isolado{prem}")
            else "n/d",
            f"{med(razoes.get(f'vs_atual{prem}', [])):.2f}×"
            if razoes.get(f"vs_atual{prem}")
            else "n/d",
        ]
        for prem in PREMIOS
    ]
    texto = (
        f"Elegíveis ao Gordon na amostra (DY confiável > 4% e ROE > 10%): **{elegiveis}**. Coluna: mediana do upside implícito "
        f"do método; última coluna: casos em que `k ≤ g` e o método não calcula.\n\n"
        + tabela(["Regime", "Elegíveis", "Mediana do upside", "k ≤ g"], linhas)
        + "\n\n**Quanto vale o erro de mistura.** Razão do fair value do regime misto contra (i) a opção B com o mesmo prêmio, que isola "
        "o erro de mistura real/nominal, e (ii) o regime atual, que soma o erro e a troca do nível da taxa (mediana por ação):\n\n"
        + tabela(
            [
                "Prêmio",
                "Misto ÷ opção B (só a mistura)",
                "Misto ÷ regime atual (mistura + nível)",
            ],
            razao_linhas,
        )
        + "\n\nObservação algébrica: com `g` deflacionado pelo quociente de Fisher, as opções A e B dão exatamente o mesmo valor "
        "(a diferença `k − g` e o fator `1 + g` escalam por `1 + IPCA`). Na tabela, A usa `g − IPCA` (subtração simples, a "
        "aproximação mais comum), por isso difere de B. O resultado que importa é o do regime **misto**, que reproduz o erro "
        "da armadilha 1."
    )
    return texto, fator_iso


def secao_cinco_anos(acoes):
    ef = {"Graham": [], "Bazin": [], "Lynch": [], "Gordon": []}
    n, anos_usados, amplos = 0, [], 0
    selic = macro_cache()["selic"]
    for t, d in acoes.items():
        m, ind = d["m"], d["ind"]
        if "erro" in m or not ind or not d.get("total") or not m.get("preco"):
            continue
        anos = [
            a
            for a in sorted(ind)
            if ind[a].get("lucro_liquido") is not None
            and ind[a].get("patrimonio_liquido")
        ]
        if len(anos) < 3:
            continue
        n += 1
        anos_usados.append(len(anos))
        sh, p = d["total"], m["preco"]
        lucros = [ind[a]["lucro_liquido"] for a in anos]
        roes = [ind[a]["lucro_liquido"] / ind[a]["patrimonio_liquido"] for a in anos]
        lpa_u, lpa_m = lucros[-1] / sh, statistics.mean(lucros) / sh
        vpa = ind[anos[-1]]["patrimonio_liquido"] / sh
        roe_u, roe_m = roes[-1], statistics.mean(roes)
        por_ano = {}
        for dt, v in (m.get("divs") or {}).items():
            por_ano[dt[:4]] = por_ano.get(dt[:4], 0) + v
        d_ult = div12m(m)
        d_med = statistics.mean([por_ano.get(str(a), 0) for a in ANOS])
        dy_u, dy_m = d_ult / p, d_med / p

        def graham(lpa):
            return (22.5 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else None

        def bazin(dy):
            return (
                dy * p / max(selic, MACRO.BAZIN_TAXA_MIN)
                if dy >= MACRO.BAZIN_DY_MIN
                else None
            )

        def lynch(lpa, roe, dy):
            if not (
                roe > MACRO.ROE_CRESCIMENTO_MIN
                and dy < MACRO.DY_CRESCIMENTO_MAX
                and lpa > 0
                and roe > 0
            ):
                return None
            payout = min(dy * p / lpa, MACRO.LYNCH_PAYOUT_MAX)
            g = min(roe * (1 - payout), MACRO.LYNCH_G_MAX)
            return lpa * min(MACRO.LYNCH_PL_MULTIPLICADOR * g * 100, MACRO.LYNCH_PL_MAX)

        def gordon(lpa, roe, dy):
            if not (dy > MACRO.GORDON_DY_MIN and roe > MACRO.GORDON_ROE_MIN):
                return None
            payout = min(dy * p / lpa, MACRO.GORDON_PAYOUT_MAX) if lpa > 0 else 0.5
            g = min(roe * (1 - payout), MACRO.GORDON_G_MAX)
            k = selic + MACRO.GORDON_PREMIO_RISCO
            return dy * p * (1 + g) / (k - g) if k > g else None

        pares = {
            "Graham": (graham(lpa_u), graham(lpa_m)),
            "Bazin": (bazin(dy_u), bazin(dy_m)),
            "Lynch": (lynch(lpa_u, roe_u, dy_u), lynch(lpa_m, roe_m, dy_m)),
            "Gordon": (gordon(lpa_u, roe_u, dy_u), gordon(lpa_m, roe_m, dy_m)),
        }
        for nome, (a, b) in pares.items():
            if a and b:
                ef[nome].append(b / a - 1)
        if lpa_u > 0 and abs(lpa_m / lpa_u - 1) > 0.25:
            amplos += 1
    linhas = [[nome, len(v), pct(med(v))] for nome, v in ef.items()]
    return (
        f"Amostra: {n} ações com pelo menos 3 anos de CVM com lucro e PL ({min(anos_usados) if anos_usados else 'n/d'} a "
        f"{max(anos_usados) if anos_usados else 'n/d'} anos usados por ação, de {len(ANOS)} possíveis); ações constantes = as atuais; "
        f'dividendos por ação por ano-calendário, com anos sem pagamento contados como zero e o "último ano" sendo os 12 meses até hoje. '
        f"As fórmulas de Bazin, Lynch e Gordon são recalculadas aqui com os parâmetros do `MacroContext` e a Selic de hoje; o "
        f'"cinco anos" troca LPA, ROE e DY pela média do período.\n\n'
        + tabela(
            [
                "Método",
                "Ações em que calcula nos dois casos",
                "Mediana da variação do valor",
            ],
            linhas,
        )
        + f"\n\nO LPA médio difere do último ano em mais de 25% em **{amplos}** das {n} ações."
    )


# ── FII ───────────────────────────────────────────────────────────────────────


def secao_fii():
    mc = macro_cache()
    ntnb_nom = (1 + mc["ntnb"]) * (1 + mc["ipca"]) - 1
    selic_liq = mc["selic"] * MACRO.FII_FATOR_IR
    linhas, dados, sem_cotacao = [], [], []
    for t in FII_CNPJ_MAP:
        m = mercado(t)
        if "erro" in m or not m.get("preco"):
            sem_cotacao.append(t)
            continue
        p = m["preco"]
        dy = div12m(m) / p if p else None
        if not dy:
            continue
        dados.append((t, p, dy, m.get("pvp")))
    for t, p, dy, pvp in dados:
        atual = dy / selic_liq - 1
        spreads = [dy / (ntnb_nom + s) - 1 for s in (0.01, 0.02, 0.03)]
        linhas.append([t, pct(dy), num(pvp), pct(atual)] + [pct(x) for x in spreads])
    resumo = [
        "Mediana",
        pct(med([x[2] for x in dados])),
        num(med([x[3] for x in dados])),
        pct(med([x[2] / selic_liq - 1 for x in dados])),
    ]
    resumo += [
        pct(med([x[2] / (ntnb_nom + s) - 1 for x in dados])) for s in (0.01, 0.02, 0.03)
    ]
    acima_selic = sum(1 for x in dados if x[2] > selic_liq)
    return (
        f"Selic = {pct(mc['selic'], 2)}, Selic líquida (× 0,85) = {pct(selic_liq, 2)}; NTN-B longa nominal = "
        f"(1 + {pct(mc['ntnb'], 2)}) × (1 + IPCA {pct(mc['ipca'], 2)}) − 1 = {pct(ntnb_nom, 2)}. DY = proventos dos últimos 12 meses ÷ "
        f"preço (yfinance, sem ajuste de vacância). Colunas de upside: `DY ÷ taxa − 1`, com o preço cancelando no fair value (F-9). "
        f"Assimetria: a Selic líquida já desconta 15% de IR e a NTN-B nominal está bruta, então parte da diferença de nível entre as colunas é tributária, não de spread. "
        f"Upside é saída mecânica do método; um DY muito alto (como o de alguns FIIs abaixo) costuma indicar risco, não oportunidade.\n\n"
        f"- {len(dados)} dos {len(FII_CNPJ_MAP)} FIIs do mapa com preço e proventos no yfinance (sem cotação no yfinance: "
        f"{', '.join(sem_cotacao) or 'nenhum'}; ticker possivelmente encerrado ou renomeado); **{acima_selic}** têm DY acima da Selic líquida.\n\n"
        + tabela(
            [
                "FII",
                "DY 12m",
                "P/VP",
                "Upside vs Selic líquida",
                "NTN-B + 1%",
                "NTN-B + 2%",
                "NTN-B + 3%",
            ],
            linhas + [resumo],
        )
        + "\n\nLeitura: trocar a Selic líquida por um spread sobre a NTN-B muda o nível de todos os fair values de uma vez e não "
        "muda a ordem entre os fundos — a ordem vem só do DY. O P/VP (âncora patrimonial) continua fora do valor."
    )


# ── Bancos ────────────────────────────────────────────────────────────────────


def ifdata_basileia():
    base = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
    estados = []
    for am in ("202512", "202509", "202506"):
        for rel in ("5", "8"):
            url = (
                f"{base}/IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
                f"?@AnoMes={am}&@TipoInstituicao=2&@Relatorio='{rel}'&$top=5&$format=json"
            )
            try:
                r = requests.get(url, timeout=60, headers=UA)
                estados.append(f"{am}/rel.{rel}: HTTP {r.status_code}")
            except Exception as exc:
                estados.append(f"{am}/rel.{rel}: {type(exc).__name__}")
    return estados


def secao_bancos(acoes):
    mc = macro_cache()
    ipca = mc["ipca"]
    bancos = {
        t: d
        for t, d in acoes.items()
        if d["setor"] and "banco" in str(d["setor"]).lower()
    }
    linhas, sem_dado = [], []
    for t, d in bancos.items():
        e = entrada_acao(t, d)
        if not e:
            sem_dado.append(t)
            continue
        roe, pvp = e["roe"], e["pvp"]
        row = [t, pct(roe), num(pvp)]
        for prem in (0.05, 0.07):
            k = (1 + mc["ntnb"] + prem) * (1 + ipca) - 1
            g = ipca + 0.01
            row.append(num((roe - g) / (k - g)) if k > g else "n/d")
        linhas.append(row)
    estados = ifdata_basileia()
    ok = any("HTTP 200" in x for x in estados)
    return (
        f'Bancos da amostra (setor CVM contendo "Banco"): **{len(bancos)}**: {", ".join(bancos) or "nenhum"}.{" Sem lucro ou PL utilizáveis nas contas genéricas, fora da tabela: " + ", ".join(sem_dado) + "." if sem_dado else ""}\n\n'
        f"**Fonte oficial.** O IF.data do Banco Central (Olinda, serviço `IFDATA`) publica Resumo, Ativo, Passivo, DRE, "
        f"Informações de Capital (índice de Basileia, relatório 5) e carteira por nível de risco (relatório 8, base da "
        f"inadimplência). Estado das chamadas nesta execução: {'; '.join(estados)}. "
        + (
            "Os relatórios 5 e 8 responderam."
            if ok
            else "Nenhuma das chamadas aos relatórios 5 e 8 retornou HTTP 200 (status na lista acima); o catálogo `ListaDeRelatorio` lista os "
            "dois, então a fonte existe, mas a disponibilidade da API não foi confirmada. Repetir a coleta antes de depender dela."
        )
        + "\n\n**Atenção ao ROE:** a V1 calcula lucro e PL com as contas genéricas da CVM (3.11 e 2.03), as mesmas para bancos (F-13). "
        "Para banco o resultado não é confiável: um ROE muito abaixo do divulgado pelo próprio banco, ou ausente, indica conta errada, não resultado ruim."
        + "\n\n**P/VP justificado** = (ROE − g) ÷ (k − g), com ROE do último DFP, g = IPCA + 1% (nominal) e k = taxa real "
        f"(NTN-B {pct(mc['ntnb'], 2)} + prêmio) levada a nominal. ROE = lucro ÷ PL da CVM; P/VP = preço ÷ (PL ÷ ações totais da CVM). **A tabela abaixo não é confiável** (contas genéricas aplicadas a banco, F-13): ROE muito baixo ou muito alto é o sintoma; ela mostra o método, não serve para decidir.\n\n"
        + tabela(
            [
                "Banco",
                "ROE",
                "P/VP",
                "P/VP justificado (prêmio 5%)",
                "P/VP justificado (prêmio 7%)",
            ],
            linhas,
        )
    )


# ── Cobertura e classe ────────────────────────────────────────────────────────


def universo(cad, fca, fii):
    emp = fca[
        fca["Valor_Mobiliario"].isin(
            ["Ações Ordinárias", "Ações Preferenciais", "Units"]
        )
    ]
    com_cad = emp[emp["CNPJ_Companhia"].isin(set(cad["CNPJ_CIA"]))]
    mapeados = {t for t in _TICKER_TO_CVM}
    tickers_fca = set(com_cad["Codigo_Negociacao"])
    fiis_bolsa = fii[fii["Mercado_Negociacao_Bolsa"] == "S"].copy()
    fiis_bolsa["ticker_isin"] = fiis_bolsa["Codigo_ISIN"].fillna("").str[2:6] + "11"
    conhecidos = {t: c for t, c in FII_CNPJ_MAP.items()}
    cnpj_para_t = {c: t for t, c in conhecidos.items()}
    sub = fiis_bolsa[fiis_bolsa["CNPJ_Fundo_Classe"].isin(cnpj_para_t)]
    acerto_isin = sum(
        1
        for _, r in sub.iterrows()
        if cnpj_para_t[r["CNPJ_Fundo_Classe"]] == r["ticker_isin"]
    )
    units = emp[emp["Valor_Mobiliario"] == "Units"]
    units_t = set(units["Codigo_Negociacao"])
    errados_units = [t for t in units_t if CLASSIFIER.is_fii(t)]
    return {
        "tickers_fca": len(tickers_fca),
        "empresas_fca": emp["CNPJ_Companhia"].nunique(),
        "mapeados": len(mapeados),
        "fiis_bolsa": len(fiis_bolsa),
        "fiis_mapeados": len(conhecidos),
        "acerto_isin": acerto_isin,
        "n_sub": len(sub),
        "units": len(units_t),
        "units_errados": sorted(errados_units),
        "segmentos": fii[fii["Segmento_Atuacao"].notna()]["Segmento_Atuacao"].nunique(),
    }


def secao_cobertura(cad, fca, fii):
    u = universo(cad, fca, fii)
    exemplos = [
        ("BOVA11", "ETF de índice"),
        ("IVVB11", "ETF de índice"),
        ("HASH11", "ETF de cripto"),
        ("AAPL34", "BDR"),
        ("MSFT34", "BDR"),
        ("TAEE11", "unit"),
        ("KLBN11", "unit"),
        ("HGLG11", "FII"),
    ]
    linhas = [[t, tipo, CLASSIFIER.classify(t).value] for t, tipo in exemplos]
    return (
        f"- **Companhias abertas com ação, preferencial ou unit negociada em bolsa** (FCA {HOJE.year}): {u['empresas_fca']} empresas, "
        f"**{u['tickers_fca']} tickers** com o código de negociação oficial da CVM — dá para montar `ticker ↔ CNPJ ↔ CD_CVM` "
        f"automaticamente, contra **{u['mapeados']}** no mapa manual (cobertura atual ≈ {u['mapeados'] / max(u['tickers_fca'], 1) * 100:.0f}%).\n"
        f"- **FIIs listados em bolsa** (Informe Mensal da CVM, `Mercado_Negociacao_Bolsa = S`): **{u['fiis_bolsa']}** fundos, contra "
        f"**{u['fiis_mapeados']}** no mapa manual. O CNPJ e o segmento (`Segmento_Atuacao`, {u['segmentos']} valores distintos) vêm da CVM; "
        f'o ticker não vem. Regra testada: letras 3–6 do ISIN + "11" acertou {u["acerto_isin"]} de {u["n_sub"]} FIIs do mapa atual '
        f"({u['acerto_isin'] / max(u['n_sub'], 1) * 100:.0f}%) — serve de ponto de partida, não de regra final. Este script não consulta a B3: uma lista de fundos da B3 "
        f"seria a fonte alternativa do ticker (não avaliada).\n"
        f"- **Units** (terminam em 11): {u['units']} no FCA; o classificador atual trata como FII as que não estão em `UNITS_CONHECIDAS`: "
        f"**{len(u['units_errados'])}** ({', '.join(u['units_errados']) or 'nenhuma'}).\n"
        f"- **ETFs e BDRs:** a regra do classificador é só o sufixo, então o resultado vale para qualquer ticker desses tipos. "
        f"Exemplos conhecidos (não é contagem exaustiva: o script não consulta fonte de ETF ou BDR com ticker):\n\n"
        + tabela(["Ticker", "Tipo real", "Classe atribuída"], linhas)
    )


# ── Carteira (fora do git) ────────────────────────────────────────────────────


def carteira(cad, fca, fii, db_path):
    import sqlite3

    caminho = Path(db_path)
    if not caminho.is_absolute():
        caminho = ROOT / caminho
    if not caminho.exists():
        return f"# Dossiê da carteira (local, fora do git)\n\n_Banco não encontrado: `{db_path}`._\n"
    # somente leitura: nada é criado nem alterado no banco apontado
    with sqlite3.connect(f"file:{caminho}?mode=ro", uri=True) as conn:
        tickers = sorted(
            {r[0] for r in conn.execute("SELECT ticker FROM carteira_real")}
        )
    if not tickers:
        return f"# Dossiê da carteira (local, fora do git)\n\n_Carteira vazia em `{db_path}`. Rode o script apontando para o banco com as posições: `python scripts/dossie_fase2.py <banco.db>`._\n"
    fca_t = set(fca["Codigo_Negociacao"])
    fii_cnpj_t = set(FII_CNPJ_MAP)
    linhas = []
    for t in tickers:
        cls = CLASSIFIER.classify(t).value
        no_cvm = t in _TICKER_TO_CVM
        no_fii = t in fii_cnpj_t
        in_fca = t in fca_t
        setor = ""
        if in_fca:
            cnpj = fca[fca["Codigo_Negociacao"] == t]["CNPJ_Companhia"].iloc[0]
            c = cad[cad["CNPJ_CIA"] == cnpj]
            setor = c["SETOR_ATIV"].iloc[0] if len(c) else ""
        banco = "sim" if "banco" in str(setor).lower() else ""
        suspeita = ""
        if t.endswith("11") and in_fca:
            suspeita = "unit (não FII)"
        elif t.endswith(("34", "35", "32", "33", "39")):
            suspeita = "provável BDR"
        elif t.endswith("11") and not no_fii and not in_fca:
            suspeita = "FII, ETF ou unit fora do mapa"
        linhas.append(
            [
                t,
                cls,
                "sim" if no_cvm else "não",
                "sim" if no_fii else "não",
                "sim" if in_fca else "não",
                banco,
                suspeita,
            ]
        )
    cobertos = sum(1 for ln in linhas if ln[2] == "sim" or ln[3] == "sim")
    return (
        f"# Dossiê da carteira (local, fora do git)\n\nGerado em {HOJE}. **Não versionar.**\n\n"
        f"Ativos: {len(linhas)}. Com cobertura CVM no mapa manual (ação ou FII): **{cobertos}**.\n\n"
        + tabela(
            [
                "Ticker",
                "Classe atribuída",
                "Mapa CVM (ação)",
                "Mapa CVM (FII)",
                "FCA (código oficial)",
                "Banco",
                "Alerta de classe",
            ],
            linhas,
        )
    )


# ── Montagem ──────────────────────────────────────────────────────────────────


def main():
    falhas = []
    cad = cadastro_cvm()
    cap = composicao_capital()
    fca_todos = fca_valores()
    fca = fca_todos[fca_todos["Data_Fim_Negociacao"].isna()]
    fii = fii_geral()
    acoes = dados_acoes(cad, cap, fca)

    mapa = secao("Mapa", lambda: secao_mapa(acoes, cad, fca_todos), falhas)
    e1 = secao("E-1", lambda: secao_e1(acoes), falhas)
    res_taxas = secao("Taxas", lambda: secao_taxas(acoes), falhas)
    taxas, entradas = res_taxas if isinstance(res_taxas, tuple) else (res_taxas, {})
    res_gordon = secao("Gordon", lambda: gordon_variantes(entradas), falhas)
    gordon, fator_iso = (
        res_gordon if isinstance(res_gordon, tuple) else (res_gordon, None)
    )
    fator_txt = (
        f"multiplica o fair value do Gordon por {fator_iso[0]:.1f}× a {fator_iso[1]:.1f}× só pela mistura real/nominal (seção 3)"
        if fator_iso
        else "distorce o Gordon (seção 3)"
    )
    fii_txt = secao("FII", secao_fii, falhas)
    cinco = secao("Cinco anos", lambda: secao_cinco_anos(acoes), falhas)
    bancos = secao("Bancos", lambda: secao_bancos(acoes), falhas)
    cobertura = secao("Cobertura", lambda: secao_cobertura(cad, fca, fii), falhas)

    doc = f"""# Dossiê de decisão da Fase 2

**Não é consultoria financeira.** Upside, fair value e classificações aqui são saídas mecânicas dos métodos da V1 sob revisão metodológica.

**Gerado por** `scripts/dossie_fase2.py` em {HOJE} (F0-6). Amostra: os tickers dos mapas atuais ({len(_TICKER_TO_CVM)} ações, {len(FII_CNPJ_MAP)} FIIs), **nunca** a carteira.
Rede só para leitura: CVM (DFP, FCA, Informe Mensal de FII), Tesouro Direto, Banco Central (SGS, IF.data) e yfinance. Nenhum módulo de produção foi alterado.
Este documento **não decide nada**: reúne os números para as decisões D-* e os itens da Fase 2 (A, B e C) do `docs/PLANO.md`.

**Achados principais (detalhe nas seções):**
- **Mapa manual ticker → CD_CVM desalinhado** (seção 0): quase todas as entradas apontam para outra empresa; não estava na auditoria de 9/9.
- **Escala da quantidade de ações** (seção 1): parte das empresas informa a Composição do Capital em milhares, sem coluna de escala no CSV.
- **Selic dirige Bazin e Gordon** (seção 2) e o regime misto de taxas {fator_txt}.
- **Cobertura** (seção 7): o cadastro oficial permite mapear as ações listadas e os FIIs automaticamente; o ticker do FII sai do ISIN.

> Limites conhecidos: (1) a NTN-B {"é o **fallback do código** (o Tesouro Direto falhou), e as seções 2, 3, 4 e 6 dependem dela" if macro_cache()["ntnb_fallback"] else "veio do Tesouro Direto"}; (2) o DY é de bases diferentes — seções 2 e 3 usam o `dividendYield` do yfinance via `_normalizar_dy` (armadilha 4), seções 4 e 5 usam proventos dos últimos 12 meses ÷ preço; (3) a seção 5 recalcula Graham e Bazin sem as travas de entrada da V1 (limites de P/L e P/VP, piso de P/L, separação crescimento × renda); (4) o FCA lido é só o do ano corrente, então ticker "sem negociação ativa" pode ser entrega pendente; (5) o IF.data só foi testado com os relatórios 5 e 8, sem uma chamada de controle; (6) a seção 2 recalcula com k real só o Gordon (seção 3) e o FII (seção 4), não Bazin nem Graham por método.
>
> O yfinance é fonte não oficial e o `sharesOutstanding` dele é o objeto de teste do E-1; os números de mercado mudam a cada execução (a Selic, a NTN-B e os preços são os do dia da geração).

## 0. Mapa manual ticker → CD_CVM

{mapa}

## 1. E-1 — ações da CVM × `sharesOutstanding`

{e1}

## 2. Taxas: Selic de 10% a 15% e k real

{taxas}

## 3. Gordon: regime atual × opção A × opção B

{gordon}

## 4. FII: Selic líquida × spread sobre a NTN-B

{fii_txt}

## 5. Cinco anos × último ano

{cinco}

## 6. Bancos

{bancos}

## 7. Cobertura e classe do ativo

{cobertura}

## 8. Perguntas que o Marcos precisa responder

0. **Mapa manual (novo, seção 0):** a maioria dos `CD_CVM` do `cvm_ticker_map.py` aponta para outra empresa. Antes de qualquer item da Fase 2A, você autoriza corrigir o mapa já na Fase 1 (ou até antes, como item de `fix:`), em vez de esperar o mapa automático do F2A-1? Enquanto isso não acontece, os fundamentos CVM da V1 estão trocados entre tickers.
1. **E-1 (F2A-3):** quando as ações da CVM e do yfinance divergirem mais de 5%, o caminho é usar sempre as ações da Composição do Capital (ON + PN − tesouraria) ou abster-se do LPA/VPA derivado? E, com duas classes, o preço de qual classe entra no P/L?
2. **Taxa de desconto (F2B-1):** qual prêmio sobre a NTN-B (a tabela da seção 2 mostra 4%, 5% e 7%) e qual regime para o Gordon: tudo real ou tudo nominal? (A seção 3 mostra que, bem feitos, dão o mesmo valor; o regime misto é o que não pode existir.) A NTN-B usada pode ser o fallback do código (a seção 2 diz qual): repita a coleta com o Tesouro Direto disponível antes de fixar o prêmio.
3. **FII (F2B):** o fair value do FII passa a comparar o DY com a NTN-B mais spread (qual spread?) ou com a Selic líquida, mantendo o P/VP só como contexto? A seção 4 mostra que o spread desloca o nível e não a ordem.
4. **Janela (F2A-7/F2C-1):** média de 5 anos de LPA e dividendos para todos os métodos, ou só para os cíclicos? A seção 5 mostra o tamanho do efeito.
5. **Bancos (F2B-3):** a lente de bancos usa P/VP justificado pelo ROE (seção 6) e Basileia/inadimplência do IF.data? A API de capital e risco não respondeu; vale tolerar essa dependência?
6. **Cobertura (F2A-1):** o mapa automático parte do FCA da CVM (ações e units) e do Informe Mensal (FIIs); para o ticker dos FIIs, aceita a regra do ISIN com validação manual ou prefere uma fonte da B3?
7. **Classe (F2A-1):** units, ETFs e BDRs entram na V2 como classes próprias (com métodos próprios) ou ficam fora do escopo?
"""
    if falhas:
        doc += (
            "\n## Apêndice — seções com falha nesta execução\n\n"
            + "\n".join(f"- {f}" for f in falhas)
            + "\n"
        )
    (ROOT / "docs" / "decisoes").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "decisoes" / "dossie-fase2.md").write_text(doc, encoding="utf-8")

    try:
        txt = carteira(
            cad, fca, fii, sys.argv[1] if len(sys.argv) > 1 else "sentinela_v6.db"
        )
    except Exception as exc:
        txt = f"# Dossiê da carteira\n\n_Indisponível: {type(exc).__name__}: {exc}_\n"
    (ROOT / "outputs").mkdir(exist_ok=True)
    (ROOT / "outputs" / "dossie-carteira.md").write_text(txt, encoding="utf-8")
    print("ok; falhas:", len(falhas))


if __name__ == "__main__":
    main()
