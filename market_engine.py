import logging
import math
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFException

from brapi_provider import BrapiProvider
from config import FII_MANUAL_FALLBACK, _normalizar_dy, get_taxa_real
from cvm_fii_provider import CVMFIIProvider
from cvm_provider import CVMProvider
from database import DatabaseManager
from sentinela.data import (
    acoes_cvm,
    contas_cvm,
    gordon_cvm,
    liquidez,
    normalizacao,
    proventos_b3,
    series_cvm,
)
from sentinela.data.providers import b3_cotahist, b3_fundos, b3_proventos
from sentinela.data.providers.b3_cotahist import HistoricoRecente
from sentinela.data.providers.ifdata import IFDataProvider
from sentinela.data.referencia.carga import ReferenciaOficial
from sentinela.domain import ticker as ticker_b3
from sentinela.domain.enums import AssetType
from sentinela.domain.provenance import FieldProvenance, FieldValue
from sentinela.domain.units import Escala
from sentinela.services.asset_classifier import AssetClassifier

logger = logging.getLogger("MarketEngine")

REQUIRED_STOCK_FUNDAMENTALS = ('pl', 'pvp', 'roe', 'dy')
REQUIRED_FII_FUNDAMENTALS = ('pvp', 'dy')
REQUIRED_FUNDAMENTALS = REQUIRED_STOCK_FUNDAMENTALS
REQUIRED_MARKET_DATA = ('preco_atual', 'historico')
FUNDAMENTAL_KEYS = (
    'pl', 'pvp', 'dy', 'roe', 'lpa', 'vpa', 'roic', 'divida_liq_ebitda',
    'div_liq_patrimonio', 'margem_liquida', 'margem_bruta',
    'patrimonio_liquido', 'receita_liquida', 'lucro_liquido',
    'ativo_total', 'ativo_circulante', 'quote_type', 'vacancia',
)
FIELD_PROVENANCE_KEYS = ('preco_atual', 'dy', 'pl', 'pvp', 'roe')
FIELD_PROVENANCE_UNITS = {
    'preco_atual': 'BRL',
    'dy': 'ratio',
    'pl': 'ratio',
    'pvp': 'ratio',
    'roe': 'ratio',
}
SOURCE_ALIASES = {
    'cache': 'fundamentals_cache',
    'manual_fii': 'manual_fallback',
    'yfinance_partial': 'yfinance',
}

# Campos do calcular_indicadores (CVM) → chaves de FUNDAMENTAL_KEYS.
# F2A-8: a alavancagem é a dívida financeira líquida (`sentinela.data.divida_liquida`);
# `divida_pl` (passivo total − PL, sobre o PL) não é dívida líquida e não é mapeado.
_CVM_TO_MARKET: dict[str, str] = {
    'roe':                'roe',
    'margem_liquida':     'margem_liquida',
    'divida_liq_ebitda':  'divida_liq_ebitda',
    'div_liq_patrimonio': 'div_liq_patrimonio',
    'patrimonio_liquido': 'patrimonio_liquido',
    'lucro_liquido':      'lucro_liquido',
    'receita_liquida':    'receita_liquida',
    'ativo_total':        'ativo_total',
    'ativo_circulante':   'ativo_circulante',
}

_DEFAULT_ASSET_CLASSIFIER = AssetClassifier()

# Índice oficial (F2A-19): um por processo, compartilhado pelos motores e pelas threads.
REFERENCIA_OFICIAL = ReferenciaOficial()

# Registro do índice → chave em `dados`.
_CAMPOS_DA_REFERENCIA = {
    'classe_ativo': 'classe',
    'especie': 'especie',
    'cnpj': 'cnpj',
    'cd_cvm': 'cd_cvm',
    'setor': 'setor',
    'segmento_fii': 'segmento',
    'controle_acionario': 'controle_acionario',
    'acoes_por_unit': 'acoes_por_unit',
    'classe_preferencial': 'classe_preferencial',
    'classes_preferenciais': 'classes_preferenciais',
}
RISCO_FORA_DA_REFERENCIA = 'ticker fora da referência oficial'
RISCO_FORA_DA_CVM = 'ticker fora da cobertura da CVM'
RISCO_SEM_REFERENCIA = 'referência oficial indisponível: dados da CVM não consultados'
RISCO_FII_FORA_DO_INFORME = 'FII fora da cobertura do Informe Mensal'
MOTIVO_DY_FORA_DA_FAIXA = 'DY fora de 0–25% (invariante dos motores): descartado no merge'
AVISO_CODIGO_DA_TABELA = 'cvm_code_from_correction_table'
AVISO_ACOES_FIM_DO_PERIODO = 'shares_end_of_period'
RISCO_SEM_POR_ACAO_CVM = 'CVM não derivou LPA, VPA, P/L e P/VP'
RISCO_SEM_VPA_CVM = 'CVM não derivou VPA e P/VP'
RISCO_SEM_LPA_CVM = 'CVM sem LPA'
RISCO_ROE_CVM = 'CVM sem ROE'
RISCO_CONTA_CVM = 'CVM sem'
RISCO_ALAVANCAGEM_CVM = 'alavancagem não avaliada'
RISCO_LIMITACAO_BANCO = 'limitação do banco'
# F2A-8: só a CVM entrega a alavancagem; a definição da brapi não é conhecida.
_CAMPOS_SO_DA_CVM = frozenset({'divida_liq_ebitda'})


