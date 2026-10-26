"""Indicadores de participação com numerador e denominador sempre explícitos.

Agregações territoriais recomputam a razão a partir das somas (Σnum/Σden),
nunca pela média simples de percentuais municipais.
"""

from __future__ import annotations

import polars as pl

# nome_indicador: (numerador, denominador)
INDICADORES: dict[str, tuple[str, str]] = {
    "taxa_abstencao": ("qt_abstencoes", "qt_aptos"),
    "taxa_comparecimento": ("qt_comparecimento", "qt_aptos"),
    "taxa_brancos": ("qt_votos_brancos", "qt_comparecimento"),
    "taxa_nulos": ("qt_votos_nulos", "qt_comparecimento"),
    "taxa_validos": ("qt_votos_validos", "qt_comparecimento"),
}


def razao(num: str, den: str) -> pl.Expr:
    return pl.when(pl.col(den) > 0).then(pl.col(num) / pl.col(den)).otherwise(None)


def adicionar_indicadores(df: pl.DataFrame) -> pl.DataFrame:
    exprs = [
        razao(n, d).alias(nome) for nome, (n, d) in INDICADORES.items() if {n, d} <= set(df.columns)
    ]
    return df.with_columns(exprs)


def agregar(df: pl.DataFrame, por: list[str], somas: list[str]) -> pl.DataFrame:
    """Soma contagens e só então recalcula as razões (ponderação correta)."""
    return adicionar_indicadores(df.group_by(por).agg([pl.col(c).sum() for c in somas]))


def variacao_entre_turnos(df: pl.DataFrame, chave: list[str], colunas: list[str]) -> pl.DataFrame:
    """Pivota turno 1/2 e calcula Δ. Para taxas, Δ é em pontos percentuais (×100)."""

    def _turno(t: int) -> pl.DataFrame:
        return (
            df.filter(pl.col("turno") == t)
            .select(chave + colunas)
            .rename({c: f"{c}_{t}" for c in colunas})
        )

    t1 = _turno(1)
    if t1.select(chave).is_duplicated().any():
        raise ValueError("Chave duplicada por turno: agregue antes de comparar turnos")
    largo = t1.join(_turno(2), on=chave, how="full", coalesce=True)
    exprs = []
    for c in colunas:
        c1, c2 = f"{c}_1", f"{c}_2"
        if c1 in largo.columns and c2 in largo.columns:
            delta = pl.col(c2) - pl.col(c1)
            exprs.append(
                (delta * 100).alias(f"delta_pp_{c}")
                if c.startswith("taxa_")
                else delta.alias(f"delta_{c}")
            )
    return largo.with_columns(exprs)
