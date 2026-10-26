"""Bronze (CSV extraído) → Silver (tabelas tipadas no DuckDB + Parquet)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CONTAGENS_PARTICIPACAO = [
    "qt_aptos",
    "qt_comparecimento",
    "qt_abstencoes",
    "qt_votos_nominais",
    "qt_votos_brancos",
    "qt_votos_nulos",
    "qt_votos_legenda",
    "qt_votos_anulados",
]
ENCODING_DUCKDB = {"utf-8": "utf-8", "latin-1": "latin-1", "utf-16": "utf-16"}


def _id(nome: str) -> str:
    if not IDENT.match(nome):
        raise ValueError(f"Nome de coluna inesperado (recusado no SQL): {nome!r}")
    return f'"{nome}"'


def _lit(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


def fonte_csv(caminho: Path, perfil: dict[str, Any]) -> str:
    enc = ENCODING_DUCKDB[perfil["encoding"]]
    return (
        f"read_csv({_lit(str(caminho))}, delim={_lit(perfil['separador'])}, header=true, "
        f"quote='\"', all_varchar=true, encoding={_lit(enc)})"
    )


def _projecao(mapa: dict[str, str], cabecalho: list[str], contagens: list[str]) -> list[str]:
    cols = []
    for alvo, origem in mapa.items():
        if origem not in cabecalho:
            continue
        if alvo in ("ano", "turno"):
            cols.append(f"CAST({_id(origem)} AS INTEGER) AS {alvo}")
        elif alvo in contagens or alvo == "qt_votos":
            cols.append(f"CAST({_id(origem)} AS BIGINT) AS {alvo}")
        elif alvo == "ds_cargo":
            cols.append(f"upper(trim({_id(origem)})) AS ds_cargo")
        else:
            cols.append(f"trim({_id(origem)}) AS {alvo}")
    return cols


def sql_silver_votos(csv: Path, perfil: dict, rec: dict, cargo: str, sha: str) -> str:
    mapa = {**rec["colunas_obrigatorias"], **rec.get("colunas_opcionais", {})}
    cols = _projecao(mapa, perfil["cabecalho"], [])
    esp = rec.get("votaveis_especiais", {})
    tipo = (
        f"CASE WHEN nr_votavel = {_lit(esp.get('branco', '95'))} THEN 'branco' "
        f"WHEN nr_votavel = {_lit(esp.get('nulo', '96'))} THEN 'nulo' ELSE 'candidato' END"
    )
    ds = _id(rec["colunas_obrigatorias"]["ds_cargo"])
    return f"""
CREATE OR REPLACE TABLE silver_votos_secao AS
WITH base AS (
    SELECT {", ".join(cols)}, {_lit(sha)} AS fonte_sha256
    FROM {fonte_csv(csv, perfil)}
    WHERE upper(trim({ds})) = {_lit(cargo)}
)
SELECT *, {tipo} AS tipo_votavel FROM base;
"""


def sql_silver_participacao(csv: Path, perfil: dict, rec: dict, cargo: str, sha: str) -> str:
    mapa = {**rec["colunas_obrigatorias"], **rec.get("colunas_opcionais", {})}
    cols = _projecao(mapa, perfil["cabecalho"], CONTAGENS_PARTICIPACAO)
    presentes = {c.split(" AS ")[-1] for c in cols}
    faltantes_opc = [c for c in ("qt_votos_legenda", "qt_votos_anulados") if c not in presentes]
    extras = [f"CAST(NULL AS BIGINT) AS {c}" for c in faltantes_opc]
    ds = _id(rec["colunas_obrigatorias"]["ds_cargo"])
    return f"""
CREATE OR REPLACE TABLE silver_participacao_secao AS
SELECT {", ".join(cols + extras)}, {_lit(sha)} AS fonte_sha256
FROM {fonte_csv(csv, perfil)}
WHERE upper(trim({ds})) = {_lit(cargo)};
"""


def filtrar_ufs(con: duckdb.DuckDBPyConnection, tabela: str, ufs: list[str] | None) -> int:
    if not ufs:
        return 0
    lista = ", ".join(_lit(u.upper()) for u in ufs)
    antes = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    con.execute(f"DELETE FROM {tabela} WHERE uf NOT IN ({lista})")
    return antes - con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]


def exportar_parquet(con: duckdb.DuckDBPyConnection, tabela: str, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".parquet.part")
    con.execute(f"COPY (SELECT * FROM {tabela} ORDER BY ALL) TO {_lit(str(tmp))} (FORMAT parquet)")
    tmp.replace(destino)
    return destino
