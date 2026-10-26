"""Orquestração dos estágios. Cada estágio é idempotente e lê/grava apenas artefatos
endereçados por conteúdo (sha256) ou por run_id."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from eleicoes.analytics.decomposition import decomposicao_exata, identificar_finalistas
from eleicoes.config import REPO_ROOT, Config
from eleicoes.ingestion.archive import extrair, inspecionar_zip, ler_membro_parcial
from eleicoes.ingestion.download import baixar
from eleicoes.ingestion.manifest import Manifesto, carregar_manifestos, classificar_status
from eleicoes.runlog import RunContext
from eleicoes.transformation import silver as sv
from eleicoes.validation import integrity as ck
from eleicoes.validation.raw import checar_colunas, perfilar_csv

log = logging.getLogger("eleicoes.pipeline")

# Recursos necessários para o MVP (Presidência, dois turnos)
RECURSOS_MVP = ["votacao_secao", "detalhe_votacao_secao"]


def _rel(p: Path) -> str:
    """Caminho relativo ao repositório quando possível (manifestos portáveis); absoluto caso contrário."""
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(p.resolve())


def _escolher_csvs(membros: list[str], uf: str | None) -> list[str]:
    csvs = [m for m in membros if m.lower().endswith(".csv")]
    if uf:
        da_uf = [m for m in csvs if m.upper().endswith(f"_{uf.upper()}.CSV")]
        if da_uf:
            return da_uf
    return csvs


def _extrair_dicionarios(
    zip_path: Path, membros: list[str], destino: Path, reports: Path, prefixo: str
) -> list[str]:
    """Extrai o leiame e grava o texto em reports/dicionarios/<prefixo>_<nome>.txt
    (prefixo = <ano>/<recurso>, pois todo ZIP do TSE chama o arquivo de `leiame.pdf`)."""
    pdfs = [m for m in membros if m.lower().endswith((".pdf", ".txt")) and "leia" in m.lower()]
    if not pdfs:
        return []
    saida = extrair(zip_path, destino, pdfs)
    textos = []
    try:
        from pypdf import PdfReader

        for p in saida:
            if p.suffix.lower() == ".pdf":
                txt = "\n".join(page.extract_text() or "" for page in PdfReader(p).pages)
                alvo = reports / "dicionarios" / f"{prefixo}_{p.stem}.txt"
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(txt, encoding="utf-8")
                textos.append(_rel(alvo))
    except Exception as exc:  # noqa: BLE001 — dicionário é auxiliar; registra e segue
        log.warning("Falha ao extrair texto do dicionário: %s", exc)
    return [str(Path(m).name) for m in pdfs] + textos


def perfilar_turnos(csv: Path, perfil: dict, rec: dict) -> dict[str, Any]:
    cols = rec["colunas_obrigatorias"]
    opc = rec.get("colunas_opcionais", {})
    src = sv.fonte_csv(csv, perfil)
    con = duckdb.connect()
    turno = sv._id(cols["turno"])
    out: dict[str, Any] = {}
    out["linhas"] = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]
    out["turnos"] = [
        r[0] for r in con.execute(f"SELECT DISTINCT {turno} FROM {src} ORDER BY 1").fetchall()
    ]
    out["cargos"] = con.execute(
        f"SELECT {sv._id(cols['cd_cargo'])}, {sv._id(cols['ds_cargo'])}, {turno}, count(*) "
        f"FROM {src} GROUP BY ALL ORDER BY ALL"
    ).fetchall()
    if "dt_geracao" in opc and opc["dt_geracao"] in perfil["cabecalho"]:
        hh = sv._id(opc["hh_geracao"]) if opc.get("hh_geracao") in perfil["cabecalho"] else "''"
        out["geracao"] = [
            f"{r[0]} {r[1]}".strip()
            for r in con.execute(
                f"SELECT DISTINCT {sv._id(opc['dt_geracao'])}, {hh} FROM {src} ORDER BY 1, 2"
            ).fetchall()
        ]
    con.close()
    return out


def ingerir(
    cfg: Config, ctx: RunContext, recurso: str, uf: str | None, escopo_uf: str | None = None
) -> Manifesto:
    """`uf` escolhe o arquivo (recursos particionados); `escopo_uf` limita quais CSVs
    internos são extraídos de um arquivo nacional (ex.: piloto MG)."""
    rec = cfg.recurso(recurso)
    url = cfg.url_recurso(recurso, uf if rec.get("particionado_por_uf") else None)
    dl_cfg = cfg.project["download"]
    zcfg = cfg.project["extracao_zip"]
    bronze = cfg.paths["bronze"] / recurso
    res = baixar(
        url,
        bronze,
        permitidos=dl_cfg["dominios_permitidos"],
        timeout_s=dl_cfg["timeout_s"],
        max_retries=dl_cfg["max_retries"],
        backoff_base_s=dl_cfg["backoff_base_s"],
        max_bytes=dl_cfg["max_bytes_arquivo"],
    )
    membros = inspecionar_zip(res.caminho, **zcfg)
    nomes = [m.nome for m in membros]
    man = Manifesto(
        run_id=ctx.run_id,
        recurso=recurso,
        uf=uf,
        instituicao="TSE",
        conjunto=cfg.conjunto(rec["conjunto"]),
        url=url,
        sha256=res.sha256,
        bytes=res.bytes,
        coletado_em=res.coletado_em,
        last_modified_http=res.last_modified,
        etag=res.etag,
        membros_zip=[asdict(m) for m in membros],
        ano=cfg.ano,
    )
    extraido = cfg.paths["bronze"] / "_extraido" / res.sha256[:12]
    man.dicionarios = _extrair_dicionarios(
        res.caminho, nomes, extraido / "_dic", cfg.paths["reports"], f"{cfg.ano}/{recurso}"
    )
    sufixo = rec.get("membro_csv_sufixo")
    csvs = _escolher_csvs(nomes, sufixo or uf or escopo_uf)
    if sufixo and not any(c.upper().endswith(f"_{sufixo.upper()}.CSV") for c in csvs):
        man.status = "incompativel"
        man.limitacoes.append(f"Membro CSV com sufixo _{sufixo} não encontrado no ZIP")
        return man
    if not csvs:
        man.status = "incompativel"
        man.limitacoes.append("Nenhum CSV encontrado no ZIP")
        return man
    perfil = perfilar_csv(ler_membro_parcial(res.caminho, csvs[0]))
    man.perfil_csv = asdict(perfil)
    if rec.get("somente_perfil"):
        man.perfil_csv["membros_csv"] = csvs
        man.status = "perfilado"
        man.limitacoes.append("Somente cabeçalho/membros coletados (mapeamento a confirmar)")
        return man
    if "colunas_obrigatorias" in rec:
        man.colunas_ausentes = checar_colunas(perfil.cabecalho, rec["colunas_obrigatorias"])
    if man.colunas_ausentes:
        man.status = "incompativel"
        man.limitacoes.append(
            "Colunas obrigatórias ausentes no cabeçalho real; atualizar configs/sources.yml "
            "conforme o dicionário de 2026: " + ", ".join(man.colunas_ausentes)
        )
        return man
    caminhos = extrair(res.caminho, extraido, csvs, **zcfg)
    if "colunas_obrigatorias" in rec:
        tot_linhas, turnos, geracao = 0, set(), set()
        for c in caminhos:
            pt = perfilar_turnos(c, man.perfil_csv, rec)
            tot_linhas += pt["linhas"]
            turnos.update(pt["turnos"])
            geracao.update(pt.get("geracao", []))
            ctx.volumes[f"{recurso}:{c.name}"] = pt["linhas"]
            if c == caminhos[0]:
                man.perfil_csv["cargos_encontrados"] = [list(r) for r in pt["cargos"][:60]]
        man.linhas = tot_linhas
        man.turnos_presentes = sorted(turnos)
        man.gerado_em_fonte = sorted(geracao)
    man.perfil_csv["arquivos_csv"] = [_rel(c) for c in caminhos]
    man.status = classificar_status(man, cfg.project["eleicao"]["turnos"])
    if man.status == "parcial":
        man.limitacoes.append(
            f"Turnos presentes {man.turnos_presentes}; esperado {cfg.project['eleicao']['turnos']}."
        )
    return man


def pasta_manifestos(cfg: Config, run_id: str) -> Path:
    return cfg.paths["manifests"] / run_id


def ultimo_manifesto(cfg: Config, recurso: str, uf: str | None) -> dict | None:
    candidatos = [
        m
        for m in carregar_manifestos(cfg.paths["manifests"])
        if m["recurso"] == recurso
        and (m["uf"] or None) == (uf or None)
        and int(m.get("ano") or 2026) == cfg.ano
    ]
    return max(candidatos, key=lambda m: m["coletado_em"]) if candidatos else None


def transformar(
    cfg: Config, ctx: RunContext, escopo_ufs: list[str] | None, uf_votos: str
) -> list[ck.Checagem]:
    """Monta Silver e Gold a partir dos manifestos mais recentes. `uf_votos` = 'BR' (nacional)
    ou a UF do piloto. Retorna as checagens de qualidade."""
    cargo = cfg.project["eleicao"]["cargo_alvo"]
    mv = ultimo_manifesto(cfg, "votacao_secao", uf_votos)
    mp = ultimo_manifesto(cfg, "detalhe_votacao_secao", None)
    for nome, m in (("votacao_secao", mv), ("detalhe_votacao_secao", mp)):
        if m is None:
            raise RuntimeError(f"Sem manifesto de '{nome}'. Rode `make ingest` antes.")
        if m["status"] not in ("disponivel", "parcial"):
            raise RuntimeError(f"Recurso '{nome}' com status {m['status']}: {m['limitacoes']}")
        ctx.insumos.append(
            {
                k: m[k]
                for k in (
                    "recurso",
                    "uf",
                    "url",
                    "sha256",
                    "coletado_em",
                    "gerado_em_fonte",
                    "turnos_presentes",
                    "status",
                )
            }
        )
        if m["status"] == "parcial":
            ctx.pendencias.append(f"{nome}: turnos {m['turnos_presentes']} — conclusões bloqueadas")

    wh = cfg.warehouse
    wh.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(wh))
    sqls = []
    for i, csv in enumerate(mv["perfil_csv"]["arquivos_csv"]):
        q = sv.sql_silver_votos(
            REPO_ROOT / csv, mv["perfil_csv"], cfg.recurso("votacao_secao"), cargo, mv["sha256"]
        )
        if i:
            q = q.replace(
                "CREATE OR REPLACE TABLE silver_votos_secao AS", "INSERT INTO silver_votos_secao"
            )
        sqls.append(q)
        con.execute(q)
    arquivos_p = mp["perfil_csv"]["arquivos_csv"]
    for i, csv in enumerate(arquivos_p):
        q = sv.sql_silver_participacao(
            REPO_ROOT / csv,
            mp["perfil_csv"],
            cfg.recurso("detalhe_votacao_secao"),
            cargo,
            mp["sha256"],
        )
        if i:
            q = q.replace(
                "CREATE OR REPLACE TABLE silver_participacao_secao AS",
                "INSERT INTO silver_participacao_secao",
            )
        sqls.append(q)
        con.execute(q)
    sv.filtrar_ufs(con, "silver_votos_secao", escopo_ufs)
    sv.filtrar_ufs(con, "silver_participacao_secao", escopo_ufs)
    runs = cfg.paths["reports"] / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / f"{ctx.run_id}_silver.sql").write_text("\n".join(sqls), encoding="utf-8")

    checks: list[ck.Checagem] = [
        ck.unicidade(
            con,
            "silver_votos_secao",
            ["turno", "uf", "cd_municipio_tse", "zona", "secao", "nr_votavel"],
        ),
        ck.unicidade(
            con, "silver_participacao_secao", ["turno", "uf", "cd_municipio_tse", "zona", "secao"]
        ),
        ck.nao_negativos(con, "silver_votos_secao", ["qt_votos"]),
        ck.nao_negativos(
            con, "silver_participacao_secao", ["qt_aptos", "qt_comparecimento", "qt_abstencoes"]
        ),
        ck.identidade_aptos(con, "silver_participacao_secao"),
    ]
    if not checks[-1].ok:
        diag = cfg.paths["reports"] / "quality" / f"{ctx.run_id}_diag"
        diag.mkdir(parents=True, exist_ok=True)
        cols_p = _colunas(con, "silver_participacao_secao")
        extra = ", ".join(c for c in ("st_secao_instalada", "st_secao_anulada", "ds_origem_voto")
                          if c in cols_p)  # fmt: skip
        con.execute(
            f"""COPY (SELECT turno, uf, cd_municipio_tse, nm_municipio, zona, secao, qt_aptos,
                             qt_comparecimento, qt_abstencoes,
                             qt_aptos - qt_comparecimento - qt_abstencoes AS diferenca
                             {", " + extra if extra else ""}
                      FROM silver_participacao_secao
                      WHERE qt_aptos <> qt_comparecimento + qt_abstencoes ORDER BY ALL)
                TO '{diag / "aptos_divergentes.csv"}' (HEADER)"""
        )
    turnos = {r[0] for r in con.execute("SELECT DISTINCT turno FROM silver_votos_secao").fetchall()}
    faltam = set(cfg.project["eleicao"]["turnos"]) - turnos
    checks.append(
        ck.Checagem(
            "completude_turnos",
            not faltam,
            True,
            f"turnos presentes={sorted(turnos)} ausentes={sorted(faltam)}",
        )
    )

    for arq in sorted((REPO_ROOT / "sql" / "gold").glob("0[12]_*.sql")):
        con.execute(arq.read_text(encoding="utf-8"))
    checks.append(
        ck.reconciliacao_hierarquica(
            con,
            "silver_votos_secao",
            "gold_votos_municipio",
            ["turno", "uf", "cd_municipio_tse"],
            "qt_votos",
        )
    )
    # válidos por soma de votos nominais vs. válidos do detalhe da apuração
    n_div = con.execute("""
        SELECT count(*) FROM gold_participacao_municipio p
        JOIN (SELECT turno, uf, cd_municipio_tse, sum(qt_votos) v FROM gold_votos_municipio
              WHERE tipo_votavel='candidato' GROUP BY ALL) v USING (turno, uf, cd_municipio_tse)
        WHERE p.qt_votos_validos <> v.v""").fetchone()[0]
    checks.append(
        ck.Checagem(
            "validos_votacao=validos_detalhe",
            n_div == 0,
            False,
            f"{n_div} município-turnos divergentes (investigar anulações/pendências)",
        )
    )

    gold = cfg.dir_ano("gold")
    gold.mkdir(parents=True, exist_ok=True)
    for t in ("silver_votos_secao", "silver_participacao_secao"):
        sv.exportar_parquet(con, t, cfg.dir_ano("silver") / f"{t}.parquet")
    for t in ("gold_votos_municipio", "gold_participacao_municipio"):
        sv.exportar_parquet(con, t, gold / f"{t}.parquet")
    checks.extend(complementares(cfg, ctx, con, escopo_ufs))

    if not faltam:
        nac = pl.from_arrow(
            con.sql(
                "SELECT turno, nr_votavel, sum(qt_votos) AS qt_votos FROM gold_votos_municipio "
                "WHERE tipo_votavel='candidato' GROUP BY ALL"
            ).to_arrow_table()
        )
        a, b = identificar_finalistas(nac)
        con.execute(
            (REPO_ROOT / "sql/gold/03_margem_municipio.sql").read_text(encoding="utf-8"),
            {"a": a, "b": b},
        )
        painel = pl.from_arrow(con.sql("SELECT * FROM gold_margem_municipio").to_arrow_table())
        painel = painel.with_columns(territorio=pl.col("uf") + "-" + pl.col("cd_municipio_tse"))
        dec = decomposicao_exata(painel.fill_null(0), "territorio")
        m1 = int(dec["margem_1"].sum())
        m2 = int(dec["margem_2"].sum())
        checks.append(
            ck.Checagem(
                "decomposicao_fecha",
                int(dec["contribuicao"].sum()) == m2 - m1,
                True,
                f"Σcontrib={int(dec['contribuicao'].sum())} ΔM={m2 - m1}",
            )
        )
        incompletos = painel.filter(pl.col("n_turnos") != 2).height
        checks.append(
            ck.Checagem(
                "pareamento_municipios",
                incompletos == 0,
                False,
                f"{incompletos} municípios sem os dois turnos",
            )
        )
        dec.write_parquet(gold / "gold_decomposicao_municipio.parquet")
        resumo = {
            "ano": cfg.ano,
            "finalista_a": a,
            "finalista_b": b,
            "margem_1": m1,
            "margem_2": m2,
            "inversao_entre_turnos": (m1 > 0) != (m2 > 0) and m2 != 0,
            "escopo_ufs": escopo_ufs or "nacional",
        }
        (gold / "resumo_virada.json").write_text(
            json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    con.close()
    return checks


COMPLEMENTARES = {
    "detalhe_votacao_munzona": "silver_detalhe_munzona",
    "votacao_candidato_munzona": "silver_candidato_munzona",
}


def _colunas(con: duckdb.DuckDBPyConnection, tabela: str) -> set[str]:
    return {r[0] for r in con.execute(f"DESCRIBE {tabela}").fetchall()}


def complementares(
    cfg: Config, ctx: RunContext, con: duckdb.DuckDBPyConnection, escopo_ufs: list[str] | None
) -> list[ck.Checagem]:
    """Carrega os arquivos por município/zona e reconcilia com a camada por seção.

    Recursos complementares nunca bloqueiam o MVP: ausência ou incompatibilidade vira pendência,
    e as divergências são reportadas como checagens não críticas (universos podem diferir, p.ex.
    eleitores de seções não instaladas e voto em trânsito).
    """
    cargo = cfg.project["eleicao"]["cargo_alvo"]
    checks: list[ck.Checagem] = []
    carregadas = set()
    for recurso, tabela in COMPLEMENTARES.items():
        m = ultimo_manifesto(cfg, recurso, None)
        if m is None or m["status"] not in ("disponivel", "parcial"):
            st = "sem manifesto" if m is None else m["status"]
            ctx.pendencias.append(f"{recurso} (complementar): {st} — reconciliação por zona pulada")
            continue
        for i, csv in enumerate(m["perfil_csv"]["arquivos_csv"]):
            q = sv.sql_silver_generico(
                tabela, REPO_ROOT / csv, m["perfil_csv"], cfg.recurso(recurso), cargo, m["sha256"]
            )
            if i:
                q = q.replace(f"CREATE OR REPLACE TABLE {tabela} AS", f"INSERT INTO {tabela}")
            con.execute(q)
        sv.filtrar_ufs(con, tabela, escopo_ufs)
        sv.exportar_parquet(con, tabela, cfg.dir_ano("silver") / f"{tabela}.parquet")
        carregadas.add(tabela)

    if "silver_detalhe_munzona" in carregadas:
        medidas = {
            "qt_aptos": "qt_aptos",
            "qt_comparecimento": "qt_comparecimento",
            "qt_abstencoes": "qt_abstencoes",
            "qt_votos_brancos": "qt_votos_brancos",
            "qt_votos_nulos": "qt_votos_nulos",
            "qt_votos_nominais": "qt_votos_nominais_validos",
        }
        sel_s = ", ".join(f"sum({a}) AS {a}" for a in medidas)
        sel_z = ", ".join(f"sum({b}) AS {a}" for a, b in medidas.items())
        cond = ", ".join(
            f"count(*) FILTER (WHERE s.{a} IS DISTINCT FROM z.{a}), "
            f"coalesce(sum(abs(coalesce(s.{a},0) - coalesce(z.{a},0))), 0)"
            for a in medidas
        )
        k = "turno, uf, cd_municipio_tse, zona"
        res = con.execute(
            f"""WITH s AS (SELECT {k}, {sel_s} FROM silver_participacao_secao GROUP BY {k}),
                     z AS (SELECT {k}, {sel_z} FROM silver_detalhe_munzona GROUP BY {k})
                SELECT count(*), {cond} FROM s FULL OUTER JOIN z USING (turno, uf, cd_municipio_tse, zona)"""
        ).fetchone()
        diag = cfg.paths["reports"] / "quality" / f"{ctx.run_id}_diag"
        diag.mkdir(parents=True, exist_ok=True)
        con.execute(
            f"""COPY (
                WITH s AS (SELECT {k}, {sel_s} FROM silver_participacao_secao GROUP BY {k}),
                     z AS (SELECT {k}, {sel_z} FROM silver_detalhe_munzona GROUP BY {k}),
                     j AS (SELECT turno, uf, cd_municipio_tse, zona,
                                  s.qt_aptos AS aptos_secao, z.qt_aptos AS aptos_zona,
                                  s.qt_votos_nominais AS nom_secao, z.qt_votos_nominais AS nom_zona
                           FROM s FULL OUTER JOIN z USING (turno, uf, cd_municipio_tse, zona))
                SELECT turno, uf,
                       count(*) FILTER (WHERE aptos_zona IS NULL) AS zonas_so_secao,
                       count(*) FILTER (WHERE aptos_secao IS NULL) AS zonas_so_zona,
                       count(*) FILTER (WHERE aptos_secao <> aptos_zona) AS zonas_aptos_diferentes,
                       count(*) FILTER (WHERE nom_secao <> nom_zona) AS zonas_nominais_diferentes,
                       sum(aptos_secao) AS aptos_secao, sum(aptos_zona) AS aptos_zona,
                       sum(nom_secao) AS nominais_secao, sum(nom_zona) AS nominais_zona,
                       min(zona) FILTER (WHERE aptos_zona IS NULL) AS ex_zona_so_secao,
                       min(zona) FILTER (WHERE aptos_secao IS NULL) AS ex_zona_so_zona
                FROM j GROUP BY turno, uf ORDER BY turno, uf
            ) TO '{diag / "secao_zona_por_uf.csv"}' (HEADER)"""
        )
        for j, a in enumerate(medidas):
            n, dif = res[1 + 2 * j], res[2 + 2 * j]
            checks.append(
                ck.Checagem(
                    f"secao→zona:{a}",
                    n == 0,
                    False,
                    f"{n} de {res[0]} zona-turnos divergentes; |dif| total = {dif}",
                )
            )

    if "silver_candidato_munzona" in carregadas:
        n, tot, dif = con.execute(
            """WITH s AS (SELECT turno, uf, cd_municipio_tse, zona, nr_votavel AS nr,
                                 sum(qt_votos) v FROM silver_votos_secao
                          WHERE tipo_votavel = 'candidato' GROUP BY ALL),
                    z AS (SELECT turno, uf, cd_municipio_tse, zona, nr_candidato AS nr,
                                 sum(qt_votos_nominais) v FROM silver_candidato_munzona GROUP BY ALL)
               SELECT count(*) FILTER (WHERE coalesce(s.v, 0) <> coalesce(z.v, 0)), count(*),
                      coalesce(sum(abs(coalesce(s.v,0) - coalesce(z.v,0))), 0)
               FROM s FULL OUTER JOIN z USING (turno, uf, cd_municipio_tse, zona, nr)
               -- o arquivo por seção omite candidatos sem voto; ausência = 0"""
        ).fetchone()
        checks.append(
            ck.Checagem(
                "secao→zona:votos_por_candidato",
                n == 0,
                False,
                f"{n} de {tot} zona-turno-candidatos divergentes; |dif| total = {dif}",
            )
        )
        disp = _colunas(con, "silver_candidato_munzona")
        attrs = [
            c
            for c in (
                "nm_urna_candidato",
                "sg_partido",
                "ds_situacao_candidatura",
                "ds_detalhe_situacao_cand",
                "ds_situacao_julgamento",
                "nm_tipo_destinacao_votos",
                "ds_sit_tot_turno",
            )
            if c in disp
        ]
        sel = "".join(f", any_value({c}) AS {c}, count(DISTINCT {c}) AS n_{c}" for c in attrs)
        con.execute(
            f"""CREATE OR REPLACE TABLE gold_dim_candidatura AS
                SELECT ano, turno, sq_candidato, nr_candidato{sel},
                       sum(qt_votos_nominais)::BIGINT AS qt_votos_nominais,
                       sum(qt_votos_nominais_validos)::BIGINT AS qt_votos_nominais_validos
                FROM silver_candidato_munzona GROUP BY ano, turno, sq_candidato, nr_candidato"""
        )
        n_var = sum(
            con.execute(f"SELECT count(*) FROM gold_dim_candidatura WHERE n_{c} > 1").fetchone()[0]
            for c in attrs
        )
        checks.append(
            ck.Checagem(
                "dim_candidatura:atributos_unicos",
                n_var == 0,
                False,
                f"{n_var} atributos com mais de um valor por candidatura-turno no recorte",
            )
        )
        sv.exportar_parquet(
            con, "gold_dim_candidatura", cfg.dir_ano("gold") / "gold_dim_candidatura.parquet"
        )
    return checks


def relatorio_qualidade(ctx: RunContext, checks: list[ck.Checagem], escopo: str) -> Path:
    criticas = [c for c in checks if c.critica and not c.ok]
    linhas = [
        f"# Relatório de qualidade — run `{ctx.run_id}`",
        "",
        f"- Ano: **{ctx.config.ano}** · Escopo: **{escopo}**",
        f"- Commit: `{ctx.commit}` · Config: `{ctx.config.config_hash}`",
        f"- Status para publicação: **{'BLOQUEADO' if criticas or ctx.pendencias else 'liberado'}**",
        "",
        "| Checagem | Crítica | Resultado | Detalhe |",
        "|---|---|---|---|",
        *[
            f"| {c.nome} | {'sim' if c.critica else 'não'} | {'✅' if c.ok else '❌'} | {c.detalhe} |"
            for c in checks
        ],
        "",
        "## Pendências",
        *([f"- {p}" for p in ctx.pendencias] or ["- nenhuma"]),
        "",
        "## Insumos",
        *[
            f"- `{i['recurso']}` {i['uf'] or ''} sha256 `{i['sha256'][:12]}` · gerado {i['gerado_em_fonte']}"
            f" · coletado {i['coletado_em']} · turnos {i['turnos_presentes']}"
            for i in ctx.insumos
        ],
    ]
    destino = ctx.config.paths["reports"] / "quality" / f"{ctx.run_id}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    if criticas:
        ctx.status = "bloqueado"
    return destino
