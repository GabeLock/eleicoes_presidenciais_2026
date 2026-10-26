"""DADOS SINTÉTICOS — usados exclusivamente em testes. Não representam nenhum resultado real.

Geram ZIPs no layout de colunas de 2022 (latin-1, separador ';', campos entre aspas) para
exercitar o pipeline sem rede. Os candidatos são fictícios (votáveis 11, 22, 33).
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

CAB_VOTOS = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "NR_TURNO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "CD_CARGO",
    "DS_CARGO",
    "NR_VOTAVEL",
    "NM_VOTAVEL",
    "QT_VOTOS",
    "SQ_CANDIDATO",
]
CAB_DETALHE = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "NR_TURNO",
    "SG_UF",
    "CD_MUNICIPIO",
    "NM_MUNICIPIO",
    "NR_ZONA",
    "NR_SECAO",
    "CD_CARGO",
    "DS_CARGO",
    "QT_APTOS",
    "QT_COMPARECIMENTO",
    "QT_ABSTENCOES",
    "QT_VOTOS_NOMINAIS",
    "QT_VOTOS_BRANCOS",
    "QT_VOTOS_NULOS",
    "QT_VOTOS_LEGENDA",
    "QT_VOTOS_ANULADOS",
]

# (uf, cd_municipio_tse, nome, zona, seção): votos por turno {votavel: qt}, aptos
SECOES = [
    (
        "MG",
        "41238",
        "BELO HORIZONTE",
        "0026",
        "0001",
        {
            1: {"11": 120, "22": 100, "33": 40, "95": 5, "96": 10},
            2: {"11": 125, "22": 140, "95": 3, "96": 7},
        },
        300,
    ),
    (
        "MG",
        "41238",
        "BELO HORIZONTE",
        "0026",
        "0002",
        {
            1: {"11": 90, "22": 95, "33": 20, "95": 2, "96": 3},
            2: {"11": 100, "22": 110, "95": 1, "96": 4},
        },
        250,
    ),
    (
        "MG",
        "40134",
        "CONTAGEM",
        "0101",
        "0010",
        {
            1: {"11": 80, "22": 50, "33": 30, "95": 1, "96": 4},
            2: {"11": 90, "22": 70, "95": 2, "96": 3},
        },
        200,
    ),
    (
        "MG",
        "47066",
        "ÁGUA BOA",
        "0200",
        "0005",
        {
            1: {"11": 10, "22": 30, "33": 5, "95": 0, "96": 1},
            2: {"11": 12, "22": 33, "95": 0, "96": 1},
        },
        60,
    ),
]
NOMES = {
    "11": "CANDIDATO FICTÍCIO A",
    "22": "CANDIDATO FICTÍCIO B",
    "33": "CANDIDATO FICTÍCIO C",
    "95": "VOTO BRANCO",
    "96": "VOTO NULO",
}


def _csv(cab: list[str], linhas: list[list[str]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(cab)
    w.writerows(linhas)
    return buf.getvalue().encode("latin-1")


def linhas_votos(turnos=(1, 2)) -> list[list[str]]:
    out = []
    for uf, mun, nome, zona, secao, votos, _ in SECOES:
        for t in turnos:
            for nr, qt in votos[t].items():
                out.append(
                    [
                        "26/10/2026",
                        "10:00:00",
                        "2026",
                        str(t),
                        uf,
                        mun,
                        nome,
                        zona,
                        secao,
                        "1",
                        "Presidente",
                        nr,
                        NOMES[nr],
                        str(qt),
                        "-1",
                    ]
                )
            # outro cargo no mesmo arquivo, que deve ser filtrado (só 1º turno)
            if t == 1:
                out.append(
                    [
                        "26/10/2026",
                        "10:00:00",
                        "2026",
                        "1",
                        uf,
                        mun,
                        nome,
                        zona,
                        secao,
                        "3",
                        "Governador",
                        "15",
                        "FICTÍCIO GOV",
                        "999",
                        "-1",
                    ]
                )
    return out


def linhas_detalhe(turnos=(1, 2)) -> list[list[str]]:
    out = []
    for uf, mun, nome, zona, secao, votos, aptos in SECOES:
        for t in turnos:
            v = votos[t]
            brancos, nulos = v.get("95", 0), v.get("96", 0)
            nominais = sum(q for k, q in v.items() if k not in ("95", "96"))
            comp = nominais + brancos + nulos
            out.append(
                [
                    "26/10/2026",
                    "10:00:00",
                    "2026",
                    str(t),
                    uf,
                    mun,
                    nome,
                    zona,
                    secao,
                    "1",
                    "Presidente",
                    str(aptos),
                    str(comp),
                    str(aptos - comp),
                    str(nominais),
                    str(brancos),
                    str(nulos),
                    "0",
                    "0",
                ]
            )
    return out


def escrever_zip(destino: Path, membros: dict[str, bytes]) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in membros.items():
            zf.writestr(nome, conteudo)
    return destino


def zips_sinteticos(pasta: Path, turnos=(1, 2)) -> dict[str, Path]:
    return {
        "votacao_secao_2026_MG.zip": escrever_zip(
            pasta / "votacao_secao_2026_MG.zip",
            {
                "votacao_secao_2026_MG.csv": _csv(CAB_VOTOS, linhas_votos(turnos)),
                "leiame.txt": b"ARQUIVO SINTETICO DE TESTE",
            },
        ),
        "detalhe_votacao_secao_2026.zip": escrever_zip(
            pasta / "detalhe_votacao_secao_2026.zip",
            {
                "detalhe_votacao_secao_2026_MG.csv": _csv(CAB_DETALHE, linhas_detalhe(turnos)),
                "detalhe_votacao_secao_2026_SP.csv": _csv(CAB_DETALHE, []),
            },
        ),
    }
