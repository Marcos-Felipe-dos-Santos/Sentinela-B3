"""
SENTINELA B3 — SCRIPT DE AUDITORIA INTERNA
============================================
Expõe tudo que a UI esconde: dados brutos do scraper, cada passo do cálculo
de valuation, o prompt exato enviado à IA, e o conteúdo real do banco.

Ao terminar, salva DOIS arquivos na mesma pasta:
  • auditoria_YYYYMMDD_HHMMSS.txt  — relatório legível (sem cores)
  • auditoria_YYYYMMDD_HHMMSS.json — dados estruturados para análise

Uso:
    python auditoria.py                  # audita PETR4, ITUB4, WEGE3
    python auditoria.py VALE3 BBAS3      # audita tickers específicos
    python auditoria.py --db-only        # só inspeciona o banco
    python auditoria.py --selic          # só testa a Selic
"""

import sys
import os
import re
import io
import json
import math
import sqlite3
from datetime import datetime

# ─── ANSI strip ───────────────────────────────────────────────────────────────
_ANSI = re.compile(r'\x1b\[[0-9;]*m')
def strip_ansi(s: str) -> str:
    return _ANSI.sub('', s)

# ─── Tee: imprime no terminal E captura em buffer limpo para arquivo ──────────
class _Tee:
    def __init__(self, stream):
        self._orig  = stream
        self._buf   = io.StringIO()

    def write(self, s):
        self._orig.write(s)
        self._buf.write(strip_ansi(s))

    def flush(self):
        self._orig.flush()

    def getvalue(self) -> str:
        return self._buf.getvalue()

# ─── cores no terminal ────────────────────────────────────────────────────────
GRN = "\033[32m"
RED = "\033[31m"
YLW = "\033[33m"
CYN = "\033[36m"
BLD = "\033[1m"
RST = "\033[0m"
ok   = lambda s: f"{GRN}✓ {s}{RST}"
err  = lambda s: f"{RED}✗ {s}{RST}"
warn = lambda s: f"{YLW}⚠ {s}{RST}"
hdr  = lambda s: f"\n{BLD}{CYN}{'═'*60}\n  {s}\n{'═'*60}{RST}"
sub  = lambda s: f"\n{BLD}── {s} ──{RST}"

DB_PATH = "sentinela_v6.db"

# ─── Relatório JSON (populado ao longo da execução) ───────────────────────────
_rel: dict = {
    "meta": {},
    "selic": {},
    "banco": {},
    "tickers": {}
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. SELIC
# ══════════════════════════════════════════════════════════════════════════════

def auditar_selic():
    print(hdr("1. TAXA SELIC"))
    import requests

    resultado = {}

    try:
        r = requests.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json",
            timeout=5
        )
        if r.status_code == 200:
            valor_raw = r.json()[0]['valor']
            selic_432 = float(valor_raw) / 100
            resultado['serie_432_raw']    = valor_raw
            resultado['serie_432_decimal'] = selic_432
            resultado['serie_432_status'] = 'OK'
            print(ok(f"Série 432 (meta Copom): {valor_raw}% a.a. → decimal: {selic_432:.4f}"))
        else:
            resultado['serie_432_status'] = f"HTTP {r.status_code}"
            print(err(f"Série 432: HTTP {r.status_code}"))
    except Exception as e:
        resultado['serie_432_status'] = str(e)
        print(err(f"Série 432 indisponível: {e}"))

    try:
        r2 = requests.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json",
            timeout=5
        )
        if r2.status_code == 200:
            valor_raw2 = r2.json()[0]['valor']
            selic_11 = float(valor_raw2) / 100
            resultado['serie_11_raw']    = valor_raw2
            resultado['serie_11_decimal'] = selic_11
            print(warn(f"Série 11 (taxa diária — BUG antigo): {valor_raw2}% ao dia → "
                       f"se fosse usada: {selic_11*100:.4f}% a.a. (ERRADO)"))
    except Exception as e:
        resultado['serie_11_status'] = str(e)

    print(sub("Impacto no Valuation"))
    exemplos = []
    for selic_val, label in [
        (resultado.get('serie_11_decimal', 0.0006), "BUGADA"),
        (resultado.get('serie_432_decimal', 0.15),  "CORRETA")
    ]:
        p = 42
        dy = 0.07
        bazin  = (dy * p) / (selic_val * 0.85)
        g_cr = 0.04
        k_cr = selic_val + 0.06
        gordon = (dy*p*(1+g_cr))/(k_cr-g_cr) if k_cr > g_cr else 0
        exemplos.append({"label": label, "selic": selic_val,
                         "bazin_EGIE3": round(bazin,2), "gordon_EGIE3": round(gordon,2)})
        print(f"  Selic {label} ({selic_val*100:.2f}%): Bazin(EGIE3)=R${bazin:.2f}, Gordon=R${gordon:.2f}")

    resultado['impacto_exemplos'] = exemplos
    _rel['selic'] = resultado


