"""Inventário: catálogo CKAN + HEAD em cada arquivo (tamanho e Last-Modified do CDN).

Checksum SHA-256 e conteúdo (turnos, geração, colunas) só existem após o download —
são preenchidos pelos manifestos de `ingest` e consolidados no inventário final.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from eleicoes.config import Config
from eleicoes.discovery.catalog import descobrir
from eleicoes.ingestion.manifest import carregar_manifestos
from eleicoes.runlog import utc_now


def head(url: str, cli: httpx.Client) -> dict[str, Any]:
    try:
        r = cli.head(url)
        return {
            "http_status": r.status_code,
            "bytes": int(r.headers["content-length"]) if "content-length" in r.headers else None,
            "last_modified_http": r.headers.get("last-modified"),
            "content_type": r.headers.get("content-type"),
        }
    except httpx.HTTPError as exc:
        return {"http_status": None, "erro": str(exc)}


def montar_inventario(cfg: Config) -> dict[str, Any]:
    permitidos = cfg.project["download"]["dominios_permitidos"]
    api = cfg.sources["catalogo"]["api"]
    itens = []
    with httpx.Client(timeout=60, follow_redirects=True) as cli:
        for apelido in cfg.sources["catalogo"]["datasets"]:
            conjunto = cfg.conjunto(apelido)
            for r in descobrir(api, conjunto, permitidos):
                item = r.como_dict() | {"apelido_conjunto": apelido, "consultado_em": utc_now()}
                item |= head(r.url, cli)
                itens.append(item)
    urls_config = set()
    for rec in cfg.sources["recursos"].values():
        if rec.get("particionado_por_uf"):
            urls_config |= {
                rec["url_modelo"].format(uf=u, ano=cfg.ano) for u in rec.get("ufs_publicadas", [])
            }
        else:
            urls_config.add(rec["url"].format(ano=cfg.ano))
    urls_catalogo = {i["url"] for i in itens}
    return {
        "gerado_em": utc_now(),
        "itens": itens,
        "config_fora_do_catalogo": sorted(urls_config - urls_catalogo),
    }


def consolidar(inv: dict[str, Any], manifests_dir: Path) -> list[dict[str, Any]]:
    """Junta catálogo + último manifesto por URL (sha256, turnos, geração, status)."""
    por_url: dict[str, dict] = {}
    for m in carregar_manifestos(manifests_dir):
        atual = por_url.get(m["url"])
        if atual is None or m["coletado_em"] > atual["coletado_em"]:
            por_url[m["url"]] = m
    linhas = []
    for i in inv["itens"]:
        m = por_url.get(i["url"], {})
        status = m.get("status") or (
            "indisponivel" if i.get("http_status") not in (200, None) else "nao_coletado"
        )
        linhas.append(
            {
                "instituicao": "TSE",
                "conjunto": i["conjunto"],
                "recurso": i["titulo"],
                "url": i["url"],
                "formato": i.get("formato"),
                "bytes": m.get("bytes") or i.get("bytes"),
                "sha256": m.get("sha256"),
                "gerado_em_fonte": m.get("gerado_em_fonte"),
                "coletado_em": m.get("coletado_em"),
                "last_modified_http": i.get("last_modified_http"),
                "turnos": m.get("turnos_presentes"),
                "status": status,
                "dicionarios": m.get("dicionarios"),
                "limitacoes": m.get("limitacoes"),
            }
        )
    return linhas


def salvar(inv: dict[str, Any], destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(inv, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
