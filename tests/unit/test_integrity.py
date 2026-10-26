import duckdb

from eleicoes.validation import integrity as ck


def _con():
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE f AS SELECT * FROM (VALUES (1,'A',10),(1,'A',5),(1,'B',3)) t(turno,m,v)"
    )
    con.execute("CREATE TABLE g AS SELECT * FROM (VALUES (1,'A',15),(1,'B',3)) t(turno,m,v)")
    return con


def test_unicidade_detecta_duplicata():
    assert not ck.unicidade(_con(), "f", ["turno", "m"]).ok
    assert ck.unicidade(_con(), "g", ["turno", "m"]).ok


def test_reconciliacao_hierarquica_exata():
    con = _con()
    assert ck.reconciliacao_hierarquica(con, "f", "g", ["turno", "m"], "v").ok
    con.execute("UPDATE g SET v = 16 WHERE m = 'A'")
    r = ck.reconciliacao_hierarquica(con, "f", "g", ["turno", "m"], "v")
    assert not r.ok and "1 grupos" in r.detalhe


def test_join_que_multiplica_linhas_e_detectado():
    con = duckdb.connect()
    con.execute("CREATE TABLE votos AS SELECT * FROM (VALUES ('M1', 100)) t(mun, votos)")
    con.execute(
        "CREATE TABLE perfil AS SELECT * FROM (VALUES ('M1','16-17'),('M1','18-24')) t(mun, faixa)"
    )
    antes = con.execute("SELECT sum(votos) FROM votos").fetchone()[0]
    depois = con.execute("SELECT sum(votos) FROM votos JOIN perfil USING (mun)").fetchone()[0]
    assert not ck.totais_preservados(antes, depois, "votos×perfil").ok


def test_identificador_malicioso_recusado():
    import pytest

    with pytest.raises(ValueError):
        ck.unicidade(_con(), "f; DROP TABLE f", ["turno"])
