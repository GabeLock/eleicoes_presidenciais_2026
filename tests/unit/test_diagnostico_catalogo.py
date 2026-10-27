"""Diagnóstico seção × zona e descoberta de conjuntos por grupo do CKAN (dados sintéticos)."""

import csv

import duckdb
import pytest

from eleicoes.analytics import diagnostico
from eleicoes.discovery.catalog import parse_busca


def _warehouse(path):
    con = duckdb.connect(str(path))
    con.execute("""CREATE TABLE silver_votos_secao AS SELECT * FROM (VALUES
        (1,'MG','00001','0001','0001','10','A',60,'candidato'),
        (1,'MG','00001','0001','0001','20','B',30,'candidato'),
        (1,'MG','00001','0001','0001','95','Branco',4,'branco'),
        (1,'MG','00001','0001','0001','96','Nulo',6,'nulo'))
        t(turno,uf,cd_municipio_tse,zona,secao,nr_votavel,nm_votavel,qt_votos,tipo_votavel)""")
    con.execute("""CREATE TABLE silver_participacao_secao AS SELECT * FROM (VALUES
        (1,'MG','00001','0001','0001',120,100,20,90,4,7,0,'N'))
        t(turno,uf,cd_municipio_tse,zona,secao,qt_aptos,qt_comparecimento,qt_abstencoes,
          qt_votos_nominais,qt_votos_brancos,qt_votos_nulos,qt_votos_anulados_apu_sep,
          st_secao_anulada)""")
    # zona: candidato 20 tem 5 votos anulados sub judice (nominais 30, válidos 25)
    con.execute("""CREATE TABLE silver_detalhe_munzona AS SELECT * FROM (VALUES
        (1,'MG','00001','0001',120,100,20,4,6,85,5))
        t(turno,uf,cd_municipio_tse,zona,qt_aptos,qt_comparecimento,qt_abstencoes,
          qt_votos_brancos,qt_votos_nulos,qt_votos_nominais_validos,qt_total_votos_anul_subjud)""")
    con.execute("""CREATE TABLE silver_candidato_munzona AS SELECT * FROM (VALUES
        (1,'MG','00001','0001','10','A',60,60,'APTO','Válido'),
        (1,'MG','00001','0001','20','B',30,25,'APTO','Anulado sub judice'))
        t(turno,uf,cd_municipio_tse,zona,nr_candidato,nm_urna_candidato,qt_votos_nominais,
          qt_votos_nominais_validos,ds_situacao_candidatura,nm_tipo_destinacao_votos)""")
    con.close()


def _ler(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_diagnostico_localiza_diferenca_por_candidato(tmp_path):
    wh = tmp_path / "wh.duckdb"
    _warehouse(wh)
    resumo = diagnostico.executar(wh, tmp_path / "out")
    cand = {r["nr"]: r for r in _ler(tmp_path / "out" / "nominais_por_candidato.csv")}
    assert cand["20"]["dif_validos"] == "5" and cand["20"]["dif_nominais"] == "0"
    assert cand["10"]["dif_validos"] == "0"
    assert "Anulado sub judice" in cand["20"]["nm_tipo_destinacao_votos"]
    zonas = _ler(tmp_path / "out" / "zonas_nominais_divergentes.csv")
    assert len(zonas) == 1 and zonas[0]["dif"] == "5"
    assert zonas[0]["zona_qt_total_votos_anul_subjud"] == "5"
    assert resumo["candidatos_uf_divergentes"] == 1


def test_diagnostico_compara_95_96_com_detalhe(tmp_path):
    wh = tmp_path / "wh.duckdb"
    _warehouse(wh)
    diagnostico.executar(wh, tmp_path / "out")
    (esp,) = _ler(tmp_path / "out" / "especiais_95_96_por_secao.csv")
    assert esp["secoes_95_diverge"] == "0"
    assert esp["votos_96"] == "6" and esp["nulos_detalhe"] == "7"
    assert esp["secoes_96_diverge"] == "1"
    assert esp["secoes_nominais_diverge"] == "0"
    vot = _ler(tmp_path / "out" / "votaveis_por_turno.csv")
    assert {r["nr_votavel"] for r in vot} == {"10", "20", "95", "96"}


def test_diagnostico_sem_warehouse_falha_claramente(tmp_path):
    with pytest.raises(FileNotFoundError):
        diagnostico.executar(tmp_path / "nao_existe.duckdb", tmp_path / "out")


def test_parse_busca_filtra_por_ano():
    payload = {
        "success": True,
        "result": {"results": [{"name": "comparecimento-2022"}, {"name": "comparecimento-2026"}]},
    }
    assert parse_busca(payload, 2026) == ["comparecimento-2026"]
    assert parse_busca(payload, None) == ["comparecimento-2022", "comparecimento-2026"]
    with pytest.raises(RuntimeError):
        parse_busca({"success": False, "error": "x"}, 2026)
