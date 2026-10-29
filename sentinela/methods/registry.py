"""Registro dos métodos de valuation: catálogo e changelog.

Os métodos extraídos da V1 mantêm seu histórico no changelog. Desde o F2B-4, o contrato
aplica o escopo de todos (classe oficial e, em STOCK/UNIT, o modelo do BPP consolidado);
a lente Bancos fica sem consumidor nos motores até o F2B-32.
"""

from __future__ import annotations

from dataclasses import dataclass

from sentinela.domain.enums import AssetType, Regime
from sentinela.methods.bancos import Bancos
from sentinela.methods.base import ValuationMethod
from sentinela.methods.bazin import Bazin
from sentinela.methods.fii_nav import FiiNav
from sentinela.methods.fii_yield import FiiYield
from sentinela.methods.gordon import Gordon
from sentinela.methods.graham import Graham
from sentinela.methods.lynch import Lynch
from sentinela.methods.qualidade import Qualidade

METODOS: tuple[ValuationMethod, ...] = (
    Graham(),
    Bazin(),
    Lynch(),
    Gordon(),
    FiiYield(),
    FiiNav(),
    Bancos(),
)

# F2C-2: quadros sem valor escalar não integram mediana/contrato de valuation.
QUADROS_DESCRITIVOS = (Qualidade(),)

DESCRICAO_1_0_0 = "comportamento da V1, extraído na Fase 1, sem mudança de número"


@dataclass(frozen=True, slots=True)
class Mudanca:
    version: str
    descricao: str


@dataclass(frozen=True, slots=True)
class Entrada:
    nome: str
    version: str
    regime: Regime
    requires: tuple[str, ...]
    assumptions: tuple[str, ...]
    applies_to: frozenset[AssetType]


CHANGELOG: dict[str, tuple[Mudanca, ...]] = {
    m.nome: (Mudanca("1.0.0", DESCRICAO_1_0_0),) for m in METODOS
}
CHANGELOG["Gordon"] += (
    Mudanca(
        "1.1.0",
        "com LPA não positivo, abstém-se; sai o payout de 50% do fallback da V1",
    ),
)
CHANGELOG["Gordon"] += (
    Mudanca(
        "2.0.0",
        "ficha Gordon1.1: desconto real, DVA dos controladores, ROE sobre PL inicial, Fisher antes do teto PIB; saem Selic, mínimos de DY/ROE e truncamento do payout",
    ),
)
CHANGELOG["Bazin"] += (
    Mudanca(
        "1.0.1",
        "motivo da abstenção (DY não confiável antes do mínimo); nenhum número muda",
    ),
    Mudanca(
        "2.0.0",
        "ficha Bazin 1.0: critério fixo de 6% sobre o DY bruto de 12 meses da relação B3; saem a Selic e o piso; aviso de prejuízo",
    ),
)
CHANGELOG["Graham"] += (
    Mudanca("1.1.0", "com VPA não positivo, abstém-se antes da raiz"),
)
CHANGELOG["Rendimento do FII"] += (
    Mudanca(
        "2.0.0",
        "ficha FII 1.1: preço justo pelo rendimento de 12 meses do Informe sobre NTN-B real + spread calibrado dos tijolos, crescimento real zero; sai a Selic líquida; nome anterior: Bazin FII",
    ),
)
CHANGELOG["P/VP do FII"] += (
    Mudanca(
        "1.1.0", "com P/VP não positivo, abstém-se em vez de classificar como desconto"
    ),
)

CHANGELOG["Bancos"] = (
    Mudanca(
        "1.0.0",
        "ficha bancos1.1: lente nova de P/VP justificado em regime real; sem consumidor no motor",
    ),
)

# F2B-4: escopo aplicado pelo contrato, antes dos insumos; nenhuma fórmula muda.
_ESCOPO_EMPRESA = "F2B-4: aplica o escopo (STOCK/UNIT, modelo empresa pelo BPP consolidado); sem classe ou modelo, abstém-se"
_ESCOPO_FII = "F2B-4: aplica o escopo (classe oficial FII, sem BPP de companhia); sem classe, abstém-se"
for _nome, _versao in (
    ("Graham", "1.2.0"),
    ("Bazin", "2.1.0"),
    ("Lynch", "1.1.0"),
    ("Gordon", "2.1.0"),
):
    CHANGELOG[_nome] += (Mudanca(_versao, _ESCOPO_EMPRESA),)
CHANGELOG["Rendimento do FII"] += (Mudanca("2.1.0", _ESCOPO_FII),)
CHANGELOG["P/VP do FII"] += (Mudanca("1.2.0", _ESCOPO_FII),)
CHANGELOG["Bancos"] += (
    Mudanca(
        "1.1.0",
        "F2B-4: classe e modelo conferidos pelo contrato antes dos insumos; sem classe ou modelo, motivo de escopo em vez de insumo ausente",
    ),
)


CHANGELOG["Graham"] += (
    Mudanca(
        "2.0.0",
        "ficha2.0aprovada28/10: média de cinco exercícios normalizada por IPCA, VPA final; retirados piso e guardas de múltiplos",
    ),
)
CHANGELOG["Lynch"] += (
    Mudanca(
        "2.0.0",
        "ficha2.0aprovada28/10: CAGR de cinco observações/quatro intervalos, m1, teto g25%, sem teto PL, payout contextual",
    ),
)

for _nome in ("Graham", "Lynch"):
    CHANGELOG[_nome] += (
        Mudanca(
            "2.1.0",
            "ficha2.1: base documental por razão(0,9;1,1) ou fator B3; reorganização apenas aviso, detecção na Fase3",
        ),
    )


def validar(
    metodos: tuple[ValuationMethod, ...], changelog: dict[str, tuple[Mudanca, ...]]
) -> None:
    nomes = [m.nome for m in metodos]
    if len(nomes) != len(set(nomes)):
        raise ValueError("nome de método repetido no registro")
    for m in metodos:
        historico = changelog.get(m.nome)
        if not historico or historico[-1].version != m.version:
            raise ValueError(f"changelog de {m.nome} não termina na versão {m.version}")
    if set(changelog) != set(nomes):
        raise ValueError("changelog com método que não está no registro")


validar(METODOS, CHANGELOG)


def entradas() -> tuple[Entrada, ...]:
    return tuple(
        Entrada(m.nome, m.version, m.regime, m.requires, m.assumptions, m.applies_to)
        for m in METODOS
    )


def obter(nome: str) -> ValuationMethod:
    for m in METODOS:
        if m.nome == nome:
            return m
    raise KeyError(nome)
