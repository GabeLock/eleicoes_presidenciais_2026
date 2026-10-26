"""Checagens de integridade: unicidade na granularidade declarada, preservação de totais
em joins e reconciliações hierárquicas. Retornam objetos de resultado (não só asserts)
para alimentar o relatório de qualidade."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb


@dataclass
class Checagem:
    nome: str
    ok: bool
    critica: bool
    detalhe: str

    def como_dict(self) -> dict:
        return self.__dict__.copy()


def _q(nome: str) -> str:
    if not nome.replace("_", "").replace(".", "").isalnum():
        raise ValueError(f"Identificador inválido: {nome!r}")
    return nome


def unicidade(con: duckdb.DuckDBPyConnection, tabela: str, chave: list[str]) -> Checagem:
    cols = ", ".join(_q(c) for c in chave)
    dup = con.execute(
        f"SELECT count(*) FROM (SELECT {cols} FROM {_q(tabela)} GROUP BY {cols} HAVING count(*) > 1)"
    ).fetchone()[0]
    return Checagem(
        f"unicidade:{tabela}", dup == 0, True, f"{dup} combinações duplicadas de ({cols})"
    )


def nao_negativos(con: duckdb.DuckDBPyConnection, tabela: str, colunas: list[str]) -> Checagem:
    cond = " OR ".join(f"{_q(c)} < 0" for c in colunas)
    n = con.execute(f"SELECT count(*) FROM {_q(tabela)} WHERE {cond}").fetchone()[0]
    return Checagem(f"nao_negativos:{tabela}", n == 0, True, f"{n} linhas com contagem negativa")


NAO_INSTALADA = ("N", "NÃO", "NAO")  # leiame diz S/N; dados 2026 trazem "Sim"/"Não"


def identidade_aptos(con: duckdb.DuckDBPyConnection, tabela: str) -> Checagem:
    """aptos = comparecimento + abstenção, só em seções instaladas (em seção não instalada o TSE
    mantém os aptos e zera comparecimento e abstenção — universo diferente, não erro)."""
    cols = {r[0] for r in con.execute(f"DESCRIBE {_q(tabela)}").fetchall()}
    instalada = "TRUE"
    if "st_secao_instalada" in cols:
        lista = ", ".join(f"'{v}'" for v in NAO_INSTALADA)
        instalada = f"coalesce(upper(st_secao_instalada), '') NOT IN ({lista})"
    n, dif, nao_inst = con.execute(
        f"""SELECT count(*) FILTER (WHERE {instalada}
                                     AND qt_aptos <> qt_comparecimento + qt_abstencoes),
                   coalesce(sum(abs(qt_aptos - qt_comparecimento - qt_abstencoes))
                            FILTER (WHERE {instalada}), 0),
                   count(*) FILTER (WHERE NOT ({instalada}))
            FROM {_q(tabela)}"""
    ).fetchone()
    return Checagem(
        f"aptos=comparecimento+abstencao:{tabela}",
        n == 0,
        False,
        f"{n} seções instaladas divergentes; |dif| total = {dif}; "
        f"{nao_inst} seções não instaladas excluídas da identidade",
    )


def totais_preservados(antes: int, depois: int, nome: str) -> Checagem:
    return Checagem(
        f"join_preserva_total:{nome}",
        antes == depois,
        True,
        f"antes={antes} depois={depois} diferença={depois - antes}",
    )


def reconciliacao_hierarquica(
    con: duckdb.DuckDBPyConnection, fina: str, agregada: str, chave: list[str], medida: str
) -> Checagem:
    """Compara Σ(fina) agrupada em `chave` com a tabela `agregada` na mesma chave (diferença exata)."""
    cols = ", ".join(_q(c) for c in chave)
    on = " AND ".join(f"f.{_q(c)} IS NOT DISTINCT FROM a.{_q(c)}" for c in chave)
    n, dif = con.execute(
        f"""WITH f AS (SELECT {cols}, sum({_q(medida)}) AS v FROM {_q(fina)} GROUP BY {cols}),
                 a AS (SELECT {cols}, sum({_q(medida)}) AS v FROM {_q(agregada)} GROUP BY {cols})
            SELECT count(*) FILTER (WHERE f.v IS DISTINCT FROM a.v),
                   coalesce(sum(abs(coalesce(f.v,0) - coalesce(a.v,0))), 0)
            FROM f FULL OUTER JOIN a ON {on}"""
    ).fetchone()
    return Checagem(
        f"reconciliacao:{fina}->{agregada}:{medida}",
        n == 0,
        True,
        f"{n} grupos divergentes; |dif| total = {dif}",
    )
