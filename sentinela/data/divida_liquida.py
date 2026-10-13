"""Alavancagem pela dívida financeira líquida (F2A-8; F-12, armadilha 17).

Funções puras: sem rede, sem relógio, sem `config`. As contas chegam lidas pela tabela de
contas (`contas_cvm`, ADR-0003 D20), do último DFP consolidado.

- **Dívida financeira líquida** (regime pós-IFRS 16, decisão de 5/10/2026): empréstimos e
  financiamentos circulantes (2.01.04) e não circulantes (2.02.01) − caixa e equivalentes
  (1.01.01) − aplicações financeiras (1.01.02). Os dois grupos já trazem, no 3º nível, as
  debêntures (2.0x.0x.02) e o passivo de arrendamento (2.0x.0x.03); usa-se o total do grupo,
  porque em parte das companhias as subcontas vêm zeradas com o total preenchido (F2A-16).
- **EBITDA** = EBIT (3.05) + depreciação, amortização e exaustão da DVA (7.04.01). Na DVA a
  conta é uma retenção e vem negativa; entra em módulo.
- `divida_liq_ebitda` = dívida líquida ÷ EBITDA; `div_liq_patrimonio` = dívida líquida ÷ PL.

Sem insumo, cada medida se abstém com o motivo; nunca devolve número no lugar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sentinela.data.contas_cvm import Abstencao, Leitura

REGIME = "pós-IFRS 16, arrendamento incluído na dívida"
CAMPOS_DA_DIVIDA = (
    "emprestimos_circulante",
    "emprestimos_nao_circulante",
    "caixa",
    "aplicacoes",
)
MOTIVO_MODELO = "banco ou seguradora: a medida de empresa não financeira não se aplica"
MOTIVO_EBITDA = "EBITDA ≤ 0"
MOTIVO_PL = "PL ≤ 0"
MOTIVO_SEM_PL = "PL ausente no documento"


@dataclass(frozen=True)
class Alavancagem:
    divida_liquida: float | None
    ebitda: float | None
    divida_liq_ebitda: float | None
    div_liq_patrimonio: float | None
    motivos: dict[str, str] = field(default_factory=dict)
    regime: str = REGIME

    def para_dict(self) -> dict:
        return {
            "divida_liquida": self.divida_liquida,
            "ebitda": self.ebitda,
            "divida_liq_ebitda": self.divida_liq_ebitda,
            "div_liq_patrimonio": self.div_liq_patrimonio,
            "motivos": dict(self.motivos),
            "regime": self.regime,
        }


def _motivo_da_conta(campo: str, leitura: Abstencao) -> str:
    detalhe = f": {leitura.detalhe}" if leitura.detalhe else ""
    return f"conta {campo} sem valor ({leitura.motivo}{detalhe})"


def medir(
    *,
    modelo: str,
    contas: dict[str, Leitura | Abstencao],
    ebit: Leitura | Abstencao,
    depreciacao: Leitura | Abstencao,
    pl: float | None,
) -> Alavancagem:
    """Dívida líquida, EBITDA e as duas razões, ou o motivo de cada abstenção.

    `contas`: as leituras de `CAMPOS_DA_DIVIDA`. Banco ou seguradora (modelo do setor, F2A-2)
    não recebe a medida.
    """
    if modelo != "empresa":
        motivos = {
            "divida_liq_ebitda": MOTIVO_MODELO,
            "div_liq_patrimonio": MOTIVO_MODELO,
        }
        return Alavancagem(None, None, None, None, motivos)

    motivos: dict[str, str] = {}
    faltando = [
        _motivo_da_conta(campo, contas[campo])
        for campo in CAMPOS_DA_DIVIDA
        if not isinstance(contas.get(campo), Leitura)
    ]
    divida = None
    if faltando:
        motivos["divida_liq_ebitda"] = motivos["div_liq_patrimonio"] = "; ".join(
            faltando
        )
    else:
        divida = (
            contas["emprestimos_circulante"].valor
            + contas["emprestimos_nao_circulante"].valor
            - contas["caixa"].valor
            - contas["aplicacoes"].valor
        )

    ebitda = None
    sem_ebitda = [
        _motivo_da_conta(campo, leitura)
        for campo, leitura in (("ebit", ebit), ("depreciacao_amortizacao", depreciacao))
        if not isinstance(leitura, Leitura)
    ]
    if sem_ebitda:
        motivos.setdefault("divida_liq_ebitda", "; ".join(sem_ebitda))
    else:
        ebitda = ebit.valor + abs(depreciacao.valor)

    divida_liq_ebitda = None
    if divida is not None and ebitda is not None:
        if ebitda <= 0:
            motivos["divida_liq_ebitda"] = MOTIVO_EBITDA
        else:
            divida_liq_ebitda = divida / ebitda

    div_liq_patrimonio = None
    if divida is not None:
        if pl is None:
            motivos["div_liq_patrimonio"] = MOTIVO_SEM_PL
        elif pl <= 0:
            motivos["div_liq_patrimonio"] = MOTIVO_PL
        else:
            div_liq_patrimonio = divida / pl

    return Alavancagem(divida, ebitda, divida_liq_ebitda, div_liq_patrimonio, motivos)
