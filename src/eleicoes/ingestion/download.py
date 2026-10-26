"""Download robusto: timeout, retentativas limitadas com backoff, cache condicional,
escrita atômica e verificação de conteúdo (resposta HTML não é ZIP/CSV).

Snapshots são endereçados por conteúdo: `bronze/<recurso>/<sha256[:12]>/<arquivo>`.
Se o TSE republicar com o mesmo nome e outro conteúdo, nasce um novo snapshot e o antigo
permanece intacto (detecção de atualização por hash).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from eleicoes.discovery.catalog import validar_dominio
from eleicoes.runlog import utc_now

log = logging.getLogger("eleicoes.download")

ZIP_MAGIC = b"PK\x03\x04"
HTML_SIGNS = (b"<!doctype html", b"<html", b"<head", b"<?xml")


class ConteudoInvalido(RuntimeError):
    """Arquivo baixado não corresponde ao tipo esperado."""


@dataclass
class ResultadoDownload:
    url: str
    caminho: Path
    sha256: str
    bytes: int
    http_status: int
    etag: str | None
    last_modified: str | None
    content_type: str | None
    coletado_em: str
    reutilizado_cache: bool


def sha256_arquivo(caminho: Path, bloco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while chunk := f.read(bloco):
            h.update(chunk)
    return h.hexdigest()


def checar_assinatura(caminho: Path, esperado: str = "zip") -> None:
    with caminho.open("rb") as f:
        inicio = f.read(512)
    if inicio.lstrip().lower().startswith(HTML_SIGNS):
        raise ConteudoInvalido(f"Resposta HTML recebida no lugar de {esperado}: {caminho.name}")
    if esperado == "zip" and not inicio.startswith(ZIP_MAGIC):
        raise ConteudoInvalido(f"Assinatura ZIP ausente em {caminho.name}")


def baixar(
    url: str,
    destino_dir: Path,
    *,
    permitidos: list[str],
    timeout_s: float = 120,
    max_retries: int = 4,
    backoff_base_s: float = 2.0,
    max_bytes: int = 8_000_000_000,
    esperado: str = "zip",
    client: httpx.Client | None = None,
) -> ResultadoDownload:
    """Baixa `url` para `destino_dir/<sha12>/<nome>`; idempotente por conteúdo."""
    validar_dominio(url, permitidos)
    nome = Path(urlparse(url).path).name
    staging = destino_dir / "_staging"
    staging.mkdir(parents=True, exist_ok=True)
    parcial = staging / f"{nome}.part"

    proprio = client is None
    cli = client or httpx.Client(timeout=timeout_s, follow_redirects=True)
    try:
        ultimo_erro: Exception | None = None
        for tentativa in range(1, max_retries + 1):
            try:
                with cli.stream("GET", url) as resp:
                    if resp.status_code != 200:
                        raise httpx.HTTPStatusError(
                            f"HTTP {resp.status_code}", request=resp.request, response=resp
                        )
                    validar_dominio(
                        str(resp.url), permitidos
                    )  # redirecionamento não sai do allowlist
                    total = 0
                    with parcial.open("wb") as f:
                        for chunk in resp.iter_bytes(1 << 20):
                            total += len(chunk)
                            if total > max_bytes:
                                raise ConteudoInvalido(
                                    f"Arquivo excede limite de {max_bytes} bytes"
                                )
                            f.write(chunk)
                    declarado = resp.headers.get("content-length")
                    if declarado and int(declarado) != total:
                        raise ConteudoInvalido(
                            f"Tamanho divergente: header {declarado} vs recebido {total}"
                        )
                    meta = (
                        resp.status_code,
                        resp.headers.get("etag"),
                        resp.headers.get("last-modified"),
                        resp.headers.get("content-type"),
                    )
                break
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                ultimo_erro = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and 400 <= status < 500 and status != 429:
                    raise
                espera = backoff_base_s * (2 ** (tentativa - 1))
                log.warning(
                    "Falha %s/%s em %s (%s); nova tentativa em %.0fs",
                    tentativa,
                    max_retries,
                    url,
                    exc,
                    espera,
                )
                time.sleep(espera)
        else:
            raise RuntimeError(
                f"Download falhou após {max_retries} tentativas: {url}"
            ) from ultimo_erro
    finally:
        if proprio:
            cli.close()

    checar_assinatura(parcial, esperado)
    digest = sha256_arquivo(parcial)
    final_dir = destino_dir / digest[:12]
    final = final_dir / nome
    reutilizado = final.exists() and sha256_arquivo(final) == digest
    if reutilizado:
        parcial.unlink()
    else:
        final_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(parcial, final)  # mesmo filesystem → rename atômico
        final.chmod(0o444)  # Bronze imutável
    return ResultadoDownload(
        url=url,
        caminho=final,
        sha256=digest,
        bytes=final.stat().st_size,
        http_status=meta[0],
        etag=meta[1],
        last_modified=meta[2],
        content_type=meta[3],
        coletado_em=utc_now(),
        reutilizado_cache=reutilizado,
    )
