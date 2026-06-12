"""Relatório de qualidade de dados de ativos financeiros (análise heurística).

Nota sobre validacao_cruzada(): a comparação ideal seria fonte-a-fonte
(CVM={x} vs Yahoo={y}), mas market_engine.py não preserva valores pré-merge.
Os checks implementados são verificações de consistência entre campos derivados
(e.g., preco/lpa vs pl declarado), que detectam os mesmos bugs práticos.
Para comparação direta por fonte, seria necessário guardar _raw_source_values
no market_engine — fora do escopo desta sessão.

Mapeamento de confiança usa lowercase para fontes (alinha com market_engine.py).
O spec original escreveu "Fundamentus" com maiúscula; o codebase usa "fundamentus".
"""
from __future__ import annotations

import math
from typing import Optional

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
    "divida_liq_ebitda",  # NÃO está em _CVM_CAMPOS: CVM só fornece div_liq_patrimonio (passivo/PL).
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
})

# Normaliza aliases usados em fonte_fundamentos (de market_engine.py SOURCE_ALIASES).
_ALIAS: dict[str, str] = {
    "yfinance_partial":   "yfinance",
    "fundamentals_cache": "fundamentus",
    "manual_fii":         "manual",
}

# Confiança por fonte (0–100). Reflete qualidade relativa da fonte de dados.
_FONTE_CONFIANCA: dict[str, int] = {
    "CVM":         100,
    "brapi":        80,
    "yfinance":     60,
    "fundamentus":  40,
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


def _safe_float(v) -> Optional[float]:
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

class DataQualityReport:
    def __init__(self, dados: dict):
        self.dados = dados or {}

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

        campos: dict[str, dict] = {}
        for campo in _CAMPOS_ESPERADOS:
            valor = d.get(campo)
            presente = _is_present(valor)

            # Fonte: preferir field_provenance (per-field), depois inferir
            if campo in field_prov:
                raw = str(field_prov[campo].get("provenance", {}).get("source") or "unknown")
                fonte = _normalize_fonte(raw)
            elif presente and cvm_ok and campo in _CVM_CAMPOS:
                fonte = "CVM"
            elif presente:
                # Não creditar CVM a campos que ela não fornece (ex: divida_liq_ebitda)
                fb = fonte_base if fonte_base != "unknown" else "unknown"
                fonte = fb if not (fb == "CVM" and campo not in _CVM_CAMPOS) else "unknown"
            else:
                fonte = "—"

            confianca = _FONTE_CONFIANCA.get(fonte, 10) if presente else 0
            campos[campo] = {"presente": presente, "fonte": fonte, "confianca": confianca}

        n_total = len(_CAMPOS_ESPERADOS)
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

        # 2. P/L derivado de preço/LPA vs P/L declarado
        if preco and lpa and abs(lpa) > 0.001 and pl is not None and pl > 0:
            pl_derivado = preco / lpa
            if pl_derivado > 0:
                divergencia = abs(pl_derivado - pl) / pl
                if divergencia > 0.10:
                    alertas.append(
                        f"pl={pl:.1f} inconsistente com preço/lpa derivado={pl_derivado:.1f} "
                        f"(divergência {divergencia:.0%})"
                    )

        # 3. P/VP derivado de preço/VPA vs P/VP declarado
        if preco and vpa and abs(vpa) > 0.001 and pvp is not None and pvp > 0:
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

        return alertas

    def badge(self) -> str:
        """Retorna badge de qualidade: 🟢 Dados CVM / 🟡 Dados parciais / 🔴 Sem CVM."""
        if bool(self.dados.get("cvm_disponivel")):
            return _BADGE_CVM
        comp = self.completude()
        if comp["completude_pct"] >= _BADGE_PARCIAL_MIN_PCT:
            return _BADGE_PARCIAL
        return _BADGE_SEM_CVM