def is_missing(value: Any) -> bool:
    """Return True for empty/null/non-finite values; numeric zero is field-specific."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == "" or value.strip().upper() in {"N/A", "NA", "NONE", "NULL"}
    try:
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            return True
    except (TypeError, ValueError):
        return False
    return False


def _as_float(value: Any) -> float | None:
    if is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_field_missing(field: str, value: Any, dados: dict[str, Any] | None = None) -> bool:
    if is_missing(value):
        return True

    numero = _as_float(value)
    if field == 'preco_atual':
        return numero is None or numero <= 0
    if field == 'historico':
        return value is None or getattr(value, 'empty', True)
    if field in {'pl', 'pvp', 'roe', 'lpa', 'vpa'}:
        # F2B-8: ausente é só None ou não finito; prejuízo e PL negativo são dado, e cada
        # método se abstém pela própria regra.
        return bool(dados and field == 'pl' and dados.get('pl_confiavel') is False)

    # DY zero can be a valid "no dividends" signal.
    return False


def _is_fii_ticker(
    ticker: str,
    dados: dict[str, Any] | None = None,
    asset_classifier: AssetClassifier | None = None,
) -> bool:
    classifier = asset_classifier or _DEFAULT_ASSET_CLASSIFIER
    return classifier.is_fii(ticker, dados)


def _required_fundamentals_for(
    dados: dict[str, Any],
    asset_classifier: AssetClassifier | None = None,
) -> tuple[str, ...]:
    ticker = str(dados.get('ticker', '')).upper()
    if _is_fii_ticker(ticker, dados, asset_classifier):
        return REQUIRED_FII_FUNDAMENTALS
    return REQUIRED_STOCK_FUNDAMENTALS


def merge_if_valid(
    base: dict[str, Any],
    supplemental: dict[str, Any],
    *,
    overwrite: bool = False,
    allowed_keys: set[str] | None = None,
) -> list[str]:
    """Merge supplemental values when valid, optionally overwriting fields."""
    preenchidos: list[str] = []
    if not supplemental:
        return preenchidos

    for chave, valor in supplemental.items():
        if chave in {
            'ticker', 'erro_scraper', 'dados_parciais', 'campos_faltantes',
            'dados_cache', 'dados_manual', 'fonte_preco', 'fonte_fundamentos',
            'riscos_dados',
        }:
            continue
        if allowed_keys is not None and chave not in allowed_keys:
            continue
        if _is_field_missing(chave, valor):
            continue
        if overwrite or _is_field_missing(chave, base.get(chave), base):
            base[chave] = valor
            preenchidos.append(chave)
            if chave == 'pl':
                base['pl_confiavel'] = bool(supplemental.get('pl_confiavel', True))

    return preenchidos


def list_missing_required_fields(
    dados: dict[str, Any],
    asset_classifier: AssetClassifier | None = None,
) -> list[str]:
    """List required fields still absent after source consolidation."""
    return [
        campo
        for campo in _required_fundamentals_for(dados, asset_classifier)
        if _is_field_missing(campo, dados.get(campo), dados)
    ]


def list_missing_market_fields(dados: dict[str, Any]) -> list[str]:
    """List required price/history fields still absent."""
    return [
        campo
        for campo in REQUIRED_MARKET_DATA
        if _is_field_missing(campo, dados.get(campo), dados)
    ]


def _retrato(dados: dict[str, Any]) -> dict[str, Any]:
    """Cópia simples e serializável do preço e de FUNDAMENTAL_KEYS como a cascata os entregou (F2A-6, E-3).

    Campo ausente ou não finito vira `None`; número vira `float`; texto fica texto.
    """
    retrato: dict[str, Any] = {}
    for chave in ('preco_atual', *FUNDAMENTAL_KEYS):
        valor = dados.get(chave)
        if isinstance(valor, str):
            retrato[chave] = valor
            continue
        numero = _as_float(valor)
        retrato[chave] = numero if numero is not None and math.isfinite(numero) else None
    return retrato


def _lpa_divulgado_comparado(
    divulgados: dict[str, Any], especie: str | None, especie_base: str | None = None
) -> dict[str, Any] | None:
    """LPA divulgado coerente da classe do ticker (F2A-5), ou o da espécie sem a classe.

    Só o coerente (F2B-14; ficha, 7.3 e 7.5): com o divulgado da classe descartado pela D19, não
    há conferência, e o alerta é o da incoerência. Sem classe (unit ou sem índice), o da escala.
    """
    for chave in (especie, especie_base):
        if chave in divulgados:
            achado = divulgados[chave]
            if not isinstance(achado, acoes_cvm.LpaDivulgado):
                return None
            return {'especie': chave, 'valor': achado.valor}
    if especie is None:
        ordem = [*acoes_cvm.ORDEM_DA_ESCALA, *sorted(set(divulgados) - set(acoes_cvm.ORDEM_DA_ESCALA))]
        for chave in ordem:
            achado = divulgados.get(chave)
            if isinstance(achado, acoes_cvm.LpaDivulgado):
                return {'especie': chave, 'valor': achado.valor}
    return None


def _linhas_de_lpa(ind: dict[str, Any]) -> dict[str, list]:
    """Linhas de LPA básico por classe; provedor anterior ao F2A-36 entrega só a primeira."""
    if 'lpa_basico_por_classe' in ind:
        return ind['lpa_basico_por_classe'] or {}
    if 'lpa_divulgado_por_especie' in ind:
        return {k: [v] for k, v in (ind['lpa_divulgado_por_especie'] or {}).items()}
    referencia = ind.get('lpa_divulgado') or {}
    if referencia.get('especie') in acoes_cvm.ORDEM_DA_ESCALA:
        return {referencia['especie']: [referencia['valor']]}
    return {}


_CAMPOS_COM_PRECO = frozenset({'pl', 'pvp'})
# F2A-37: campos que dependem do lucro e do PL dos controladores.
_CAMPOS_DA_RESERVA = {
    'lucro_controladores': ('roe', 'lpa'),
    'pl_controladores': ('roe', 'vpa'),
}


def _guardar_por_fonte(dados: dict[str, Any], fonte: str, valores: dict[str, Any]) -> None:
    """Guarda o que a fonte entregou, antes do merge (F2A-5), para a validação cruzada."""
    entregues = {
        chave: valor
        for chave, valor in _retrato(valores).items()
        if valor is not None and chave in valores
    }
    if entregues:
        dados.setdefault('valores_por_fonte', {})[fonte] = entregues


def _registrar_fonte_fundamentos(dados: dict[str, Any], fonte: str) -> None:
    atual = dados.get('fonte_fundamentos')
    if not atual:
        dados['fonte_fundamentos'] = fonte
        return
    fontes = atual.split('+')
    if fonte not in fontes:
        dados['fonte_fundamentos'] = f"{atual}+{fonte}"


def _definir_fonte_fundamentos(dados: dict[str, Any], fonte: str) -> None:
    dados['fonte_fundamentos'] = fonte


def _fundamentos_validos_para_cache(
    dados: dict[str, Any],
    asset_classifier: AssetClassifier | None = None,
) -> bool:
    return not list_missing_required_fields(dados, asset_classifier)


class MarketEngine:
    def __init__(self, asset_classifier: AssetClassifier | None = None) -> None:
        self.brapi = BrapiProvider()
        self.cvm = CVMProvider()
        self.ifdata = IFDataProvider()
        self.cvm_fii = CVMFIIProvider()
        self.cotahist = HistoricoRecente()
        self.b3_proventos = b3_proventos
        self.b3_fundos = b3_fundos
        self.database = DatabaseManager()
        self.asset_classifier = asset_classifier or AssetClassifier()
        self.referencia = REFERENCIA_OFICIAL

    def _is_fii_ticker(self, ticker: str, dados: dict[str, Any] | None = None) -> bool:
        return _is_fii_ticker(
            ticker,
            dados,
            getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER),
        )

    def _record_field_sources(
        self,
        dados: dict[str, Any],
        fields: list[str] | tuple[str, ...],
        source: str,
    ) -> None:
        field_sources = dados.setdefault('_field_sources', {})
        for field in fields:
            if field in FIELD_PROVENANCE_KEYS:
                field_sources[field] = source

    def _normalize_provenance_source(self, source: Any) -> tuple[str, bool]:
        if not source:
            return 'unknown', False

        source_text = str(source)
        inferred = '+' in source_text
        source_key = source_text.split('+')[-1].strip()
        return SOURCE_ALIASES.get(source_key, source_key or 'unknown'), inferred

    def _infer_field_source(self, field: str, dados: dict[str, Any]) -> tuple[str, bool]:
        field_sources = dados.get('_field_sources')
        if isinstance(field_sources, dict) and field in field_sources:
            return self._normalize_provenance_source(field_sources[field])

        if field == 'preco_atual':
            return self._normalize_provenance_source(dados.get('fonte_preco'))

        source, inferred = self._normalize_provenance_source(dados.get('fonte_fundamentos'))
        return source, inferred or source != 'unknown'

    def _field_provenance_confidence(
        self,
        field: str,
        dados: dict[str, Any],
        source: str,
        inferred: bool,
    ) -> float:
        if _is_field_missing(field, dados.get(field), dados):
            return 0.0
        if source == 'manual_fallback':
            return 0.6
        if source == 'fundamentals_cache':
            return 0.75
        if inferred:
            return 0.8
        if source == 'unknown':
            return 0.5
        return 1.0

    def _field_provenance_warnings(
        self,
        field: str,
        dados: dict[str, Any],
        source: str,
        inferred: bool,
    ) -> list[str]:
        warnings: list[str] = []
        missing = _is_field_missing(field, dados.get(field), dados)

        if missing:
            warnings.append('missing_value')
        if inferred and source != 'unknown':
            warnings.append('source_inferred_from_aggregate_flag')
        if dados.get('dados_parciais') and (missing or field in dados.get('campos_faltantes', [])):
            warnings.append('partial_data')
        if source == 'manual_fallback':
            warnings.append('manual_fallback')
        if source == 'CVM' and (dados.get('referencia_oficial') or {}).get('correcao'):
            warnings.append(AVISO_CODIGO_DA_TABELA)
        if source == 'CVM' and dados.get('acoes_cvm') and (
            field == 'pvp'
            or (
                field == 'pl'
                # F2A-36: com o LPA divulgado (média ponderada), o P/L não usa as ações do fim.
                and acoes_cvm.NOTA_RECALCULADO in (dados.get('lpa_cvm') or {}).get('notas', [])
            )
        ):
            warnings.append(AVISO_ACOES_FIM_DO_PERIODO)

        return warnings

    def _field_value_dict(self, field: str, dados: dict[str, Any]) -> dict[str, Any]:
        source, inferred = self._infer_field_source(field, dados)
        provenance = FieldProvenance(
            source=source,
            confidence=self._field_provenance_confidence(field, dados, source, inferred),
            cached=source == 'fundamentals_cache',
            manual=source == 'manual_fallback',
            warnings=self._field_provenance_warnings(field, dados, source, inferred),
        )
        return FieldValue(
            name=field,
            value=dados.get(field),
            unit=FIELD_PROVENANCE_UNITS.get(field),
            provenance=provenance,
        ).to_dict()

    def _attach_field_provenance(self, dados: dict[str, Any]) -> None:
        dados['field_provenance'] = {
            field: self._field_value_dict(field, dados)
            for field in FIELD_PROVENANCE_KEYS
        }
        dados.pop('_field_sources', None)

    def buscar_dados_ticker(self, ticker: str) -> dict[str, Any] | None:
        """Busca dados de mercado com fallback multi-fonte."""
        # F2A-12: ticker fora do formato da B3 não chega a nenhuma fonte externa.
        normalizado = ticker_b3.normalizar(ticker)
        if normalizado is None:
            logger.warning(f"Ticker inválido recusado: {ticker!r}")
            return None
        ticker = normalizado

        dados: dict[str, Any] = {
            'ticker': ticker,
            'historico': pd.DataFrame(),
            'fonte_preco': None,
            'fonte_fundamentos': None,
            'fundamentos_incompletos': False,
            'dados_parciais': False,
            'campos_faltantes': [],
            'dados_cache': False,
            'dados_manual': False,
            'cvm_disponivel': False,
            'riscos_dados': [],
        }

        classifier = getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER)

        # 0. Índice oficial: classe, CNPJ, CD_CVM e atributos do ticker.
        self._aplicar_referencia(ticker, dados)
        if dados.get('_sem_referencia'):
            # F2B-17: o aviso vale para qualquer classe, sem depender da etapa da CVM.
            dados['riscos_dados'].append(RISCO_SEM_REFERENCIA)
        if 'classe_ativo' not in dados:
            # F2A-43: fora do índice (ou sem ele), a classe é a do classificador (final 11 sem
            # dado oficial vira UNKNOWN), para a guarda de escopo do motor de ações valer.
            dados['classe_ativo'] = classifier.classify(ticker, dados).value

        # 1. yfinance: always first for price, history and fallback basics.
        self._buscar_yfinance(ticker, dados)

        # 2. Brapi: cotação recente + complemento de fundamentos.
        self._buscar_brapi(ticker, dados)

        # 3. CVM: fundamentos oficiais das demonstrações financeiras.
        #    Roda após brapi para ter a última palavra nos campos que provê.
        self._buscar_cvm(ticker, dados)

        if not dados.get('fonte_preco'):
            return None

        self._buscar_ifdata(dados, as_of=datetime.now(UTC))
        self._buscar_cvm_fii(ticker, dados)
        self._buscar_rendimento_fii(ticker, dados)
        self._buscar_proventos_b3(ticker, dados)
        self._buscar_liquidez(ticker, dados)
        self._buscar_taxa_real(dados)

        if list_missing_required_fields(dados, classifier):
            self._aplicar_cache_fundamentos(ticker, dados)

        # F2A-23: a estimativa manual de FII (`FII_MANUAL_FALLBACK`) deixou de ser aplicada.

        # F2A-22: o Fundamentus saiu da cascata; a falta de campo obrigatório depois de
        # todas as fontes (inclusive cache e fallback manual) vira `fundamentos_incompletos`.
        obrigatorios_faltando = list_missing_required_fields(dados, classifier)
        dados['fundamentos_incompletos'] = bool(obrigatorios_faltando)
        dados['campos_faltantes'] = obrigatorios_faltando + list_missing_market_fields(dados)
        dados['dados_parciais'] = bool(dados['campos_faltantes'])
        self._salvar_cache_se_valido(ticker, dados)
        dados.setdefault('ticker', ticker)
        self._attach_field_provenance(dados)
        dados['valores_coletados'] = _retrato(dados)
        dados.pop('_sem_referencia', None)
        return dados

    def _aplicar_referencia(self, ticker: str, dados: dict[str, Any]) -> None:
        """Copia para `dados` o registro do ticker no índice oficial, com a fonte.

        Sem índice (rede e índice salvo indisponíveis), marca `_sem_referencia`: a CVM não é
        consultada (F2A-31), porque os mapas manuais deixaram de ser lidos.
        """
        referencia = getattr(self, 'referencia', None)
        indice = referencia.indice(datetime.now(UTC)) if referencia is not None else None
        if indice is None:
            dados['_sem_referencia'] = True
            return
        registro = indice.buscar(ticker)
        if registro is None:
            motivo = next((e.motivo for e in indice.excecoes if e.codigo == ticker), None)
            dados['riscos_dados'].append(
                f"{RISCO_FORA_DA_REFERENCIA} ({motivo})" if motivo else RISCO_FORA_DA_REFERENCIA
            )
            return
        for chave, campo in _CAMPOS_DA_REFERENCIA.items():
            dados[chave] = getattr(registro, campo)
        # F2B-11 (ficha 1.1, 7.8): espécies da companhia no FCA, pelos registros do mesmo CNPJ.
        dados['especies_da_companhia'] = sorted(
            {
                especie
                for r in indice.registros.values()
                if r.cnpj and r.cnpj == registro.cnpj
                for especie in (
                    [r.especie]
                    if r.especie
                    else [acoes_cvm.especie_da_classe(c) for c in r.acoes_por_unit or ()]
                )
            }
        )
        dados['referencia_oficial'] = {
            'regra': registro.regra,
            'fonte': registro.fonte,
            'correcao': registro.correcao,
            'gerado_em': indice.gerado_em,
        }

    def _buscar_yfinance(self, ticker: str, dados: dict[str, Any]) -> bool:
        """Busca dados via yfinance. Retorna True se obteve preco valido."""
        try:
            tk = yf.Ticker(f"{ticker}.SA")

            hist = tk.history(period="1y", timeout=10)
            if hist is not None and not hist.empty:
                dados['historico'] = hist
                dados['preco_atual'] = hist['Close'].iloc[-1]
                dados['fonte_preco'] = 'yfinance'
                self._record_field_sources(dados, ('preco_atual',), 'yfinance')
                # F2B-54 (BUG-2B-33): o DY da B3 usa o fechamento bruto (ficha Bazin, §2); o
                # `historico` ajustado fica para retorno e técnico (armadilha 11).
                # Leitura à parte: a falha dela não pode derrubar os fundamentos do `info`.
                try:
                    bruto = tk.history(period="1mo", auto_adjust=False, timeout=10)
                except (OSError, ValueError, KeyError, YFException) as exc:
                    logger.warning(f"[{ticker}] fechamento bruto do yfinance indisponível: {exc}")
                    bruto = None
                if bruto is not None and not bruto.empty and 'Close' in bruto:
                    dados['fechamentos_brutos'] = {
                        i.date().isoformat(): float(c)
                        for i, c in bruto['Close'].tail(10).items()
                        if isinstance(c, (int, float)) and math.isfinite(c) and c > 0
                    }

            info = tk.info
            if info:
                # F2A-4: o `dividendYield` do yfinance é percentual (F2A-16, seção 8).
                dy_raw = normalizacao.dy_na_fronteira(info.get('dividendYield'), 'yfinance').valor

                pl_raw = _as_float(info.get('trailingPE'))
                pl_confiavel = True
                if pl_raw is not None:
                    if pl_raw < 0:
                        pl_raw = None
                        pl_confiavel = False
                        logger.warning(f"[{ticker}] PL negativo (prejuizo) - descartado")
                    elif pl_raw > 80:
                        pl_confiavel = False
                        logger.warning(
                            f"[{ticker}] PL={pl_raw:.1f} via Yahoo muito alto (>80) "
                            "Possivel TTM atipico; pode ser sobrescrito por fonte melhor."
                        )

                preco_info = _as_float(info.get('currentPrice'))
                if not dados.get('fonte_preco') and preco_info and preco_info > 0:
                    dados['preco_atual'] = preco_info
                    dados['fonte_preco'] = 'yfinance'
                    self._record_field_sources(dados, ('preco_atual',), 'yfinance')

                shares = _as_float(info.get('sharesOutstanding'))
                if shares and shares > 0:
                    dados['_shares_outstanding'] = shares

                payload = {
                    'pl': pl_raw,
                    'pvp': _as_float(info.get('priceToBook')),
                    'dy': dy_raw,
                    # F2A-30: o `returnOnEquity` do yfinance é razão (F2A-16, seção 8).
                    'roe': self._roe_guardado(
                        dados,
                        'yfinance',
                        normalizacao.roe_na_fronteira(info.get('returnOnEquity'), 'yfinance').valor,
                    ),
                    'pl_confiavel': pl_confiavel,
                    'quote_type': info.get('quoteType', ''),
                }
                _guardar_por_fonte(
                    dados, 'yfinance', {**payload, 'preco_atual': dados.get('preco_atual')}
                )
                preenchidos_yfinance: list[str] = []
                for chave, valor in payload.items():
                    if not is_missing(valor):
                        dados[chave] = valor
                        preenchidos_yfinance.append(chave)
                self._record_field_sources(dados, preenchidos_yfinance, 'yfinance')
                if 'dy' in preenchidos_yfinance:
                    dados.setdefault('proveniencia', {})['dy'] = normalizacao.proveniencia_dy('yfinance')
                if 'roe' in preenchidos_yfinance:
                    dados.setdefault('proveniencia', {})['roe'] = normalizacao.proveniencia_roe('yfinance')

                if any(not _is_field_missing(k, dados.get(k), dados) for k in ('pl', 'pvp', 'dy', 'roe')):
                    _registrar_fonte_fundamentos(dados, 'yfinance_partial')

            return bool(dados.get('fonte_preco'))

        except Exception as e:
            logger.warning(f"Yahoo error {ticker}: {e}")
            return False

    def _buscar_brapi(self, ticker: str, dados: dict[str, Any]) -> bool:
        """Busca fundamentos via Brapi, sobrescrevendo fundamentos do Yahoo."""
        if not self.brapi.disponivel:
            logger.warning(f"[{ticker}] Brapi indisponivel: BRAPI_TOKEN ausente")
            return False

        try:
            brapi_data = self.brapi.get_fundamentals(ticker)
            if not brapi_data:
                return False

            fundamentos = {
                chave: valor
                for chave, valor in brapi_data.items()
                if chave in FUNDAMENTAL_KEYS and chave not in _CAMPOS_SO_DA_CVM
            }
            if 'roe' in fundamentos:
                fundamentos['roe'] = self._roe_guardado(dados, 'brapi', fundamentos['roe'])
            if 'dy' in fundamentos:
                fundamentos['dy'] = self._dy_guardado(dados, 'brapi', fundamentos['dy'])
            _guardar_por_fonte(
                dados, 'brapi', {**fundamentos, 'preco_atual': brapi_data.get('preco_atual')}
            )
            preenchidos = merge_if_valid(
                dados,
                fundamentos,
                overwrite=True,
                allowed_keys=set(FUNDAMENTAL_KEYS),
            )
            self._record_field_sources(dados, preenchidos, 'brapi')
            if 'dy' in preenchidos:
                # F2A-4: a representação usada na fronteira (inferida, na brapi).
                dados.setdefault('proveniencia', {})['dy'] = normalizacao.proveniencia_dy('brapi')
            if 'roe' in preenchidos:
                dados.setdefault('proveniencia', {})['roe'] = normalizacao.proveniencia_roe('brapi')

            if _is_field_missing('preco_atual', dados.get('preco_atual'), dados):
                preenchidos_preco = merge_if_valid(dados, brapi_data, allowed_keys={'preco_atual'})
                self._record_field_sources(dados, preenchidos_preco, 'brapi')

            if dados.get('preco_atual') and not dados.get('fonte_preco'):
                dados['fonte_preco'] = 'brapi'

            campos_fundamentalistas = [c for c in preenchidos if c in FUNDAMENTAL_KEYS and c != 'quote_type']
            if campos_fundamentalistas:
                _definir_fonte_fundamentos(dados, 'brapi')
                logger.info(f"[{ticker}] Brapi definiu {len(campos_fundamentalistas)} fundamentos")
                return True

        except Exception as e:
            logger.warning(f"[{ticker}] Brapi error: {e}")

        return False

    def _buscar_rendimento_fii(self, ticker: str, dados: dict[str, Any]) -> None:
        """Informe Mensal e complemento da B3 do FII, para a lente de rendimento (F2B-2).

        Grava, fora do prompt, `dados['informe_fii']` (linhas do complemento com a entrega e
        o ISIN do `geral`, composições do `ativo_passivo`, ISIN e proveniência) e
        `dados['b3_fundo']` (a resposta literal do `fundsCall` da B3, ou a abstenção). A conta,
        com o as_of, é do motor (`rendimento_fii.entradas`). O CNPJ vem só do índice oficial;
        provedores por `getattr`. Sem eles ou sem CNPJ, as chaves ficam de fora.
        """
        if not self._is_fii_ticker(ticker, dados):
            return
        ler = getattr(getattr(self, 'cvm_fii', None), 'obter_rendimentos_fii', None)
        cnpj = dados.get('cnpj')
        if ler is None or not cnpj:
            return
        try:
            dados['informe_fii'] = ler(cnpj)
        except Exception as exc:
            logger.warning(
                f"[{ticker}] Informe Mensal indisponível para o rendimento: {exc}"
            )
            dados['informe_fii'] = {'abstencao': f"Informe Mensal indisponível: {exc}"}
            return
        provedor = getattr(self, 'b3_fundos', None)
        if provedor is None:
            return
        try:
            dados['b3_fundo'] = provedor.coletar(cnpj, ticker, datetime.now(UTC))
        except (OSError, ValueError) as exc:
            logger.warning(f"[{ticker}] complemento da B3 do fundo indisponível: {exc}")
            dados['b3_fundo'] = {
                'abstencao': f"complemento da B3 do fundo indisponível: {exc}"
            }

    def _buscar_taxa_real(self, dados: dict[str, Any]) -> None:
        """Registro aditivo, fora dos métodos e do prompt (F2B-30).

        Sem início/fim comprovados, IPCA se abstém; não inferir janeiro pela
        data final de um balanço nem usar a janela do TTM como DFP anual.
        """
        janela = dados.get('janela_contabil_cvm')
        dados['taxa_real'] = get_taxa_real(
            as_of=datetime.now(UTC), janela=janela
        )

    def _buscar_proventos_b3(self, ticker: str, dados: dict[str, Any]) -> None:
        """Relação de proventos em dinheiro da B3 para o Bazin (F2B-31), fora do prompt.

        Só STOCK e UNIT do modelo empresa pelo BPP consolidado (ficha Bazin 1.0, §4). Grava em
        `dados['proventos_b3']` os registros literais, o total do serviço, os eventos em ações
        e os proventos em dinheiro do complemento (a conferência do emissor),
        os últimos fechamentos brutos do yfinance por data (o motor usa o último pregão encerrado
        antes do as_of, marcador da 2B, §2.2), o calendário de pregões
        quando a data ex depende dele e os dividendos do yfinance, só para conferência; ou a
        abstenção. A conta, com o as_of, é do motor (`proventos_b3.entradas`). Provedor por
        `getattr`; sem ele, a chave fica de fora.
        """
        if dados.get('classe_ativo') not in ('STOCK', 'UNIT'):
            return
        provedor = getattr(self, 'b3_proventos', None)
        if provedor is None:
            return
        modelo = dados.get('modelo_bpp')
        if modelo != 'empresa':
            dados['proventos_b3'] = {
                'abstencao': f"fora do escopo do Bazin: modelo {modelo}"
                if modelo
                else "modelo empresa não demonstrado no BPP consolidado"
            }
            return
        historico = dados.get('historico')
        fechamentos = dados.get('fechamentos_brutos')
        if (
            dados.get('fonte_preco') != 'yfinance'
            or not isinstance(historico, pd.DataFrame)
            or historico.empty
            or not isinstance(fechamentos, dict)
            or not fechamentos
        ):
            dados['proventos_b3'] = {'abstencao': proventos_b3.MOTIVO_PRECO}
            return
        agora = datetime.now(UTC)
        hoje = agora.astimezone(proventos_b3.FUSO).date()
        anteriores = [date.fromisoformat(d) for d in fechamentos if date.fromisoformat(d) < hoje]
        if not anteriores:
            dados['proventos_b3'] = {'abstencao': proventos_b3.MOTIVO_PRECO_NAO_ENCERRADO}
            return
        referencia = max(anteriores)
        try:
            relacao = provedor.coletar(dados['cd_cvm'], agora)
        except Exception as exc:
            logger.warning(f"[{ticker}] relação de proventos da B3 indisponível: {exc}")
            dados['proventos_b3'] = {
                'abstencao': f"relação de proventos da B3 indisponível: {exc}"
            }
            return
        dividendos = None
        if 'Dividends' in historico:
            pagos = historico['Dividends'][historico['Dividends'] > 0]
            dividendos = {i.date().isoformat(): float(v) for i, v in pagos.items()}
        dados['proventos_b3'] = {
            'registros': list(relacao.registros),
            'total': relacao.total,
            'eventos_acoes': list(relacao.eventos_acoes),
            'dinheiro_complemento': list(relacao.dinheiro_complemento),
            'fechamentos': fechamentos,
            'pregoes': self._pregoes_da_data_ex(relacao.registros, referencia, agora),
            'conferencia_yfinance': dividendos,
            'coleta': relacao.coleta,
            'proveniencia': {
                'fonte': 'B3, relação de proventos em dinheiro (CompanyCall)',
                'nome_pregao': relacao.nome_pregao,
                'coleta': relacao.coleta,
                'arquivos': list(relacao.fontes),
            },
        }

    @staticmethod
    def _pregoes_da_data_ex(registros, referencia: date, agora: datetime) -> list | None:
        """Pregões do COTAHIST em torno do início da janela, se alguma data com cair nele.

        `None` quando nenhuma data ex depende do calendário, ou se o COTAHIST não puder ser
        lido (a série se abstém nesse caso).
        """
        inicio = proventos_b3.inicio_da_janela(referencia)
        limite = inicio - proventos_b3.FOLGA_SEM_PREGAO
        datas = {
            proventos_b3.ler_data(r.get('lastDatePriorEx'))
            for r in registros
            if isinstance(r, dict)
        }
        if not any(d is not None and limite < d < inicio for d in datas):
            return None
        meses = sorted({(limite.year, limite.month), (inicio.year, inicio.month)})
        try:
            pregoes = {
                cotacao.data
                for ano, mes in meses
                for cotacao in b3_cotahist.ler_zip_em_cache(
                    b3_cotahist.baixar_mes(ano, mes, agora)
                )
            }
        except Exception as exc:
            logger.warning(f"COTAHIST indisponível para a data ex: {exc}")
            return None
        return sorted(d.isoformat() for d in pregoes)

    def _buscar_liquidez(self, ticker: str, dados: dict[str, Any]) -> None:
        """Liquidez do ticker pelo COTAHIST (F2A-26), em `dados['liquidez']`, fora do prompt.

        Provedor por `getattr`; sem ele, a chave fica de fora. Falha de coleta é
        preservada no bloco para que os motores mostrem o aviso.
        """
        historico = getattr(self, 'cotahist', None)
        if historico is None:
            return
        try:
            coleta = historico.coletar(datetime.now(UTC))
        except Exception as exc:
            logger.warning(f"[{ticker}] COTAHIST indisponível para a liquidez: {exc}")
            dados['liquidez'] = {'abstencao': f'falha de coleta: {exc}'}
            return
        resultado = liquidez.metricas(
            coleta.cotacoes, ticker, meses_ausentes=coleta.meses_ausentes
        )
        dados['liquidez'] = (
            {'abstencao': resultado.motivo, 'meses_ausentes': list(coleta.meses_ausentes)}
            if isinstance(resultado, liquidez.Abstencao)
            else resultado
        )


        if isinstance(resultado, liquidez.Abstencao) and resultado.motivo == liquidez.MOTIVO_TICKER_AUSENTE:
            # A ausência do ticker só vale como zero se a coleta cobrir a janela.
            pregoes = len({c.data for c in coleta.cotacoes})
            dados['liquidez']['incompleta'] = pregoes < 63

    def _buscar_cvm_fii(self, ticker: str, dados: dict[str, Any]) -> bool:
        """VPA, P/VP, PL e cotas do FII pelo Informe Mensal da CVM (F2A-11; E-10, armadilha 9).

        O CNPJ vem só do índice oficial (F2A-31; sem ele, o Informe não é consultado). O P/VP
        oficial (preço ÷ valor da cota) sobrescreve as outras fontes; sem o Informe, elas
        ficam. Provedor por `getattr`: os motores montados com `__new__` não passam por aqui.
        """
        if not self._is_fii_ticker(ticker, dados):
            return False
        provedor = getattr(self, 'cvm_fii', None)
        if provedor is None:
            return False
        cnpj = dados.get('cnpj')  # F2A-31: só do índice oficial
        if not cnpj:
            if not dados.get('_sem_referencia'):
                dados.setdefault('riscos_dados', []).append(RISCO_FII_FORA_DO_INFORME)
            return False
        try:
            informe = provedor.obter_dados_fii(cnpj)
        except Exception as exc:
            logger.warning(f"[{ticker}] Informe Mensal do FII indisponível: {exc}")
            dados.setdefault('riscos_dados', []).append(
                f"Informe Mensal do FII indisponível: {exc}"
            )
            return False
        if not informe:
            return False
        if informe.get('abstencao'):
            dados.setdefault('riscos_dados', []).append(
                f"Informe Mensal do FII não usado: {informe['abstencao']}"
            )
            return False
        vpa = _as_float(informe.get('valor_cota'))
        if not vpa or vpa <= 0:
            return False
        campos: dict[str, Any] = {
            'vpa': vpa,
            'patrimonio_liquido': informe.get('patrimonio_liquido'),
        }
        preco = _as_float(dados.get('preco_atual'))
        if preco and preco > 0:
            campos['pvp'] = preco / vpa
        # F2B-16 (BUG-2A-12): o que o Informe entregou, para a validação cruzada (F2A-5).
        _guardar_por_fonte(dados, 'CVM', campos)
        preenchidos = merge_if_valid(
            dados, campos, overwrite=True, allowed_keys=set(FUNDAMENTAL_KEYS)
        )
        self._record_field_sources(dados, preenchidos, 'CVM')
        dados['cotas_emitidas'] = informe.get('cotas_emitidas')
        dados['cvm_fii_dt_referencia'] = informe.get('dt_referencia')
        if informe.get('proveniencia'):
            # P/VP fica de fora: depende também do preço, que não tem registro (F2A-32).
            dados.setdefault('proveniencia', {}).update(
                {
                    campo: informe['proveniencia']
                    for campo in preenchidos
                    if campo not in _CAMPOS_COM_PRECO
                }
            )
        _registrar_fonte_fundamentos(dados, 'CVM')
        dados['cvm_disponivel'] = True
        return True

    @staticmethod
    def _roe_guardado(dados: dict[str, Any], fonte: str, valor: Any) -> float | None:
        """ROE depois da guarda de fronteira (F2A-30).

        O valor descartado não entra na cascata; o de outra fonte, se houver, fica. O descarte
        vai para `riscos_dados` e para `dados['proveniencia']['roe_descartes']`, sem tocar no
        registro da fonte que preencheu o campo.
        """
        # F2B-18: o piso vale só nas fontes de mercado; o ROE dos controladores da CVM não
        # passa por ele (decisão C da [AUDITORIA], 18/10/2026).
        roe, motivo = normalizacao.guardar_roe(valor, com_piso=fonte != 'cvm')
        if motivo:
            dados.setdefault('riscos_dados', []).append(f"ROE descartado ({fonte}): {motivo}")
            dados.setdefault('proveniencia', {}).setdefault('roe_descartes', []).append(
                {**normalizacao.proveniencia_roe(fonte), 'motivo': motivo}
            )
        return roe

    @staticmethod
    def _dy_guardado(dados: dict[str, Any], fonte: str, valor: Any) -> float | None:
        """DY de fonte posterior pelo invariante dos motores (F2B-39; BUG-2A-15, armadilha 4).

        Finito e fora de 0–25%, não entra no merge: o válido anterior fica, e o descarte vai
        para `riscos_dados` e `dados['proveniencia']['dy_descartes']`. Nenhuma conversão aqui:
        a da fronteira (`normalizacao`) continua a única. Ausente ou não finito, segue `None`.
        """
        numero = _as_float(valor)
        if numero is None:
            return None
        if _normalizar_dy(numero)[1]:
            return numero
        dados.setdefault('riscos_dados', []).append(
            f"DY descartado ({fonte}): {MOTIVO_DY_FORA_DA_FAIXA}"
        )
        dados.setdefault('proveniencia', {}).setdefault('dy_descartes', []).append(
            {'fonte': fonte, 'valor': numero, 'motivo': MOTIVO_DY_FORA_DA_FAIXA}
        )
        return None

    def _buscar_cvm(self, ticker: str, dados: dict[str, Any]) -> bool:
        """Preenche fundamentos a partir das DFPs oficiais da CVM.

        Cobre: ROE (dos controladores), margens, PL, lucro, receita, ativo circulante/total,
        alavancagem (dívida financeira líquida, F2A-8) e LPA, VPA, P/L e P/VP pela Composição do Capital do
        mesmo documento (F2A-3, `sentinela.data.acoes_cvm`). O `sharesOutstanding` do
        yfinance só entra na divergência (`dados['divergencia_acoes']`), nunca no cálculo.
        """
        cvm = getattr(self, 'cvm', None)
        if cvm is None:
            return False

        # F2A-31: o CD_CVM vem só do índice oficial; os mapas manuais não são mais lidos.
        cd_cvm = dados.get('cd_cvm')
        if cd_cvm is None:
            dados['cvm_disponivel'] = False
            # F2B-17 (BUG-2A-13): o FII é coberto pelo Informe Mensal, não pelas DFPs; sem
            # índice, o aviso já foi gravado na etapa da referência.
            if not dados.get('_sem_referencia') and not self._is_fii_ticker(ticker, dados):
                dados.setdefault('riscos_dados', []).append(RISCO_FORA_DA_CVM)
            return False

        try:
            # F2A-38: o modelo de demonstração vem do setor; o padrão (empresa) não é passado,
            # para manter a interface dos provedores anteriores ao F2A-33.
            modelo = contas_cvm.modelo_do_setor(dados.get('setor'))
            extra = {} if modelo == 'empresa' else {'modelo': modelo}
            self._serie_cvm(ticker, dados, cvm, cd_cvm, modelo)
            historico = cvm.calcular_indicadores(cd_cvm, anos=1, **extra)
            if not historico:
                dados['cvm_disponivel'] = False
                return False

            ind = historico[max(historico)]

            # Campos com mapeamento direto para FUNDAMENTAL_KEYS
            cvm_campos: dict[str, Any] = {}
            for cvm_key, market_key in _CVM_TO_MARKET.items():
                v = ind.get(cvm_key)
                if v is not None:
                    cvm_campos[market_key] = v

            for campo, motivo in (ind.get('contas_abstidas') or {}).items():
                dados.setdefault('riscos_dados', []).append(
                    f"{RISCO_CONTA_CVM} {campo}: {motivo}"
                )
            if ind.get('roe_motivo'):
                dados.setdefault('riscos_dados', []).append(
                    f"{RISCO_ROE_CVM}: {ind['roe_motivo']}"
                )
            if 'alavancagem_regime' in ind:
                # F2A-8: medida, regime e motivo de cada abstenção.
                dados['alavancagem_cvm'] = {
                    'regime': ind['alavancagem_regime'],
                    'divida_liquida': ind.get('divida_liquida'),
                    'ebitda': ind.get('ebitda'),
                    'motivos': dict(ind.get('alavancagem_motivos') or {}),
                }
                for campo, motivo in dados['alavancagem_cvm']['motivos'].items():
                    dados.setdefault("riscos_dados", []).append(
                        f"{RISCO_ALAVANCAGEM_CVM} ({campo}): {motivo}"
                    )
            cvm_campos.update(self._por_acao_cvm(ticker, dados, ind))
            obter_modelo = getattr(cvm, "modelo_do_documento", None)
            if callable(obter_modelo):
                # F2B-31 e F2B-4: escopo dos métodos pelo BPP consolidado, com a entrega da
                # DFP que o demonstra (o motor confere contra o as_of).
                dados["modelo_bpp"] = obter_modelo(cd_cvm, ind)
                dados["modelo_bpp_proveniencia"] = ind.get("proveniencia")
            obter_gordon = getattr(cvm, "gordon_do_documento", None)
            if callable(obter_gordon):
                instante_gordon = datetime.now(UTC)
                fato = obter_gordon(cd_cvm, ind, instante_gordon)
                if "abstencao" not in fato:
                    acoes = dados.get("acoes_cvm") or {}
                    doc = acoes.get("documento") or {}
                    mesmo_documento = (
                        doc.get("cnpj") == fato.get("cnpj")
                        and doc.get("dt_refer") == fato.get("fim")
                        and str(doc.get("versao")) == str(fato.get("versao"))
                    )
                    obter_recente = getattr(cvm, "composicao_mais_recente", None)
                    recente = (
                        obter_recente(
                            ind["cnpj"], instante_gordon, int(fato["fim"][:4])
                        )
                        if callable(obter_recente)
                        else {"abstencao": "composição recente indisponível"}
                    )
                    base = {"compativel": False, "avisos": [gordon_cvm.AVISO_EVENTOS]}
                    if (
                        mesmo_documento
                        and ind.get("composicao_capital") is not None
                        and recente.get("composicao") is not None
                        and acoes.get("escala")
                    ):
                        base = gordon_cvm.compatibilidade_base(
                            ind["composicao_capital"],
                            recente["composicao"],
                            escala=Escala[acoes["escala"]],
                            escala_recente=(
                                Escala[recente["escala"]]
                                if recente.get("escala")
                                else None
                            ),
                            especie=dados.get("especie"),
                            eh_unit=dados.get("classe_ativo") == "UNIT",
                            acoes_por_unit=dados.get("acoes_por_unit"),
                            shares_outstanding=_as_float(
                                dados.get("_shares_outstanding")
                            ),
                        )
                    base["proveniencia"] = recente.get("proveniencia")
                    if recente.get("abstencao"):
                        base["motivo"] = recente["abstencao"]
                    dados["base_acionaria_gordon"] = base
                    fato.update(
                        acoes_base=acoes.get("acoes") if mesmo_documento else None,
                        lpa=cvm_campos.get("lpa"),
                        fator_unit=acoes.get("acoes_por_papel", 1),
                        base_acionaria_compativel=base["compativel"],
                        direitos_compativeis=(
                            dados.get("classe_ativo") != "UNIT"
                            or (
                                acoes_cvm._unit_valida(dados.get("acoes_por_unit"))
                                and len(dados["acoes_por_unit"]) == 1
                            )
                        ),
                        avisos=base["avisos"],
                    )
                    dados["janela_contabil_cvm"] = (
                        date.fromisoformat(fato["inicio"]),
                        date.fromisoformat(fato["fim"]),
                    )
                dados["gordon_cvm"] = fato
            if "roe" in cvm_campos:
                # F2A-30: o ROE derivado da CVM passa pela mesma guarda.
                cvm_campos['roe'] = self._roe_guardado(dados, 'cvm', cvm_campos['roe'])
                if cvm_campos['roe'] is None:
                    del cvm_campos['roe']
            _guardar_por_fonte(dados, 'CVM', cvm_campos)

            preenchidos = merge_if_valid(
                dados,
                cvm_campos,
                overwrite=True,
                allowed_keys=set(FUNDAMENTAL_KEYS),
            )
            self._record_field_sources(dados, preenchidos, 'CVM')

            campos_fund = [c for c in preenchidos if c in FUNDAMENTAL_KEYS and c != 'quote_type']
            if ind.get('proveniencia') and campos_fund:
                # F2A-32: de quando é, de onde veio e quando foi coletado cada campo da CVM.
                # P/L e P/VP ficam de fora: dependem também do preço, que não tem registro.
                dados.setdefault('proveniencia', {}).update(
                    {
                        campo: ind['proveniencia']
                        for campo in campos_fund
                        if campo not in _CAMPOS_COM_PRECO
                    }
                )
                # F2A-37 (D20): a reserva do lucro ou do PL dos controladores vai para os campos
                # que dependem dela.
                reservas = ind.get('reservas_controladores') or {}
                for origem, campos_dependentes in _CAMPOS_DA_RESERVA.items():
                    for campo in campos_dependentes:
                        if origem in reservas and campo in dados['proveniencia']:
                            registro = dados['proveniencia'][campo]
                            dados['proveniencia'][campo] = {
                                **registro,
                                'reservas': [*registro.get('reservas', []), reservas[origem]],
                            }
                if 'vpa' in dados['proveniencia'] and dados.get('escala_pelo_consolidado'):
                    # F2B-10 (D16): a escala do VPA veio do consolidado, com a confirmação.
                    dados['proveniencia']['vpa'] = {
                        **dados['proveniencia']['vpa'],
                        'escala': dados['escala_pelo_consolidado'],
                    }
                if 'lpa' in dados['proveniencia'] and dados.get('lpa_cvm'):
                    # F2A-36 (D16): origem do LPA, com a marca do recalculado ou do sinal.
                    dados['proveniencia']['lpa'] = {
                        **dados['proveniencia']['lpa'],
                        'lpa': dados['lpa_cvm'],
                    }
            if campos_fund:
                _definir_fonte_fundamentos(dados, 'CVM')
                dados['cvm_disponivel'] = True
                logger.info(f"[{ticker}] CVM preencheu {len(campos_fund)} campos (cd_cvm={cd_cvm})")
                return True

        except Exception as exc:
            logger.warning(f"[{ticker}] CVM error: {exc}")

        dados['cvm_disponivel'] = False
        return False

    def _buscar_ifdata(self, dados: dict[str, Any], *, as_of: datetime) -> None:
        """Basileia e inadimplência do IF.data para banco (F2A-9), com a fonte e a data-base.

        Só para o setor de banco (F2A-2). O que falta vira limitação declarada em `riscos_dados`.
        """
        if contas_cvm.modelo_do_setor(dados.get('setor')) != 'banco':
            return
        riscos = dados.setdefault('riscos_dados', [])
        ifdata = getattr(self, 'ifdata', None)
        if ifdata is None:
            riscos.append(f"{RISCO_LIMITACAO_BANCO}: Basileia e inadimplência sem fonte (IF.data não consultado)")
            return
        try:
            capital = ifdata.capital(dados.get('cnpj'), as_of.astimezone(ZoneInfo('America/Sao_Paulo')).date(), as_of=as_of)
        except Exception as exc:
            riscos.append(f"{RISCO_LIMITACAO_BANCO}: Basileia e inadimplência sem fonte (IF.data indisponível: {exc})")
            return
        dados['basileia'] = capital.basileia
        dados['inadimplencia'] = capital.inadimplencia
        dados['ifdata'] = {
            'fonte': capital.fonte,
            'data_base': capital.data_base,
            'codinst': capital.codinst,
            'proveniencia': capital.proveniencia,
        }
        for campo, motivo in capital.motivos.items():
            riscos.append(f"{RISCO_LIMITACAO_BANCO} ({campo}): {motivo}")

    def _serie_cvm(
        self, ticker: str, dados: dict[str, Any], cvm: Any, cd_cvm: int, modelo: str
    ) -> None:
        """Série de cinco exercícios e TTM da CVM (F2A-7), em `dados['serie_cvm']` e `dados['ttm_cvm']`.

        Só disponibiliza os dados: nenhum campo dos métodos sai daqui (F2C-1), e o exercício
        corrente continua sendo o da chamada de um ano. Provedor sem a interface (anterior ao
        item) não passa pela etapa.
        """
        indicadores_da_serie = getattr(cvm, 'indicadores_da_serie', None)
        acumulados_ttm = getattr(cvm, 'acumulados_ttm', None)
        if indicadores_da_serie is None or acumulados_ttm is None:
            return
        hoje = date.today()
        try:
            classifier = getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER)
            exercicios = series_cvm.serie_anual(
                indicadores_da_serie(cd_cvm, hoje.year - 1, modelo),
                hoje.year - 1,
                especie=dados.get('especie'),
                classe=dados.get('classe_preferencial') or dados.get('especie'),
                classes_preferenciais=dados.get('classes_preferenciais'),
                eh_unit=classifier.classify(ticker, dados) == AssetType.UNIT,
                acoes_por_unit=dados.get('acoes_por_unit'),
            )
            dados['serie_cvm'] = {
                'exercicios': exercicios,
                'proventos_base': series_cvm.COMPETENCIA,
            }
            acumulados = acumulados_ttm(cd_cvm, hoje, modelo)
            if exercicios:
                atual = exercicios[-1]
                janelas = {(a.inicio, a.fim) for a in acumulados
                           if a.documento == 'DFP' and a.dt_refer == atual.get('dt_refer')
                           and str(a.versao) == str(atual.get('versao'))}
                if len(janelas) == 1:
                    dados['janela_contabil_cvm'] = next(iter(janelas))
            ttm = series_cvm.ttm(acumulados, hoje)
            dados['ttm_cvm'] = (
                {'abstencao': ttm.motivo} if isinstance(ttm, series_cvm.Abstencao) else ttm
            )
        except Exception as exc:
            logger.warning(f"[{ticker}] CVM série/TTM error: {exc}")

    def _por_acao_cvm(
        self, ticker: str, dados: dict[str, Any], ind: dict[str, Any]
    ) -> dict[str, float]:
        """LPA, VPA, P/L e P/VP da CVM; sem eles, o motivo vai para `riscos_dados`.

        O LPA dos métodos é o divulgado da classe do ticker, quando coerente; sem ele, o
        recalculado pela Composição do Capital (F2A-36, D19), que também serve de conferência
        (`acoes_cvm['lpa_recalculado']`, F2A-5). A origem fica em `dados['lpa_cvm']`. A escala
        indeterminada derruba o recalculado, o VPA e o P/VP, não o divulgado.

        Provedor que não informa `composicao_capital` (interface anterior ao F2A-3) não passou
        pela etapa: nada é derivado e nada é registrado.
        """
        if 'composicao_capital' not in ind:
            return {}
        classifier = getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER)
        eh_unit = classifier.classify(ticker, dados) == AssetType.UNIT
        acoes_por_unit = dados.get('acoes_por_unit')
        classe = dados.get('classe_preferencial') or dados.get('especie')
        composicao = ind.get('composicao_capital')
        especies_confirmadas = None
        if composicao is not None and all(
            isinstance(q, (int,float)) and not isinstance(q,bool) and math.isfinite(q) and q >= 0
            for q in (composicao.on, composicao.pn)
        ):
            presentes = {especie for especie, q in (('ON',composicao.on),('PN',composicao.pn)) if q > 0}
            declaradas = set(dados.get('especies_da_companhia') or ())
            if len(presentes) == 1 and presentes == declaradas and len(dados.get('classes_preferenciais') or ()) <= 1:
                especies_confirmadas = sorted(presentes)
        linhas, linha_agregada = acoes_cvm.linhas_da_especie_unica(
            _linhas_de_lpa(ind),
            ind.get('lpa_basico_agregado'),
            especies_confirmadas,
            lucro_controladores=ind.get('lucro_controladores'),
            acoes=composicao.total if composicao is not None else 0.0,
        )
        divulgados = acoes_cvm.divulgados_coerentes(
            linhas,
            ind.get('lucro_controladores'),
            ind.get('lucro_liquido'),
        )
        resultado = acoes_cvm.derivar_por_acao(
            lucro_controladores=ind.get('lucro_controladores'),
            pl_controladores=ind.get('pl_controladores'),
            composicao=ind.get('composicao_capital'),
            motivo_composicao=ind.get('composicao_motivo'),
            lpa_divulgado=acoes_cvm.divulgado_da_escala(divulgados),
            preco=_as_float(dados.get('preco_atual')),
            eh_unit=eh_unit,
            acoes_por_unit=acoes_por_unit,
            # F2B-10 (ficha 1.1, 7.7): escala pelo consolidado, confirmada pelo yfinance.
            lucro_consolidado=ind.get('lucro_liquido'),
            shares_outstanding=_as_float(dados.get('_shares_outstanding')),
        )
        if resultado.escala_pelo_consolidado is not None:
            dados['escala_pelo_consolidado'] = resultado.escala_pelo_consolidado
        fator = sum(acoes_por_unit.values()) if eh_unit and acoes_cvm._unit_valida(acoes_por_unit) else 1
        por_acao = resultado if isinstance(resultado, acoes_cvm.PorAcao) else None
        recalculado = por_acao.lpa / fator if por_acao and por_acao.lpa is not None else None
        lpa = acoes_cvm.lpa_dos_metodos(
            especie=dados.get('especie'),
            classe=classe,
            classes_preferenciais=dados.get('classes_preferenciais'),
            eh_unit=eh_unit,
            acoes_por_unit=acoes_por_unit,
            divulgados=divulgados,
            recalculado=recalculado,
        )
        self._registrar_abstencoes_por_acao(dados, resultado, lpa)
        campos: dict[str, Any] = {}
        if not isinstance(lpa, acoes_cvm.Abstencao):
            campos['lpa'], dados['lpa_cvm'] = lpa
            if linha_agregada is not None and dados['lpa_cvm'].get('origem') == 'divulgado':
                # F2B-11 (D16): o LPA veio da linha agregada da companhia de espécie única.
                dados['lpa_cvm'] = {
                    **dados['lpa_cvm'],
                    'linha_agregada': linha_agregada,
                    'notas': [*dados['lpa_cvm'].get('notas', []), linha_agregada['nota']],
                }
            preco = _as_float(dados.get('preco_atual'))
            if preco and preco > 0:
                campos['pl'] = preco / campos['lpa']
        if por_acao is None:
            return campos
        dados['acoes_cvm'] = {
            **por_acao.detalhe(
                {
                    'cnpj': ind.get('cnpj'),
                    'dt_refer': ind.get('cvm_dt_refer'),
                    'versao': ind.get('cvm_versao'),
                    'lpa_divulgado': ind.get('lpa_divulgado'),
                }
            ),
            'acoes_por_papel': fator,
            'lpa_recalculado': por_acao.lpa,
            'lpa_divulgado_comparado': _lpa_divulgado_comparado(
                divulgados,
                None if eh_unit else classe,
                None if eh_unit else dados.get('especie'),
            ),
        }
        dados['divergencia_acoes'] = acoes_cvm.divergencia_acoes(
            ind['composicao_capital'],
            por_acao.escala,
            especie=dados.get('especie'),
            eh_unit=eh_unit,
            acoes_por_unit=acoes_por_unit,
            shares_outstanding=_as_float(dados.get('_shares_outstanding')),
        )
        campos.update({'vpa': por_acao.vpa, 'pvp': por_acao.pvp})
        return {k: v for k, v in campos.items() if v is not None}

    @staticmethod
    def _registrar_abstencoes_por_acao(
        dados: dict[str, Any],
        resultado: Any,
        lpa: Any,
    ) -> None:
        """Motivos das abstenções por ação em `riscos_dados` (F2A-3 e F2A-36)."""
        riscos = dados.setdefault('riscos_dados', [])
        sem_lpa = isinstance(lpa, acoes_cvm.Abstencao)
        if isinstance(resultado, acoes_cvm.Abstencao):
            rotulo = RISCO_SEM_POR_ACAO_CVM if sem_lpa else RISCO_SEM_VPA_CVM
            riscos.append(f"{rotulo}: {resultado.motivo}")
            if sem_lpa and lpa.motivo.startswith(acoes_cvm.MOTIVOS_DO_DIVULGADO):
                riscos.append(f"{RISCO_SEM_LPA_CVM}: {lpa.motivo}")
        elif sem_lpa:
            riscos.append(f"{RISCO_SEM_LPA_CVM}: {lpa.motivo}")

    def _aplicar_cache_fundamentos(
        self,
        ticker: str,
        dados: dict[str, Any],
    ) -> bool:
        database = getattr(self, 'database', None)
        if database is None:
            return False

        try:
            cache = database.buscar_fundamentos_cache(ticker)
        except Exception as e:
            logger.warning(f"[{ticker}] Cache fundamentos indisponivel: {e}")
            return False

        if not cache:
            return False

        preenchidos = merge_if_valid(
            dados,
            cache,
            allowed_keys=set(FUNDAMENTAL_KEYS),
        )
        self._record_field_sources(dados, preenchidos, 'fundamentals_cache')
        if not preenchidos:
            return False

        dados['dados_cache'] = True
        _registrar_fonte_fundamentos(dados, 'cache')
        dados.setdefault('riscos_dados', []).append(
            'campos fundamentais preenchidos via cache'
        )
        logger.info(f"[{ticker}] Usando cache de fundamentos ({len(preenchidos)} campos)")
        return True

    def _aplicar_fallback_manual_fii(self, ticker: str, dados: dict[str, Any]) -> bool:
        ticker_norm = ticker.upper().replace(".SA", "").strip()
        if not self._is_fii_ticker(ticker_norm, dados):
            return False

        fallback = FII_MANUAL_FALLBACK.get(ticker_norm)
        if not fallback:
            return False

        preenchidos = merge_if_valid(
            dados,
            fallback,
            allowed_keys={'dy', 'pvp', 'vacancia'},
        )
        self._record_field_sources(dados, preenchidos, 'manual_fallback')
        if not preenchidos:
            return False

        dados['dados_manual'] = True
        _registrar_fonte_fundamentos(dados, 'manual_fii')
        dados.setdefault('riscos_dados', []).append(
            'fundamentos FII preenchidos manualmente'
        )
        logger.info(f"[{ticker_norm}] Fallback manual FII preencheu {len(preenchidos)} campos")
        return True

    def _salvar_cache_se_valido(self, ticker: str, dados: dict[str, Any]) -> None:
        if (
            dados.get('dados_cache')
            or dados.get('dados_manual')
            or not _fundamentos_validos_para_cache(
                dados,
                getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER),
            )
        ):
            return

        fonte = dados.get('fonte_fundamentos')
        if not fonte or fonte == 'yfinance_partial':
            return

        payload = {
            chave: dados[chave]
            for chave in FUNDAMENTAL_KEYS
            if chave in dados and not _is_field_missing(chave, dados.get(chave), dados)
        }
        if not _fundamentos_validos_para_cache(
            {'ticker': ticker, **payload},
            getattr(self, 'asset_classifier', _DEFAULT_ASSET_CLASSIFIER),
        ):
            return

        database = getattr(self, 'database', None)
        if database is None:
            return

        try:
            database.salvar_fundamentos_cache(ticker, payload, fonte)
        except Exception as e:
            logger.warning(f"[{ticker}] Falha ao salvar cache de fundamentos: {e}")