# ══════════════════════════════════════════════════════════════════════════════
# 2. DADOS BRUTOS DO SCRAPER
# ══════════════════════════════════════════════════════════════════════════════

def auditar_dados_scraper(ticker: str):
    print(hdr(f"2. DADOS BRUTOS — {ticker}"))

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from market_engine import MarketEngine
    except ImportError as e:
        print(err(f"Não foi possível importar market_engine: {e}"))
        return None

    market = MarketEngine()
    print(f"  Buscando dados de {ticker}...")
    dados = market.buscar_dados_ticker(ticker)

    if not dados:
        print(err("Nenhum dado retornado."))
        return None

    hist = dados.pop('historico', None)

    print(sub("Dados Fundamentalistas"))
    campos_importantes = ['ticker','preco_atual','pl','pvp','dy','roe','roic',
                          'margem_liquida','margem_bruta','div_liq_patrimonio',
                          'patrimonio_liquido','receita_liquida','lucro_liquido',
                          'quote_type','pl_confiavel']

    dados_json = {}
    for campo in campos_importantes:
        val = dados.get(campo)
        dados_json[campo] = val
        if val is not None:
            if campo == 'quote_type':
                # Classificação do ativo pelo Yahoo — chave para FII vs ação
                tipo_map = {
                    'MUTUALFUND': (ok,   'FII / Fundo Imobiliário → engine FII será usado'),
                    'EQUITY':     (ok,   'Ação/Unit → engine Valuation será usado'),
                    'ETF':        (warn, 'ETF → engine FII será usado (fallback)'),
                }
                fn_cor, desc = tipo_map.get(val, (warn, f'Tipo desconhecido: {val}'))
                print(f"  {campo:<25}: {fn_cor(f'{val} — {desc}')}")
            elif campo in ['dy','roe','roic','margem_liquida','margem_bruta'] and isinstance(val, float):
                # Avisar se DY parece estar em formato percentagem (não decimal)
                if campo == 'dy' and val > 0.5:
                    msg = (
                        f"{val} — FORMATO % (>50%)! Yahoo retornou em % "
                        "em vez de decimal. Valuation engine vai normalizar."
                    )
                    print(f"  {campo:<25}: {warn(msg)}")
                elif campo == 'dy' and val > 0.04:
                    msg = "Verificar: DY>4% sendo tratado como is_growth=False"
                    print(
                        f"  {campo:<25}: {val*100:.2f}%  "
                        f"(decimal: {val:.4f})  {warn(msg)}"
                    )
                else:
                    print(f"  {campo:<25}: {val*100:.2f}%  (decimal: {val:.4f})")
            elif campo == 'preco_atual':
                # Float64 artifact indica que o preço veio do Yahoo, não do Fundamentus
                preco_str = str(val)
                fonte = warn("Yahoo Finance (Fundamentus falhou)") if len(preco_str) > 10 else ok("Fundamentus")
                print(f"  {campo:<25}: R$ {val:.2f}  ← fonte: {fonte}")
            else:
                print(f"  {campo:<25}: {val}")
        else:
            print(f"  {campo:<25}: {warn('AUSENTE')}")

    extras = {k: v for k, v in dados.items() if k not in campos_importantes and v is not None}
    if extras:
        print(sub("Campos adicionais"))
        for k, v in extras.items():
            dados_json[k] = v
            print(f"  {k:<25}: {v}")

    hist_json = {}
    if hist is not None and not hist.empty:
        print(sub("Histórico"))
        print(f"  Período: {hist.index[0].date()} → {hist.index[-1].date()}")
        print(f"  Pregões: {len(hist)}")
        print(f"  Preço mín/máx 1 ano: R${hist['Close'].min():.2f} / R${hist['Close'].max():.2f}")
        print(f"  Preço atual (último Close): R${hist['Close'].iloc[-1]:.2f}")
        import numpy as np
        vol_anual = hist['Close'].pct_change().std() * (252**0.5)
        print(f"  Volatilidade anualizada: {vol_anual*100:.1f}%")
        hist_json = {
            "pregoes": len(hist),
            "inicio": str(hist.index[0].date()),
            "fim": str(hist.index[-1].date()),
            "preco_min_1a": round(float(hist['Close'].min()), 2),
            "preco_max_1a": round(float(hist['Close'].max()), 2),
            "preco_atual_close": round(float(hist['Close'].iloc[-1]), 2),
            "volatilidade_anual_pct": round(vol_anual * 100, 1),
        }
        dados['historico'] = hist
    else:
        print(warn("  Histórico indisponível."))

    if ticker not in _rel['tickers']:
        _rel['tickers'][ticker] = {}
    _rel['tickers'][ticker]['dados_scraper'] = dados_json
    _rel['tickers'][ticker]['historico']     = hist_json

    return dados


