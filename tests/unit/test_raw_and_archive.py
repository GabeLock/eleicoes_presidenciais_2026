import zipfile

import pytest

from eleicoes.ingestion.archive import ZipInseguro, extrair, inspecionar_zip
from eleicoes.ingestion.download import ConteudoInvalido, checar_assinatura
from eleicoes.validation.raw import checar_colunas, detectar_encoding, perfilar_csv


def test_perfil_latin1_ponto_e_virgula():
    amostra = '"NR_TURNO";"NM_MUNICIPIO";"QT_VOTOS"\n"1";"ÁGUA BOA";"10"\n"2";"SÃO JOÃO";"#NULO#"\n'
    p = perfilar_csv(amostra.encode("latin-1"))
    assert p.encoding == "latin-1"
    assert p.separador == ";"
    assert p.cabecalho == ["NR_TURNO", "NM_MUNICIPIO", "QT_VOTOS"]


def test_perfil_utf8_com_bom_e_virgula():
    amostra = "﻿a,b,c\n1,2,3\n4,5,6\n".encode()
    p = perfilar_csv(amostra)
    assert (p.encoding, p.bom, p.separador) == ("utf-8", True, ",")


def test_amostra_cortada_no_meio_de_multibyte_continua_utf8():
    txt = "a;b\nção;1\n".encode() + "ã".encode()[:1]
    assert detectar_encoding(txt)[0] == "utf-8"


def test_colunas_ausentes():
    assert checar_colunas(["A", "B"], {"x": "A", "y": "C"}) == ["C"]


def test_html_no_lugar_de_zip(tmp_path):
    f = tmp_path / "x.zip"
    f.write_bytes(b"<!DOCTYPE html><html><body>erro</body></html>")
    with pytest.raises(ConteudoInvalido, match="HTML"):
        checar_assinatura(f)


def test_zip_com_path_traversal_e_recusado(tmp_path):
    f = tmp_path / "mal.zip"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr("../../etc/passwd", "x")
    with pytest.raises(ZipInseguro, match="inseguro"):
        inspecionar_zip(f)


def test_zip_bomb_por_taxa_de_compressao(tmp_path):
    f = tmp_path / "bomba.zip"
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.csv", b"0" * 5_000_000)
    with pytest.raises(ZipInseguro, match="compressão"):
        inspecionar_zip(f, max_taxa_compressao=50)


def test_extracao_idempotente(tmp_path):
    f = tmp_path / "ok.zip"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr("pasta/a.csv", "x;y\n1;2\n")
    p1 = extrair(f, tmp_path / "out")
    mtime = p1[0].stat().st_mtime_ns
    p2 = extrair(f, tmp_path / "out")
    assert p1 == p2 and p2[0].stat().st_mtime_ns == mtime
