"""Leitura das configurações versionadas (configs/*.yml)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs"
UFS_BRASIL = [
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
]


@dataclass(frozen=True)
class Config:
    project: dict[str, Any]
    sources: dict[str, Any]
    config_hash: str
    ano: int = 2026

    @property
    def paths(self) -> dict[str, Path]:
        return {k: REPO_ROOT / v for k, v in self.project["paths"].items()}

    @property
    def anos_suportados(self) -> list[int]:
        return list(self.project["eleicao"].get("anos_suportados", [self.ano]))

    def com_ano(self, ano: int) -> Config:
        if ano not in self.anos_suportados:
            raise ValueError(f"Ano {ano} não suportado; anos configurados: {self.anos_suportados}")
        return replace(self, ano=ano)

    def dir_ano(self, chave: str) -> Path:
        """Pasta por ano para camadas derivadas (silver, gold)."""
        return self.paths[chave] / str(self.ano)

    @property
    def warehouse(self) -> Path:
        w = self.paths["warehouse"]
        return w.with_name(f"{w.stem}_{self.ano}{w.suffix}")

    def conjunto(self, apelido: str) -> str:
        return self.sources["catalogo"]["datasets"][apelido].format(ano=self.ano)

    def recurso(self, nome: str) -> dict[str, Any]:
        try:
            return self.sources["recursos"][nome]
        except KeyError as exc:
            raise KeyError(f"Recurso '{nome}' não está em configs/sources.yml") from exc

    def url_recurso(self, nome: str, uf: str | None = None) -> str:
        rec = self.recurso(nome)
        if rec.get("particionado_por_uf"):
            if uf is None:
                raise ValueError(f"Recurso '{nome}' é particionado por UF; informe a UF.")
            uf = uf.upper()
            publicadas = rec.get("ufs_publicadas", [])
            if publicadas and uf not in publicadas:
                raise ValueError(f"UF '{uf}' não consta como publicada para '{nome}'.")
            return rec["url_modelo"].format(uf=uf, ano=self.ano)
        return rec["url"].format(ano=self.ano)


def load_config(config_dir: Path = CONFIG_DIR) -> Config:
    raw_p = (config_dir / "project.yml").read_bytes()
    raw_s = (config_dir / "sources.yml").read_bytes()
    digest = hashlib.sha256(raw_p + b"\x00" + raw_s).hexdigest()[:16]
    project = yaml.safe_load(raw_p)
    return Config(
        project=project,
        sources=yaml.safe_load(raw_s),
        config_hash=digest,
        ano=int(project["eleicao"]["ano"]),
    )
