"""Fatores documentados da B3 para as bases anuais de Graham/Lynch 2.1.

Manual Câmara B3, pp.176–177: quantidade ajustada = quantidade × F;
bonificação/desdobramento F=1+B, grupamento F=1/RL:
https://www.b3.com.br/data/files/B1/F0/C1/10/76B3D8103152D4C8AC094EA8/MPO%20da%20Camara%20B3.pdf
O JSON CompanyCall não tem dicionário público de `factor` identificado. As conversões
são demonstradas também por eventos oficiais, não inferidas dos preços:
- Cemig, aviso29/04/2024,30,00000002726% de novas ações da mesma espécie:
https://ri.cemig.com.br/docs/Aviso-aos-Acionistas-cemig-2024-04-29-BCtpjgMp.pdf
- Cosan, AGOE30/04/2021,pp.7–8:1→4, corresponde ao campo300:
https://api.mziq.com/mzfilemanager/v2/d/6aa68515-2422-4cc4-bafa-8870ccdfedb0/04bcf9ef-0740-4296-1b61-38541f627539?origin=1
- Cemig,DFP2007,p.101:500→1, corresponde ao campo0,002 (já multiplicativo):
https://ri.cemig.com.br/docs/cemig-2007-12-31-qNw7f9TR.pdf

Outros rótulos e distribuição em espécie distinta não têm conversão presumida.
Não coleta fontes, não lê relógio e não transforma falta de evento em fator1.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from itertools import pairwise

from sentinela.data import proventos_b3 as pb


def _mapa(valor: object, nome: str) -> Mapping:
    if not isinstance(valor, Mapping):
        raise TypeError(f"{nome} ausente ou inválido")
    return valor


def _positivo(valor: object) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError("quantidade de ações do documento inválida")
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError("quantidade de ações do documento não positiva ou não finita")
    return float(valor)


def _coleta(valor: object, instante: datetime) -> str:
    coleta = datetime.fromisoformat(str(valor))
    if coleta.tzinfo is None or coleta.utcoffset() is None or coleta > instante:
        raise ValueError("coleta sem fuso ou posterior ao as_of")
    return str(valor)


def _fator(evento: Mapping) -> float:
    rotulo = evento.get("label")
    if rotulo not in ("DESDOBRAMENTO", "BONIFICACAO", "GRUPAMENTO"):
        raise ValueError(f"evento em ações não demonstrado: {rotulo}")
    numero = pb._numero(evento.get("factor"), "fator oficial B3")
    if isinstance(numero, pb.Abstencao):
        raise TypeError(numero.motivo)
    fator = numero if rotulo == "GRUPAMENTO" else 1 + numero / 100
    if not math.isfinite(fator) or fator <= 0:
        raise ValueError("fator oficial B3 não positivo ou não finito")
    return fator


def _fator_do_par(
    eventos: Sequence,
    componentes: Mapping,
    inicio: date,
    fim: date,
    dia: date,
) -> tuple[float, list[dict]]:
    fatores = {classe: 1.0 for classe in componentes}
    encontrados = set()
    vistos = set()
    evidencia = []
    for bruto in eventos:
        evento = _mapa(bruto, "evento em ações")
        data_com = pb.ler_data(evento.get("lastDatePrior"))
        if data_com is None:
            raise ValueError("data com do evento em ações inválida")
        if data_com < inicio or data_com > fim:
            continue
        isin, emitido = evento.get("isinCode"), evento.get("assetIssued")
        if not isinstance(isin, str) or not isinstance(emitido, str):
            raise TypeError("espécie do evento em ações não demonstrada")
        classe = pb.ESPECIE_DO_ISIN.get(isin[6:11])
        if classe is None:
            raise ValueError("espécie do evento em ações não demonstrada")
        if classe not in componentes and emitido == isin:
            continue
        if data_com in (inicio, fim):
            raise ValueError(
                "data com coincide com encerramento; data ex não demonstrada"
            )
        if emitido != isin or classe not in componentes:
            raise ValueError("evento em espécie distinta sem reconciliação demonstrada")
        aprovacao = pb.ler_data(evento.get("approvedOn"))
        if aprovacao is None or aprovacao >= dia or data_com >= dia:
            raise ValueError("aprovação ou data com do evento não elegível até o as_of")
        chave = tuple(
            evento.get(c)
            for c in (
                "label",
                "factor",
                "isinCode",
                "assetIssued",
                "lastDatePrior",
                "approvedOn",
            )
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        fator = _fator(evento)
        fatores[classe] *= fator
        encontrados.add(classe)
        evidencia.append(dict(evento))
    if not encontrados:
        raise ValueError("base incompatível sem evento oficial B3 no par documental")
    if encontrados != set(componentes):
        raise ValueError("componente da unit sem evento oficial B3 no par documental")
    if len(set(fatores.values())) != 1:
        raise ValueError("componentes da unit com fatores distintos")
    fator = next(iter(fatores.values()))
    if not math.isfinite(fator) or fator <= 0:
        raise ValueError("fator oficial acumulado não positivo ou não finito")
    return fator, evidencia


def fatores_da_relacao(dados: Mapping, registros: Sequence, instante: datetime) -> dict:
    """Fatores acumulados até a base final ou abstenção com causa e sem fonte nova.

    Só pares fora de (0,9;1,1) precisam de eventos; quantidades recebidas já estão em
    unidades pela escala do próprio documento. A razão residual, após o fator oficial,
    também deve pertencer ao intervalo. COM no encerramento é ambíguo e não vira EX.
    """
    try:
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("as_of exige fuso horário")
        if not isinstance(registros, (list, tuple)) or len(registros) < 2:
            raise ValueError("pares documentais anuais ausentes")
        documentos = sorted(registros, key=lambda r: _mapa(r, "documento")["exercicio"])
        quantidades = [_positivo(r.get("acoes")) for r in documentos]
        fins = [date.fromisoformat(r["fim"]) for r in documentos]
        if any(b <= a for a, b in pairwise(fins)):
            raise ValueError("encerramentos documentais não crescentes")
        razoes = [b / a for a, b in pairwise(quantidades)]
        incompativeis = any(not 0.9 < r < 1.1 for r in razoes)
        eventos = []
        componentes = {}
        if incompativeis:
            relacao = _mapa(dados.get("proventos_b3"), "relação de eventos B3")
            if relacao.get("abstencao"):
                raise ValueError(str(relacao["abstencao"]))
            proveniencia = _mapa(relacao.get("proveniencia"), "proveniência B3")
            fonte = proveniencia.get("fonte")
            if not fonte:
                raise ValueError("fonte B3 não demonstrada")
            coleta = _coleta(relacao.get("coleta"), instante)
            eventos = relacao.get("eventos_acoes")
            if not isinstance(eventos, (list, tuple)):
                raise ValueError("lista de eventos em ações ausente ou inválida")
            componentes = pb._componentes(
                dados.get("especie"),
                dados.get("classe_ativo") == "UNIT",
                dados.get("acoes_por_unit"),
            )
            if isinstance(componentes, pb.Abstencao):
                raise ValueError(componentes.motivo)
        else:
            fontes = [
                _mapa(r.get("proveniencia"), "proveniência documental")
                for r in documentos
            ]
            if any(not p.get("fonte") for p in fontes):
                raise ValueError("fonte documental não demonstrada")
            coletas = [_coleta(p.get("data_coleta"), instante) for p in fontes]
            coleta = max(coletas, key=datetime.fromisoformat)
            fonte, proveniencia = "Composição do Capital de cada documento", fontes
        evidencias, fatores_pares = [], []
        dia = instante.astimezone(pb.FUSO).date()
        for i, razao in enumerate(razoes):
            fator, usados = (
                (1.0, [])
                if 0.9 < razao < 1.1
                else _fator_do_par(
                    eventos,
                    componentes,
                    fins[i],
                    fins[i + 1],
                    dia,
                )
            )
            residual = razao / fator
            if not 0.9 < residual < 1.1:
                raise ValueError(
                    "razão residual da base incompatível após fator oficial B3"
                )
            fatores_pares.append(fator)
            evidencias.append(
                {
                    "anterior": documentos[i]["exercicio"],
                    "posterior": documentos[i + 1]["exercicio"],
                    "razao": razao,
                    "fator": fator,
                    "razao_residual": residual,
                    "eventos": usados,
                }
            )
        acumulados = [math.prod(fatores_pares[i:]) for i in range(len(documentos))]
        if any(not math.isfinite(f) or f <= 0 for f in acumulados):
            raise ValueError("fator acumulado não positivo ou não finito")
        return {
            "fonte": fonte,
            "coleta": coleta,
            "proveniencia": proveniencia,
            "inicio": documentos[0]["inicio"],
            "fim": documentos[-1]["fim"],
            "fatores": {
                str(r["exercicio"]): f
                for r, f in zip(documentos, acumulados, strict=True)
            },
            "evidencias": evidencias,
        }
    except (ValueError, KeyError, TypeError, OverflowError, ZeroDivisionError) as erro:
        return {"abstencao": str(erro)}
