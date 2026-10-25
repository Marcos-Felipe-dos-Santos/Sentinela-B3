"""Relatório de qualidade de dados de ativos financeiros (análise heurística).

Nota sobre validacao_cruzada(): a comparação ideal seria fonte-a-fonte
(CVM={x} vs Yahoo={y}), mas market_engine.py não preserva valores pré-merge.
Os checks implementados são verificações de consistência entre campos derivados
(e.g., preco/lpa vs pl declarado), que detectam os mesmos bugs práticos.
Para comparação direta por fonte, seria necessário guardar _raw_source_values
no market_engine — fora do escopo desta sessão.

Mapeamento de confiança usa lowercase para fontes (alinha com market_engine.py).
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_CAMPOS_ESPERADOS: list[str] = [
    "preco_atual",
    "dy",
    "pl",
    "pvp",
    "roe",
    "lpa",
    "vpa",
    "divida_liq_ebitda",  # F2A-8: só a CVM, pela dívida financeira líquida ÷ EBITDA.
    "margem_liquida",
    "receita_liquida",
]

# Campos que CVMProvider preenche diretamente quando cvm_disponivel=True.
_CVM_CAMPOS: frozenset[str] = frozenset({
    "roe",
    "margem_liquida",
    "receita_liquida",
    "lpa",   # lucro_liquido / shares — requer sharesOutstanding do yfinance
    "vpa",   # patrimonio_liquido / shares — requer sharesOutstanding do yfinance
    "divida_liq_ebitda",  # F2A-8: dívida financeira líquida ÷ EBITDA (pós-IFRS 16)
})

# Normaliza aliases usados em fonte_fundamentos (de market_engine.py SOURCE_ALIASES).
_ALIAS: dict[str, str] = {
    "yfinance_partial":   "yfinance",
    "fundamentals_cache": "cache",
    "manual_fii":         "manual",
}

# Confiança por fonte (0–100). Reflete qualidade relativa da fonte de dados.
_FONTE_CONFIANCA: dict[str, int] = {
    "CVM":         100,
    "brapi":        80,
    "yfinance":     60,
    "manual":       20,
    "cache":        30,
    "unknown":      10,
}

_BADGE_CVM:     str = "🟢 Dados CVM"
_BADGE_PARCIAL: str = "🟡 Dados parciais"
_BADGE_SEM_CVM: str = "🔴 Sem CVM"

# Completude mínima (%) para badge amarelo em vez de vermelho. Limite arbitrário.
_BADGE_PARCIAL_MIN_PCT: int = 40


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_fonte(fonte: str) -> str:
    """Normaliza aliases de fonte para o nome canônico."""
    return _ALIAS.get(str(fonte).strip(), str(fonte).strip())


def _best_fonte(fonte_str: str) -> str:
    """Retorna a fonte de maior confiança em 'CVM+brapi' ou string simples."""
    fontes = [_normalize_fonte(f) for f in fonte_str.split("+") if f.strip()]
    if not fontes:
        return "unknown"
    return max(fontes, key=lambda f: _FONTE_CONFIANCA.get(f, 0))


def _safe_float(v) -> float | None:
    """Converte para float, retorna None se inválido ou NaN."""
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _is_present(v) -> bool:
    """True se o valor existe e é numericamente válido (inclui 0.0)."""
    if v is None:
        return False
    f = _safe_float(v)
    if f is not None:
        return True
    # Fallback para strings não-numéricas
    s = str(v).strip()
    return bool(s) and s.lower() not in ("nan", "none", "")


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

_LIMIAR_ACOES = 0.05  # checkpoint da Fase 0, seção 4, item 1
_LIMIAR_LPA = 0.10  # o mesmo dos checks 2 e 3
_LIMIAR_PVP_FII = 0.10  # F2B-16: o mesmo dos checks 2 e 3 ([AUDITORIA], 18/10/2026)
_FONTES_DE_MERCADO = ("yfinance", "brapi")
_FOLGA = 1e-9


def _numero_br(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


class DataQualityReport:
    def __init__(self, dados: dict):
        # F2A-6 (E-3): com o retrato da cascata (`valores_coletados`), os campos coletados
        # são avaliados como a cascata os entregou, e não como os motores os sobrescreveram
        # (`app.py`: `dados.update(analise)`). Sem retrato, valem os valores de `dados`.
        dados = dados or {}
        retrato = dados.get("valores_coletados")
        self.dados = {**dados, **retrato} if isinstance(retrato, dict) else dados

    # ── API pública ────────────────────────────────────────────────────────

    def completude(self) -> dict:
        """Retorna completude por campo e métricas agregadas.

        Cada campo retorna:
            presente (bool), fonte (str), confianca (int 0–100)

        Métricas agregadas:
            completude_pct: % de campos presentes (0–100)
            score_confianca: confiança média normalizada sobre todos os campos (0–100)
        """
        d = self.dados
        fonte_fund = str(d.get("fonte_fundamentos") or "")
        cvm_ok = bool(d.get("cvm_disponivel"))
        field_prov: dict = d.get("field_provenance") or {}
        fonte_base = _best_fonte(fonte_fund) if fonte_fund else "unknown"
        classe = str(d.get("classe_ativo") or "").strip().upper()
        # F2B-63 (BUG-2B-06, reaberto): o modelo que a cascata grava (F2B-4).
        modelo = str(d.get("modelo_bpp") or "").strip().lower()
        limitacoes = []
        if classe == "FII":
            esperados = ["preco_atual", "dy", "pvp", "vpa"]
        elif modelo == "banco":
            esperados = [c for c in _CAMPOS_ESPERADOS if c not in (
                "receita_liquida", "margem_liquida", "divida_liq_ebitda"
            )]
        else:
            esperados = _CAMPOS_ESPERADOS
            if modelo != "empresa":
                limitacoes.append(
                    "modelo não demonstrado: percentual dos campos gerais, "
                    "sem certificação de completude do modelo"
                )

        campos: dict[str, dict] = {}
        for campo in esperados:
            valor = d.get(campo)
            presente = _is_present(valor)

            # Fonte: preferir field_provenance (per-field), depois inferir
            if campo in field_prov:
                raw = str(field_prov[campo].get("provenance", {}).get("source") or "unknown")
                fonte = _normalize_fonte(raw)
            elif presente and cvm_ok and campo in _CVM_CAMPOS:
                fonte = "CVM"
            elif presente:
                # Não creditar CVM a campos que ela não fornece (fora de _CVM_CAMPOS, ex: pvp)
                fb = fonte_base if fonte_base != "unknown" else "unknown"
                fonte = fb if not (fb == "CVM" and campo not in _CVM_CAMPOS) else "unknown"
            else:
                fonte = "—"

            confianca = _FONTE_CONFIANCA.get(fonte, 10) if presente else 0
            campos[campo] = {"presente": presente, "fonte": fonte, "confianca": confianca}

        n_total = len(esperados)
        n_presente = sum(1 for v in campos.values() if v["presente"])
        completude_pct = round(n_presente / n_total * 100)

        # Score normalizado: soma das confianças / (n_total × 100) × 100
        score_confianca = round(
            sum(v["confianca"] for v in campos.values()) / (n_total * 100) * 100
        )

        return {
            "campos": campos,
            "completude_pct": completude_pct,
            "score_confianca": score_confianca,
            "limitacoes": limitacoes,
            "completude_do_modelo_determinada": not limitacoes,
        }

    def validacao_cruzada(self) -> list[str]:
        """Verifica consistência entre campos derivados. Retorna lista de alertas.

        Checks implementados (não comparação direta entre fontes — ver docstring do módulo):
        1. DY > 25%: possível bug Yahoo (retornou como % em vez de decimal)
        2. P/L derivado (preço/LPA) diverge > 10% do P/L declarado
        3. P/VP derivado (preço/VPA) diverge > 10% do P/VP declarado
        4. ROE > 15% com margem_liquida negativa: inconsistência provável de fonte
        """
        alertas: list[str] = []
        d = self.dados

        preco = _safe_float(d.get("preco_atual"))
        dy = _safe_float(d.get("dy"))
        pl = _safe_float(d.get("pl"))
        pvp = _safe_float(d.get("pvp"))
        lpa = _safe_float(d.get("lpa"))
        vpa = _safe_float(d.get("vpa"))
        roe = _safe_float(d.get("roe"))
        margem = _safe_float(d.get("margem_liquida"))

        # 1. DY > 25%: Yahoo Finance às vezes retorna percentual em vez de decimal
        if dy is not None and dy > 0.25:
            alertas.append(
                f"dy={dy:.4f} ({dy * 100:.1f}%) improvável — "
                f"Yahoo possivelmente retornou como % (valor real estimado: {dy / 100:.4f})"
            )

        # 2. P/L derivado de preço/LPA vs P/L declarado (só entre fontes diferentes: F2A-5)
        if (
            preco and lpa and abs(lpa) > 0.001 and pl is not None and pl > 0
            and not self._mesma_fonte("pl", "lpa")
        ):
            pl_derivado = preco / lpa
            if pl_derivado > 0:
                divergencia = abs(pl_derivado - pl) / pl
                if divergencia > 0.10:
                    alertas.append(
                        f"pl={pl:.1f} inconsistente com preço/lpa derivado={pl_derivado:.1f} "
                        f"(divergência {divergencia:.0%})"
                    )

        # 3. P/VP derivado de preço/VPA vs P/VP declarado (só entre fontes diferentes: F2A-5)
        if (
            preco and vpa and abs(vpa) > 0.001 and pvp is not None and pvp > 0
            and not self._mesma_fonte("pvp", "vpa")
        ):
            pvp_derivado = preco / vpa
            divergencia = abs(pvp_derivado - pvp) / pvp
            if divergencia > 0.10:
                alertas.append(
                    f"pvp={pvp:.2f} inconsistente com preço/vpa derivado={pvp_derivado:.2f} "
                    f"(divergência {divergencia:.0%})"
                )

        # 4. ROE positivo alto com margem negativa (possível inconsistência de fonte)
        if roe is not None and margem is not None:
            if roe > 0.15 and margem < 0:
                alertas.append(
                    f"roe={roe:.1%} positivo com margem_liquida={margem:.1%} negativa — "
                    "possível inconsistência de fonte"
                )

        alertas += self._alertas_fontes_independentes(lpa)
        alertas += self._alertas_pvp_do_fii()
        return alertas

    def _mesma_fonte(self, multiplo: str, por_acao: str) -> bool:
        """O múltiplo e o valor por ação vieram da mesma fonte? Então a comparação é identidade.

        A fonte do múltiplo vem de `field_provenance`; a do valor por ação, de
        `valores_por_fonte` (a fonte que entregou o valor que ficou). Sem esses registros
        (chamadas antigas), não se sabe, e a comparação roda como antes.
        """
        d = self.dados
        prov = ((d.get("field_provenance") or {}).get(multiplo) or {}).get("provenance") or {}
        fonte_multiplo = prov.get("source")
        valor = _safe_float(d.get(por_acao))
        if not fonte_multiplo or valor is None:
            return False
        entregue = (d.get("valores_por_fonte") or {}).get(fonte_multiplo) or {}
        do_mesmo = _safe_float(entregue.get(por_acao))
        return do_mesmo is not None and abs(do_mesmo - valor) <= _FOLGA * max(1.0, abs(valor))

    def _alertas_pvp_do_fii(self) -> list[str]:
        """P/VP do Informe Mensal (CVM) × P/VP de cada fonte de mercado (F2B-16; BUG-2A-12).

        O P/VP da CVM é preço ÷ VPA do próprio Informe, e a checagem 3 é identidade; a
        conferência independente é contra o P/VP que o yfinance ou a brapi entregaram.
        """
        por_fonte = self.dados.get("valores_por_fonte") or {}
        cvm = _safe_float((por_fonte.get("CVM") or {}).get("pvp"))
        if not self.dados.get("cvm_fii_dt_referencia") or not cvm or cvm <= 0:
            return []
        alertas: list[str] = []
        for fonte in _FONTES_DE_MERCADO:
            mercado = _safe_float((por_fonte.get(fonte) or {}).get("pvp"))
            if mercado is None or mercado <= 0:
                continue
            divergencia = abs(mercado - cvm) / cvm
            if divergencia > _LIMIAR_PVP_FII + _FOLGA:
                alertas.append(
                    f"P/VP da CVM {_numero_br(cvm)} × P/VP do {fonte} {_numero_br(mercado)}: "
                    f"divergência {divergencia:.0%}"
                )
        return alertas

    def _alertas_fontes_independentes(self, lpa: float | None) -> list[str]:
        """Ações da CVM × yfinance e LPA recalculado × LPA básico divulgado (F2A-5, E-2)."""
        alertas: list[str] = []
        d = self.dados
        divergencia = d.get("divergencia_acoes") or {}
        diferenca = _safe_float(divergencia.get("diferenca"))
        if diferenca is not None and abs(diferenca) > _LIMIAR_ACOES + _FOLGA:
            alertas.append(
                f"ações {divergencia.get('especie')}: CVM {divergencia.get('acoes_cvm'):,.0f} × "
                f"yfinance {divergencia.get('acoes_yfinance'):,.0f} (divergência {diferenca:+.0%})"
            )
        acoes_cvm = d.get("acoes_cvm") or {}
        comparado = acoes_cvm.get("lpa_divulgado_comparado") or {}
        divulgado = _safe_float(comparado.get("valor"))
        papel = _safe_float(acoes_cvm.get("acoes_por_papel")) or 1.0
        if "lpa_recalculado" in acoes_cvm:
            # F2A-36 (ficha, 7.3): o LPA dos métodos já é o divulgado; confere-se o recalculado.
            lpa = _safe_float(acoes_cvm["lpa_recalculado"])
        if lpa is not None and divulgado:
            por_acao = lpa / papel
            divergencia_lpa = abs(por_acao - divulgado) / abs(divulgado)
            if divergencia_lpa > _LIMIAR_LPA + _FOLGA:
                alertas.append(
                    f"LPA {_numero_br(por_acao)} × LPA básico divulgado "
                    f"{_numero_br(divulgado)} ({comparado.get('especie')}): divergência "
                    f"{divergencia_lpa:.0%}. O divulgado usa a média ponderada de ações do "
                    "exercício; o calculado, as ações do fim do período"
                )
        return alertas

    def badge(self) -> str:
        """Retorna badge de qualidade: 🟢 Dados CVM / 🟡 Dados parciais / 🔴 Sem CVM."""
        if bool(self.dados.get("cvm_disponivel")):
            return _BADGE_CVM
        comp = self.completude()
        if comp["completude_pct"] >= _BADGE_PARCIAL_MIN_PCT:
            return _BADGE_PARCIAL
        return _BADGE_SEM_CVM
