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
import sys
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment

import fii_engine as modulo_fii
import valuation_engine as modulo_valuation
from sentinela.domain import ticker as ticker_b3
from sentinela.domain import units
from sentinela.methods.base import Abstention, MethodResult

RAIZ = Path(__file__).resolve().parents[2]
PASTA_SAIDA = RAIZ / "outputs"
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
    "lpa": "derivado no motor: preço ÷ P/L",
    "vpa": "derivado no motor: preço ÷ P/VP",
    "dy": (
        "invariante no motor (_normalizar_dy: fora de 0 a 25% é inválido e zerado); a conversão "
        "de percentual é da fronteira do provedor (F2A-4)"
    ),
    "perfil": "derivado no motor: ROE e DY",
    "selic": "sem proveniência registrada (E-6): BCB SGS 432 ou valor de contingência",
}
LIMITES = (
    (
        "E-6: a Selic usada não carrega proveniência (fonte, data de coleta); vem do BCB (SGS 432) "
        "com cache de 24 horas ou de um valor de contingência fixo."
    ),
    (
        "E-1: quando o P/L vem da CVM, o LPA é o LPA básico divulgado na DRE para a classe do "
        "ticker (média ponderada de ações do exercício; na unit, o LPA de cada classe vezes a "
        "quantidade dela na unit, somados). Divulgado incoerente faz o LPA se abster; sem linha "
        "divulgada da classe, entra marcado o recalculado: lucro dos controladores ÷ ações "
        "(ON + PN − tesouraria) da Composição do Capital do mesmo documento, ações do fim do "
        "período; com escala indeterminada, ou numa preferencial de companhia com mais de uma "
        "classe preferencial, o LPA se abstém. Quando o P/VP vem da CVM, o VPA é o PL dos controladores ÷ essas mesmas ações, "
        "com a escala inferida pelo LPA divulgado. Com P/L e P/VP de outra fonte, LPA e VPA "
        "herdam o escopo dela."
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


def _texto_acoes(acoes: dict[str, Any]) -> str:
    documento = acoes.get("documento") or {}
    return (
        f"{_numero(acoes.get('acoes'), 0)} ações da Composição do Capital "
        f"(DFP de {documento.get('dt_refer')}, versão {documento.get('versao')}, "
        f"escala {acoes.get('escala')}; {acoes.get('nota')})"
    )


def _texto_lpa_da_classe(origem: dict[str, Any], acoes: dict[str, Any] | None) -> str:
    """Origem do LPA de uma classe (F2A-36, D19): o divulgado ou o recalculado, com as notas."""
    if origem.get("origem") == "divulgado":
        texto = (
            f"LPA básico divulgado na DRE da classe {origem.get('classe')} "
            "(média ponderada de ações do exercício)"
        )
    else:
        denominador = _texto_acoes(acoes) if acoes else "ações da Composição do Capital"
        texto = (
            f"LPA recalculado da classe {origem.get('classe')}: lucro dos controladores ÷ "
            f"{denominador}"
        )
    notas = origem.get("notas") or []
    return f"{texto} [{'; '.join(notas)}]" if notas else texto


def _texto_lpa_cvm(lpa_cvm: dict[str, Any], acoes: dict[str, Any] | None) -> str:
    """LPA da CVM nos métodos (F2A-36): da classe do ticker ou, na unit, a soma das classes."""
    if lpa_cvm.get("origem") != "unit":
        return _texto_lpa_da_classe(lpa_cvm, acoes)
    partes = [
        f"{_numero(componente.get('quantidade'), 0)} × "
        f"{_texto_lpa_da_classe(componente, acoes)}"
        for componente in (lpa_cvm.get("componentes") or {}).values()
    ]
    return f"soma das classes da unit: {' + '.join(partes)}"


def _proveniencia_derivada(campo: str, dados: dict[str, Any]) -> str:
    """LPA e VPA: com P/L ou P/VP da CVM, dizem a origem (F2A-3, F2A-36, F2A-44).

    LPA: o divulgado ou o recalculado da classe (`dados['lpa_cvm']`), mesmo sem a Composição
    do Capital (escala indeterminada). VPA: o PL dos controladores ÷ as ações do documento.
    """
    texto = PROVENIENCIA_DERIVADA[campo]
    multiplo = {"lpa": "pl", "vpa": "pvp"}.get(campo)
    fonte = ((dados.get("field_provenance") or {}).get(multiplo) or {}).get(
        "provenance"
    ) or {}
    if not multiplo or fonte.get("source") != "CVM":
        return texto
    acoes = dados.get("acoes_cvm")
    if campo == "lpa":
        lpa_cvm = dados.get("lpa_cvm")
        return (
            f"{texto}; P/L da CVM: {_texto_lpa_cvm(lpa_cvm, acoes)}"
            if lpa_cvm
            else texto
        )
    if not acoes:
        return texto
    return f"{texto}; P/VP da CVM: PL dos controladores ÷ {_texto_acoes(acoes)}"


def _texto_referencia(referencia: dict[str, Any]) -> str:
    """Regra do índice oficial (F2A-19); com correção, o código veio da tabela, não da fonte."""
    texto = f"{referencia.get('regra')} (índice de {referencia.get('gerado_em')})"
    correcao = referencia.get("correcao")
    if correcao and correcao.get("campo") == "especie":
        # F2B-13: a correção de espécie mantém o código e troca a espécie do FCA.
        texto += (
            f"; espécie da tabela de correções, não do arquivo da fonte: "
            f"{correcao.get('valor')} para {correcao.get('ticker')} "
            f"(evidência: {correcao.get('arquivo')}, {correcao.get('coluna')}, "
            f"{correcao.get('data')})"
        )
    elif correcao:
        texto += (
            f"; código da tabela de correções, não do arquivo da fonte: "
            f"{correcao.get('codigo_na_fonte')} → {correcao.get('ticker')} "
            f"(evidência: {correcao.get('arquivo')}, {correcao.get('coluna')}, "
            f"{correcao.get('data')})"
        )
    return texto


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


def _texto_liquidez(liquidez: dict[str, Any]) -> str:
    ausentes = liquidez.get("meses_ausentes") or []
    lacuna = f"; meses ausentes na coleta: {', '.join(ausentes)}" if ausentes else ""
    if "abstencao" in liquidez:
        return f"não calculada: {liquidez['abstencao']}{lacuna}"
    partes = [
        f"{n} pregões{' (incompleta)' if j['incompleta'] else ''}: volume mediano "
        f"R$ {_numero(j['volume_mediano'])}/dia, negócios {_numero(j['negocios_mediana'], 1)}/dia, "
        f"presença {_numero(100 * j['presenca'], 1)}%"
        for n, j in liquidez["janelas"].items()
    ]
    return f"{'; '.join(partes)}; até {liquidez['data_final']} ({liquidez['fonte']}){lacuna}"


def _texto_rendimento_fii(medida: dict[str, Any], dy_cascata: Any) -> str:
    if "abstencao" in medida:
        return f"não calculado: {medida['abstencao']}"
    cascata = (
        f"{_numero(dy_cascata * 100)}%"
        if isinstance(dy_cascata, (int, float)) and not isinstance(dy_cascata, bool)
        else "n/d"
    )
    return (
        f"DY de 12 meses {_numero(medida['dy'] * 100)}% pelo Informe (até {medida['mes_final']}, "
        f"rendimento de R$ {_numero(medida['rendimento_12m'])} por cota, sobre o "
        f"{medida['base']}) contra {cascata} da cascata"
    )


def construir_contexto(dados, eh_fii, hoje, motor_acoes, motor_fii) -> dict[str, Any]:
    """Roda o motor da V1 sobre `dados`, capturando o detalhe de cada método."""
    instancias = _instancias(eh_fii)
    registros: list = []
    with _capturar(instancias, registros):
        analise = motor_fii.analisar(dados) if eh_fii else motor_acoes.processar(dados)
    if analise is None:
        raise ValueError("dados insuficientes para a análise")

    por_instancia = {id(r[0]): r for r in registros}
    fora_do_escopo = (
        analise.get("recomendacao") == modulo_valuation.ROTULO_FORA_DO_ESCOPO
    )
    if fora_do_escopo:
        # F2A-29: classe fora do escopo dos métodos de ação; nenhum número no lugar.
        motivo_ausente = analise["riscos"][0]
    elif analise.get("perfil") == "DISTRESSED":
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
    descartes_roe = (dados.get("proveniencia") or {}).get("roe_descartes") or []
    for i in insumos:
        if i["campo"] == "roe":
            i["proveniencia"] += (
                "; guarda de fronteira (F2A-30): ROE não finito ou acima de 2 é descartado"
            )
            for descarte in descartes_roe:
                i["proveniencia"] += (
                    f"; descartado de {descarte['fonte']}: {descarte['motivo']}"
                )
    alavancagem = dados.get("alavancagem_cvm") or {}
    for i in insumos:
        if i["campo"] != "divida_liq_ebitda":
            continue
        if alavancagem.get("regime"):
            i["proveniencia"] += f"; regime da dívida: {alavancagem['regime']}"
        valor = dados.get("divida_liq_ebitda")
        if not isinstance(valor, (int, float)) or not math.isfinite(valor):
            motivo = (alavancagem.get("motivos") or {}).get(
                "divida_liq_ebitda", "sem dado na cascata"
            )
            i["proveniencia"] += (
                f"; alavancagem não avaliada ({motivo}): o motor não aplica a penalidade"
            )
    if eh_fii and not dados.get("pvp"):
        for i in insumos:
            if i["campo"] == "pvp":
                i["proveniencia"] += (
                    "; ausente: a lente de P/VP se abstém e não pontua (F2A-11)"
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
                    else _proveniencia_derivada(campo, dados)
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

    flags = ("dados_parciais", "dados_cache", "dados_manual", "fundamentos_incompletos")
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

    referencia = dados.get("referencia_oficial")
    if referencia:
        fontes.append(("Referência oficial", _texto_referencia(referencia)))
    serie = dados.get("serie_cvm")
    if serie:
        anos = (
            ", ".join(str(e["exercicio"]) for e in serie.get("exercicios") or [])
            or "nenhum"
        )
        fontes.append(
            (
                "Série da CVM (F2A-7, ainda sem uso nos métodos)",
                f"exercícios: {anos}; proventos por {serie.get('proventos_base')}",
            )
        )
    liquidez = dados.get("liquidez")
    if liquidez:
        fontes.append(
            ("Liquidez (F2A-26, ainda sem uso nos métodos)", _texto_liquidez(liquidez))
        )
    rendimento = dados.get("rendimento_fii_cvm")
    if rendimento:
        fontes.append(
            (
                "Rendimento do FII pelo Informe (F2B-28, ainda sem uso nos métodos)",
                _texto_rendimento_fii(rendimento, dados.get("dy")),
            )
        )
    ttm = dados.get("ttm_cvm")
    if ttm:
        fontes.append(
            (
                "Últimos doze meses da CVM",
                f"não calculado: {ttm['abstencao']}"
                if "abstencao" in ttm
                else f"{ttm['inicio']} a {ttm['fim']}; proventos por {ttm.get('proventos_base')}",
            )
        )

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
    if fora_do_escopo:
        sintese = [("Abstenção do motor", motivo_ausente)]

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
    return ticker_b3.validar(texto)  # F2A-12: a mesma lista permitida das fronteiras


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
