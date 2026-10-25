"""Contraprova D27 do F2B-2 (lente de FII sobre NTN-B + spread): a mesma entrada nos dois commits.

Uso: python f2b2_fii.py <raiz da worktree>, uma vez no commit pai (7e1dfb4) e outra no commit do
item (7ffe016). Cada cenário monta a entrada no formato que a cascata grava (`informe_fii` com
as linhas do complemento e a composição, `b3_fundo` com a resposta da B3, `taxa_real` com a
NTN-B) e aplica a regra que os testes fixam. No pai, que não lia nada disso, o motor devolve o
preço justo pela Selic líquida; no item, a regra abstém com o próprio motivo (ou dá o valor da
NTN-B + spread): a diferença entre as duas saídas é a falha econômica que a contraprova pede.

A importação do `config` consulta o BCB (armadilha 8); a Selic do cálculo é fixada por `patch`.
"""

import copy
import inspect
import sys
from datetime import UTC, datetime
from unittest.mock import patch

sys.path.insert(0, sys.argv[1])
import fii_engine
from config import MACRO
from fii_engine import FIIEngine

AS_OF = datetime(2026, 10, 20, 15, tzinfo=UTC)
ISIN = "BRTSTFCTF000"
COM_AS_OF = "as_of" in inspect.signature(FIIEngine.analisar).parameters


def _meses(final=(2026, 9)):
    ano, mes = final
    saida = []
    for _ in range(13):
        saida.append((ano, mes))
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida[::-1]


def entrada(dy_mes="0.01", final=(2026, 9), **mudar):
    """FII de tijolo com 12 meses de DY de 1% sobre VP 100 (R = 12) e preço 100."""
    registros = []
    for i, (ano, mes) in enumerate(_meses(final)):
        prox = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
        registros.append(
            {
                "Data_Referencia": f"{ano:04d}-{mes:02d}-01",
                "Versao": "1",
                "Data_Entrega": f"{prox[0]:04d}-{prox[1]:02d}-14",
                "Codigo_ISIN": ISIN,
                "Valor_Patrimonial_Cotas": "100",
                "Percentual_Dividend_Yield_Mes": None if i == 0 else dy_mes,
                "Percentual_Amortizacao_Cotas_Mes": "0",
                "Cotas_Emitidas": "1000",
            }
        )
    composicao = {
        "Data_Referencia": f"{final[0]:04d}-{final[1]:02d}-01",
        "Versao": "1",
        "Imoveis_Renda_Acabados": "900",
        "CRI": "100",
    }
    dados = {
        "ticker": "TSTF11",
        "preco_atual": 100.0,
        "dy": 0.12,
        "pvp": 1.0,
        "taxa_real": {"ntnb": 0.07},
        "informe_fii": {
            "registros": registros,
            "composicoes": [composicao],
            "isin": ISIN,
            "proveniencia": {"fonte": "contraprova"},
        },
        "b3_fundo": {
            "resposta": {"code": "TSTF", "fund": "FII TESTE", "stockDividends": [],
                         "cashDividends": []},
            "codigo": "TSTF",
        },
    }  # fmt: skip
    for caminho, valor in mudar.items():
        alvo, *chaves = caminho.split(".")
        destino = dados
        for chave in [alvo, *chaves[:-1]]:
            destino = (
                destino[int(chave)] if isinstance(destino, list) else destino[chave]
            )
        ultimo = chaves[-1] if chaves else None
        if ultimo is None:
            if valor is None:
                dados.pop(alvo)
            else:
                dados[alvo] = valor
        elif isinstance(destino, list):
            destino[int(ultimo)] = valor
        else:
            destino[ultimo] = valor
    return dados


_SPREAD = getattr(MACRO, "FII_SPREAD_TIJOLO", None)


def analisar(dados, spread=_SPREAD):
    dados = copy.deepcopy(dados)
    with (
        patch.object(fii_engine, "get_selic_atual", return_value=0.145),
        patch.object(MACRO, "FII_SPREAD_TIJOLO", spread, create=True),
    ):
        r = (
            FIIEngine().analisar(dados, as_of=AS_OF)
            if COM_AS_OF
            else FIIEngine().analisar(dados)
        )
    return r.get("fair_value"), r.get("metodos_usados")


CENARIOS = {
    "C1 tijolo elegível: R de 12 meses ÷ (NTN-B + spread)": {},
    "C4a sem NTN-B": {"taxa_real": None},
    "C4c FII de papel pela composição do mês final": {"informe_fii.composicoes.0.CRI": "9000"},
    "C4d composição sem maioria estrita": {"informe_fii.composicoes.0.CRI": "900"},
    "C4e desdobramento oficial na janela": {
        "b3_fundo.resposta.stockDividends": [{"label": "DESDOBRAMENTO", "lastDatePrior": "10/03/2026"}]
    },
    "C4f fonte de eventos da B3 indisponível": {"b3_fundo": {"abstencao": "sem rede"}},
    "C4g Informe do mês final entregue no dia do as_of": {"informe_fii.registros.12.Data_Entrega": "2026-10-20"},
    "C4i DY mensal negativo declarado": {"informe_fii.registros.5.Percentual_Dividend_Yield_Mes": "-0.001"},
    "C4i' amortização na janela": {"informe_fii.registros.5.Percentual_Amortizacao_Cotas_Mes": "0.01"},
    "C4i'' cotas não positivas": {"informe_fii.registros.5.Cotas_Emitidas": "0"},
    "C4k sem Informe": {"informe_fii": None},
}  # fmt: skip

print(f"código: {'item (com as_of)' if COM_AS_OF else 'pai (sem as_of)'}")
for nome, mudar in CENARIOS.items():
    valor, metodos = analisar(entrada(**mudar))
    print(f"{nome}: fair_value={valor} | {metodos}")
valor, metodos = analisar(entrada(), spread=None)
print(f"C4b sem spread calibrado: fair_value={valor} | {metodos}")
valor, metodos = analisar(entrada(final=(2026, 5)))
print(f"C4h Informe com mais de 3 meses: fair_value={valor} | {metodos}")
valor, metodos = analisar(entrada(dy_mes="0"))
print(f"C4j rendimento anual zero: fair_value={valor} | {metodos}")
# C2 e C3 pelo motor: o mesmo FII com Selic de 5%, 10% e 15%; o exemplo da ficha (HGLG11).
for selic in (0.05, 0.10, 0.15):
    with patch.object(fii_engine, "get_selic_atual", return_value=selic):
        dados = copy.deepcopy(entrada())
        r = (
            FIIEngine().analisar(dados, as_of=AS_OF)
            if COM_AS_OF
            else FIIEngine().analisar(dados)
        )
    print(f"C2 Selic {selic:.0%}: fair_value={r.get('fair_value')}")
r12, preco = 13.240529645135538184, 147.95
ficha = entrada(preco_atual=preco, dy=r12 / preco, taxa_real={"ntnb": 74.38 / 1100})
for registro in ficha["informe_fii"]["registros"][1:]:
    registro["Percentual_Dividend_Yield_Mes"] = repr(r12 / 12 / 100)
valor, _ = analisar(ficha)
print(f"C3 exemplo da ficha (R = {r12:.6f}, NTN-B 74,38/1100): fair_value={valor}")
