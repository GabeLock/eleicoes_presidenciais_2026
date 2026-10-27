"""Nulos técnicos (ADR 0005): votos de candidatura inapta saem dos válidos sem virar nulo digitado."""

import duckdb

from eleicoes.config import load_config
from eleicoes.transformation import silver as sv

CAB = ["ANO_ELEICAO", "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO",
       "CD_CARGO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS"]  # fmt: skip


def _csv(tmp_path):
    linhas = [
        ("1", "10", 50), ("1", "28", 3), ("1", "95", 2), ("1", "96", 4),
        ("2", "10", 55), ("2", "28", 1),
    ]  # fmt: skip
    corpo = [";".join(f'"{c}"' for c in CAB)]
    for turno, nr, q in linhas:
        v = ["2026", turno, "MG", "1", "X", "1", "1", "1", "PRESIDENTE", nr, nr, str(q)]
        corpo.append(";".join(f'"{c}"' for c in v))
    p = tmp_path / "v.csv"
    p.write_text("\n".join(corpo) + "\n", encoding="utf-8")
    return p


def test_reclassifica_so_no_turno_configurado_e_ajusta_validos(tmp_path):
    rec = load_config().recurso("votacao_secao")
    perfil = {"encoding": "utf-8", "separador": ";", "cabecalho": CAB}
    con = duckdb.connect()
    con.execute(sv.sql_silver_votos(_csv(tmp_path), perfil, rec, "PRESIDENTE", "x", {1: ["28"]}))
    tipos = dict(
        con.execute(
            "SELECT turno || '-' || nr_votavel, tipo_votavel FROM silver_votos_secao"
        ).fetchall()
    )
    assert tipos["1-28"] == "nulo_tecnico"
    assert tipos["2-28"] == "candidato"  # regra vale só para o turno declarado
    assert tipos["1-96"] == "nulo" and tipos["1-95"] == "branco"

    con.execute("""CREATE TABLE silver_participacao_secao AS SELECT * FROM (VALUES
        (1,'MG','00001','0001','0001',53,2,4,NULL::BIGINT),
        (2,'MG','00001','0001','0001',56,0,0,NULL::BIGINT))
        t(turno,uf,cd_municipio_tse,zona,secao,qt_votos_nominais,qt_votos_brancos,
          qt_votos_nulos,qt_votos_legenda)""")
    sv.harmonizar_validos(con)
    r = dict(
        con.execute(
            "SELECT turno, (qt_votos_validos, qt_votos_nulos_tecnicos, qt_votos_nulos) "
            "FROM silver_participacao_secao"
        ).fetchall()
    )
    assert r[1] == (50, 3, 4)  # nulos digitados intactos
    assert r[2] == (56, 0, 0)
    sv.harmonizar_validos(con)  # idempotente
    assert (
        con.execute("SELECT sum(qt_votos_validos) FROM silver_participacao_secao").fetchone()[0]
        == 106
    )


def test_config_declara_nulo_tecnico_2026():
    from eleicoes import pipeline

    cfg = load_config().com_ano(2026)
    assert pipeline.nulos_tecnicos_do_ano(cfg) == {1: ["28"]}
    assert pipeline.nulos_tecnicos_do_ano(load_config().com_ano(2022)) == {}
