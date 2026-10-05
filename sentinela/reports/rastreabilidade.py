"""Relatório estático de rastreabilidade v0 (F1-12).

    python -m sentinela.reports.rastreabilidade <TICKER>

Grava `outputs/rastreabilidade/<TICKER>-<data>.html`, fora do git. Lê a cascata e os
motores da V1 como estão (a mesma sequência do `app.py`, sem IA e sem gravar análise;
a cascata ainda grava o cache de fundamentos, como no app). O detalhe de cada método
vem das chamadas que os motores já fazem aos métodos de `sentinela/methods/`: nenhum
cálculo novo. Não mostra o rótulo de classificação da V1.
"""

from __future__ import annotations

import argparse
import dataclasses
import math
import re
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment

import fii_engine as modulo_fii
import valuation_engine as modulo_valuation
from sentinela.domain import units
from sentinela.methods.base import Abstention, MethodResult

RAIZ = Path(__file__).resolve().parents[2]
PASTA_SAIDA = RAIZ / "outputs"
TICKER = re.compile(r"[A-Z0-9]{4,7}")
PLANO_URL = (
    "https://github.com/Marcos-Felipe-dos-Santos/Sentinela-B3/blob/main/docs/PLANO.md"
)

CAMPOS_ACAO = (
    ("preco_atual", "BRL"),
    ("pl", "razão"),
    ("pvp", "razão"),
    ("dy", "como veio da fonte"),
    ("roe", "razão"),
    ("divida_liq_ebitda", "razão"),
)
CAMPOS_FII = (
    ("preco_atual", "BRL"),
    ("dy", "como veio da fonte"),
    ("pvp", "razão"),
    ("tipo", "texto"),
)
PROVENIENCIA_DERIVADA = {
    "lpa": "derivado no motor: preço ÷ P/L (E-1: sem reconciliação de escopo)",
    "vpa": "derivado no motor: preço ÷ P/VP (E-1: sem reconciliação de escopo)",
    "dy": "normalizado no motor (_normalizar_dy: acima de 1 é percentual, acima de 0,25 é inválido e zerado)",
    "perfil": "derivado no motor: ROE e DY",
    "selic": "sem proveniência registrada (E-6): BCB SGS 432 ou valor de contingência",
}
LIMITES = (
    (
        "E-6: a Selic usada não carrega proveniência (fonte, data de coleta); vem do BCB (SGS 432) "
        "com cache de 24 horas ou de um valor de contingência fixo."
    ),
    (
        "E-1: LPA e VPA são derivados do preço e dos múltiplos, sem reconciliar o escopo das ações "
        "(lucro consolidado ÷ quantidade de ações de outra fonte); o selo de qualidade dos dados "
        "não cobre isso."
    ),
    (
        "A proveniência registrada pela cascata cobre cinco campos (preço, DY, P/L, P/VP e ROE); "
        "os demais herdam a fonte agregada dos fundamentos."
    ),
)

TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rastreabilidade {{ ticker }} — {{ data }}</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 62rem; margin: 1.5rem auto; padding: 0 1rem; line-height: 1.45; color: #1c1c1c; background: #fff; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0 1rem; }
th, td { border: 1px solid #c8c8c8; padding: .3rem .5rem; text-align: left; vertical-align: top; }
th { background: #f0f0f0; }
.aviso { border: 2px solid #b36b00; background: #fff4e0; padding: .6rem .9rem; }
.metodo { border: 1px solid #c8c8c8; border-radius: 6px; padding: .6rem .9rem; margin: .8rem 0; }
.abstencao { background: #f6f6f6; }
code { background: #f0f0f0; padding: 0 .2rem; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #151515; }
  th { background: #2a2a2a; } th, td { border-color: #444; }
  .aviso { background: #3a2a10; border-color: #d89a3a; } .metodo { border-color: #444; }
  .abstencao { background: #222; } code { background: #2a2a2a; }
}
</style>
</head>
<body>
<h1>Rastreabilidade — {{ ticker }}</h1>
<p>Gerado em {{ data }}. Ativo tratado como {{ classe }}.</p>
<p class="aviso"><strong>Resultados em revisão metodológica — não use para decisão.</strong>
Os métodos, as taxas e a classificação desta versão estão sendo refeitos (<a href="{{ plano_url }}">docs/PLANO.md</a>).
Não é consultoria financeira.</p>

<h2>Limites conhecidos</h2>
<ul>{% for l in limites %}<li>{{ l }}</li>{% endfor %}</ul>

<h2>Fontes da cascata</h2>
<table>
{% for nome, valor in fontes %}<tr><th>{{ nome }}</th><td>{{ valor }}</td></tr>{% endfor %}
</table>

<h2>Selic usada</h2>
<p>{{ selic }} ao ano (taxa nominal).</p>

<h2>Insumos</h2>
<table>
<tr><th>Campo</th><th>Valor</th><th>Unidade</th><th>Proveniência</th></tr>
{% for i in insumos %}<tr><td>{{ i.campo }}</td><td>{{ i.valor }}</td><td>{{ i.unidade }}</td><td>{{ i.proveniencia }}</td></tr>{% endfor %}
</table>

<h2>Métodos</h2>
{% for m in metodos %}
<div class="metodo{% if m.abstencao or m.nao_calculado %} abstencao{% endif %}">
<h3>{{ m.nome }} <small>versão {{ m.versao }} · regime {{ m.regime }}</small></h3>
<p>Aplica-se a: {{ m.applies_to }}</p>
<p>Premissas:</p>
<ul>{% for a in m.premissas %}<li>{{ a }}</li>{% endfor %}</ul>
{% if m.params %}<p>Parâmetros:</p>
<table>{% for k, v in m.params %}<tr><td><code>{{ k }}</code></td><td>{{ v }}</td></tr>{% endfor %}</table>{% endif %}
{% if m.nao_calculado %}<p><strong>Método não calculado:</strong> {{ m.nao_calculado }}</p>
{% elif m.abstencao %}<p><strong>Abstenção:</strong> {{ m.abstencao }}</p>
{% else %}<p><strong>Resultado:</strong> {{ m.valor }}</p>
{% if m.intermediarios %}<table>{% for k, v in m.intermediarios %}<tr><td>{{ k }}</td><td>{{ v }}</td></tr>{% endfor %}</table>{% endif %}
{% if m.alertas %}<p>Alertas: {{ m.alertas | join("; ") }}</p>{% endif %}
{% endif %}
</div>
{% endfor %}

<h2>Síntese</h2>
<table>
{% for nome, valor in sintese %}<tr><th>{{ nome }}</th><td>{{ valor }}</td></tr>{% endfor %}
</table>
</body>
</html>
"""

_ENV = Environment(autoescape=True)


# ── formatação ────────────────────────────────────────────────────────────────


def _numero(x: float, casas: int = 2) -> str:
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
        return "n/d"
    return f"{x:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _formatar(valor: Any) -> str:
    """Valor com unidade (units.py) ou número/texto do dado de entrada."""
    if isinstance(valor, units.BRL):
        return f"R$ {_numero(valor.valor)}"
    if isinstance(valor, (units.RateNominal, units.RateReal)):
        return f"{_numero(valor.valor * 100)}%"
    if isinstance(valor, units.Percent):
        return f"{_numero(valor.valor)}%"
    if isinstance(valor, units.Ratio):
        return _numero(valor.valor, 4)
    if isinstance(valor, units.QuantidadeAcoes):
        return f"{_numero(valor.valor, 0)} ({valor.escala.name.lower()})"
    if isinstance(valor, bool) or valor is None:
        return "ausente" if valor is None else ("sim" if valor else "não")
    if isinstance(valor, float):
        return _numero(valor, 4)
    return str(valor)


def _param(v: Any) -> str:
    return repr(v) if isinstance(v, float) else str(v)


# ── captura das chamadas aos métodos ──────────────────────────────────────────


@contextmanager
def _capturar(instancias, registros):
    """Registra cada `calcular` feito pelos motores, sem alterá-los."""
    try:
        for inst in instancias:
            original = inst.calcular

            def embrulho(inputs, params, _inst=inst, _original=original):
                resultado = _original(inputs, params)
                registros.append((_inst, inputs, params, resultado))
                return resultado

            inst.calcular = embrulho
        yield
    finally:
        for inst in instancias:
            inst.__dict__.pop("calcular", None)


def _instancias(eh_fii: bool):
    if eh_fii:
        return [modulo_fii._FII_YIELD, modulo_fii._FII_NAV]
    return [
        modulo_valuation._GRAHAM,
        modulo_valuation._BAZIN,
        modulo_valuation._LYNCH,
        modulo_valuation._GORDON,
    ]


# ── contexto ──────────────────────────────────────────────────────────────────


def _proveniencia(campo: str, dados: dict[str, Any]) -> str:
    registro = (dados.get("field_provenance") or {}).get(campo)
    if registro:
        prov = registro.get("provenance") or {}
        avisos = prov.get("warnings") or []
        extra = f" (avisos: {', '.join(avisos)})" if avisos else ""
        return f"{prov.get('source', 'unknown')}{extra}"
    return f"herdada de fonte_fundamentos: {dados.get('fonte_fundamentos') or 'desconhecida'}"


def _bloco_metodo(registro) -> dict[str, Any]:
    inst, _, params, resultado = registro
    bloco: dict[str, Any] = {
        "nome": inst.nome,
        "versao": inst.version,
        "regime": inst.regime.value,
        "applies_to": ", ".join(sorted(a.value for a in inst.applies_to)),
        "premissas": list(inst.assumptions),
        "params": [(k, _param(v)) for k, v in dataclasses.asdict(params).items()],
        "abstencao": None,
        "nao_calculado": None,
    }
    if isinstance(resultado, Abstention):
        bloco["abstencao"] = resultado.motivo
    elif isinstance(resultado, MethodResult):
        bloco["valor"] = _formatar(resultado.valor)
        bloco["intermediarios"] = [
            (i.nome, _formatar(i.valor)) for i in resultado.intermediarios
        ]
        bloco["alertas"] = list(resultado.alertas)
    return bloco


def _bloco_nao_calculado(inst, motivo: str) -> dict[str, Any]:
    return {
        "nome": inst.nome,
        "versao": inst.version,
        "regime": inst.regime.value,
        "applies_to": ", ".join(sorted(a.value for a in inst.applies_to)),
        "premissas": list(inst.assumptions),
        "params": [],
        "abstencao": None,
        "nao_calculado": motivo,
    }


def construir_contexto(dados, eh_fii, hoje, motor_acoes, motor_fii) -> dict[str, Any]:
    """Roda o motor da V1 sobre `dados`, capturando o detalhe de cada método."""
    instancias = _instancias(eh_fii)
    registros: list = []
    with _capturar(instancias, registros):
        analise = motor_fii.analisar(dados) if eh_fii else motor_acoes.processar(dados)
    if analise is None:
        raise ValueError("dados insuficientes para a análise")

    por_instancia = {id(r[0]): r for r in registros}
    if analise.get("perfil") == "DISTRESSED":
        motivo_ausente = (
            "guarda de situação especial (distressed): nenhum método foi chamado"
        )
    elif str(analise.get("metodos_usados", "")).startswith("Dados insuficientes"):
        motivo_ausente = analise["metodos_usados"]
    else:
        motivo_ausente = "valor não finito na entrada"
    metodos = [
        _bloco_metodo(por_instancia[id(i)])
        if id(i) in por_instancia
        else _bloco_nao_calculado(i, motivo_ausente)
        for i in instancias
    ]

    entradas = next(
        (r[1] for r in registros if r[1].selic is not None),
        registros[0][1] if registros else None,
    )
    selic = entradas.selic if entradas is not None else None
    insumos = [
        {
            "campo": campo,
            "valor": _formatar(units.BRL(dados[campo]))
            if unidade == "BRL"
            and isinstance(dados.get(campo), (int, float))
            and math.isfinite(dados[campo])
            else _formatar(dados.get(campo)),
            "unidade": unidade,
            "proveniencia": _proveniencia(campo, dados),
        }
        for campo, unidade in (CAMPOS_FII if eh_fii else CAMPOS_ACAO)
    ]
    if eh_fii and not dados.get("pvp"):
        for i in insumos:
            if i["campo"] == "pvp":
                i["proveniencia"] += (
                    "; ausente: o motor usa P/VP = 1,0 (sem CVMFIIProvider injetado)"
                )
    derivados = {}
    for _, inputs, _, _ in registros:
        for campo in ("dy", "lpa", "vpa", "perfil", "vacancia"):
            valor = getattr(inputs, campo)
            if valor is not None:
                derivados[campo] = valor
    for campo, valor in derivados.items():
        insumos.append(
            {
                "campo": "dy (normalizado)" if campo == "dy" else campo,
                "valor": valor.value if campo == "perfil" else _formatar(valor),
                "unidade": "texto"
                if campo == "perfil"
                else ("razão" if campo in ("vacancia", "dy") else "BRL"),
                "proveniencia": (
                    f"{analise.get('vacancia_fonte', 'desconhecida')}"
                    if campo == "vacancia"
                    else PROVENIENCIA_DERIVADA[campo]
                ),
            }
        )

    if selic is not None:
        insumos.append(
            {
                "campo": "selic",
                "valor": _formatar(selic),
                "unidade": "taxa nominal a.a.",
                "proveniencia": PROVENIENCIA_DERIVADA["selic"],
            }
        )

    flags = ("dados_parciais", "dados_cache", "dados_manual", "erro_scraper")
    fontes = [
        ("Fonte do preço", dados.get("fonte_preco") or "desconhecida"),
        ("Fonte dos fundamentos", dados.get("fonte_fundamentos") or "desconhecida"),
        *[
            (f.replace("_", " ").capitalize(), "sim" if dados.get(f) else "não")
            for f in flags
        ],
        (
            "Campos faltantes",
            ", ".join(map(str, dados.get("campos_faltantes") or [])) or "nenhum",
        ),
    ]

    sintese = [
        (
            "Nenhum método calculou: o valor é o próprio preço"
            if not analise.get("metodos_usados")
            or str(analise["metodos_usados"]).startswith("Dados insuficientes")
            else (
                "Preço justo do rendimento"
                if eh_fii
                else "Mediana dos métodos calculados"
            ),
            f"R$ {_numero(analise.get('fair_value'))}",
        ),
        (
            "Variação sobre o preço",
            f"{_numero(analise.get('upside') or 0)}%",
        ),
        ("Score", str(analise.get("score_final"))),
    ]
    if analise.get("confianca") is not None:
        sintese.append(("Confiança", str(analise["confianca"])))
    if analise.get("riscos"):
        sintese.append(
            ("Riscos sinalizados pelo motor", "; ".join(map(str, analise["riscos"])))
        )
    sintese.append(("Métodos usados", str(analise.get("metodos_usados") or "nenhum")))

    return {
        "ticker": dados.get("ticker", ""),
        "data": hoje.isoformat(),
        "classe": "FII" if eh_fii else "ação",
        "plano_url": PLANO_URL,
        "limites": LIMITES,
        "fontes": fontes,
        "selic": _formatar(selic) if selic is not None else "indisponível",
        "insumos": insumos,
        "metodos": metodos,
        "sintese": sintese,
    }


def renderizar(contexto: dict[str, Any]) -> str:
    return _ENV.from_string(TEMPLATE).render(**contexto)


# ── saída ─────────────────────────────────────────────────────────────────────


def validar_ticker(texto: str) -> str:
    ticker = (texto or "").upper().strip()
    if not TICKER.fullmatch(ticker):
        raise ValueError(f"ticker inválido: {texto!r}")
    return ticker


def gravar(html: str, ticker: str, hoje: date, pasta: Path = PASTA_SAIDA) -> Path:
    destino = pasta / "rastreabilidade" / f"{ticker}-{hoje.isoformat()}.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Relatório de rastreabilidade de um ticker."
    )
    ap.add_argument("ticker")
    args = ap.parse_args(argv)
    ticker = validar_ticker(args.ticker)

    from market_engine import MarketEngine
    from sentinela.services.asset_classifier import AssetClassifier

    mercado, classificador = MarketEngine(), AssetClassifier()
    dados = mercado.buscar_dados_ticker(ticker)
    if not dados or "erro" in dados:
        print("Ativo não encontrado.", file=sys.stderr)
        return 1
    eh_fii = classificador.is_fii(ticker, dados)
    hoje = date.today()
    try:
        contexto = construir_contexto(
            dados,
            eh_fii,
            hoje,
            modulo_valuation.ValuationEngine(),
            modulo_fii.FIIEngine(),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(gravar(renderizar(contexto), ticker, hoje))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
