"""Contraprova D27 do F2B-54 (escala da composição recente): a mesma entrada no pai e no item.

Uso: python f2b54_escala.py <raiz da worktree>, no commit pai (5c9ed55) e no do item (7e1dfb4).
Mesmo cenário dos testes `tests/test_gordon_cvm.py::test_escala_da_composicao_recente_*`
e `tests/test_gordon_composicao_recente.py::test_escala_do_documento_recente_pela_regra_da_dfp`,
pela API que existia: a falha esperada é econômica (razão errada, compatível onde não há
prova), não de interface.
"""

import inspect
import sys

sys.path.insert(0, sys.argv[1])
from sentinela.data import gordon_cvm
from sentinela.data.acoes_cvm import Composicao
from sentinela.domain.units import Escala


def comp(total, dt):
    return Composicao(
        on=total,
        pn=0,
        tesouraria_on=0,
        tesouraria_pn=0,
        tesouraria_total=0,
        dt_refer=dt,
        versao="1",
    )


assinatura = inspect.signature(gordon_cvm.compatibilidade_base)
ITEM = "escala_recente" in assinatura.parameters
print("código:", "item (com escala_recente)" if ITEM else "pai (sem escala_recente)")


def compat(base, recente, escala, escala_recente):
    extra = {"escala_recente": escala_recente} if ITEM else {}
    return gordon_cvm.compatibilidade_base(
        base,
        recente,
        escala=escala,
        especie="ON",
        eh_unit=False,
        acoes_por_unit=None,
        shares_outstanding=None,
        **extra,
    )


falhas = 0
# 1. DFP em MIL (1.000 mil) e ITR em UNIDADE (1.010.000): a mesma base, razão 1,01.
for esc_dfp, tot_dfp, esc_rec, tot_rec in (
    ("MIL", 1000, "UNIDADE", 1_010_000),
    ("UNIDADE", 1_000_000, "MIL", 1010),
):
    r = compat(
        comp(tot_dfp, "2025-12-31"),
        comp(tot_rec, "2026-06-30"),
        Escala[esc_dfp],
        Escala[esc_rec],
    )
    ok = r.get("compativel") is True and abs((r.get("razao") or 0) - 1.01) < 1e-9
    falhas += not ok
    print(
        f"escala DFP {esc_dfp}: compativel={r.get('compativel')} razao={r.get('razao')}"
        f" motivo={r.get('motivo')} -> {'PASS' if ok else 'FAIL (econômica)'}"
    )
# 2. Escala do documento recente indeterminada (no item, `escala_recente=None`; o pai não tem
# o parâmetro e decide como se fosse a da DFP, a armadilha 10).
r = compat(comp(1000, "2025-12-31"), comp(1000, "2026-06-30"), Escala.UNIDADE, None)
ok = r.get("compativel") is False and "indeterminada" in str(r.get("motivo"))
falhas += not ok
print(
    f"escala recente indeterminada: compativel={r.get('compativel')} motivo={r.get('motivo')}"
    f" -> {'PASS' if ok else 'FAIL (econômica: compatível sem prova da escala)'}"
)
print("falhas:", falhas)
