"""Exploração local (Streamlit). Lê apenas a camada Gold e mostra o status da base.

Executar: `make dashboard`. Sem Gold disponível, o app mostra o que falta — nunca números simulados.
"""

from __future__ import annotations

import json

import plotly.express as px
import polars as pl
import streamlit as st

from eleicoes.analytics.indicators import adicionar_indicadores
from eleicoes.config import load_config

st.set_page_config(page_title="Eleições presidenciais — 1º × 2º turno", layout="wide")
cfg0 = load_config()
with st.sidebar:
    ano = st.selectbox("Eleição", sorted(cfg0.anos_suportados, reverse=True))
cfg = cfg0.com_ano(ano)
GOLD = cfg.dir_ano("gold")
REPORTS = cfg.paths["reports"]
COR_A, COR_B = "#1f6feb", "#d97706"  # cores fixas por finalista em todo o app

st.title(f"Eleição presidencial {ano} — comparação entre turnos")

qualidade = [
    q
    for q in sorted((REPORTS / "quality").glob("*.md"))
    if f"Ano: **{ano}**" in q.read_text(encoding="utf-8")
]
status = "sem relatório de qualidade"
if qualidade:
    status = "BLOQUEADA" if "BLOQUEADO" in qualidade[-1].read_text(encoding="utf-8") else "liberada"
with st.sidebar:
    st.markdown(f"**Status da base:** {status}")
    if qualidade:
        st.caption(f"Relatório: {qualidade[-1].name}")
    st.caption("Contagens observadas do TSE. Decomposições são contábeis, não causais.")

part_path = GOLD / "gold_participacao_municipio.parquet"
if not part_path.exists():
    st.warning("Camada Gold ausente. Rode `make pilot` (MG) ou `make national` antes.")
    st.stop()
if status != "liberada":
    st.error("Base não liberada: números abaixo são PRELIMINARES e não sustentam conclusões.")

part = pl.read_parquet(part_path)
ufs = sorted(part["uf"].unique().to_list())
with st.sidebar:
    turno = st.radio("Turno", [1, 2], horizontal=True)
    uf_sel = st.multiselect("UF", ufs, default=ufs)

filtro = part.filter(pl.col("uf").is_in(uf_sel))
somas = [
    "qt_aptos",
    "qt_comparecimento",
    "qt_abstencoes",
    "qt_votos_brancos",
    "qt_votos_nulos",
    "qt_votos_validos",
]
tot = adicionar_indicadores(filtro.group_by("turno").agg([pl.col(c).sum() for c in somas]))
linha = tot.filter(pl.col("turno") == turno)
if linha.height:
    r = linha.row(0, named=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Comparecimento",
        f"{r['taxa_comparecimento']:.2%}",
        help=f"{r['qt_comparecimento']:,} / {r['qt_aptos']:,} aptos",
    )
    c2.metric(
        "Abstenção",
        f"{r['taxa_abstencao']:.2%}",
        help=f"{r['qt_abstencoes']:,} / {r['qt_aptos']:,} aptos",
    )
    c3.metric(
        "Brancos",
        f"{r['taxa_brancos']:.2%}",
        help=f"{r['qt_votos_brancos']:,} / {r['qt_comparecimento']:,} comparecimento",
    )
    c4.metric(
        "Nulos",
        f"{r['taxa_nulos']:.2%}",
        help=f"{r['qt_votos_nulos']:,} / {r['qt_comparecimento']:,} comparecimento",
    )
else:
    st.info(f"Sem dados do {turno}º turno no recorte.")

dec_path = GOLD / "gold_decomposicao_municipio.parquet"
resumo_path = GOLD / "resumo_virada.json"
if dec_path.exists() and resumo_path.exists():
    resumo = json.loads(resumo_path.read_text(encoding="utf-8"))
    st.subheader("Contribuição para a mudança da margem (A − B)")
    st.caption(
        f"A = votável {resumo['finalista_a']} (líder do 1º turno no escopo "
        f"{resumo['escopo_ufs']}); B = votável {resumo['finalista_b']}. "
        "Contribuição = margem no 2º turno − margem no 1º turno, em votos."
    )
    dec = pl.read_parquet(dec_path).filter(pl.col("uf").is_in(uf_sel))
    por_uf = dec.group_by("uf").agg(pl.col("contribuicao").sum()).sort("contribuicao")
    fig = px.bar(
        por_uf.to_pandas(),
        x="contribuicao",
        y="uf",
        orientation="h",
        color=por_uf["contribuicao"].to_pandas() > 0,
        color_discrete_map={True: COR_A, False: COR_B},
        labels={"contribuicao": "Δ margem A − B (votos)", "uf": "UF", "color": "favorece A"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        dec.select("uf", "nm_municipio", "margem_1", "margem_2", "contribuicao", "mudou_vencedor")
        .head(50)
        .to_pandas(),
        use_container_width=True,
    )
else:
    st.info("Decomposição indisponível: exige os dois turnos completos e reconciliados.")

with st.expander("Metodologia e fonte"):
    st.markdown(
        "Ver `docs/methodology.md` e `docs/limitations.md`. Fonte: TSE — Portal de Dados "
        "Abertos; snapshot identificado pelo SHA-256 nos manifestos."
    )
