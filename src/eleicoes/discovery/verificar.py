"""Verificação leve de atualização dos arquivos do TSE (HEAD, sem download).

Compara `Content-Length` e `Last-Modified` de cada recurso do MVP com a última referência
conhecida — o estado salvo da verificação anterior (cache do Actions) ou, na falta dele, o
manifesto mais recente versionado no repositório. Detecta republicação mesmo com o mesmo nome
de arquivo; a confirmação de conteúdo (turnos, SHA-256) é feita depois pela ingestão.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from eleicoes.config import Config
from eleicoes.discovery.catalog import validar_dominio
from eleicoes.ingestion.manifest import carregar_manifestos
from eleicoes.runlog import utc_now


def urls_mvp(cfg: Config) -> dict[str, str]:
    arq = cfg.recurso("votacao_secao").get("arquivo_presidente", "BR")
    return {
        "votacao_secao": cfg.url_recurso("votacao_secao", arq),
        "detalhe_votacao_secao": cfg.url_recurso("detalhe_votacao_secao"),
    }


def referencia(cfg: Config, url: str, estado: dict[str, Any]) -> dict[str, Any] | None:
    if url in estado:
        return estado[url]
    ms = [m for m in carregar_manifestos(cfg.paths["manifests"]) if m.get("url") == url]
    if not ms:
        return None
    m = max(ms, key=lambda x: x["coletado_em"])
    return {
        "bytes": m["bytes"],
        "last_modified_http": m["last_modified_http"],
        "origem": "manifesto",
    }


def comparar(atual: dict[str, Any], ref: dict[str, Any] | None) -> bool:
    """True se mudou (ou se não há referência)."""
    if ref is None:
        return True
    return (atual.get("bytes"), atual.get("last_modified_http")) != (
        ref.get("bytes"),
        ref.get("last_modified_http"),
    )


def verificar(cfg: Config, estado_path: Path, client: httpx.Client | None = None) -> dict[str, Any]:
    permitidos = cfg.project["download"]["dominios_permitidos"]
    estado: dict[str, Any] = {}
    if estado_path.exists():
        estado = json.loads(estado_path.read_text(encoding="utf-8"))
    proprio = client is None
    cli = client or httpx.Client(timeout=60, follow_redirects=True)
    itens = []
    try:
        for recurso, url in urls_mvp(cfg).items():
            validar_dominio(url, permitidos)
            r = cli.head(url)
            atual = {
                "http_status": r.status_code,
                "bytes": int(r.headers["content-length"])
                if "content-length" in r.headers
                else None,
                "last_modified_http": r.headers.get("last-modified"),
            }
            ref = referencia(cfg, url, estado)
            mudou = r.status_code == 200 and comparar(atual, ref)
            itens.append({"recurso": recurso, "url": url, "atual": atual, "referencia": ref,
                          "mudou": mudou})  # fmt: skip
            if r.status_code == 200:
                estado[url] = atual | {"origem": "verificacao", "visto_em": utc_now()}
    finally:
        if proprio:
            cli.close()
    estado_path.parent.mkdir(parents=True, exist_ok=True)
    estado_path.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ano": cfg.ano, "verificado_em": utc_now(), "mudou": any(i["mudou"] for i in itens),
            "itens": itens}  # fmt: skip
