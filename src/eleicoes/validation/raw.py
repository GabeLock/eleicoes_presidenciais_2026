"""Validação bruta: inspeção de encoding, separador, cabeçalho e sentinelas a partir do próprio
arquivo — nenhum padrão é assumido como universal."""

from __future__ import annotations

import codecs
import csv
import io
from dataclasses import dataclass, field

CANDIDATOS_SEPARADOR = [";", ",", "\t", "|"]
SENTINELAS_CONHECIDAS = ["#NULO#", "#NE#", "#NULO", "-1", "-3"]  # contadas, nunca convertidas aqui


@dataclass
class PerfilCSV:
    encoding: str
    bom: bool
    separador: str
    aspas: str | None
    cabecalho: list[str]
    linhas_amostra: int
    sentinelas_amostra: dict[str, int] = field(default_factory=dict)
    alertas: list[str] = field(default_factory=list)


def detectar_encoding(amostra: bytes) -> tuple[str, bool]:
    if amostra.startswith(codecs.BOM_UTF8):
        return "utf-8", True
    if amostra.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16", True
    # Corta no último \n para não quebrar caractere multibyte no fim da amostra
    corte = amostra[: amostra.rfind(b"\n") + 1] or amostra
    try:
        corte.decode("utf-8")
        return "utf-8", False
    except UnicodeDecodeError:
        return "latin-1", False


def perfilar_csv(amostra: bytes) -> PerfilCSV:
    encoding, bom = detectar_encoding(amostra)
    texto = amostra.decode(encoding, errors="replace")
    if bom:
        texto = texto.lstrip("﻿")
    linhas = texto.splitlines()
    if len(linhas) > 1:
        linhas = linhas[:-1]  # última linha da amostra pode estar truncada
    if not linhas:
        raise ValueError("Amostra vazia")
    primeira = linhas[0]
    contagem = {s: primeira.count(s) for s in CANDIDATOS_SEPARADOR}
    separador = max(contagem, key=contagem.get)
    alertas = []
    if contagem[separador] == 0:
        raise ValueError("Não foi possível identificar o separador no cabeçalho")
    leitor = csv.reader(io.StringIO("\n".join(linhas)), delimiter=separador, quotechar='"')
    rows = list(leitor)
    cabecalho = [c.strip() for c in rows[0]]
    if len(set(cabecalho)) != len(cabecalho):
        alertas.append("Cabeçalho com nomes de coluna duplicados")
    n_col = len(cabecalho)
    irregulares = sum(1 for r in rows[1:] if len(r) != n_col)
    if irregulares:
        alertas.append(f"{irregulares} linhas da amostra com número de colunas != cabeçalho")
    aspas = '"' if primeira.startswith('"') else None
    sent = {s: sum(r.count(s) for r in rows[1:]) for s in SENTINELAS_CONHECIDAS}
    return PerfilCSV(
        encoding=encoding,
        bom=bom,
        separador=separador,
        aspas=aspas,
        cabecalho=cabecalho,
        linhas_amostra=len(rows) - 1,
        sentinelas_amostra={k: v for k, v in sent.items() if v},
        alertas=alertas,
    )


def checar_colunas(cabecalho: list[str], obrigatorias: dict[str, str]) -> list[str]:
    """Retorna as colunas obrigatórias (nome oficial) ausentes do cabeçalho real."""
    presentes = set(cabecalho)
    return sorted(v for v in obrigatorias.values() if v not in presentes)
