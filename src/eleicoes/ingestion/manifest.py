"""Manifestos de insumos: o registro durável de cada snapshot (os dados brutos ficam fora do Git).

Um manifesto separa explicitamente:
- `gerado_em_fonte`: data/hora de geração declarada DENTRO do arquivo (DT_GERACAO/HH_GERACAO);
- `coletado_em`: momento em que este pipeline baixou o arquivo;
- `last_modified_http`: cabeçalho HTTP do CDN (não é a data de geração oficial).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Manifesto:
    run_id: str
    recurso: str
    uf: str | None
    instituicao: str
    conjunto: str
    url: str
    sha256: str
    bytes: int
    coletado_em: str
    last_modified_http: str | None
    etag: str | None
    membros_zip: list[dict[str, Any]] = field(default_factory=list)
    dicionarios: list[str] = field(default_factory=list)
    perfil_csv: dict[str, Any] = field(default_factory=dict)
    colunas_ausentes: list[str] = field(default_factory=list)
    gerado_em_fonte: list[str] = field(default_factory=list)
    turnos_presentes: list[str] = field(default_factory=list)
    linhas: int | None = None
    status: str = "a_validar"  # disponivel | parcial | indisponivel | incompativel
    limitacoes: list[str] = field(default_factory=list)
    ano: int | None = None

    def salvar(self, pasta: Path) -> Path:
        pasta.mkdir(parents=True, exist_ok=True)
        nome = f"{self.recurso}{'_' + self.uf if self.uf else ''}.json"
        caminho = pasta / nome
        tmp = caminho.with_suffix(".json.part")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(caminho)
        return caminho


def classificar_status(m: Manifesto, turnos_esperados: list[int]) -> str:
    if m.colunas_ausentes:
        return "incompativel"
    if not m.turnos_presentes:
        return "a_validar"
    faltando = {str(t) for t in turnos_esperados} - set(m.turnos_presentes)
    return "parcial" if faltando else "disponivel"


def carregar_manifestos(pasta: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pasta.glob("**/*.json"))]
