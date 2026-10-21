import calendar
import io
import logging
import math
import re
import threading
import zipfile
from collections import OrderedDict
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from cvm_download import baixar_arquivo
from sentinela.data import (
    acoes_cvm,
    contas_cvm,
    controladores,
    divida_liquida,
    gordon_cvm,
    proveniencia,
    series_cvm,
)
from sentinela.data.acoes_cvm import (
    MOTIVO_DOCUMENTO_DIFERENTE,
    MOTIVO_SEM_COMPOSICAO,
    Composicao,
    roe_dos_controladores,
)

logger = logging.getLogger(__name__)

_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
_ITR_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/itr_cia_aberta_{ano}.zip"

# Chave semântica → (campo da tabela de contas, demonstrativo). A leitura confere o par
# (código, descrição) pela tabela do F2A-33 (ADR-0003, D20); nunca só o código.
_CONTAS: dict[str, tuple[str, str]] = {
    "ativo_total":        ("ativo_total", "bpa"),
    "ativo_circulante":   ("ativo_circulante", "bpa"),
    "passivo_total":      ("passivo_total", "bpp"),
    "passivo_circulante": ("passivo_circulante", "bpp"),
    "patrimonio_liquido": ("pl_total", "bpp"),
    "receita_liquida":    ("receita_liquida", "dre"),
    "ebit":               ("ebit", "dre"),
    "lucro_liquido":      ("lucro_liquido", "dre"),
}

# F2A-9: campos sem significado para banco; abstêm-se com o motivo, nunca com outra conta.
_SEM_SIGNIFICADO_PARA_BANCO = frozenset({"receita_liquida"})
MOTIVO_SEM_SIGNIFICADO_BANCO = "sem significado para banco (modelo de instituição financeira)"

# F2A-8: demonstrativo de cada conta da dívida financeira líquida.
_DEMONSTRATIVO_DA_DIVIDA = {
    "emprestimos_circulante": "bpp",
    "emprestimos_nao_circulante": "bpp",
    "caixa": "bpa",
    "aplicacoes": "bpa",
}

