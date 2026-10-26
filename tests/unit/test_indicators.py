import polars as pl
import pytest

from eleicoes.analytics.indicators import agregar, variacao_entre_turnos

# DADOS SINTÉTICOS: município grande e pequeno com taxas muito diferentes
MUN = pl.DataFrame(
    {
        "uf": ["MG", "MG"],
        "turno": [1, 1],
        "qt_aptos": [1_000_000, 1_000],
        "qt_comparecimento": [800_000, 500],
        "qt_abstencoes": [200_000, 500],
    }
)


def test_agregacao_e_ponderada_e_nao_media_simples():
    uf = agregar(MUN, ["uf", "turno"], ["qt_aptos", "qt_comparecimento", "qt_abstencoes"])
    esperado = 800_500 / 1_001_000
    media_simples = (0.8 + 0.5) / 2
    assert uf["taxa_comparecimento"][0] == pytest.approx(esperado)
    assert uf["taxa_comparecimento"][0] != pytest.approx(media_simples)


def test_denominador_zero_vira_nulo():
    df = pl.DataFrame(
        {
            "uf": ["ZZ"],
            "turno": [1],
            "qt_aptos": [0],
            "qt_comparecimento": [0],
            "qt_abstencoes": [0],
        }
    )
    assert (
        agregar(df, ["uf", "turno"], ["qt_aptos", "qt_comparecimento", "qt_abstencoes"])[
            "taxa_comparecimento"
        ][0]
        is None
    )


def test_variacao_de_taxa_em_pontos_percentuais():
    df = pl.DataFrame({"uf": ["MG", "MG"], "turno": [1, 2], "taxa_comparecimento": [0.8, 0.78]})
    v = variacao_entre_turnos(df, ["uf"], ["taxa_comparecimento"])
    assert v["delta_pp_taxa_comparecimento"][0] == pytest.approx(-2.0)
