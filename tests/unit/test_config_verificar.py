import json

import httpx
import pytest

from eleicoes.config import load_config
from eleicoes.discovery import verificar as ver


def test_urls_por_ano():
    cfg = load_config()
    assert cfg.ano == 2026
    c22 = cfg.com_ano(2022)
    assert c22.url_recurso("votacao_secao", "BR").endswith("votacao_secao_2022_BR.zip")
    assert c22.url_recurso("detalhe_votacao_secao").endswith("detalhe_votacao_secao_2022.zip")
    assert c22.conjunto("resultados") == "resultados-2022"
    assert c22.warehouse.name == "warehouse_2022.duckdb"
    assert c22.dir_ano("gold").name == "2022"


def test_ano_nao_suportado():
    with pytest.raises(ValueError, match="não suportado"):
        load_config().com_ano(1990)


def _cliente(lm: str, tamanho: int) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"last-modified": lm, "content-length": str(tamanho)})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_verificar_detecta_mudanca_e_guarda_estado(tmp_path, monkeypatch):
    cfg = load_config()
    monkeypatch.setattr(ver, "carregar_manifestos", lambda _p: [])  # sem referência no repo
    estado = tmp_path / "estado.json"
    r1 = ver.verificar(cfg, estado, _cliente("Mon, 26 Oct 2026 10:00:00 GMT", 100))
    assert r1["mudou"]  # sem referência = mudou
    r2 = ver.verificar(cfg, estado, _cliente("Mon, 26 Oct 2026 10:00:00 GMT", 100))
    assert not r2["mudou"]
    r3 = ver.verificar(cfg, estado, _cliente("Tue, 27 Oct 2026 02:00:00 GMT", 120))
    assert r3["mudou"] and all(i["mudou"] for i in r3["itens"])
    assert len(json.loads(estado.read_text())) == 2


def test_verificar_usa_manifesto_quando_sem_estado(tmp_path, monkeypatch):
    cfg = load_config()
    url = ver.urls_mvp(cfg)["votacao_secao"]
    man = [{"url": url, "bytes": 100, "last_modified_http": "X", "coletado_em": "2026-10-26"}]
    monkeypatch.setattr(ver, "carregar_manifestos", lambda _p: man)
    r = ver.verificar(cfg, tmp_path / "e.json", _cliente("X", 100))
    por = {i["recurso"]: i["mudou"] for i in r["itens"]}
    assert por == {"votacao_secao": False, "detalhe_votacao_secao": True}
