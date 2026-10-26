"""Contexto de execução: run_id, commit Git, versão de configuração, duração, volumes e status.

Cada comando da CLI abre um RunContext; ao fechar, grava `reports/runs/<run_id>.json`.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eleicoes.config import REPO_ROOT, Config  # noqa: F401

log = logging.getLogger("eleicoes")


def git_commit() -> str:
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        dirty = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain", "--untracked-files=no"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "desconhecido"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class RunContext:
    comando: str
    config: Config
    parametros: dict[str, Any] = field(default_factory=dict)
    run_id: str = field(
        default_factory=lambda: (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
        )
    )
    commit: str = field(default_factory=git_commit)
    inicio: str = field(default_factory=utc_now)
    fim: str | None = None
    duracao_s: float | None = None
    status: str = "em_execucao"
    volumes: dict[str, int] = field(default_factory=dict)
    insumos: list[dict[str, Any]] = field(default_factory=list)
    pendencias: list[str] = field(default_factory=list)
    _t0: float = field(default_factory=time.monotonic, repr=False)

    def __enter__(self) -> RunContext:
        log.info(
            "run %s | %s | commit %s | config %s",
            self.run_id,
            self.comando,
            self.commit,
            self.config.config_hash,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.fim = utc_now()
        self.duracao_s = round(time.monotonic() - self._t0, 3)
        if exc is not None:
            self.status = "falhou"
            self.pendencias.append(f"{exc_type.__name__}: {exc}")
        elif self.status == "em_execucao":
            self.status = "concluido_com_pendencias" if self.pendencias else "concluido"
        self.salvar()
        return False

    def salvar(self, destino: Path | None = None) -> Path:
        destino = destino or (self.config.paths["reports"] / "runs")
        destino.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in asdict(self).items() if not k.startswith("_") and k != "config"}
        payload["config_version"] = self.config.project.get("config_version")
        payload["config_hash"] = self.config.config_hash
        caminho = destino / f"{self.run_id}.json"
        tmp = caminho.with_suffix(".json.part")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(caminho)
        return caminho
