"""Dataclass transport models for the current dict-based analysis flow."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Optional, TypeVar


T = TypeVar("T")


def _as_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return dict(data)
    return {}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _build_dataclass(cls: type[T], data: Any) -> T:
    raw = _as_dict(data)
    known = {item.name for item in fields(cls) if item.init and item.name != "extra"}
    values = {key: raw[key] for key in known if key in raw}

    extra: dict[str, Any] = {}
    raw_extra = raw.get("extra")
    if isinstance(raw_extra, dict):
        extra.update(raw_extra)
    extra.update({key: value for key, value in raw.items() if key not in known and key != "extra"})
    values["extra"] = extra
    return cls(**values)


def _serialize(value: Any) -> Any:
    if is_dataclass(value) and hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_serialize(item) for item in value)
    return value


def _to_dict(instance: Any) -> dict[str, Any]:
    data = dict(getattr(instance, "extra", {}) or {})
    for item in fields(instance):
        if item.name == "extra":
            continue
        data[item.name] = _serialize(getattr(instance, item.name))
    return data


def _coerce_model(model_cls: type[T], value: Any) -> T:
    if isinstance(value, model_cls):
        return value
    return model_cls.from_dict(value)


@dataclass
class MarketSnapshot:
    ticker: str = ""
    preco_atual: Any = None
    historico: Any = None
    quote_type: str = ""
    fonte_preco: Optional[str] = None
    fonte_fundamentos: Optional[str] = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "MarketSnapshot":
        return _build_dataclass(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass
class FundamentalsSnapshot:
    ticker: str = ""
    pl: Any = None
    pvp: Any = None
    dy: Any = None
    roe: Any = None
    lpa: Any = None
    vpa: Any = None
    roic: Any = None
    divida_liq_ebitda: Any = None
    div_liq_patrimonio: Any = None
    margem_liquida: Any = None
    margem_bruta: Any = None
    patrimonio_liquido: Any = None
    receita_liquida: Any = None
    lucro_liquido: Any = None
    ativo_total: Any = None
    ativo_circulante: Any = None
    vacancia: Any = None
    tipo: Optional[str] = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "FundamentalsSnapshot":
        return _build_dataclass(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass
class DataQualityReport:
    erro_scraper: bool = False
    dados_parciais: bool = False
    dados_cache: bool = False
    dados_manual: bool = False
    campos_faltantes: list[Any] = field(default_factory=list)
    riscos_dados: list[Any] = field(default_factory=list)
    pl_confiavel: Optional[bool] = None
    dy_confiavel: Optional[bool] = None
    confianca: Any = None
    score: Any = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.campos_faltantes = _as_list(self.campos_faltantes)
        self.riscos_dados = _as_list(self.riscos_dados)
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "DataQualityReport":
        return _build_dataclass(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass
class ValuationResult:
    fair_value: Any = None
    upside: Any = None
    score_final: Any = None
    recomendacao: str = ""
    metodos_usados: Any = None
    perfil: str = ""
    confianca: Any = None
    riscos: list[Any] = field(default_factory=list)
    pl_confiavel: Optional[bool] = None
    dy_confiavel: Optional[bool] = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.riscos = _as_list(self.riscos)
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "ValuationResult":
        return _build_dataclass(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass
class TechnicalResult:
    rsi: Any = None
    momento: str = ""
    tendencia: str = ""
    ma50: Any = None
    ma200: Any = None
    macd_line: Any = None
    macd_signal: Any = None
    macd_hist: Any = None
    macd_rec: str = ""
    bb_upper: Any = None
    bb_lower: Any = None
    bb_signal: str = ""
    atr: Any = None
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "TechnicalResult":
        return _build_dataclass(cls, data)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass
class AnalysisResult:
    ticker: str = ""
    is_fii: bool = False
    success: bool = True
    error: Optional[str] = None
    market: MarketSnapshot = field(default_factory=MarketSnapshot)
    fundamentals: FundamentalsSnapshot = field(default_factory=FundamentalsSnapshot)
    data_quality: DataQualityReport = field(default_factory=DataQualityReport)
    valuation: ValuationResult = field(default_factory=ValuationResult)
    technical: TechnicalResult = field(default_factory=TechnicalResult)
    peers: dict[str, Any] = field(default_factory=dict)
    ai_analysis: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    collected_at: Optional[str] = None
    confidence: Any = None
    warnings: list[Any] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.market = _coerce_model(MarketSnapshot, self.market)
        self.fundamentals = _coerce_model(FundamentalsSnapshot, self.fundamentals)
        self.data_quality = _coerce_model(DataQualityReport, self.data_quality)
        self.valuation = _coerce_model(ValuationResult, self.valuation)
        self.technical = _coerce_model(TechnicalResult, self.technical)
        self.peers = _as_dict(self.peers)
        self.raw = _as_dict(self.raw)
        self.warnings = _as_list(self.warnings)

    @classmethod
    def from_dict(cls, data: Any) -> "AnalysisResult":
        raw = _as_dict(data)
        known = {item.name for item in fields(cls) if item.init and item.name != "extra"}

        values: dict[str, Any] = {
            key: raw[key]
            for key in known
            if key in raw
            and key
            not in {
                "market",
                "fundamentals",
                "data_quality",
                "valuation",
                "technical",
            }
        }
        values["market"] = MarketSnapshot.from_dict(raw.get("market", raw))
        values["fundamentals"] = FundamentalsSnapshot.from_dict(raw.get("fundamentals", raw))
        values["data_quality"] = DataQualityReport.from_dict(raw.get("data_quality", raw))
        values["valuation"] = ValuationResult.from_dict(raw.get("valuation", raw))
        values["technical"] = TechnicalResult.from_dict(raw.get("technical", raw.get("tech", raw)))

        if "peers" not in values:
            values["peers"] = raw.get("peers", raw.get("peers_data", {}))
        if "ai_analysis" not in values:
            values["ai_analysis"] = raw.get("ai_analysis", raw.get("analise_ia"))
        if "raw" not in values:
            values["raw"] = raw

        extra: dict[str, Any] = {}
        raw_extra = raw.get("extra")
        if isinstance(raw_extra, dict):
            extra.update(raw_extra)
        extra.update({key: value for key, value in raw.items() if key not in known and key != "extra"})
        values["extra"] = extra
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)