# ══════════════════════════════════════════════════════════════════════════════
# 3. VALUATION — CÁLCULO PASSO A PASSO
# ══════════════════════════════════════════════════════════════════════════════

def auditar_valuation(ticker: str, dados: dict):
    print(hdr(f"3. VALUATION PASSO A PASSO — {ticker}"))

    try:
        from config import get_selic_atual
    except ImportError:
        def get_selic_atual(): return 0.15

    p   = float(dados.get('preco_atual', 0) or 0)
    roe = float(dados.get('roe', 0) or 0)
    pl  = float(dados.get('pl',  0) or 0)
    pvp = float(dados.get('pvp', 0) or 0)
    selic = get_selic_atual()

    # Normalização DY — mesma lógica do valuation_engine (v14)
    dy_raw = float(dados.get('dy', 0) or 0)
    dy_confiavel = True

    if dy_raw > 1:
        dy = dy_raw / 100
        print(f"  {warn(f'DY={dy_raw:.4f} em % → normalizado para {dy:.4f} decimal')}")
    elif dy_raw > 0.25:
        msg = (
            f"DY={dy_raw:.4f} ({dy_raw*100:.1f}%) improvável "
            "→ dado suspeito (Yahoo bug) → desconsiderado"
        )
        print(f"  {err(msg)}")
        dy = 0.0
        dy_confiavel = False
    else:
        dy = dy_raw
        if dy_raw > 0 and dy_raw < 1:
            print(f"  {ok(f'DY={dy_raw:.4f} já em decimal = {dy_raw*100:.2f}%')}")

    print(f"\n  Inputs brutos (do scraper):")
    print(f"    DY bruto (scraper) : {dy_raw}  (confiável={dy_confiavel})")
    print(f"    Preço atual : R$ {p:.2f}")
    print(f"    P/L         : {pl:.2f}")
    print(f"    P/VP        : {pvp:.2f}")
    print(f"    DY (usado)  : {dy:.4f} = {dy*100:.2f}%")
    print(f"    ROE         : {roe*100:.2f}%")
    print(f"    Selic       : {selic*100:.2f}% a.a.")

    vpa = (p / pvp) if pvp > 0 else 0
    if dy_confiavel:
        is_growth = roe > 0.20 and dy < 0.04
    else:
        is_growth = False  # sem DY confiável, não assumir crescimento

    # pl_confiavel: False quando Yahoo retornou PL negativo ou >80 (TTM atípico)
    pl_confiavel = bool(dados.get('pl_confiavel', True))

    print(f"\n  Variáveis derivadas:")
    print(f"    VPA (P / P/VP)     : R$ {vpa:.2f}")
    if pl > 0:
        print(f"    LPA real (P / P/L) : R$ {p/pl:.2f}")
    print(f"    dy_confiavel       : {dy_confiavel}")
    pl_status = '(OK)' if pl_confiavel else warn(
        'PL do Yahoo suspeito — Graham será ignorado'
    )
    print(f"    pl_confiavel       : {pl_confiavel}  {pl_status}")
    print(f"    is_growth          : {is_growth}  "
          f"({'ROE>20% AND DY<4%' if dy_confiavel else 'False (DY não confiável)'})")
    print(f"    → Perfil: {'CRESCIMENTO (Lynch)' if is_growth else 'RENDA/VALOR (Graham+Bazin+Gordon)'}")

    metodos      = {}
    metodos_log  = {}

    # Graham — limite PL=25 para ambos os perfis (era 20 para RENDA/VALOR)
    limite_pvp = 3.0 if is_growth else 2.5
    limite_pl  = 25.0
    print(sub("Método Graham"))
    if not pl_confiavel:
        r = "pl_confiavel=False (Yahoo TTM suspeito) — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Graham'] = {"status": "IGNORADO", "motivo": r}
    elif pl <= 0:
        r = "P/L ausente ou negativo — IGNORADO"
        print(f"  {err(r)}")
        metodos_log['Graham'] = {"status": "IGNORADO", "motivo": r}
    elif pvp <= 0:
        r = "P/VP ausente — IGNORADO"
        print(f"  {err(r)}")
        metodos_log['Graham'] = {"status": "IGNORADO", "motivo": r}
    elif pl > limite_pl:
        r = f"P/L={pl:.1f} > limite {limite_pl:.0f} — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Graham'] = {"status": "IGNORADO", "motivo": r}
    elif pvp > limite_pvp:
        r = f"P/VP={pvp:.2f} > limite {limite_pvp:.1f} — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Graham'] = {"status": "IGNORADO", "motivo": r}
    else:
        pl_g    = max(pl, 7.0)
        lpa_adj = p / pl_g
        g_val   = (22.5 * lpa_adj * vpa) ** 0.5
        metodos['Graham'] = g_val
        print(f"  pl_graham = max({pl:.1f}, 7.0) = {pl_g:.1f}")
        print(f"  LPA_adj   = {p:.2f} / {pl_g:.1f} = {lpa_adj:.4f}")
        print(f"  Graham    = √(22.5 × {lpa_adj:.4f} × {vpa:.4f}) = {ok(f'R$ {g_val:.2f}')}")
        metodos_log['Graham'] = {"status": "OK", "valor": round(g_val, 2),
                                  "pl_graham": pl_g, "lpa_adj": round(lpa_adj, 4)}

    # Bazin
    print(sub("Método Bazin"))
    if is_growth:
        r = "Perfil CRESCIMENTO — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Bazin'] = {"status": "IGNORADO", "motivo": r}
    elif not dy_confiavel:
        r = "DY não confiável (dado suspeito) — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Bazin'] = {"status": "IGNORADO", "motivo": r}
    elif dy <= 0:
        r = "DY = 0 — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Bazin'] = {"status": "IGNORADO", "motivo": r}
    else:
        taxa_b = selic * 0.85
        b_val  = (dy * p) / taxa_b
        div_anual = dy * p
        metodos['Bazin'] = b_val
        print(f"  Dividendo anual = {dy*100:.2f}% × R${p:.2f} = R$ {div_anual:.2f}")
        print(f"  Taxa mínima (Selic×0.85) = {selic*100:.2f}%×0.85 = {taxa_b*100:.2f}%")
        print(f"  Bazin = R${div_anual:.2f} / {taxa_b:.4f} = {ok(f'R$ {b_val:.2f}')}")
        if b_val < p:
            msg = (
                f"Bazin ({b_val:.2f}) < Preço ({p:.2f}): "
                "DY insuficiente vs Selic — correto com juros altos"
            )
            print(f"  {warn(msg)}")
        metodos_log['Bazin'] = {"status": "OK", "valor": round(b_val, 2),
                                 "div_anual": round(div_anual, 4), "taxa_bazin": round(taxa_b, 4)}

    # Lynch
    print(sub("Método Lynch (Crescimento)"))
    if not is_growth:
        r = "Perfil RENDA/VALOR — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Lynch'] = {"status": "IGNORADO", "motivo": r}
    elif not dy_confiavel:
        r = "DY não confiável — Lynch não aplicado (evita FV inflado)"
        print(f"  {warn(r)}")
        metodos_log['Lynch'] = {"status": "IGNORADO", "motivo": r}
    elif pl <= 0:
        r = "P/L ausente ou negativo — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Lynch'] = {"status": "IGNORADO", "motivo": r}
    else:
        lpa_l = p / pl
        payout_ratio = min((dy * p) / lpa_l, 0.95) if lpa_l > 0 else 0.5
        retencao = 1 - payout_ratio
        taxa_l = min(roe * retencao * 100, 30)
        l_val = lpa_l * taxa_l
        metodos['Lynch'] = l_val
        print(f"  LPA real = {p:.2f} / {pl:.1f} = {lpa_l:.4f}")
        print(f"  Payout = {payout_ratio*100:.1f}%")
        print(f"  Retenção = {retencao*100:.1f}%")
        print(
            f"  Taxa cresc. = min(ROE×retenção×100, 30) = "
            f"{taxa_l:.1f}%"
        )
        print(f"  Lynch = {lpa_l:.4f} × {taxa_l:.1f} = {ok(f'R$ {l_val:.2f}')}")
        metodos_log['Lynch'] = {"status": "OK", "valor": round(l_val, 2),
                                  "lpa": round(lpa_l, 4),
                                  "payout_ratio": round(payout_ratio, 4),
                                  "taxa_cresc": taxa_l}

    # Gordon
    print(sub("Método Gordon"))
    if not dy_confiavel:
        r = "DY não confiável — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Gordon'] = {"status": "IGNORADO", "motivo": r}
    elif dy <= 0.04:
        r = f"DY={dy*100:.2f}% ≤ 4% — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Gordon'] = {"status": "IGNORADO", "motivo": r}
    elif roe <= 0.10:
        r = f"ROE={roe*100:.2f}% ≤ 10% — IGNORADO"
        print(f"  {warn(r)}")
        metodos_log['Gordon'] = {"status": "IGNORADO", "motivo": r}
    else:
        g_cr  = min(roe * 0.5, 0.04)
        k_cr  = selic + 0.06
        if k_cr <= g_cr:
            r = "k <= g: modelo instável — IGNORADO"
            print(f"  {err(r)}")
            metodos_log['Gordon'] = {"status": "IGNORADO", "motivo": r}
        else:
            div_prox = (dy * p) * (1 + g_cr)
            go_val   = div_prox / (k_cr - g_cr)
            metodos['Gordon'] = go_val
            print(f"  g (cresc. dividendo) = min(ROE×0.5, 4%) = {g_cr*100:.2f}%")
            print(f"  k (taxa desconto)    = Selic + 6% = {k_cr*100:.2f}%")
            print(f"  Div próximo          = R${dy*p:.4f} × (1+{g_cr:.4f}) = R${div_prox:.4f}")
            print(f"  Gordon = {div_prox:.4f} / ({k_cr:.4f}-{g_cr:.4f}) = {ok(f'R$ {go_val:.2f}')}")
            metodos_log['Gordon'] = {"status": "OK", "valor": round(go_val, 2),
                                      "g": round(g_cr, 4), "k": round(k_cr, 4)}

    # Resultado
    print(sub("Resultado Final"))
    vals = list(metodos.values())
    if not vals:
        fv = p
        upside = 0.0
        print(f"  {warn('Nenhum método aplicado → Fair Value = Preço atual (Fallback)')}")
    else:
        fv     = sum(vals) / len(vals)
        upside = (fv / p) - 1
        for nome, val in metodos.items():
            peso = val / sum(vals) * 100
            print(f"  {nome:<20}: R$ {val:.2f}  ({peso:.0f}% do peso)")
        print(f"  {'─'*38}")
        print(f"  Média simples    : R$ {fv:.2f}")

    upside_pct = (fv / p - 1) * 100
    score = 50 + 48 * (2 / (1 + math.exp(-upside * 3)) - 1)
    score = max(0, min(100, score))

    # Ajustes de qualidade — idênticos ao valuation_engine.py de produção
    if roe > 0.20:
        score += 10
    if roe < 0.05:
        score -= 15
    if not dy_confiavel:
        score -= 5
    if not pl_confiavel:
        score -= 5
    score = max(0, min(100, score))

    rec = "NEUTRO"
    if upside > 0.15 or (is_growth and upside > 0.05):
        rec = "COMPRA"
    if upside < -0.15:
        rec = "VENDA"
    if score >= 75 and upside > 0.05:
        rec = "COMPRA FORTE"
    if score >= 75 and upside <= 0:
        rec = "QUALIDADE — AGUARDAR"

    cor = GRN if upside_pct > 15 else (RED if upside_pct < -15 else YLW)
    print(f"\n  Preço Atual  : R$ {p:.2f}")
    print(f"  Fair Value   : R$ {fv:.2f}")
    print(f"  Upside       : {cor}{upside_pct:+.1f}%{RST}")
    print(f"  Score        : {score:.0f}/100")
    print(f"  Recomendação : {rec}")

    _rel['tickers'][ticker]['valuation'] = {
        "inputs": {"preco": p, "pl": pl, "pvp": pvp, "dy": dy, "roe": roe,
                   "selic": selic, "is_growth": is_growth,
                   "dy_confiavel": dy_confiavel, "pl_confiavel": pl_confiavel},
        "metodos": metodos_log,
        "resultado": {
            "fair_value":    round(fv, 2),
            "upside_pct":    round(upside_pct, 1),
            "score":         round(score, 1),
            "recomendacao":  rec,
        }
    }

    analise_dict = {
        'fair_value':     round(fv, 2),
        'upside':         round(upside_pct, 1),
        'score_final':    int(score),
        'recomendacao':   rec,
        'perfil':         'CRESCIMENTO' if is_growth else 'RENDA/VALOR',
        'metodos_usados': ', '.join([f"{k}: R${v:.2f}" for k, v in metodos.items()]),
        'pl_confiavel':   pl_confiavel,
    }
    return fv, upside, analise_dict


