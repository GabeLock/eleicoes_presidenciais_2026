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


def _status_base(reports: Path) -> dict:
    qualidade = sorted((reports / "quality").glob("*.md"))
    if not qualidade:
        return {"status": "sem_relatorio_de_qualidade", "relatorio": None}
    ultimo = qualidade[-1]
    bloqueado = "BLOQUEADO" in ultimo.read_text(encoding="utf-8")
    return {"status": "bloqueado" if bloqueado else "liberado", "relatorio": ultimo.name}


def quadro_resumo(cfg: Config, ctx: RunContext) -> Path:
    gold = cfg.paths["gold"]
    part_path = gold / "gold_participacao_municipio.parquet"
    if not part_path.exists():
        raise RuntimeError("Gold ausente; rode `make transform` antes.")
    saida = cfg.paths["reports"] / "analysis" / ctx.run_id
    saida.mkdir(parents=True, exist_ok=True)
    status = _status_base(cfg.paths["reports"])
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
    meta = {
        "run_id": ctx.run_id,
        "commit": ctx.commit,
        "status_base": status,
        "aviso": "Contagens observadas; decomposições são contábeis, não causais.",
    }
    (saida / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return saida
