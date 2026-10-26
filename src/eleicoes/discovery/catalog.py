"""Descoberta de recursos no catálogo CKAN do Portal de Dados Abertos do TSE.

Usa a API documentada do CKAN (`package_show`). Nada é inferido: cada recurso retornado
carrega os metadados exatamente como publicados, e a URL só é aceita se o domínio estiver
na lista de domínios permitidos de configs/project.yml.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True)
class RecursoCatalogo:
    conjunto: str
    resource_id: str
    titulo: str
    descricao: str | None
    url: str
    formato: str | None
    mimetype: str | None
    criado: str | None
    modificado_metadados: str | None
    tamanho_declarado: int | None

    def como_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def validar_dominio(url: str, permitidos: list[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"URL sem HTTPS recusada: {url}")
    if parsed.hostname not in set(permitidos):
        raise ValueError(f"Domínio fora da lista permitida: {parsed.hostname} ({url})")


def parse_package(payload: dict[str, Any], conjunto: str) -> list[RecursoCatalogo]:
    if not payload.get("success"):
        raise RuntimeError(f"CKAN respondeu sem sucesso para '{conjunto}': {payload.get('error')}")
    recursos = []
    for r in payload["result"].get("resources", []):
        size = r.get("size")
        recursos.append(
            RecursoCatalogo(
                conjunto=conjunto,
                resource_id=r.get("id", ""),
                titulo=r.get("name") or "",
                descricao=r.get("description"),
                url=r.get("url") or "",
                formato=r.get("format"),
                mimetype=r.get("mimetype"),
                criado=r.get("created"),
                modificado_metadados=r.get("metadata_modified") or r.get("last_modified"),
                tamanho_declarado=int(size) if str(size or "").isdigit() else None,
            )
        )
    return recursos


def descobrir(
    api: str, conjunto: str, permitidos: list[str], timeout_s: float = 60
) -> list[RecursoCatalogo]:
    validar_dominio(api, permitidos)
    with httpx.Client(timeout=timeout_s, follow_redirects=False) as cli:
        resp = cli.get(api, params={"id": conjunto})
        resp.raise_for_status()
        recursos = parse_package(resp.json(), conjunto)
    for r in recursos:
        validar_dominio(r.url, permitidos)
    return recursos