# ══════════════════════════════════════════════════════════════════════════════
# 4. ANÁLISE TÉCNICA
# ══════════════════════════════════════════════════════════════════════════════

def auditar_tecnica(ticker: str, dados: dict):
    print(hdr(f"4. ANÁLISE TÉCNICA — {ticker}"))
    import numpy as np

    hist = dados.get('historico')
    if hist is None or hist.empty:
        print(warn("  Histórico indisponível."))
        _rel['tickers'][ticker]['tecnica'] = {"disponivel": False}
        return

    close = hist['Close']
    n     = len(close)
    print(f"  Pregões: {n}")

    delta = close.diff()
    gain  = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs    = gain / loss.replace(0, float('nan'))
    rsi   = (100 - (100 / (1 + rs))).fillna(50).iloc[-1]

    ma50  = close.rolling(50).mean().iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1]
    preco = close.iloc[-1]

    ma50_ok  = not (ma50  != ma50)   # not NaN
    ma200_ok = not (ma200 != ma200)

    print(f"\n  RSI (14) : {rsi:.1f}  → {'Sobrecomprado' if rsi>70 else ('Sobrevendido' if rsi<30 else 'Neutro')}")
    print(f"  MA50     : {'R$ '+f'{ma50:.2f}'  if ma50_ok  else warn('NaN (< 50 pregões)')}")
    print(f"  MA200    : {'R$ '+f'{ma200:.2f}' if ma200_ok else warn('NaN (< 200 pregões)')}")
    print(f"  Preço    : R$ {preco:.2f}")

    if ma200_ok:
        tend = "Alta (Longo Prazo)" if preco > ma200 else "Baixa (Longo Prazo)"
    elif ma50_ok:
        tend = "Alta (Curto Prazo)" if preco > ma50  else "Baixa (Curto Prazo)"
    else:
        tend = "Indefinida"
    print(f"  Tendência: {tend}")

    _rel['tickers'][ticker]['tecnica'] = {
        "disponivel": True,
        "pregoes":    n,
        "rsi":        round(float(rsi), 1),
        "ma50":       round(float(ma50),  2) if ma50_ok  else None,
        "ma200":      round(float(ma200), 2) if ma200_ok else None,
        "preco":      round(float(preco), 2),
        "tendencia":  tend,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. PROMPT EXATO PARA A IA
# ══════════════════════════════════════════════════════════════════════════════

def auditar_prompt(ticker: str, dados: dict, fv: float = 0, upside: float = 0, analise_dict: dict = None):
    print(hdr(f"5. PROMPT ENVIADO À IA — {ticker}"))

    # Em produção: app.py faz dados.update(analise) ANTES de chamar ai_engine.analisar()
    # Simulamos aqui mesclando o dict de valuation no dados
    dados_simulados = dict(dados)
    if analise_dict:
        dados_simulados.update(analise_dict)

    excluir  = {'historico', 'analise_ia', 'tech'}
    linhas   = [f"- {k}: {v}" for k, v in dados_simulados.items()
                if v is not None and k not in excluir]
    dados_txt = "\n".join(linhas)
    perfil    = dados_simulados.get('perfil', 'GERAL')

    prompt = f"""Analise a ação {ticker} (Perfil: {perfil}).

Dados Fundamentais:
{dados_txt}

Responda em Português com exatamente 3 tópicos:
1. Qualidade da empresa (Forte / Moderada / Fraca) — justifique com os dados acima.
2. Riscos principais — liste os 2-3 maiores riscos identificados.
3. Veredito final (Compra / Neutro / Venda) — justifique com base no valuation e qualidade."""

    print(f"\n  Tamanho: {len(prompt)} chars, {len(linhas)} campos enviados")
    print(f"\n  Campos enviados:")
    for l in linhas:
        print(f"    {l}")
    print(f"\n  ┌── PROMPT COMPLETO {'─'*40}")
    for l in prompt.split('\n'):
        print(f"  │ {l}")
    print(f"  └{'─'*59}")

    print(sub("Checklist de qualidade"))
    checks = [
        ('historico' not in '\n'.join(linhas), "Histórico excluído do prompt"),
        ('analise_ia' not in '\n'.join(linhas), "analise_ia anterior excluída"),
        (perfil != 'GERAL',                     f"Perfil definido: {perfil}"),
        (any('fair_value'   in l for l in linhas), "fair_value incluído"),
        (any('upside'       in l for l in linhas), "upside incluído"),
        (any('recomendacao' in l for l in linhas), "recomendacao incluída"),
    ]
    check_results = []
    for passou, desc in checks:
        print(f"  {'✓' if passou else '⚠'} {desc}")
        check_results.append({"ok": passou, "desc": desc})

    _rel['tickers'][ticker]['prompt'] = {
        "tamanho_chars":  len(prompt),
        "num_campos":     len(linhas),
        "perfil":         perfil,
        "campos_enviados": [l.lstrip('- ') for l in linhas],
        "prompt_completo": prompt,
        "checklist":      check_results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. BANCO DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

def auditar_banco():
    print(hdr("6. BANCO DE DADOS"))

    if not os.path.exists(DB_PATH):
        print(warn(f"  Banco {DB_PATH!r} não encontrado no diretório atual."))
        _rel['banco'] = {"erro": "arquivo não encontrado"}
        return

    tamanho_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"  Arquivo: {DB_PATH}  ({tamanho_mb:.2f} MB)")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indices = [r[0] for r in cur.fetchall()]
    print(f"  Tabelas : {tabelas}")
    print(f"  Índices : {indices}")
    if 'idx_data' in indices:
        print(f"  {ok('idx_data presente')}")
    else:
        print(f"  {warn('idx_data ausente — full scan em queries por data')}")

    # Carteira
    print(sub("Carteira"))
    cur.execute("SELECT * FROM carteira_real")
    cart = cur.fetchall()
    cart_json = []
    if cart:
        total_inv = sum(r['quantidade'] * r['preco_medio'] for r in cart)
        print(f"  {len(cart)} posições — Total investido: R$ {total_inv:,.2f}")
        for r in cart:
            linha = dict(r)
            cart_json.append(linha)
            print(
                f"    {r['ticker']:<8} {r['quantidade']:>6} × "
                f"R${r['preco_medio']:>9.2f}  (desde {r['data_aporte']})"
            )
    else:
        print("  Carteira vazia.")

    # Análises
    print(sub("Análises salvas"))
    cur.execute("SELECT ticker, data_analise, score, recomendacao, dados_completos "
                "FROM analises ORDER BY data_analise DESC")
    analises = cur.fetchall()
    analises_json = []
    if analises:
        print(f"  {len(analises)} análise(s):\n")
        for a in analises:
            entrada = {
                "ticker":       a['ticker'],
                "data_analise": a['data_analise'],
                "score":        a['score'],
                "recomendacao": a['recomendacao'],
            }
            print(f"  {'─'*50}")
            print(f"  Ticker     : {a['ticker']}")
            print(f"  Data       : {a['data_analise']}")
            print(f"  Score      : {a['score']}/100")
            print(f"  Recomend.  : {a['recomendacao']}")
            try:
                d = json.loads(a['dados_completos'])
                tam = len(a['dados_completos'])
                print(f"  JSON size  : {tam:,} bytes ({tam/1024:.1f} KB)")
                if 'historico' in d:
                    print(f"  {err('ATENÇÃO: historico presente no banco!')}")
                    entrada['historico_no_banco'] = True
                else:
                    print(f"  {ok('historico excluído do banco')}")
                    entrada['historico_no_banco'] = False
                entrada['json_bytes'] = tam
                for campo in ['fair_value','upside','perfil','metodos_usados']:
                    if campo in d:
                        entrada[campo] = d[campo]
                        print(f"  {campo:<15}: {d[campo]}")
                if 'analise_ia' in d:
                    preview = d['analise_ia'][:300].replace('\n',' ')
                    entrada['analise_ia_preview'] = preview
                    print(f"  analise_ia : \"{preview}...\"")
            except Exception as e:
                entrada['erro_json'] = str(e)
                print(f"  {err(f'JSON corrompido: {e}')}")
            analises_json.append(entrada)
    else:
        print("  Nenhuma análise ainda.")

    conn.close()

    _rel['banco'] = {
        "arquivo":    DB_PATH,
        "tamanho_mb": round(tamanho_mb, 3),
        "tabelas":    tabelas,
        "indices":    indices,
        "idx_data":   'idx_data' in indices,
        "carteira":   cart_json,
        "analises":   analises_json,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. VERIFICAÇÃO MANUAL (link Fundamentus)
# ══════════════════════════════════════════════════════════════════════════════

def auditar_referencia(ticker: str, dados: dict):
    print(hdr(f"7. VERIFICAÇÃO MANUAL — {ticker}"))
    print(f"""
  Compare com: https://www.fundamentus.com.br/detalhes.php?papel={ticker}

  Campo               Valor capturado
  ──────────────────────────────────────────────────""")

    campos_ref = [
        ('preco_atual',         'Cotação atual'),
        ('pl',                  'P/L'),
        ('pvp',                 'P/VP'),
        ('dy',                  'Div. Yield'),
        ('roe',                 'ROE'),
        ('roic',                'ROIC'),
        ('margem_liquida',      'Marg. Líquida'),
        ('patrimonio_liquido',  'Patrim. Líq'),
        ('lucro_liquido',       'Lucro Líquido'),
    ]
    ref_json = {}
    for campo, label in campos_ref:
        val = dados.get(campo)
        ref_json[campo] = val
        if val is None:
            print(f"  {label:<22}: {warn('AUSENTE')}")
        elif campo in ['dy','roe','roic','margem_liquida']:
            print(f"  {label:<22}: {val*100:.2f}%")
        elif campo == 'preco_atual':
            print(f"  {label:<22}: R$ {val:.2f}")
        else:
            print(f"  {label:<22}: {val}")

    print(f"\n  → Se algum valor divergir do Fundamentus, o bug está em")
    print(f"    fundamentus_scraper.py → _limpar_valor() ou buscar_dados()\n")

    _rel['tickers'][ticker]['referencia_manual'] = {
        "url":    f"https://www.fundamentus.com.br/detalhes.php?papel={ticker}",
        "campos": ref_json,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # Iniciar captura do output
    _tee = _Tee(sys.stdout)
    sys.stdout = _tee

    ts    = datetime.now().strftime('%Y%m%d_%H%M%S')
    fname = f"auditoria_{ts}"

    args = [a for a in sys.argv[1:] if a]

    print(f"{BLD}{CYN}")
    print("╔══════════════════════════════════════════════════════╗")
    print("║       SENTINELA B3 — AUDITORIA INTERNA               ║")
    print(f"║       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(RST)

    _rel['meta'] = {
        "timestamp":  datetime.now().isoformat(),
        "versao":     "Sentinela B3 v13",
        "db_path":    DB_PATH,
        "tickers":    [],
        "modo":       "full",
    }

    if '--db-only' in args:
        _rel['meta']['modo'] = 'db-only'
        auditar_banco()
    elif '--selic' in args:
        _rel['meta']['modo'] = 'selic-only'
        auditar_selic()
    else:
        tickers = [a.upper() for a in args if not a.startswith('--')]
        if not tickers:
            tickers = ['PETR4', 'ITUB4', 'WEGE3']
            print(f"  {warn('Nenhum ticker informado — usando padrão: PETR4, ITUB4, WEGE3')}")
            print(f"  Uso: python auditoria.py VALE3 BBAS3\n")

        _rel['meta']['tickers'] = tickers

        auditar_selic()
        auditar_banco()

        for ticker in tickers:
            print(f"\n\n{'█'*60}")
            print(f"  TICKER: {ticker}")
            print(f"{'█'*60}")

            dados = auditar_dados_scraper(ticker)
            if dados is None:
                _rel['tickers'][ticker] = {"erro": "dados não obtidos"}
                continue

            # Roteamento FII vs Ação — idêntico ao app.py
            qt = dados.get('quote_type', '')
            is_fii = (
                qt == 'MUTUALFUND'
                or (not qt and '11' in ticker and 'SA' not in ticker)
            )

            if is_fii:
                print(hdr(f"3. VALUATION — {ticker}"))
                print(f"\n  {warn('Perfil FII detectado (quoteType='+repr(qt)+')')}")
                print(f"  Em produção: fii_engine.analisar() é chamado em vez de val_engine.processar()")
                try:
                    from fii_engine import FIIEngine
                    analise = FIIEngine().analisar(dados)
                    fv     = analise.get('fair_value', dados.get('preco_atual', 0))
                    upside_val = analise.get('upside', 0)
                    rec_fii = analise.get('recomendacao', '?')
                    print(
                        f"\n  FII Engine → FV=R${fv:.2f}  "
                        f"Upside={upside_val:+.1f}%  Rec={rec_fii}"
                    )
                    _rel['tickers'][ticker]['valuation'] = {
                        "perfil": "FII",
                        "resultado": analise,
                    }
                except Exception as e:
                    analise = {'fair_value': dados.get('preco_atual', 0), 'upside': 0,
                               'score_final': 50, 'recomendacao': 'NEUTRO', 'perfil': 'FII'}
                    fv, upside_val = analise['fair_value'], 0.0
                    print(f"  {warn(f'FIIEngine indisponível no audit: {e}')}")
                    _rel['tickers'][ticker]['valuation'] = {"perfil": "FII", "nota": str(e)}
            else:
                fv, upside_val, analise = auditar_valuation(ticker, dados)
            # CORRIGIDO: mergear resultado do valuation em dados antes do prompt
            # (mesmo que app.py faz com dados.update(analise))
            dados.update(analise)
            auditar_tecnica(ticker, dados)
            auditar_prompt(ticker, dados, fv, upside_val)
            auditar_referencia(ticker, dados)

        print(hdr("AUDITORIA CONCLUÍDA"))
        print(f"  Tickers: {', '.join(tickers)}")

    # ── Salvar TXT ────────────────────────────────────────────────────────────
    txt_path = f"{fname}.txt"
    try:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(_tee.getvalue())
        # Restaurar stdout antes de imprimir o aviso
        sys.stdout = _tee._orig
        print(f"\n  {ok(f'Relatório TXT salvo: {txt_path}')}")
    except Exception as e:
        sys.stdout = _tee._orig
        print(f"\n  {err(f'Erro ao salvar TXT: {e}')}")

    # ── Salvar JSON ───────────────────────────────────────────────────────────
    json_path = f"{fname}.json"
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(_rel, f, ensure_ascii=False, indent=2, default=str)
        print(f"  {ok(f'Dados JSON salvos:   {json_path}')}")
    except Exception as e:
        print(f"  {err(f'Erro ao salvar JSON: {e}')}")

    print(f"\n  Envie os dois arquivos para análise:")
    print(f"    📄 {txt_path}")
    print(f"    📊 {json_path}\n")


if __name__ == "__main__":
    main()
