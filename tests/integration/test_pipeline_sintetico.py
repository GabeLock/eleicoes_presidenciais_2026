"""Integração ponta a ponta com DADOS SINTÉTICOS, sem rede (httpx.MockTransport)."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import polars as pl
import pytest

from eleicoes import pipeline
from eleicoes.config import load_config
from eleicoes.ingestion import download as dl
from eleicoes.runlog import RunContext
from tests.fixtures.sintetico import zips_sinteticos

pytestmark = pytest.mark.integration


def _cfg(tmp: Path):
    cfg = load_config()
    proj = json.loads(json.dumps(cfg.project))
    for k in proj["paths"]:
        proj["paths"][k] = str(tmp / k)
    proj["paths"]["warehouse"] = str(tmp / "wh.duckdb")
    return replace(cfg, project=proj)


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    zips = zips_sinteticos(tmp_path / "cdn")

    def handler(request: httpx.Request) -> httpx.Response:
        nome = request.url.path.rsplit("/", 1)[-1]
        if nome not in zips:
            return httpx.Response(404)
        corpo = zips[nome].read_bytes()
        return httpx.Response(200, content=corpo, headers={"content-length": str(len(corpo))})

    original = dl.baixar

    def baixar_mock(url, destino_dir, **kw):
        return original(
            url,
            destino_dir,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
            **{**kw, "backoff_base_s": 0},
        )

    monkeypatch.setattr(pipeline, "baixar", baixar_mock)
    return _cfg(tmp_path)


def _ingest(cfg):
    with RunContext("ingest", cfg) as ctx:
        pasta = pipeline.pasta_manifestos(cfg, ctx.run_id)
        mv = pipeline.ingerir(cfg, ctx, "votacao_secao", "BR")
        mv.salvar(pasta)
        mp = pipeline.ingerir(cfg, ctx, "detalhe_votacao_secao", None)
        mp.salvar(pasta)
    return mv, mp


def test_piloto_sintetico_reconcilia_e_e_idempotente(ambiente):
    cfg = ambiente
    mv, mp = _ingest(cfg)
    assert mv.status == "disponivel" and mv.turnos_presentes == ["1", "2"]
    assert mp.perfil_csv["encoding"] == "latin-1"
    assert [c.rsplit("/", 1)[-1] for c in mp.perfil_csv["arquivos_csv"]] == [
        "detalhe_votacao_secao_2026_BR.csv"
    ]  # só o membro de Presidente

    with RunContext("transform", cfg) as ctx:
        checks = pipeline.transformar(cfg, ctx, ["MG"], "BR")
    falhas = [c for c in checks if c.critica and not c.ok]
    assert not falhas, falhas
    gold = cfg.dir_ano("gold")
    part = pl.read_parquet(gold / "gold_participacao_municipio.parquet")
    assert part.height == 3 * 2
    resumo = json.loads((gold / "resumo_virada.json").read_text())
    # sintético: A=11 lidera o 1º turno (300 x 275) e B=22 vence o 2º (353 x 327)
    assert (resumo["finalista_a"], resumo["finalista_b"]) == ("11", "22")
    assert resumo["margem_1"] == 25 and resumo["margem_2"] == -26
    assert resumo["inversao_entre_turnos"] is True
    # governador filtrado
    votos = pl.read_parquet(gold / "gold_votos_municipio.parquet")
    assert set(votos["nr_votavel"]) == {"11", "22", "33", "95", "96"}
    # código de município preservado como texto
    assert votos["cd_municipio_tse"].dtype == pl.String

    # Reexecução: mesmo snapshot (cache por hash) e mesmas tabelas
    h1 = pl.read_parquet(gold / "gold_decomposicao_municipio.parquet")
    mv2, _ = _ingest(cfg)
    assert mv2.sha256 == mv.sha256
    with RunContext("transform", cfg) as ctx:
        pipeline.transformar(cfg, ctx, ["MG"], "BR")
    assert h1.equals(pl.read_parquet(gold / "gold_decomposicao_municipio.parquet"))


def test_segundo_turno_ausente_bloqueia(tmp_path, monkeypatch):
    zips = zips_sinteticos(tmp_path / "cdn", turnos=(1,))

    def handler(request):
        corpo = zips[request.url.path.rsplit("/", 1)[-1]].read_bytes()
        return httpx.Response(200, content=corpo)

    original = dl.baixar
    monkeypatch.setattr(
        pipeline,
        "baixar",
        lambda url, d, **kw: original(
            url, d, client=httpx.Client(transport=httpx.MockTransport(handler)), **kw
        ),
    )
    cfg = _cfg(tmp_path)
    mv, _ = _ingest(cfg)
    assert mv.status == "parcial"
    with RunContext("transform", cfg) as ctx:
        checks = pipeline.transformar(cfg, ctx, ["MG"], "BR")
        rel = pipeline.relatorio_qualidade(ctx, checks, "MG")
    assert "BLOQUEADO" in rel.read_text()
    assert not (cfg.dir_ano("gold") / "resumo_virada.json").exists()


def test_colunas_divergentes_tornam_recurso_incompativel(ambiente, monkeypatch):
    cfg = ambiente
    rec = json.loads(json.dumps(cfg.sources))
    rec["recursos"]["votacao_secao"]["colunas_obrigatorias"]["qt_votos"] = "QT_VOTOS_INEXISTENTE"
    cfg = replace(cfg, sources=rec)
    with RunContext("ingest", cfg) as ctx:
        m = pipeline.ingerir(cfg, ctx, "votacao_secao", "BR")
    assert m.status == "incompativel"
    assert m.colunas_ausentes == ["QT_VOTOS_INEXISTENTE"]
