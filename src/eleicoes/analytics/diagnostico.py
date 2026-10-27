"""Diagnósticos de consistência entre arquivos do TSE (sem interpretação automática).

Lê o warehouse DuckDB gerado por `transform` e grava CSVs + um resumo em Markdown:

- I-01 / A-04: votos nominais por seção × por município/zona, por candidatura e por UF, junto
  com a situação jurídica e a destinação dos votos declaradas no arquivo por zona.
- A-06: votáveis especiais (95/96 e quaisquer outros códigos) do arquivo por seção comparados
  com brancos, nulos e nominais do detalhe da apuração, seção a seção.

Os números são contagens observadas; a explicação das diferenças é feita por pessoa,
citando o leiame e a versão de cada arquivo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

ATRIBUTOS_CANDIDATURA = (
    "ds_situacao_candidatura",
    "ds_detalhe_situacao_cand",
    "ds_situacao_julgamento",
    "nm_tipo_destinacao_votos",
    "ds_sit_tot_turno",
)


def _tabelas(con: duckdb.DuckDBPyConnection) -> set[str]:
    return {r[0] for r in con.execute("SHOW TABLES").fetchall()}


def _colunas(con: duckdb.DuckDBPyConnection, tabela: str) -> list[str]:
    return [r[0] for r in con.execute(f"DESCRIBE {tabela}").fetchall()]


def _copiar(con: duckdb.DuckDBPyConnection, sql: str, destino: Path) -> int:
    con.execute(f"CREATE OR REPLACE TEMP TABLE _saida AS {sql}")
    n = con.execute("SELECT count(*) FROM _saida").fetchone()[0]
    tmp = destino.with_suffix(".csv.part")
    con.execute(f"COPY (SELECT * FROM _saida) TO '{tmp}' (HEADER)")
    tmp.replace(destino)
    return int(n)


def _sql_candidatos(con: duckdb.DuckDBPyConnection, por_uf: bool) -> str:
    attrs = [c for c in ATRIBUTOS_CANDIDATURA if c in _colunas(con, "silver_candidato_munzona")]
    agg = "".join(f", string_agg(DISTINCT {c}, ' | ') AS {c}" for c in attrs)
    k = "turno, uf, " if por_uf else "turno, "
    filtro = "WHERE dif_nominais <> 0 OR dif_validos <> 0" if por_uf else ""
    return f"""
        WITH s AS (SELECT {k}nr_votavel AS nr, any_value(nm_votavel) AS nm_secao,
                          sum(qt_votos) AS votos_secao
                   FROM silver_votos_secao WHERE tipo_votavel = 'candidato' GROUP BY ALL),
             z AS (SELECT {k}nr_candidato AS nr, any_value(nm_urna_candidato) AS nm_zona,
                          sum(qt_votos_nominais) AS nominais_zona,
                          sum(qt_votos_nominais_validos) AS validos_zona{agg}
                   FROM silver_candidato_munzona GROUP BY ALL),
             j AS (SELECT *, coalesce(votos_secao, 0) - coalesce(nominais_zona, 0) AS dif_nominais,
                          coalesce(votos_secao, 0) - coalesce(validos_zona, 0) AS dif_validos
                   FROM s FULL OUTER JOIN z USING ({k}nr))
        SELECT * FROM j {filtro} ORDER BY ALL"""


def _sql_totais_colunas(con: duckdb.DuckDBPyConnection, tabela: str, fonte: str) -> str:
    qts = [c for c in _colunas(con, tabela) if c.startswith("qt_")]
    partes = [
        f"SELECT turno, '{fonte}' AS fonte, '{c}' AS coluna, sum({c})::BIGINT AS total, "
        f"count(*) FILTER (WHERE {c} < 0) AS linhas_sentinela FROM {tabela} GROUP BY turno"
        for c in qts
    ]
    return " UNION ALL ".join(partes)


def _sql_zonas(con: duckdb.DuckDBPyConnection) -> str:
    cz = _colunas(con, "silver_detalhe_munzona")
    cp = _colunas(con, "silver_participacao_secao")
    extra_z = [
        c
        for c in (
            "qt_votos_nominais",
            "qt_total_votos_anulados",
            "qt_total_votos_anul_subjud",
            "qt_votos_anulados_apu_sep",
            "qt_votos_nulos_tecnicos",
            "qt_total_votos_nulos",
        )
        if c in cz
    ]
    sel_z = "".join(f", sum({c})::BIGINT AS zona_{c}" for c in extra_z)
    extra_s = ""
    if "qt_votos_anulados_apu_sep" in cp:
        extra_s += ", sum(qt_votos_anulados_apu_sep)::BIGINT AS secao_qt_votos_anulados_apu_sep"
    for c in ("st_secao_anulada", "ds_origem_voto"):
        if c in cp:
            extra_s += f", string_agg(DISTINCT {c}, ' | ') AS secao_{c}"
    k = "turno, uf, cd_municipio_tse, zona"
    return f"""
        WITH s AS (SELECT {k}, sum(qt_votos_nominais)::BIGINT AS secao_nominais,
                          count(*) AS secoes{extra_s}
                   FROM silver_participacao_secao GROUP BY ALL),
             z AS (SELECT {k}, sum(qt_votos_nominais_validos)::BIGINT AS zona_nominais_validos{sel_z}
                   FROM silver_detalhe_munzona GROUP BY ALL)
        SELECT *, secao_nominais - zona_nominais_validos AS dif
        FROM s JOIN z USING (turno, uf, cd_municipio_tse, zona)
        WHERE secao_nominais IS DISTINCT FROM zona_nominais_validos
        ORDER BY abs(dif) DESC, turno, uf, cd_municipio_tse, zona"""


SQL_VOTAVEIS = """
    SELECT turno, nr_votavel, tipo_votavel, string_agg(DISTINCT nm_votavel, ' | ') AS nm_votavel,
           sum(qt_votos)::BIGINT AS votos, count(*) AS linhas_secao
    FROM silver_votos_secao GROUP BY ALL ORDER BY turno, votos DESC"""

SQL_ESPECIAIS_SECAO = """
    WITH v AS (SELECT turno, uf, cd_municipio_tse, zona, secao,
                      sum(qt_votos) FILTER (WHERE tipo_votavel = 'branco') AS v95,
                      sum(qt_votos) FILTER (WHERE tipo_votavel = 'nulo') AS v96,
                      sum(qt_votos) FILTER (WHERE tipo_votavel = 'candidato') AS vcand
               FROM silver_votos_secao GROUP BY ALL),
         j AS (SELECT p.turno,
                      coalesce(v.v95, 0) AS v95, p.qt_votos_brancos AS brancos,
                      coalesce(v.v96, 0) AS v96, p.qt_votos_nulos AS nulos,
                      coalesce(v.vcand, 0) AS vcand, p.qt_votos_nominais AS nominais,
                      v.turno IS NULL AS sem_linha_votacao
               FROM silver_participacao_secao p
               LEFT JOIN v USING (turno, uf, cd_municipio_tse, zona, secao))
    SELECT turno, count(*) AS secoes_detalhe,
           count(*) FILTER (WHERE sem_linha_votacao) AS secoes_sem_votacao,
           sum(v95)::BIGINT AS votos_95, sum(brancos)::BIGINT AS brancos_detalhe,
           count(*) FILTER (WHERE v95 <> brancos) AS secoes_95_diverge,
           sum(v96)::BIGINT AS votos_96, sum(nulos)::BIGINT AS nulos_detalhe,
           count(*) FILTER (WHERE v96 <> nulos) AS secoes_96_diverge,
           sum(vcand)::BIGINT AS votos_candidatos, sum(nominais)::BIGINT AS nominais_detalhe,
           count(*) FILTER (WHERE vcand <> nominais) AS secoes_nominais_diverge
    FROM j GROUP BY turno ORDER BY turno"""


def executar(warehouse: Path, destino: Path) -> dict[str, Any]:
    if not Path(warehouse).exists():
        raise FileNotFoundError(f"Warehouse {warehouse} não existe; rode `make transform`.")
    destino.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(warehouse), read_only=True)
    tabs = _tabelas(con)
    resumo: dict[str, Any] = {"tabelas": sorted(tabs)}
    if "silver_votos_secao" in tabs:
        resumo["votaveis"] = _copiar(con, SQL_VOTAVEIS, destino / "votaveis_por_turno.csv")
    if {"silver_votos_secao", "silver_participacao_secao"} <= tabs:
        resumo["especiais_secao"] = _copiar(
            con, SQL_ESPECIAIS_SECAO, destino / "especiais_95_96_por_secao.csv"
        )
    if {"silver_votos_secao", "silver_candidato_munzona"} <= tabs:
        resumo["candidatos"] = _copiar(
            con, _sql_candidatos(con, False), destino / "nominais_por_candidato.csv"
        )
        resumo["candidatos_uf_divergentes"] = _copiar(
            con, _sql_candidatos(con, True), destino / "nominais_por_candidato_uf.csv"
        )
    if {"silver_participacao_secao", "silver_detalhe_munzona"} <= tabs:
        partes = [_sql_totais_colunas(con, "silver_participacao_secao", "detalhe_votacao_secao")]
        partes.append(_sql_totais_colunas(con, "silver_detalhe_munzona", "detalhe_votacao_munzona"))
        if "silver_candidato_munzona" in tabs:
            partes.append(
                _sql_totais_colunas(con, "silver_candidato_munzona", "votacao_candidato_munzona")
            )
        resumo["totais_colunas"] = _copiar(
            con,
            "SELECT * FROM (" + " UNION ALL ".join(partes) + ") ORDER BY turno, fonte, coluna",
            destino / "totais_por_coluna.csv",
        )
        resumo["zonas_nominais_divergentes"] = _copiar(
            con, _sql_zonas(con), destino / "zonas_nominais_divergentes.csv"
        )
    con.close()
    (destino / "resumo.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resumo
