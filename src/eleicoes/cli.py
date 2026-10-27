"""Interface de linha de comando. Os alvos do Makefile chamam estes comandos."""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from eleicoes.config import UFS_BRASIL, load_config
from eleicoes.runlog import RunContext

app = typer.Typer(add_completion=False, help="Pipeline TSE — Presidência, 1º × 2º turno.")
console = Console()
SEM_MUDANCA = 10  # código de saída de `verificar` quando nada mudou
Ano = Annotated[int, typer.Option("--year", help="Ano da eleição (ver configs/project.yml)")]


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False)],
    )


def _cfg(ano: int):
    try:
        return load_config().com_ano(ano)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


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
def inventory(year: Ano = 2026) -> None:
    """Consulta o catálogo CKAN do TSE e faz HEAD em cada arquivo."""
    from eleicoes.discovery import inventory as inv_mod

    cfg = _cfg(year)
    with RunContext("inventory", cfg) as ctx:
        inv = inv_mod.montar_inventario(cfg)
        destino = inv_mod.salvar(inv, cfg.paths["reports"] / "inventory" / f"{ctx.run_id}.json")
        linhas = inv_mod.consolidar(inv, cfg.paths["manifests"])
        (destino.with_suffix(".consolidado.json")).write_text(
            json.dumps(linhas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ctx.volumes["recursos_catalogo"] = len(inv["itens"])
        for e in inv.get("conjuntos_com_erro", []):
            ctx.pendencias.append(f"Catálogo: {e.get('conjunto') or e.get('grupo')} — {e['erro']}")
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
    year: Ano = 2026,
    uf: Annotated[str, typer.Option("--uf", help="MG | MG,SP | ALL")] = "MG",
    extras: Annotated[
        bool, typer.Option(help="Perfila também os arquivos por município/zona")
    ] = True,
) -> None:
    """Baixa, valida e extrai os recursos do MVP para o escopo informado."""
    from eleicoes import pipeline

    cfg = _cfg(year)
    _ufs(uf)  # valida o parâmetro; o recorte por UF é aplicado na Silver (make transform)
    with RunContext("ingest", cfg, {"year": year, "uf": uf}) as ctx:
        pasta = pipeline.pasta_manifestos(cfg, ctx.run_id)
        # Presidente: arquivo de abrangência federal ("BR"); o recorte por UF é feito na Silver
        arq = cfg.recurso("votacao_secao").get("arquivo_presidente", "BR")
        alvos = [("votacao_secao", arq, None), ("detalhe_votacao_secao", None, None)]
        if extras:
            alvos += [
                (nome, None, None)
                for nome, rec in cfg.sources["recursos"].items()
                if rec.get("complementar") or rec.get("somente_perfil")
            ]
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
            if m.status not in ("disponivel", "perfilado"):
                ctx.pendencias.extend(m.limitacoes or [f"{m.recurso}: {m.status}"])


@app.command()
def validate(year: Ano = 2026) -> None:
    """Mostra o status dos manifestos do ano e bloqueia se o mais recente de cada recurso for
    incompatível ou indisponível."""
    from eleicoes.ingestion.manifest import carregar_manifestos

    cfg = _cfg(year)
    with RunContext("validate", cfg) as ctx:
        todos = [
            m
            for m in carregar_manifestos(cfg.paths["manifests"])
            if int(m.get("ano") or 2026) == year
        ]
        recentes: dict[tuple, dict] = {}
        for m in todos:
            k = (m["recurso"], m["uf"])
            if k not in recentes or m["coletado_em"] > recentes[k]["coletado_em"]:
                recentes[k] = m
        ms = sorted(recentes.values(), key=lambda m: m["recurso"])
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
    year: Ano = 2026,
    uf: Annotated[str, typer.Option("--uf", help="MG (piloto) | ALL (nacional)")] = "MG",
) -> None:
    """Monta Silver e Gold e grava o relatório de qualidade."""
    from eleicoes import pipeline

    cfg = _cfg(year)
    escopo = _ufs(uf)
    uf_votos = cfg.recurso("votacao_secao").get("arquivo_presidente", "BR")
    with RunContext("transform", cfg, {"uf": uf}) as ctx:
        checks = pipeline.transformar(cfg, ctx, escopo, uf_votos)
        rel = pipeline.relatorio_qualidade(ctx, checks, uf if escopo else "nacional + exterior")
        console.print(rel.read_text(encoding="utf-8"))


@app.command()
def analyze(year: Ano = 2026) -> None:
    """Gera os quadros descritivos a partir das tabelas Gold (marcados se a base estiver bloqueada)."""
    from eleicoes.analytics import report

    cfg = _cfg(year)
    with RunContext("analyze", cfg) as ctx:
        saida = report.quadro_resumo(cfg, ctx)
        console.print(f"Quadros em {saida}")


@app.command()
def diagnosticar(year: Ano = 2026) -> None:
    """Diagnósticos sobre a base já transformada (rode `make transform` antes): votos nominais
    seção × zona por candidatura (I-01) e votáveis especiais 95/96 (A-06)."""
    from eleicoes.analytics import diagnostico

    cfg = _cfg(year)
    with RunContext("diagnosticar", cfg) as ctx:
        destino = cfg.paths["reports"] / "diagnosticos" / ctx.run_id
        resumo = diagnostico.executar(cfg.warehouse, destino)
        ctx.volumes |= {k: v for k, v in resumo.items() if isinstance(v, int)}
        console.print(f"Diagnósticos em {destino}")


@app.command()
def verificar(year: Ano = 2026) -> None:
    """HEAD nos arquivos do MVP; sai com 0 se algo mudou e 10 se nada mudou.

    Escreve `mudou=true|false` em $GITHUB_OUTPUT quando rodando no Actions.
    """
    from eleicoes.discovery import verificar as ver

    cfg = _cfg(year)
    with RunContext("verificar", cfg) as ctx:
        estado = cfg.paths["reports"] / "verificacao" / f"estado_{year}.json"
        res = ver.verificar(cfg, estado)
        destino = cfg.paths["reports"] / "verificacao" / f"{ctx.run_id}.json"
        destino.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        for i in res["itens"]:
            console.print(
                f"{i['recurso']}: {'MUDOU' if i['mudou'] else 'sem mudança'} · "
                f"{i['atual'].get('last_modified_http')} · {i['atual'].get('bytes')} bytes"
            )
    saida = os.environ.get("GITHUB_OUTPUT")
    if saida:
        with open(saida, "a", encoding="utf-8") as f:
            f.write(f"mudou={'true' if res['mudou'] else 'false'}\n")
    if not res["mudou"]:
        raise typer.Exit(code=SEM_MUDANCA)


if __name__ == "__main__":
    app()
