"""Extração segura de ZIP: bloqueia path traversal, links, excesso de membros,
tamanho descompactado e taxa de compressão anômala (zip bomb)."""

from __future__ import annotations

import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


class ZipInseguro(RuntimeError):
    pass


@dataclass(frozen=True)
class MembroZip:
    nome: str
    bytes_compactado: int
    bytes_descompactado: int
    crc: int


def inspecionar_zip(
    caminho: Path,
    *,
    max_membros: int = 200,
    max_bytes_descompactados: int = 40_000_000_000,
    max_taxa_compressao: float = 200,
) -> list[MembroZip]:
    try:
        zf = zipfile.ZipFile(caminho)
    except zipfile.BadZipFile as exc:
        raise ZipInseguro(f"ZIP corrompido: {caminho.name}") from exc
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > max_membros:
            raise ZipInseguro(f"ZIP com {len(infos)} membros (> {max_membros})")
        total = 0
        membros = []
        for i in infos:
            p = PurePosixPath(i.filename)
            if p.is_absolute() or ".." in p.parts or "\\" in i.filename:
                raise ZipInseguro(f"Caminho inseguro no ZIP: {i.filename!r}")
            modo = (i.external_attr >> 16) & 0o170000
            if modo and stat.S_ISLNK(modo):
                raise ZipInseguro(f"Link simbólico no ZIP: {i.filename!r}")
            if i.compress_size and i.file_size / i.compress_size > max_taxa_compressao:
                raise ZipInseguro(f"Taxa de compressão anômala em {i.filename!r}")
            total += i.file_size
            membros.append(MembroZip(i.filename, i.compress_size, i.file_size, i.CRC))
        if total > max_bytes_descompactados:
            raise ZipInseguro(f"Conteúdo descompactado de {total} bytes excede o limite")
        bad = zf.testzip()
        if bad is not None:
            raise ZipInseguro(f"CRC inválido no membro {bad!r}")
    return membros


def extrair(
    caminho: Path, destino: Path, membros: list[str] | None = None, **limites
) -> list[Path]:
    """Extrai membros validados para `destino` (idempotente: pula arquivos já extraídos com mesmo tamanho)."""
    validos = {m.nome: m for m in inspecionar_zip(caminho, **limites)}
    alvo = membros or list(validos)
    destino.mkdir(parents=True, exist_ok=True)
    saida: list[Path] = []
    raiz = destino.resolve()
    with zipfile.ZipFile(caminho) as zf:
        for nome in alvo:
            m = validos[nome]
            out = (destino / PurePosixPath(nome).name).resolve()
            if raiz not in out.parents:
                raise ZipInseguro(f"Destino fora da pasta de extração: {nome!r}")
            if out.exists() and out.stat().st_size == m.bytes_descompactado:
                saida.append(out)
                continue
            tmp = out.with_name(out.name + ".part")
            with zf.open(nome) as src, tmp.open("wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            tmp.replace(out)
            saida.append(out)
    return saida


def ler_membro_parcial(caminho: Path, nome: str, n_bytes: int = 256_000) -> bytes:
    """Lê só o início de um membro (cabeçalho, amostra) sem extrair o arquivo inteiro."""
    with zipfile.ZipFile(caminho) as zf, zf.open(nome) as f:
        return f.read(n_bytes)
