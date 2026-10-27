"""Quadros descritivos a partir da camada Gold. Cada saída carrega escopo, snapshot e status."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from eleicoes.analytics.indicators import adicionar_indicadores
from eleicoes.config import Config
from eleicoes.runlog import RunContext

SOMAS_PART = [
    "qt_aptos",
    "qt_comparecimento",
    "qt_abstencoes",
    "qt_votos_brancos",
    "qt_votos_nulos",
    "qt_votos_validos",
]


def _status_base(reports: Path, ano: int) -> dict:
    qualidade = [
        q
        for q in sorted((reports / "quality").glob("*.md"))
        if f"Ano: **{ano}**" in q.read_text(encoding="utf-8")
    ]
    if not qualidade:
        return {"status": "sem_relatorio_de_qualidade", "relatorio": None}
    ultimo = qualidade[-1]
    bloqueado = "BLOQUEADO" in ultimo.read_text(encoding="utf-8")
    return {"status": "bloqueado" if bloqueado else "liberado", "relatorio": ultimo.name}


def exportar_votos_candidato(gold: Path, saida: Path) -> None:
    """Votos por candidatura: UF × turno (todos) e município × candidatura no 1º turno.

    Só linhas `tipo_votavel == 'candidato'`; brancos/nulos ficam na tabela de participação.
    """
    path = gold / "gold_votos_municipio.parquet"
    if not path.exists():
        return
    votos = pl.read_parquet(path).filter(pl.col("tipo_votavel") == "candidato")
    (
        votos.group_by(["uf", "turno", "nr_votavel"])
        .agg(pl.col("nm_votavel").first(), pl.col("qt_votos").sum())
        .sort(["uf", "turno", "nr_votavel"])
        .write_csv(saida / "votos_candidato_uf_turno.csv")
    )
    (
        votos.filter(pl.col("turno") == 1)
        .select(["uf", "cd_municipio_tse", "nr_votavel", "qt_votos"])
        .sort(["uf", "cd_municipio_tse", "nr_votavel"])
        .write_csv(saida / "votos_candidato_municipio_t1.csv")
    )


def quadro_resumo(cfg: Config, ctx: RunContext) -> Path:
    gold = cfg.dir_ano("gold")
    part_path = gold / "gold_participacao_municipio.parquet"
    if not part_path.exists():
        raise RuntimeError("Gold ausente; rode `make transform` antes.")
    saida = cfg.paths["reports"] / "analysis" / ctx.run_id
    saida.mkdir(parents=True, exist_ok=True)
    status = _status_base(cfg.paths["reports"], cfg.ano)
    if status["status"] != "liberado":
        ctx.pendencias.append(f"Base {status['status']}: quadros marcados como PRELIMINARES.")

    part = pl.read_parquet(part_path)
    nac = adicionar_indicadores(part.group_by("turno").agg([pl.col(c).sum() for c in SOMAS_PART]))
    nac.sort("turno").write_csv(saida / "participacao_por_turno.csv")
    por_uf = adicionar_indicadores(
        part.group_by(["uf", "turno"]).agg([pl.col(c).sum() for c in SOMAS_PART])
    )
    por_uf.sort(["uf", "turno"]).write_csv(saida / "participacao_uf_turno.csv")

    dec_path = gold / "gold_decomposicao_municipio.parquet"
    if dec_path.exists():
        dec = pl.read_parquet(dec_path)
        uf = (
            dec.group_by("uf")
            .agg(
                pl.col("margem_1").sum(),
                pl.col("margem_2").sum(),
                pl.col("contribuicao").sum(),
                pl.col("mudou_vencedor").sum().alias("municipios_viraram"),
                pl.len().alias("municipios"),
            )
            .sort("contribuicao")
        )
        uf.write_csv(saida / "contribuicao_uf.csv")
        dec.sort("contribuicao").head(25).write_csv(saida / "top_contrib_negativas.csv")
        dec.sort("contribuicao", descending=True).head(25).write_csv(
            saida / "top_contrib_positivas.csv"
        )
        # Painel completo (uma linha por município/localidade do exterior): base dos dashboards.
        dec.sort(["uf", "cd_municipio_tse"]).write_csv(saida / "painel_municipio.csv")
    exportar_votos_candidato(gold, saida)
    resumo = gold / "resumo_virada.json"
    if resumo.exists():
        (saida / "resumo_virada.json").write_text(
            resumo.read_text(encoding="utf-8"), encoding="utf-8"
        )
    meta = {
        "ano": cfg.ano,
        "run_id": ctx.run_id,
        "commit": ctx.commit,
        "status_base": status,
        "aviso": "Contagens observadas; decomposições são contábeis, não causais.",
    }
    (saida / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return saida
