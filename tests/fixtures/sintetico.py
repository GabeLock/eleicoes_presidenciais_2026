"""DADOS SINTÉTICOS — usados exclusivamente em testes. Não representam nenhum resultado real.

Reproduzem o LAYOUT confirmado no leiame de 2026 (latin-1, ';', campos entre aspas) e a
organização dos ZIPs do TSE: Presidente fica nos membros `_BR` (abrangência federal); os membros
por UF trazem só cargos estaduais. Candidatos fictícios: votáveis 11, 22, 33.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

CAB_VOTOS = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "CD_CARGO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL",
    "QT_VOTOS", "SQ_CANDIDATO",
]  # fmt: skip
CAB_DETALHE = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "CD_CARGO", "DS_CARGO", "QT_APTOS",
    "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_VOTOS_NOMINAIS", "QT_VOTOS_BRANCOS",
    "QT_VOTOS_NULOS", "QT_VOTOS_LEGENDA", "QT_VOTOS_ANULADOS_APU_SEP", "DS_ORIGEM_VOTO",
    "ST_SECAO_INSTALADA", "ST_SECAO_ANULADA",
]  # fmt: skip

# (uf, cd_municipio_tse, nome, zona, seção, {turno: {votável: qt}}, aptos)
SECOES = [
    ("MG", "41238", "BELO HORIZONTE", "0026", "0001",
     {1: {"11": 120, "22": 100, "33": 40, "95": 5, "96": 10},
      2: {"11": 125, "22": 140, "95": 3, "96": 7}}, 300),
    ("MG", "41238", "BELO HORIZONTE", "0026", "0002",
     {1: {"11": 90, "22": 95, "33": 20, "95": 2, "96": 3},
      2: {"11": 100, "22": 110, "95": 1, "96": 4}}, 250),
    ("MG", "40134", "CONTAGEM", "0101", "0010",
     {1: {"11": 80, "22": 50, "33": 30, "95": 1, "96": 4},
      2: {"11": 90, "22": 70, "95": 2, "96": 3}}, 200),
    ("MG", "47066", "ÁGUA BOA", "0200", "0005",
     {1: {"11": 10, "22": 30, "33": 5, "95": 0, "96": 1},
      2: {"11": 12, "22": 33, "95": 0, "96": 1}}, 60),
    # fora do escopo do piloto: deve ser removida pelo recorte SG_UF = MG
    ("SP", "71072", "SÃO PAULO", "0001", "0001",
     {1: {"11": 500, "22": 10, "33": 1, "95": 0, "96": 0},
      2: {"11": 10, "22": 500, "95": 0, "96": 0}}, 600),
]  # fmt: skip
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
                out.append(["26/10/2026", "10:00:00", "2026", str(t), uf, mun, nome, zona, secao,
                            "1", "Presidente", nr, NOMES[nr], str(qt), "-1"])  # fmt: skip
    return out


def linhas_detalhe(turnos=(1, 2)) -> list[list[str]]:
    out = []
    for uf, mun, nome, zona, secao, votos, aptos in SECOES:
        for t in turnos:
            v = votos[t]
            brancos, nulos = v.get("95", 0), v.get("96", 0)
            nominais = sum(q for k, q in v.items() if k not in ("95", "96"))
            comp = nominais + brancos + nulos
            out.append(["26/10/2026", "10:00:00", "2026", str(t), uf, mun, nome, zona, secao, "1",
                        "Presidente", str(aptos), str(comp), str(aptos - comp), str(nominais),
                        str(brancos), str(nulos), "0", "0", "U", "S", "N"])  # fmt: skip
    return out


def linhas_governador() -> list[list[str]]:
    return [["26/10/2026", "10:00:00", "2026", "1", "MG", "41238", "BELO HORIZONTE", "0026",
             "0001", "3", "Governador", "300", "1", "299", "1", "0", "0", "0", "0", "U", "S",
             "N"]]  # fmt: skip


CAB_MUNZONA = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NM_MUNICIPIO", "NR_ZONA", "CD_CARGO", "DS_CARGO", "QT_APTOS", "QT_COMPARECIMENTO",
    "QT_ABSTENCOES", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS_VALIDOS", "QT_VOTOS_BRANCOS",
    "QT_VOTOS_NULOS",
]  # fmt: skip
CAB_CAND_MUNZONA = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO",
    "NM_MUNICIPIO", "NR_ZONA", "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO",
    "NM_URNA_CANDIDATO", "SG_PARTIDO", "DS_SITUACAO_CANDIDATURA", "NM_TIPO_DESTINACAO_VOTOS",
    "DS_SIT_TOT_TURNO", "ST_VOTO_EM_TRANSITO", "QT_VOTOS_NOMINAIS", "QT_VOTOS_NOMINAIS_VALIDOS",
]  # fmt: skip


def _por_zona(turnos):
    agg: dict = {}
    for uf, mun, nome, zona, _secao, votos, aptos in SECOES:
        for t in turnos:
            k = (t, uf, mun, nome, zona)
            a = agg.setdefault(k, {"aptos": 0, "votos": {}})
            a["aptos"] += aptos
            for nr, q in votos[t].items():
                a["votos"][nr] = a["votos"].get(nr, 0) + q
    return agg


def linhas_munzona(turnos=(1, 2)) -> list[list[str]]:
    out = []
    for (t, uf, mun, nome, zona), a in _por_zona(turnos).items():
        v = a["votos"]
        br, nu = v.get("95", 0), v.get("96", 0)
        nom = sum(q for k, q in v.items() if k not in ("95", "96"))
        comp = nom + br + nu
        out.append(["26/10/2026", "10:00:00", "2026", str(t), uf, mun, nome, zona, "1",
                    "Presidente", str(a["aptos"]), str(comp), str(a["aptos"] - comp), "N",
                    str(nom), str(br), str(nu)])  # fmt: skip
    return out


def linhas_cand_munzona(turnos=(1, 2)) -> list[list[str]]:
    out = []
    for (t, uf, mun, nome, zona), a in _por_zona(turnos).items():
        for nr, q in a["votos"].items():
            if nr in ("95", "96"):
                continue
            out.append(["26/10/2026", "10:00:00", "2026", str(t), uf, mun, nome, zona, "1",
                        "Presidente", f"9{nr}", nr, NOMES[nr], "PF", "APTO", "Válido",
                        "2º TURNO" if t == 1 and nr in ("11", "22") else "#NULO", "N", str(q),
                        str(q)])  # fmt: skip
    return out


def escrever_zip(destino: Path, membros: dict[str, bytes]) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in membros.items():
            zf.writestr(nome, conteudo)
    return destino


def zips_sinteticos(pasta: Path, turnos=(1, 2)) -> dict[str, Path]:
    return {
        "votacao_secao_2026_BR.zip": escrever_zip(
            pasta / "votacao_secao_2026_BR.zip",
            {
                "votacao_secao_2026_BR.csv": _csv(CAB_VOTOS, linhas_votos(turnos)),
                "leiame.txt": b"ARQUIVO SINTETICO DE TESTE",
            },
        ),
        "detalhe_votacao_secao_2026.zip": escrever_zip(
            pasta / "detalhe_votacao_secao_2026.zip",
            {
                "detalhe_votacao_secao_2026_MG.csv": _csv(CAB_DETALHE, linhas_governador()),
                "detalhe_votacao_secao_2026_BR.csv": _csv(CAB_DETALHE, linhas_detalhe(turnos)),
                "detalhe_votacao_secao_2026_ZZ.csv": _csv(CAB_DETALHE, []),
            },
        ),
        "detalhe_votacao_munzona_2026.zip": escrever_zip(
            pasta / "detalhe_votacao_munzona_2026.zip",
            {"detalhe_votacao_munzona_2026_BR.csv": _csv(CAB_MUNZONA, linhas_munzona(turnos))},
        ),
        "votacao_candidato_munzona_2026.zip": escrever_zip(
            pasta / "votacao_candidato_munzona_2026.zip",
            {
                "votacao_candidato_munzona_2026_BR.csv": _csv(
                    CAB_CAND_MUNZONA, linhas_cand_munzona(turnos)
                )
            },
        ),
    }
