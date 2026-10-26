"""Interface de linha de comando. Os alvos do Makefile chamam estes comandos."""

from __future__ import annotations

import json
import logging
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from eleicoes.config import UFS_BRASIL, load_config
from eleicoes.runlog import RunContext

app = typer.Typer(add_completion=False, help="Pipeline TSE — Presidência 2026, 1º × 2º turno.")
console = Console()
ANOS_SUPORTADOS = {2026}


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def _checar_ano(ano: int) -> None:
    if ano not in ANOS_SUPORTADOS:
        raise typer.BadParameter(
            f"Ano {ano} ainda não implementado (2018/2022 entram na expansão histórica)."
        )


def _ufs(uf: str) -> list[str] | None:
    u = uf.upper()
    if u in ("ALL", "BR", "TODAS"):
        return None  # nacional, inclusive exterior
    lista = [x.strip() for x in u.split(",") if x.strip()]
    invalidas = [x for x in lista if x not in UFS_BRASIL and x != "ZZ"]
    if invalidas:
        raise typer.BadParameter(f"UF inválida: {invalidas}")
    return lista


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    _setup_logging(verbose)


@app.command()
def inventory() -> None:
    """Consulta o catálogo CKAN do TSE e faz HEAD em cada arquivo."""
    from eleicoes.discovery import inventory as inv_mod

    cfg = load_config()
    with RunContext("inventory", cfg) as ctx:
        inv = inv_mod.montar_inventario(cfg)
        destino = inv_mod.salvar(inv, cfg.paths["reports"] / "inventory" / f"{ctx.run_id}.json")
        linhas = inv_mod.consolidar(inv, cfg.paths["manifests"])
        (destino.with_suffix(".consolidado.json")).write_text(
            json.dumps(linhas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ctx.volumes["recursos_catalogo"] = len(inv["itens"])
        if inv["config_fora_do_catalogo"]:
            ctx.pendencias.append(
                f"URLs da config fora do catálogo: {inv['config_fora_do_catalogo']}"
            )
        t = Table("conjunto", "recurso", "HTTP", "bytes", "status")
        for linha in linhas:
            t.add_row(
                linha["conjunto"],
                linha["recurso"][:55],
                str(next((i["http_status"] for i in inv["itens"] if i["url"] == linha["url"]), "")),
                str(linha["bytes"] or ""),
                linha["status"],
            )
        console.print(t)
        console.print(f"Inventário salvo em {destino}")


@app.command()
def ingest(
    year: Annotated[int, typer.Option("--year")] = 2026,
    uf: Annotated[str, typer.Option("--uf", help="MG | MG,SP | ALL")] = "MG",
) -> None:
    """Baixa, valida e extrai os recursos do MVP para o escopo informado."""
    from eleicoes import pipeline

    _checar_ano(year)
    cfg = load_config()
    _ufs(uf)  # valida o parâmetro; o recorte por UF é aplicado na Silver (make transform)
    with RunContext("ingest", cfg, {"year": year, "uf": uf}) as ctx:
        pasta = pipeline.pasta_manifestos(cfg, ctx.run_id)
        # votos por seção: arquivo por UF no piloto; arquivo 'BR' (Presidente) no nacional
        # Presidente: arquivo de abrangência federal ("BR"); o recorte por UF é feito na Silver
        arq = cfg.recurso("votacao_secao").get("arquivo_presidente", "BR")
        alvos = [("votacao_secao", arq, None), ("detalhe_votacao_secao", None, None)]
        for recurso, u, escopo_uf in alvos:
            m = pipeline.ingerir(cfg, ctx, recurso, u, escopo_uf=escopo_uf)
            m.salvar(pasta)
            ctx.insumos.append(
                {"recurso": m.recurso, "uf": u or escopo_uf, "sha256": m.sha256, "status": m.status}
            )
            console.print(
                f"{recurso} {u or escopo_uf or ''}: {m.status} · turnos {m.turnos_presentes} · "
                f"linhas {m.linhas}"
            )
            if m.status != "disponivel":
                ctx.pendencias.extend(m.limitacoes or [f"{m.recurso}: {m.status}"])


@app.command()
def validate() -> None:
    """Mostra o status dos manifestos mais recentes e bloqueia se houver incompatibilidade."""
    from eleicoes.ingestion.manifest import carregar_manifestos

    cfg = load_config()
    with RunContext("validate", cfg) as ctx:
        ms = carregar_manifestos(cfg.paths["manifests"])
        if not ms:
            ctx.pendencias.append("Nenhum manifesto encontrado; rode `make ingest`.")
        t = Table("run", "recurso", "uf", "status", "turnos", "colunas ausentes")
        for m in ms:
            t.add_row(
                m["run_id"],
                m["recurso"],
                m["uf"] or "-",
                m["status"],
                ",".join(m["turnos_presentes"]),
                ",".join(m["colunas_ausentes"]),
            )
            if m["status"] in ("incompativel", "indisponivel"):
                ctx.pendencias.append(f"{m['recurso']} {m['uf'] or ''}: {m['status']}")
        console.print(t)
    if ctx.pendencias:
        raise typer.Exit(code=1)


@app.command()
def transform(
    uf: Annotated[str, typer.Option("--uf", help="MG (piloto) | ALL (nacional)")] = "MG",
) -> None:
    """Monta Silver e Gold e grava o relatório de qualidade."""
    from eleicoes import pipeline

    cfg = load_config()
    escopo = _ufs(uf)
    uf_votos = cfg.recurso("votacao_secao").get("arquivo_presidente", "BR")
    with RunContext("transform", cfg, {"uf": uf}) as ctx:
        checks = pipeline.transformar(cfg, ctx, escopo, uf_votos)
        rel = pipeline.relatorio_qualidade(ctx, checks, uf if escopo else "nacional + exterior")
        console.print(rel.read_text(encoding="utf-8"))


@app.command()
def analyze() -> None:
    """Gera os quadros descritivos a partir das tabelas Gold (somente se a base não estiver bloqueada)."""
    from eleicoes.analytics import report

    cfg = load_config()
    with RunContext("analyze", cfg) as ctx:
        saida = report.quadro_resumo(cfg, ctx)
        console.print(f"Quadros em {saida}")


if __name__ == "__main__":
    app()
