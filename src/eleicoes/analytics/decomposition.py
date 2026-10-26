"""Decomposições contábeis da mudança de margem entre turnos.

Todas as decomposições aqui são IDENTIDADES CONTÁBEIS. Elas dizem onde (território) e em que
componente (volume de válidos × margem relativa; aptos × comparecimento × validade × participação)
a margem mudou. Não identificam quem voltou às urnas, quem trocou de candidato nem efeitos causais.

Convenções:
- A = finalista que liderou o 1º turno nacional; B = o outro finalista.
- M_it = votos_A_it − votos_B_it (turno t ∈ {1, 2}).
- Contribuição_i = M_i2 − M_i1, e Σ_i Contribuição_i = M_BR,2 − M_BR,1 (exato, inteiro).
"""

from __future__ import annotations

from itertools import permutations
from math import factorial, prod

import polars as pl


def decomposicao_exata(df: pl.DataFrame, chave: str = "territorio") -> pl.DataFrame:
    """Espera colunas: chave, votos_a_1, votos_b_1, votos_a_2, votos_b_2 (inteiros).

    Retorna margens, contribuição absoluta e participação no saldo líquido nacional.
    A participação pode exceder ±100% quando o saldo líquido é pequeno frente às
    contribuições brutas de sinais opostos — isso é esperado e documentado.
    """
    req = {chave, "votos_a_1", "votos_b_1", "votos_a_2", "votos_b_2"}
    faltando = req - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas ausentes: {sorted(faltando)}")
    if df[chave].is_duplicated().any():
        raise ValueError(f"Chave '{chave}' duplicada: decomposição exige uma linha por território")
    out = df.with_columns(
        margem_1=pl.col("votos_a_1") - pl.col("votos_b_1"),
        margem_2=pl.col("votos_a_2") - pl.col("votos_b_2"),
    ).with_columns(contribuicao=pl.col("margem_2") - pl.col("margem_1"))
    saldo = out["contribuicao"].sum()
    bruto_pos = out.filter(pl.col("contribuicao") > 0)["contribuicao"].sum()
    bruto_neg = out.filter(pl.col("contribuicao") < 0)["contribuicao"].sum()
    return out.with_columns(
        participacao_saldo=(
            pl.when(pl.lit(saldo) != 0).then(pl.col("contribuicao") / pl.lit(saldo)).otherwise(None)
        ),
        saldo_liquido=pl.lit(saldo),
        bruto_positivo=pl.lit(bruto_pos),
        bruto_negativo=pl.lit(bruto_neg),
        mudou_vencedor=(pl.col("margem_1").sign() * pl.col("margem_2").sign()) < 0,
    ).sort("contribuicao")


def decomposicao_simetrica(df: pl.DataFrame) -> pl.DataFrame:
    """ΔM = média(d1,d2)·ΔV + média(V1,V2)·Δd, com d = (A−B)/V.

    Espera: votos_a_t, votos_b_t, validos_t para t=1,2. Linhas com V=0 em algum turno
    recebem componentes nulos e `v_zero=True` (o ΔM total continua exato na decomposição exata).
    """
    m1 = pl.col("votos_a_1") - pl.col("votos_b_1")
    m2 = pl.col("votos_a_2") - pl.col("votos_b_2")
    v1, v2 = pl.col("validos_1"), pl.col("validos_2")
    ok = (v1 > 0) & (v2 > 0)
    d1 = pl.when(ok).then(m1 / v1)
    d2 = pl.when(ok).then(m2 / v2)
    return df.with_columns(
        v_zero=~ok,
        d_1=d1,
        d_2=d2,
        delta_m=m2 - m1,
        comp_volume_validos=((d1 + d2) / 2) * (v2 - v1),
        comp_margem_relativa=((v1 + v2) / 2) * (d2 - d1),
    )


def shapley_produto(fatores_1: dict[str, float], fatores_2: dict[str, float]) -> dict[str, float]:
    """Decomposição de Shapley da variação de um produto de fatores entre dois estados.

    Ex.: votos = aptos × taxa_comparecimento × taxa_validos × participacao_candidato.
    A soma das contribuições é exatamente prod(f2) − prod(f1). Média sobre todas as ordens
    resolve as interações sem favorecer nenhum fator (4 fatores → 24 ordens).
    """
    if fatores_1.keys() != fatores_2.keys():
        raise ValueError("Os dois estados precisam dos mesmos fatores")
    nomes = list(fatores_1)
    n = len(nomes)
    contrib = dict.fromkeys(nomes, 0.0)
    for ordem in permutations(nomes):
        estado = dict(fatores_1)
        anterior = prod(estado.values())
        for f in ordem:
            estado[f] = fatores_2[f]
            atual = prod(estado.values())
            contrib[f] += atual - anterior
            anterior = atual
    return {k: v / factorial(n) for k, v in contrib.items()}


def identificar_finalistas(votos_nacionais: pl.DataFrame) -> tuple[str, str]:
    """A partir de votos nacionais por (turno, nr_votavel) já sem brancos/nulos,
    retorna (A, B): A = finalista com mais votos no 1º turno.

    Exige exatamente dois votáveis com votos no 2º turno.
    """
    t2 = votos_nacionais.filter(pl.col("turno") == 2)
    finalistas = t2.filter(pl.col("qt_votos") > 0)["nr_votavel"].unique().to_list()
    if len(finalistas) != 2:
        raise ValueError(f"Esperados 2 finalistas no 2º turno; encontrados {len(finalistas)}")
    t1 = votos_nacionais.filter(
        (pl.col("turno") == 1) & pl.col("nr_votavel").is_in(finalistas)
    ).sort("qt_votos", descending=True)
    if t1.height != 2:
        raise ValueError("Os dois finalistas precisam constar no 1º turno")
    if t1["qt_votos"][0] == t1["qt_votos"][1]:
        raise ValueError("Empate no 1º turno entre finalistas: definição de A ambígua")
    return t1["nr_votavel"][0], t1["nr_votavel"][1]