_OUTPUT_COLS = ["CNPJ_CIA", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA"]

# Memoização por processo dos demonstrativos já filtrados (E-16). A chave inclui
# mtime e tamanho do ZIP: download novo invalida a entrada.
_CACHE_MAX_ENTRADAS = 32
_cache_parse: OrderedDict[tuple, pd.DataFrame] = OrderedDict()
_cache_trava = threading.Lock()
_travas_chave: dict[tuple, threading.Lock] = {}

# F2A-3: linhas 3.99 (LPA divulgado, em R$ por ação, sem a escala monetária) e Composição
# do Capital, por arquivo. A chave inclui mtime e tamanho, como a do parse.
_cache_por_acao: dict[tuple, tuple[pd.DataFrame, pd.DataFrame]] = {}
_CACHE_POR_ACAO_MAX = 8
# F2A-32: índice de entregas do ZIP (`<doc>_cia_aberta_<ano>.csv`, com `DT_RECEB`), por arquivo.
_cache_entregas: dict[tuple, list[dict]] = {}
_CACHE_ENTREGAS_MAX = 8
_COLUNAS_COMPOSICAO = {
    "on": "QT_ACAO_ORDIN_CAP_INTEGR",
    "pn": "QT_ACAO_PREF_CAP_INTEGR",
    "tesouraria_on": "QT_ACAO_ORDIN_TESOURO",
    "tesouraria_pn": "QT_ACAO_PREF_TESOURO",
    "tesouraria_total": "QT_ACAO_TOTAL_TESOURO",
}


def _ler(df: pd.DataFrame, campo: str, modelo: str):
    return contas_cvm.ler_conta(df.to_dict("records"), campo, modelo, contas_cvm.tabela())


def _pares_de_todos_os_modelos(campo: str) -> tuple[contas_cvm.Conta, ...]:
    """Os pares do campo em qualquer modelo, sem repetir, na ordem da tabela.

    O caminho dos controladores do F2A-3 achava a linha pela descrição em qualquer modelo; a
    união preserva isso (o banco sem setor no índice segue achando "aos sócios").
    """
    vistos: dict[tuple[str, str], contas_cvm.Conta] = {}
    for conta in contas_cvm.tabela():
        if conta.campo == campo:
            vistos.setdefault(
                (conta.codigo, conta.descricao), replace(conta, modelo="empresa")
            )
    return tuple(vistos.values())


def _ler_em_qualquer_modelo(df: pd.DataFrame, campo: str):
    return contas_cvm.ler_conta(
        df.to_dict("records"), campo, "empresa", _pares_de_todos_os_modelos(campo)
    )


def lucro_controladores_com_reserva(
    dre_emp: pd.DataFrame, bpp_emp: pd.DataFrame
) -> controladores.Resultado:
    """Lucro atribuído aos sócios da controladora (3.11.01, 3.09.01 ou 3.13.01), pela tabela.

    As reservas seguem a D20 e a decisão 7.2 da ficha (`sentinela.data.controladores`). As
    quatro leituras, inclusive a dos não controladores no balanço, são em qualquer modelo
    (F2A-41), por isso o modelo do setor não entra.
    """
    return controladores.lucro_dos_controladores(
        _ler_em_qualquer_modelo(dre_emp, "lucro_controladores"),
        _ler_em_qualquer_modelo(dre_emp, "lucro_nao_controladores"),
        _ler_em_qualquer_modelo(dre_emp, "lucro_liquido"),
        _ler_em_qualquer_modelo(bpp_emp, "pl_nao_controladores"),
    )


def pl_controladores_com_reserva(
    bpp_emp: pd.DataFrame, dre_emp: pd.DataFrame, modelo: str = "empresa"
) -> controladores.Resultado:
    """PL dos controladores: PL total menos não controladores, pela tabela de contas.

    Sem o par do PL no modelo (a 2.03 do banco é "Provisões", F2A-16), o valor é `None`: o PL
    certo dos bancos é do F2A-9.
    """
    return controladores.pl_dos_controladores(
        _ler(bpp_emp, "pl_total", modelo),
        _ler(bpp_emp, "pl_nao_controladores", modelo),
        _ler_em_qualquer_modelo(dre_emp, "lucro_nao_controladores"),
    )


def lpa_divulgado(linhas_399: pd.DataFrame) -> dict | None:
    """LPA básico divulgado no documento, pela espécie da descrição: ON, depois PN.

    O código da conta não define a espécie (a 3.99.01.01 é PN em algumas companhias); sem
    linha por espécie, vale a 3.99.01 e, por fim, a 3.99, se diferentes de zero.
    """
    if linhas_399.empty:
        return None
    basico = linhas_399[linhas_399["CD_CONTA"].str.startswith("3.99.01.")]
    descricao = basico["DS_CONTA"].fillna("").str.strip().str.upper()
    candidatos = [
        ("ON", basico[descricao == "ON"]),
        ("PN", basico[descricao.str.startswith("PN")]),
        ("BASICO", linhas_399[linhas_399["CD_CONTA"] == "3.99.01"]),
        ("BASICO", linhas_399[linhas_399["CD_CONTA"] == "3.99"]),
    ]
    for especie, linhas in candidatos:
        valores = pd.to_numeric(linhas["VL_CONTA"], errors="coerce")
        valores = valores[valores.notna() & (valores != 0)]
        if not valores.empty:
            return {
                "especie": especie,
                "conta": str(linhas.loc[valores.index[0], "CD_CONTA"]),
                "valor": float(valores.iloc[0]),
            }
    return None


_CLASSE_NA_DESCRICAO = re.compile(r"^(ON|PN[A-Z]?)$")


def lpa_basico_por_classe(
    linhas_399: pd.DataFrame,
) -> dict[str, list[float] | acoes_cvm.Abstencao]:
    """Valores das linhas de LPA básico (3.99.01.xx) por classe da descrição, sem zeros.

    Cada classe fica na sua chave (ON, PN, PNA, PNB…; F2A-36, D19, regra 3); linhas repetidas
    ficam todas, para a conferência de conflito (`acoes_cvm.divulgados_coerentes`).
    """
    if linhas_399.empty:
        return {}
    basico = linhas_399[linhas_399["CD_CONTA"].str.startswith("3.99.01.")]
    descricao = basico["DS_CONTA"].fillna("").str.strip().str.upper()
    valores = pd.to_numeric(basico["VL_CONTA"], errors="coerce")
    resultado: dict[str, list[float] | acoes_cvm.Abstencao] = {}
    for classe, valor in zip(descricao, valores):
        if not _CLASSE_NA_DESCRICAO.match(classe):
            continue
        if pd.isna(valor) or not math.isfinite(valor):
            resultado[classe] = acoes_cvm.Abstencao(acoes_cvm.MOTIVO_LPA_INVALIDO)
        elif valor != 0 and not isinstance(resultado.get(classe), acoes_cvm.Abstencao):
            resultado.setdefault(classe, []).append(float(valor))
    return resultado


def lpa_basico_agregado(linhas_399: pd.DataFrame) -> dict[str, float | acoes_cvm.Abstencao | None]:
    """Valores das linhas agregadas 3.99.01 e 3.99, sem espécie (ficha 1.1, 7.8); zero vira `None`."""
    resultado: dict[str, float | acoes_cvm.Abstencao | None] = {}
    for conta in ("3.99.01", "3.99"):
        linhas = linhas_399[linhas_399["CD_CONTA"] == conta] if not linhas_399.empty else linhas_399
        valores = pd.to_numeric(linhas["VL_CONTA"], errors="coerce") if not linhas.empty else []
        if any(pd.isna(v) or not math.isfinite(v) for v in valores):
            resultado[conta] = acoes_cvm.Abstencao(acoes_cvm.MOTIVO_LPA_INVALIDO)
            continue
        numeros = [float(v) for v in valores if pd.notna(v) and v != 0]
        resultado[conta] = (acoes_cvm.Abstencao(acoes_cvm.MOTIVO_LINHAS_CONFLITANTES)
                            if len(set(numeros)) > 1 else numeros[0] if numeros else None)
    return resultado


def lpa_divulgado_por_especie(linhas_399: pd.DataFrame) -> dict[str, float]:
    """Primeiro LPA básico divulgado de cada classe (ON, PN, PNA…), sem zeros (F2A-5)."""
    return {
        classe: valores[0] for classe, valores in lpa_basico_por_classe(linhas_399).items()
        if not isinstance(valores, acoes_cvm.Abstencao)
    }


def composicao_do_documento(
    cc: pd.DataFrame, cnpj: str | None, dt_refer: str | None, versao: str | None
) -> tuple[Composicao | None, str | None]:
    """Composição do Capital do mesmo documento (CNPJ, `DT_REFER`, `VERSAO`) ou o motivo da falta."""
    if cc.empty or not cnpj:
        return None, MOTIVO_SEM_COMPOSICAO
    da_cia = cc[cc["CNPJ_CIA"] == cnpj]
    if da_cia.empty:
        return None, MOTIVO_SEM_COMPOSICAO
    mesmo = da_cia[
        (da_cia["DT_REFER"].astype(str) == str(dt_refer))
        & (da_cia["VERSAO"].astype(str) == str(versao))
    ]
    if mesmo.empty:
        return None, MOTIVO_DOCUMENTO_DIFERENTE
    linha = mesmo.iloc[0]
    valores = {}
    for campo, coluna in _COLUNAS_COMPOSICAO.items():
        bruto = linha.get(coluna)
        if campo == "tesouraria_total" and (bruto is None or pd.isna(bruto)):
            continue
        numero = pd.to_numeric(bruto, errors="coerce")
        if (
            pd.api.types.is_bool(bruto) or pd.isna(numero) or not math.isfinite(numero)
            or numero < 0 or numero % 1
        ):
            return None, f"quantidade de ações ausente ou inválida: {coluna}"
        valores[campo] = float(numero)
    if "tesouraria_total" not in valores:
        # Sem o total da tesouraria, vale a soma das espécies.
        valores["tesouraria_total"] = valores["tesouraria_on"] + valores["tesouraria_pn"]
    if valores["tesouraria_on"] > valores["on"] or valores["tesouraria_pn"] > valores["pn"]:
        return None, "Composição do Capital inválida: tesouraria maior que a espécie"
    return (
        Composicao(
            **valores,
            dt_refer=str(linha["DT_REFER"]),
            versao=str(linha["VERSAO"]),
        ),
        None,
    )


class CVMProvider:
    def __init__(self, cache_dir: str = "data/cvm"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Cache de arquivos
    # ------------------------------------------------------------------

    def _cache_path(self, nome: str) -> Path:
        return self.cache_dir / nome

    def baixar_dfp(self, ano: int) -> Path:
        """Baixa o ZIP de DFP do ano e retorna o Path local (com cache 7d), com a proveniência ao lado."""
        caminho = baixar_arquivo(_DFP_URL.format(ano=ano), self._cache_path(f"dfp_{ano}.zip"))
        proveniencia.registrar_sem_falhar(caminho, _DFP_URL.format(ano=ano), "DFP", str(ano))
        return caminho

    def baixar_itr(self, ano: int) -> Path:
        """Baixa o ZIP de ITR do ano e retorna o Path local (com cache 7d), com a proveniência ao lado."""
        caminho = baixar_arquivo(_ITR_URL.format(ano=ano), self._cache_path(f"itr_{ano}.zip"))
        proveniencia.registrar_sem_falhar(caminho, _ITR_URL.format(ano=ano), "ITR", str(ano))
        return caminho

    def _entregas(self, zip_path: Path) -> list[dict]:
        """Linhas do índice de entregas do ZIP (`dfp_cia_aberta_<ano>.csv` ou o do ITR)."""
        stat = Path(zip_path).stat()
        chave = (str(Path(zip_path).resolve()), stat.st_mtime_ns, stat.st_size)
        with _cache_trava:
            if chave in _cache_entregas:
                return _cache_entregas[chave]
        with zipfile.ZipFile(zip_path) as zf:
            nome = next(
                n for n in zf.namelist() if re.fullmatch(r"(dfp|itr)_cia_aberta_\d{4}\.csv", n)
            )
            with zf.open(nome) as f:
                linhas = pd.read_csv(
                    io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str
                ).to_dict("records")
        with _cache_trava:
            _cache_entregas[chave] = linhas
            while len(_cache_entregas) > _CACHE_ENTREGAS_MAX:
                _cache_entregas.pop(next(iter(_cache_entregas)))
        return linhas

    def proveniencia_do_documento(
        self, zip_path: Path, ano: int, cnpj: str | None, dt_refer: str | None, versao: str | None
    ) -> dict | None:
        """Proveniência da DFP usada (F2A-32): período, entrega (`DT_RECEB`), versão, fonte e hash.

        `None` se o arquivo local não existe ou não é legível.
        """
        try:
            arquivo = proveniencia.registrar_arquivo(
                zip_path, _DFP_URL.format(ano=ano), "DFP", str(ano)
            )
        except OSError:
            return None
        try:
            entrega = proveniencia.entrega_no_indice(
                self._entregas(zip_path),
                {"CNPJ_CIA": cnpj, "DT_REFER": dt_refer, "VERSAO": versao},
            )
        except (OSError, StopIteration, ValueError, KeyError, zipfile.BadZipFile):
            entrega = None
        return arquivo.do_documento(
            dt_refer, versao, entrega, proveniencia.MOTIVO_DOCUMENTO_FORA_DO_INDICE
        ).para_dict()

    # ------------------------------------------------------------------
    # Leitura e parse de CSVs dentro do ZIP
    # ------------------------------------------------------------------

    def _find_csv_name(self, zip_path: Path, tipo: str) -> str:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if tipo in name and name.lower().endswith(".csv"):
                    return name
        raise FileNotFoundError(f"Tipo '{tipo}' não encontrado em {zip_path.name}")

    def _read_raw(self, zip_path: Path, tipo: str) -> pd.DataFrame:
        csv_name = self._find_csv_name(zip_path, tipo)
        with zipfile.ZipFile(zip_path) as zf, zf.open(csv_name) as f:
            return pd.read_csv(
                io.TextIOWrapper(f, encoding="latin-1"),
                sep=";",
                dtype=str,
                low_memory=False,
            )

    def parsear_demonstrativo(
        self,
        zip_path: Path,
        tipo: str,
        include_cd_cvm: bool = False,
        include_versao: bool = False,
        include_periodo: bool = False,
    ) -> pd.DataFrame:
        """
        Lê o CSV do tipo dentro do ZIP e retorna DataFrame limpo.
        Por padrão, retorna 5 colunas:
        CNPJ_CIA, DT_REFER, CD_CONTA, DS_CONTA, VL_CONTA.

        Se include_cd_cvm for True, inclui a coluna CD_CVM. Se include_periodo for True,
        inclui DT_INI_EXERC e DT_FIM_EXERC (F2A-7: acumulado e trimestre do ITR).

        Aplica a escala monetária (MIL -> BRL) em VL_CONTA.

        Filtros aplicados:
        - ORDEM_EXERC == "ÚLTIMO"  (descarta reapresentações)
        - GRUPO_DFP contém "Consolidado"
        """
        stat = Path(zip_path).stat()
        chave = (
            str(Path(zip_path).resolve()),
            stat.st_mtime_ns,
            stat.st_size,
            tipo,
            include_cd_cvm,
            include_versao,
            include_periodo,
        )
        with _cache_trava:
            trava = _travas_chave.setdefault(chave[:1] + chave[3:], threading.Lock())
        with trava:
            with _cache_trava:
                if chave in _cache_parse:
                    _cache_parse.move_to_end(chave)
                    return _cache_parse[chave].copy()
            df = self._parsear_sem_cache(
                zip_path, tipo, include_cd_cvm, include_versao, include_periodo
            )
            with _cache_trava:
                _cache_parse[chave] = df
                while len(_cache_parse) > _CACHE_MAX_ENTRADAS:
                    _cache_parse.popitem(last=False)
        return df.copy()

    def _parsear_sem_cache(
        self,
        zip_path: Path,
        tipo: str,
        include_cd_cvm: bool,
        include_versao: bool,
        include_periodo: bool = False,
    ) -> pd.DataFrame:
        df = self._read_raw(zip_path, tipo)

        if "ORDEM_EXERC" in df.columns:
            df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
        if "GRUPO_DFP" in df.columns:
            df = df[df["GRUPO_DFP"].str.contains("Consolidado", na=False)]

        df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"], errors="coerce")

        if "CD_CVM" in df.columns:
            df["CD_CVM"] = pd.to_numeric(df["CD_CVM"], errors="coerce").astype("Int64")

        if "ESCALA_MOEDA" in df.columns:
            mask_mil = df["ESCALA_MOEDA"].str.upper() == "MIL"
            df.loc[mask_mil, "VL_CONTA"] = df.loc[mask_mil, "VL_CONTA"] * 1000

        cols = [c for c in _OUTPUT_COLS if c in df.columns]
        if include_cd_cvm and "CD_CVM" in df.columns:
            cols.append("CD_CVM")
        if include_versao and "VERSAO" in df.columns:
            cols.append("VERSAO")
        if include_periodo:
            cols += [c for c in ("DT_INI_EXERC", "DT_FIM_EXERC") if c in df.columns]

        return df[cols].reset_index(drop=True)

    def _dados_por_acao(self, zip_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
        """(linhas 3.99 da DRE consolidada, sem escala monetária; Composição do Capital).

        Frames vazios se o arquivo não existe ou não tem os CSVs: a CVM se abstém.
        """
        vazio = (pd.DataFrame(), pd.DataFrame())
        try:
            stat = Path(zip_path).stat()
        except OSError:
            return vazio
        chave = (str(Path(zip_path).resolve()), stat.st_mtime_ns, stat.st_size)
        with _cache_trava:
            if chave in _cache_por_acao:
                return _cache_por_acao[chave]
        try:
            dre = self._read_raw(zip_path, "DRE_con")
            cc = self._read_raw(zip_path, "composicao_capital")
            if "ORDEM_EXERC" in dre.columns:
                dre = dre[dre["ORDEM_EXERC"] == "ÚLTIMO"]
            linhas_399 = dre[dre["CD_CONTA"].astype(str).str.startswith("3.99")][
                ["CNPJ_CIA", "DT_REFER", "VERSAO", "CD_CONTA", "DS_CONTA", "VL_CONTA"]
            ].reset_index(drop=True)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            return vazio
        with _cache_trava:
            _cache_por_acao[chave] = (linhas_399, cc)
            while len(_cache_por_acao) > _CACHE_POR_ACAO_MAX:
                _cache_por_acao.pop(next(iter(_cache_por_acao)))
        return linhas_399, cc


    def _dva_do_documento(
        self, zip_path: Path, cd_cvm: int, dt_refer: str | None, versao: str | None
    ) -> pd.DataFrame:
        """Linhas da DVA consolidada do documento; frame vazio sem a DVA (a conta se abstém)."""
        try:
            dva = self.parsear_demonstrativo(
                zip_path, "DVA_con", include_cd_cvm=True, include_versao=True
            )
            return dva[
                (dva["CD_CVM"] == cd_cvm)
                & (dva["DT_REFER"].astype(str) == str(dt_refer))
                & (dva["VERSAO"].astype(str) == str(versao))
            ]
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            return pd.DataFrame(columns=_OUTPUT_COLS)

    # ------------------------------------------------------------------
    # Cálculo de indicadores históricos
    # ------------------------------------------------------------------

    def calcular_indicadores(
        self, cd_cvm: int, anos: int = 5, modelo: str = "empresa", ano_final: int | None = None
    ) -> dict:
        """
        Retorna dict {ano: {indicador: valor}} para os últimos N anos, até `ano_final`
        (padrão: o ano anterior ao corrente).

        Indicadores: ativo_total, ativo_circulante, passivo_total,
        passivo_circulante, patrimonio_liquido, receita_liquida, ebit,
        lucro_liquido, roe, margem_liquida, divida_pl (passivo total − PL, sobre o PL; sem uso
        na cascata) e, pelo F2A-8, divida_liquida, ebitda, divida_liq_ebitda,
        div_liq_patrimonio, alavancagem_motivos e alavancagem_regime.

        `modelo` é o modelo de demonstração (`contas_cvm.modelo_do_setor`). Cada conta é lida
        pelo par (código, descrição); sem correspondência, o campo fica `None` e o motivo vai
        para `contas_abstidas`. Banco lê o PL, o lucro e os não controladores pelas contas do
        modelo de instituição financeira (F2A-9); receita e margem não têm significado para
        banco e se abstêm com esse motivo. O lucro dos controladores procura os pares de todos
        os modelos, como o F2A-3 fazia pela descrição.
        """
        if ano_final is None:
            ano_final = date.today().year - 1
        resultado: dict[int, dict] = {}

        for delta in range(anos):
            ano = ano_final - delta
            try:
                zip_path = self.baixar_dfp(ano)
                bpa = self.parsear_demonstrativo(zip_path, "BPA_con", include_cd_cvm=True, include_versao=True)
                bpp = self.parsear_demonstrativo(zip_path, "BPP_con", include_cd_cvm=True, include_versao=True)
                dre = self.parsear_demonstrativo(zip_path, "DRE_con", include_cd_cvm=True, include_versao=True)

                def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
                    if "CD_CVM" in df.columns:
                        return df[df["CD_CVM"] == cd_cvm]
                    return df.iloc[0:0]

                bpa_emp = _filtrar(bpa)
                bpp_emp = _filtrar(bpp)
                dre_emp = _filtrar(dre)

                # Descobre a maior VERSAO do DT_REFER mais recente
                metadata: dict = {}
                df_concat = pd.concat([bpa_emp, bpp_emp, dre_emp], ignore_index=True)

                if not df_concat.empty and "DT_REFER" in df_concat.columns:
                    if "VERSAO" in df_concat.columns:
                        # Converte VERSAO para numérico temporariamente para ordenação correta (ex: "10" > "9")
                        df_concat["_VERSAO_NUM"] = pd.to_numeric(df_concat["VERSAO"], errors="coerce").fillna(0)
                        df_concat = df_concat.sort_values(by=["DT_REFER", "_VERSAO_NUM"], ascending=[False, False])
                        df_concat = df_concat.drop(columns=["_VERSAO_NUM"])
                    else:
                        df_concat = df_concat.sort_values(by=["DT_REFER"], ascending=[False])

                    row = df_concat.iloc[0]

                    dt_ref = str(row["DT_REFER"]) if pd.notna(row["DT_REFER"]) else None
                    ver = str(row["VERSAO"]) if "VERSAO" in row and pd.notna(row["VERSAO"]) else None

                    metadata["cvm_dt_refer"] = dt_ref
                    metadata["cvm_versao"] = ver

                    def _filtrar_versao(df: pd.DataFrame) -> pd.DataFrame:
                        if df.empty:
                            return df
                        if dt_ref and "DT_REFER" in df.columns:
                            df = df[df["DT_REFER"].astype(str) == dt_ref]
                        if ver and "VERSAO" in df.columns:
                            df = df[df["VERSAO"].astype(str) == ver]
                        return df

                    bpa_emp = _filtrar_versao(bpa_emp)
                    bpp_emp = _filtrar_versao(bpp_emp)
                    dre_emp = _filtrar_versao(dre_emp)

                demonstrativos = {"bpa": bpa_emp, "bpp": bpp_emp, "dre": dre_emp}
                valores: dict[str, float | None] = {}
                leituras: dict[str, contas_cvm.Leitura | contas_cvm.Abstencao] = {}
                contas_abstidas: dict[str, str] = {}
                for chave, (campo, demonstrativo) in _CONTAS.items():
                    if modelo == "banco" and chave in _SEM_SIGNIFICADO_PARA_BANCO:
                        valores[chave] = None
                        leituras[chave] = contas_cvm.Abstencao(MOTIVO_SEM_SIGNIFICADO_BANCO)
                        contas_abstidas[chave] = MOTIVO_SEM_SIGNIFICADO_BANCO
                        if chave == "receita_liquida":
                            contas_abstidas["margem_liquida"] = MOTIVO_SEM_SIGNIFICADO_BANCO
                        continue
                    leitura = _ler(demonstrativos[demonstrativo], campo, modelo)
                    leituras[chave] = leitura
                    if isinstance(leitura, contas_cvm.Leitura):
                        valores[chave] = leitura.valor
                        continue
                    valores[chave] = None
                    if leitura.motivo != contas_cvm.MOTIVO_LINHA_AUSENTE:
                        contas_abstidas[chave] = f"{leitura.motivo} ({leitura.detalhe})"
                ativo_total        = valores["ativo_total"]
                ativo_circulante   = valores["ativo_circulante"]
                passivo_total      = valores["passivo_total"]
                passivo_circulante = valores["passivo_circulante"]
                pl                 = valores["patrimonio_liquido"]
                receita            = valores["receita_liquida"]
                ebit               = valores["ebit"]
                lucro              = valores["lucro_liquido"]

                cnpj = next(
                    (str(df["CNPJ_CIA"].iloc[0]) for df in (dre_emp, bpp_emp, bpa_emp)
                     if not df.empty and "CNPJ_CIA" in df.columns),
                    None,
                )
                lucro_res = lucro_controladores_com_reserva(dre_emp, bpp_emp)
                pl_res = pl_controladores_com_reserva(bpp_emp, dre_emp, modelo)
                lucro_ctrl, pl_ctrl = lucro_res.valor, pl_res.valor
                linhas_399, cc = self._dados_por_acao(zip_path)
                if not linhas_399.empty and cnpj:
                    linhas_399 = linhas_399[
                        (linhas_399["CNPJ_CIA"] == cnpj)
                        & (linhas_399["DT_REFER"].astype(str) == str(metadata.get("cvm_dt_refer")))
                        & (linhas_399["VERSAO"].astype(str) == str(metadata.get("cvm_versao")))
                    ]
                else:
                    linhas_399 = pd.DataFrame()
                composicao, motivo_composicao = composicao_do_documento(
                    cc, cnpj, metadata.get("cvm_dt_refer"), metadata.get("cvm_versao")
                )
                roe_ctrl, motivo_roe = roe_dos_controladores(lucro_ctrl, pl_ctrl)
                alavancagem = divida_liquida.medir(
                    modelo=modelo,
                    contas={
                        campo: _ler(demonstrativos[_DEMONSTRATIVO_DA_DIVIDA[campo]], campo, "empresa")
                        for campo in divida_liquida.CAMPOS_DA_DIVIDA
                    },
                    ebit=leituras["ebit"],
                    depreciacao=_ler(
                        self._dva_do_documento(
                            zip_path, cd_cvm, metadata.get("cvm_dt_refer"), metadata.get("cvm_versao")
                        ),
                        "depreciacao_amortizacao",
                        "empresa",
                    ),
                    pl=pl,
                )
                if roe_ctrl is None:
                    # F2A-37: o motivo da abstenção do lucro ou do PL é mais preciso que o genérico.
                    motivo_roe = (
                        (lucro_res.motivo if lucro_ctrl is None else None)
                        or (pl_res.motivo if pl_ctrl is None else None)
                        or motivo_roe
                    )

                ind: dict = {
                    "ativo_total":        ativo_total,
                    "ativo_circulante":   ativo_circulante,
                    "passivo_total":      passivo_total,
                    "passivo_circulante": passivo_circulante,
                    "patrimonio_liquido": pl,
                    "receita_liquida":    receita,
                    "ebit":               ebit,
                    "lucro_liquido":      lucro,
                    "roe":                None,
                    "margem_liquida":     None,
                    "divida_pl":          None,
                    "cvm_dt_refer":       metadata.get("cvm_dt_refer"),
                    "cvm_versao":         metadata.get("cvm_versao"),
                    "cnpj":               cnpj,
                    "lucro_controladores": lucro_ctrl,
                    "pl_controladores":   pl_ctrl,
                    "reservas_controladores": {
                        campo: r.reserva
                        for campo, r in (
                            ("lucro_controladores", lucro_res), ("pl_controladores", pl_res),
                        )
                        if r.reserva
                    },
                    "roe_motivo":         motivo_roe,
                    "divida_liquida":     alavancagem.divida_liquida,
                    "ebitda":             alavancagem.ebitda,
                    "divida_liq_ebitda":  alavancagem.divida_liq_ebitda,
                    "div_liq_patrimonio": alavancagem.div_liq_patrimonio,
                    "alavancagem_motivos": alavancagem.motivos,
                    "alavancagem_regime": alavancagem.regime,
                    "lpa_divulgado":      lpa_divulgado(linhas_399),
                    "lpa_divulgado_por_especie": lpa_divulgado_por_especie(linhas_399),
                    "lpa_basico_por_classe": lpa_basico_por_classe(linhas_399),
                    "lpa_basico_agregado": lpa_basico_agregado(linhas_399),
                    "composicao_capital": composicao,
                    "composicao_motivo":  motivo_composicao,
                    "contas_abstidas":    contas_abstidas,
                    "proveniencia":       self.proveniencia_do_documento(
                        zip_path, ano, cnpj,
                        metadata.get("cvm_dt_refer"), metadata.get("cvm_versao"),
                    ),
                }
                ind["roe"] = roe_ctrl

                if pl and pl != 0:
                    if passivo_total is not None:
                        ind["divida_pl"] = (passivo_total - pl) / pl

                if receita and receita != 0 and lucro is not None:
                    ind["margem_liquida"] = lucro / receita

                resultado[ano] = ind

            except Exception as exc:
                logger.warning("Erro ao calcular indicadores cd_cvm=%d ano=%d: %s", cd_cvm, ano, exc)

        return resultado

    # ------------------------------------------------------------------
    # Série de cinco anos e TTM (F2A-7)
    # ------------------------------------------------------------------

    def composicao_mais_recente(self, cnpj: str, as_of: datetime, ano_dfp: int) -> dict:
        """Última referência/versão ITR ou DFP entregue até o corte (Gordon1.1).

        Data de entrega sem hora entra após o fim do dia de Brasília. A seleção
        usa o índice de entregas, antes de ler a composição; falta na última
        entrega elegível não permite voltar silenciosamente a documento antigo.
        """
        from zoneinfo import ZoneInfo

        if as_of.tzinfo is None or as_of.utcoffset() is None:
            return {"abstencao": "as_of exige fuso horário"}
        dia = as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
        candidatos = []
        for ano in range(ano_dfp, dia.year + 1):
            for documento, baixar, url in (
                ("DFP", self.baixar_dfp, _DFP_URL),
                ("ITR", self.baixar_itr, _ITR_URL),
            ):
                try:
                    caminho = baixar(ano)
                    arquivo = proveniencia.registrar_arquivo(
                        caminho, url.format(ano=ano), documento, str(ano)
                    )
                    if datetime.fromisoformat(arquivo.data_coleta) > as_of:
                        return {
                            "abstencao": "composição recente com coleta posterior ao as_of"
                        }
                    for linha in self._entregas(caminho):
                        if linha.get("CNPJ_CIA") != cnpj:
                            continue
                        referencia = date.fromisoformat(linha["DT_REFER"])
                        entrega = proveniencia.entrega_no_indice(
                            [linha],
                            {k: linha[k] for k in ("CNPJ_CIA", "DT_REFER", "VERSAO")},
                        )
                        if (
                            entrega is None
                            or date.fromisoformat(entrega) >= dia
                            or referencia >= dia
                        ):
                            continue
                        candidatos.append(
                            (
                                referencia,
                                int(linha["VERSAO"]),
                                caminho,
                                arquivo.do_documento(
                                    referencia.isoformat(),
                                    linha["VERSAO"],
                                    entrega,
                                    proveniencia.MOTIVO_DOCUMENTO_FORA_DO_INDICE,
                                ),
                            )
                        )
                except OSError as erro:
                    # 404 atesta ausência do arquivo anual, não falha de consulta.
                    if (
                        getattr(getattr(erro, "response", None), "status_code", None)
                        == 404
                    ):
                        continue
                    return {
                        "abstencao": "não foi possível conferir a composição mais recente"
                    }
                except (
                    StopIteration,
                    KeyError,
                    TypeError,
                    ValueError,
                    zipfile.BadZipFile,
                ):
                    return {"abstencao": "índice da composição mais recente inválido"}
        if not candidatos:
            return {"abstencao": "composição recente sem documento elegível"}
        referencia, versao, caminho, prov = max(candidatos, key=lambda x: (x[0], x[1]))
        try:
            cc = self._read_raw(caminho, "composicao_capital")
            composicao, motivo = composicao_do_documento(
                cc, cnpj, referencia.isoformat(), str(versao)
            )
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            composicao, motivo = None, "composição recente indisponível"
        if composicao is None:
            return {"abstencao": motivo, "proveniencia": prov.para_dict()}
        return {
            "composicao": composicao,
            "escala": self._escala_da_composicao(
                caminho, cnpj, referencia.isoformat(), str(versao), composicao
            ),
            "proveniencia": prov.para_dict(),
        }

    def _escala_da_composicao(
        self,
        caminho: Path,
        cnpj: str,
        dt_refer: str,
        versao: str,
        composicao: Composicao,
    ) -> str | None:
        """Escala da quantidade de ações do documento recente (ficha por-ação 1.1; F2B-54).

        Pela regra da DFP (`acoes_cvm.inferir_escala`): lucro dos controladores do mesmo
        documento e período, com as reservas da D20 (`lucro_controladores_com_reserva`, com
        o BPP do mesmo documento), ÷ ações, contra o LPA divulgado. O período é o acumulado
        do exercício (menor `DT_INI_EXERC`) da linha "ÚLTIMO". `None` quando indeterminada.
        """

        def do_documento(tipo: str) -> pd.DataFrame:
            df = self._read_raw(caminho, tipo)
            df = df[
                (df["CNPJ_CIA"] == cnpj)
                & (df["DT_REFER"].astype(str) == dt_refer)
                & (df["VERSAO"].astype(str) == versao)
            ]
            if "ORDEM_EXERC" in df.columns:
                df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
            return df.assign(VL_CONTA=pd.to_numeric(df["VL_CONTA"], errors="coerce"))

        def em_reais(df: pd.DataFrame) -> pd.DataFrame:
            if "ESCALA_MOEDA" not in df.columns:
                return df
            mil = df["ESCALA_MOEDA"].astype(str).str.upper() == "MIL"
            return df.assign(VL_CONTA=df["VL_CONTA"].where(~mil, df["VL_CONTA"] * 1000))

        try:
            dre = do_documento("DRE_con")
            if "DT_INI_EXERC" in dre.columns and not dre.empty:
                dre = dre[dre["DT_INI_EXERC"] == dre["DT_INI_EXERC"].min()]
            try:
                bpp = em_reais(do_documento("BPP_con"))
            except FileNotFoundError:
                bpp = pd.DataFrame(columns=["CD_CONTA", "DS_CONTA", "VL_CONTA"])
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            return None
        e_lpa = dre["CD_CONTA"].astype(str).str.startswith("3.99")
        divulgado = lpa_divulgado(dre[e_lpa])
        lucro = lucro_controladores_com_reserva(em_reais(dre[~e_lpa]), bpp).valor
        inferida = acoes_cvm.inferir_escala(
            lucro, composicao.total, divulgado["valor"] if divulgado else None
        )
        return None if inferida is None else inferida[0].name

    def gordon_do_documento(self, cd_cvm: int, ind: dict, as_of: datetime) -> dict:
        """DVA anual e PL inicial do mesmo documento, com disponibilidade explícita.

        Não certifica eventos entre a DFP e o preço; essa evidência chega separada
        na fronteira de mercado. Ausência de prova não vira dado positivo.
        """
        from zoneinfo import ZoneInfo

        try:
            if as_of.tzinfo is None or as_of.utcoffset() is None:
                return {"abstencao": "as_of exige fuso horário"}
            dia = as_of.astimezone(ZoneInfo("America/Sao_Paulo")).date()
            referencia = date.fromisoformat(ind["cvm_dt_refer"])
            versao = ind["cvm_versao"]
            caminho = self.baixar_dfp(referencia.year)
            prov = self.proveniencia_do_documento(
                caminho, referencia.year, ind["cnpj"], referencia.isoformat(), versao
            )
            if (
                prov is None
                or prov.get("data_entrega") is None
                or date.fromisoformat(prov["data_entrega"]) >= dia
                or datetime.fromisoformat(prov["data_coleta"]) > as_of
            ):
                return {"abstencao": "disponibilidade histórica da DFP não demonstrada"}

            def linhas(tipo: str, ordem: str) -> pd.DataFrame:
                bruto = self._read_raw(caminho, tipo)
                doc = bruto[
                    (pd.to_numeric(bruto["CD_CVM"], errors="coerce") == cd_cvm)
                    & (bruto["DT_REFER"].astype(str) == referencia.isoformat())
                    & (pd.to_numeric(bruto["VERSAO"], errors="coerce") == float(versao))
                    & (bruto["ORDEM_EXERC"] == ordem)
                ].copy()
                if not doc.empty:
                    doc["VL_CONTA"] = pd.to_numeric(doc["VL_CONTA"], errors="coerce")
                    if (
                        "ESCALA_MOEDA" not in doc
                        or not doc["ESCALA_MOEDA"]
                        .isin(["REAL", "MIL", "UNIDADE"])
                        .all()
                    ):
                        raise ValueError("escala monetária da DFP indeterminada")
                    doc.loc[doc["ESCALA_MOEDA"] == "MIL", "VL_CONTA"] *= 1000
                return doc

            dre = linhas("DRE_con", "ÚLTIMO")
            bpp = linhas("BPP_con", "ÚLTIMO")
            dva = linhas("DVA_con", "ÚLTIMO")
            if dre.empty or bpp.empty or dva.empty:
                return {"abstencao": "DFP anual sem DRE, BPP ou DVA consolidada"}
            if isinstance(_ler(bpp, "pl_total", "banco"), contas_cvm.Leitura):
                return {"abstencao": "modelo banco fora do escopo do Gordon"}
            if not isinstance(_ler(bpp, "pl_total", "empresa"), contas_cvm.Leitura):
                return {
                    "abstencao": "modelo empresa não demonstrado no BPP consolidado"
                }
            janelas = set(
                zip(dre["DT_INI_EXERC"].astype(str), dre["DT_FIM_EXERC"].astype(str))
            )
            janelas_dva = set(
                zip(dva["DT_INI_EXERC"].astype(str), dva["DT_FIM_EXERC"].astype(str))
            )
            if len(janelas) != 1 or janelas_dva != janelas:
                return {"abstencao": "DRE e DVA com janelas incompatíveis"}
            inicio_texto, fim_texto = next(iter(janelas))
            inicio, fim = (
                date.fromisoformat(inicio_texto),
                date.fromisoformat(fim_texto),
            )
            if fim != referencia:
                return {"abstencao": "fim do exercício difere da referência da DFP"}
            inicial = linhas("BPP_con", "PENÚLTIMO")
            inicial = inicial[
                inicial["DT_FIM_EXERC"].astype(str)
                == (inicio - timedelta(days=1)).isoformat()
            ]
            if inicial.empty:
                return {"abstencao": "PL inicial ausente do comparativo da mesma DFP"}
            dre_inicial = linhas("DRE_con", "PENÚLTIMO")
            dre_inicial = dre_inicial[
                dre_inicial["DT_FIM_EXERC"].astype(str)
                == (inicio - timedelta(days=1)).isoformat()
            ]
            pl_inicial = controladores.pl_dos_controladores(
                _ler(inicial, "pl_total", "empresa"),
                _ler(inicial, "pl_nao_controladores", "empresa"),
                _ler(dre_inicial, "lucro_nao_controladores", "empresa"),
            )
            total = gordon_cvm.proventos_da_dva(
                _ler(dva, "dividendos", "empresa"),
                _ler(dva, "jcp", "empresa"),
                _ler(dva, "dva_nao_controladores", "empresa"),
                _ler(dre, "lucro_nao_controladores", "empresa"),
                _ler(bpp, "pl_nao_controladores", "empresa"),
            )
            if isinstance(total, gordon_cvm.Abstencao):
                return {"abstencao": total.motivo}
            mencao_extraordinaria = (
                dva["DS_CONTA"]
                .astype(str)
                .str.contains("extraordin", case=False, na=False)
            )
            if not dva.loc[mencao_extraordinaria, "VL_CONTA"].map(math.isfinite).all():
                return {"abstencao": "distribuição extraordinária com valor inválido"}
            extraordinario = mencao_extraordinaria & (dva["VL_CONTA"] != 0)
            # A ficha §1 aceita a DVA anual como aproximação do fluxo recorrente.
            # Isto é hipótese do modelo, não certificado de ausência de eventos.
            # A guarda §3 exclui evento extraordinário ou estrutural identificado.
            anual = (
                inicio.day == 1
                and fim.day == calendar.monthrange(fim.year, fim.month)[1]
                and (fim.year - inicio.year) * 12 + fim.month - inicio.month == 11
            )
            mudanca_estrutural = ind.get("mudanca_estrutural_sem_reconciliacao") is True
            return {
                "modelo": "empresa",
                "documento": "DFP",
                "inicio": inicio_texto,
                "fim": fim_texto,
                "data_entrega": prov["data_entrega"],
                "versao": str(versao),
                "cnpj": ind["cnpj"],
                "lucro_controladores": lucro_controladores_com_reserva(dre, bpp).valor,
                "pl_inicial_controladores": pl_inicial.valor,
                "proventos_controladores": total,
                "hipotese_dva_anual": anual,
                "distribuicao_extraordinaria_identificada": bool(extraordinario.any()),
                "mudanca_estrutural_sem_reconciliacao": mudanca_estrutural,
                "fundamento_fluxo": "hipótese de DVA anual como aproximação do fluxo recorrente (ficha Gordon1.1, §1)",
                "proveniencia": prov,
            }
        except (KeyError, ValueError, TypeError, OSError, zipfile.BadZipFile) as erro:
            return {"abstencao": f"DFP anual do Gordon indisponível: {erro}"}

    def modelo_do_documento(self, cd_cvm: int, ind: dict) -> str | None:
        """Modelo de demonstração pelo BPP consolidado do documento de `ind` (F2B-31).

        "banco" com o PL no par do modelo de instituição financeira, "empresa" com o par do
        modelo empresa, `None` sem o BPP do documento ou sem nenhum dos dois: a mesma regra
        de `gordon_do_documento`, para o escopo do Bazin (ficha Bazin 1.0, §4), que não é o
        rótulo do setor.
        """
        try:
            referencia = date.fromisoformat(ind["cvm_dt_refer"])
            bruto = self._read_raw(self.baixar_dfp(referencia.year), "BPP_con")
            bpp = bruto[
                (pd.to_numeric(bruto["CD_CVM"], errors="coerce") == cd_cvm)
                & (bruto["DT_REFER"].astype(str) == referencia.isoformat())
                & (pd.to_numeric(bruto["VERSAO"], errors="coerce") == float(ind["cvm_versao"]))
                & (bruto["ORDEM_EXERC"] == "ÚLTIMO")
            ].copy()
        except (KeyError, ValueError, TypeError, OSError, zipfile.BadZipFile):
            return None
        if bpp.empty:
            return None
        bpp["VL_CONTA"] = pd.to_numeric(bpp["VL_CONTA"], errors="coerce")
        for modelo in ("banco", "empresa"):
            if isinstance(_ler(bpp, "pl_total", modelo), contas_cvm.Leitura):
                return modelo
        return None

    def proventos_do_documento(
        self,
        zip_path: Path,
        cd_cvm: int,
        dt_refer: str | None,
        versao: str | None,
        modelo: str = "empresa",
    ) -> dict:
        """Dividendos e JCP declarados na DVA consolidada do documento, pela tabela de contas.

        Por competência (`series_cvm.COMPETENCIA`). Sem a linha ou a DVA, o campo fica `None`
        e o motivo vai para `proventos_motivos`.
        """
        try:
            dva = self.parsear_demonstrativo(
                zip_path, "DVA_con", include_cd_cvm=True, include_versao=True
            )
            dva = dva[
                (dva["CD_CVM"] == cd_cvm)
                & (dva["DT_REFER"].astype(str) == str(dt_refer))
                & (dva["VERSAO"].astype(str) == str(versao))
            ]
        except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
            motivo = f"DVA indisponível ({exc})"
            return {"dividendos": None, "jcp": None,
                    "proventos_motivos": {"dividendos": motivo, "jcp": motivo}}
        if dva.empty:
            motivo = "DVA indisponível no documento"
            return {"dividendos": None, "jcp": None,
                    "proventos_motivos": {"dividendos": motivo, "jcp": motivo}}
        saida: dict = {"proventos_motivos": {}}
        for campo in ("dividendos", "jcp"):
            leitura = _ler(dva, campo, modelo)
            if isinstance(leitura, contas_cvm.Leitura):
                saida[campo] = leitura.valor
            else:
                saida[campo] = None
                saida["proventos_motivos"][campo] = f"{leitura.motivo} {leitura.detalhe}".strip()
        return saida

    def indicadores_da_serie(
        self, cd_cvm: int, ano_final: int, modelo: str = "empresa"
    ) -> dict[int, dict]:
        """`calcular_indicadores` dos cinco exercícios até `ano_final`, com os proventos da DVA."""
        indicadores = self.calcular_indicadores(
            cd_cvm, anos=series_cvm.MAX_EXERCICIOS, modelo=modelo, ano_final=ano_final
        )
        for ano, ind in indicadores.items():
            ind.update(
                self.proventos_do_documento(
                    self.baixar_dfp(ano), cd_cvm,
                    ind.get("cvm_dt_refer"), ind.get("cvm_versao"), modelo,
                )
            )
        return indicadores

    def _acumulados_do_arquivo(
        self, zip_path: Path, documento: str, cd_cvm: int, modelo: str
    ) -> list[series_cvm.Acumulado]:
        """Acumulados do exercício (DRE e DVA consolidadas) de cada documento do arquivo.

        No ITR, o acumulado é a linha de `DT_INI_EXERC` mais antigo do documento; a outra é o
        trimestre isolado.
        """
        partes = []
        dva_indisponivel = None
        for tipo in ("DRE_con", "DVA_con"):
            try:
                df = self.parsear_demonstrativo(
                    zip_path, tipo, include_cd_cvm=True, include_versao=True, include_periodo=True
                )
            except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
                if tipo != "DVA_con":
                    raise
                dva_indisponivel = f"DVA indisponível ({exc})"
                continue
            partes.append(df[df["CD_CVM"] == cd_cvm])
        linhas = pd.concat(partes, ignore_index=True)
        if linhas.empty:
            return []
        # F2B-37 (BUG-2A-10): o balanço do mesmo documento, para a reserva da decisão 7.2.
        try:
            bpp = self.parsear_demonstrativo(
                zip_path, "BPP_con", include_cd_cvm=True, include_versao=True
            )
            bpp = bpp[bpp["CD_CVM"] == cd_cvm]
        except (OSError, KeyError, ValueError):
            bpp = pd.DataFrame(columns=["DT_REFER", "VERSAO", "CD_CONTA", "DS_CONTA", "VL_CONTA"])
        acumulados = []
        for (dt_refer, versao), doc in linhas.groupby(["DT_REFER", "VERSAO"]):
            inicio = doc["DT_INI_EXERC"].min()
            doc = doc[doc["DT_INI_EXERC"] == inicio]
            fim = doc["DT_FIM_EXERC"].max()
            valores, motivos = {}, {}
            for campo in series_cvm.CAMPOS_TTM:
                leitura = _ler(doc, campo, modelo)
                valores[campo] = leitura.valor if isinstance(leitura, contas_cvm.Leitura) else None
                if campo in ("dividendos", "jcp") and isinstance(leitura, contas_cvm.Abstencao):
                    if dva_indisponivel or not doc["CD_CONTA"].str.startswith("7.").any():
                        motivos[campo] = dva_indisponivel or "DVA indisponível no documento"
                    else:
                        motivos[campo] = f"{leitura.motivo} {leitura.detalhe}".strip()
            # F2B-37: o lucro dos controladores pela mesma leitura com reservas da série anual
            # (D20 e decisão 7.2), com o balanço do mesmo documento.
            bpp_doc = bpp[
                (bpp["DT_REFER"].astype(str) == str(dt_refer))
                & (bpp["VERSAO"].astype(str) == str(versao))
            ]
            controladores_doc = lucro_controladores_com_reserva(doc, bpp_doc)
            valores["lucro_controladores"] = controladores_doc.valor
            if controladores_doc.valor is None and controladores_doc.motivo:
                motivos["lucro_controladores"] = controladores_doc.motivo
            acumulados.append(
                series_cvm.Acumulado(
                    documento=documento,
                    dt_refer=str(dt_refer),
                    versao=int(versao),
                    inicio=date.fromisoformat(str(inicio)),
                    fim=date.fromisoformat(str(fim)),
                    valores=valores,
                    motivos=motivos,
                )
            )
        return acumulados

    def acumulados_ttm(
        self, cd_cvm: int, data_referencia: date, modelo: str = "empresa"
    ) -> list[series_cvm.Acumulado]:
        """Acumulados dos ITR do ano da data e dos dois anteriores, e das DFPs dos dois anteriores.

        Antes de sair a DFP do ano anterior, o 4º trimestre mais recente é a DFP de dois anos
        antes menos o ITR de nove meses do mesmo ano. Arquivo que não baixa ou não abre fica de
        fora, com aviso no log.
        """
        fontes = [
            ("ITR", self.baixar_itr, data_referencia.year),
            ("ITR", self.baixar_itr, data_referencia.year - 1),
            ("ITR", self.baixar_itr, data_referencia.year - 2),
            ("DFP", self.baixar_dfp, data_referencia.year - 1),
            ("DFP", self.baixar_dfp, data_referencia.year - 2),
        ]
        acumulados: list[series_cvm.Acumulado] = []
        for documento, baixar, ano in fontes:
            try:
                acumulados += self._acumulados_do_arquivo(baixar(ano), documento, cd_cvm, modelo)
            except Exception as exc:
                logger.warning(
                    "Sem %s %d para o TTM de cd_cvm=%d: %s", documento, ano, cd_cvm, exc
                )
        return acumulados

