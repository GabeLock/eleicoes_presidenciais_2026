import polars as pl
import pytest

from eleicoes.analytics.decomposition import (
    decomposicao_exata,
    decomposicao_simetrica,
    identificar_finalistas,
    shapley_produto,
)

# DADOS SINTÉTICOS
PAINEL = pl.DataFrame(
    {
        "territorio": ["X", "Y", "Z"],
        "votos_a_1": [100, 50, 10],
        "votos_b_1": [80, 60, 5],
        "votos_a_2": [110, 55, 8],
        "votos_b_2": [120, 50, 9],
        "validos_1": [200, 130, 20],
        "validos_2": [230, 105, 17],
    }
)


def test_decomposicao_exata_fecha_com_variacao_nacional():
    dec = decomposicao_exata(PAINEL)
    m1 = (PAINEL["votos_a_1"] - PAINEL["votos_b_1"]).sum()
    m2 = (PAINEL["votos_a_2"] - PAINEL["votos_b_2"]).sum()
    assert dec["contribuicao"].sum() == m2 - m1
    assert dec["participacao_saldo"].sum() == pytest.approx(1.0)


def test_mudou_vencedor_detecta_inversao_de_sinal():
    dec = decomposicao_exata(PAINEL).sort("territorio")
    assert dec["mudou_vencedor"].to_list() == [True, True, True]


def test_participacao_pode_exceder_100pct_com_saldo_pequeno():
    df = pl.DataFrame(
        {
            "territorio": ["P", "N"],
            "votos_a_1": [0, 100],
            "votos_b_1": [0, 0],
            "votos_a_2": [1000, 0],
            "votos_b_2": [0, 899],
        }
    )
    dec = decomposicao_exata(df)
    assert dec["participacao_saldo"].abs().max() > 1


def test_chave_duplicada_e_rejeitada():
    with pytest.raises(ValueError, match="duplicada"):
        decomposicao_exata(pl.concat([PAINEL, PAINEL]))


def test_decomposicao_simetrica_soma_delta_m():
    d = decomposicao_simetrica(PAINEL)
    soma = d["comp_volume_validos"] + d["comp_margem_relativa"]
    assert (soma - d["delta_m"]).abs().max() < 1e-9


def test_decomposicao_simetrica_trata_v_zero():
    df = PAINEL.with_columns(pl.Series("validos_1", [0, 130, 20]))
    d = decomposicao_simetrica(df)
    assert d["v_zero"].to_list() == [True, False, False]
    assert d["comp_volume_validos"][0] is None


def test_shapley_soma_variacao_do_produto():
    f1 = {"aptos": 1000, "comp": 0.8, "validos": 0.9, "part": 0.45}
    f2 = {"aptos": 1000, "comp": 0.78, "validos": 0.95, "part": 0.52}
    c = shapley_produto(f1, f2)
    total = 1000 * 0.78 * 0.95 * 0.52 - 1000 * 0.8 * 0.9 * 0.45
    assert sum(c.values()) == pytest.approx(total)
    assert c["aptos"] == pytest.approx(0)


def test_identificar_finalistas_usa_lider_do_primeiro_turno():
    nac = pl.DataFrame(
        {
            "turno": [1, 1, 1, 2, 2],
            "nr_votavel": ["11", "22", "33", "11", "22"],
            "qt_votos": [300, 280, 90, 330, 350],
        }
    )
    assert identificar_finalistas(nac) == ("11", "22")


def test_identificar_finalistas_exige_dois_no_segundo_turno():
    nac = pl.DataFrame({"turno": [1, 2], "nr_votavel": ["11", "11"], "qt_votos": [10, 10]})
    with pytest.raises(ValueError, match="2 finalistas"):
        identificar_finalistas(nac)
