# -*- coding: utf-8 -*-
import json
from pathlib import Path
from functools import lru_cache
import polars as pl
import altair as alt
import streamlit as st

# ----------------------------------------------------------------------
# Paths (descobre a raiz subindo até achar /data e /notebooks)
# ----------------------------------------------------------------------
def find_project_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "data").exists() and (p / "notebooks").exists():
            return p
    return start  # fallback (caso rode fora da estrutura)

CWD = Path.cwd()
ROOT = find_project_root(CWD)
EXPORT = ROOT / "data" / "exports" / "dashboard"

# ----------------------------------------------------------------------
# Data loaders (com cache)
# ----------------------------------------------------------------------
@lru_cache(maxsize=8)
def load_parquet(name: str) -> pl.DataFrame:
    return pl.read_parquet(EXPORT / name)

@lru_cache(maxsize=1)
def load_manifest() -> dict:
    fp = EXPORT / "_manifest.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def topics_table() -> pl.DataFrame:
    if (EXPORT / "topics_current.parquet").exists():
        return load_parquet("topics_current.parquet")
    return load_parquet("topics.parquet")

# ----------------------------------------------------------------------
# Pequenas utilidades de apresentação
# ----------------------------------------------------------------------
def fmt_topic_label(topic_row: dict) -> str:
    t = topic_row["topic"]
    lab = topic_row["label"]
    return f"[{t}] {lab}"

def human_pct(x: float) -> str:
    try:
        return f"{100.0 * float(x):.1f}%"
    except Exception:
        return "–"

# ----------------------------------------------------------------------
# Layout e Sidebar
# ----------------------------------------------------------------------
st.set_page_config(page_title="TCCs CC@UFCG – Mapeamento Temático", layout="wide")

st.sidebar.title("Navegação")
page = st.sidebar.radio(
    "Selecione",
    ("Visão geral", "Pesquisar orientadores", "Filtrar TCCs por tema", "Perfil do orientador", "Evolução de temas")
)

# Info do manifesto (rodapé)
manifest = load_manifest()

with st.sidebar.expander("Artefatos & Execução"):
    if manifest:
        st.markdown(f"**Gerado em:** {manifest.get('generated_at', '–')}")
        sel = manifest.get("selection", {})
        if sel:
            st.markdown(f"**Modelo:** {sel.get('method','–')}  \n**Run/Trial:** {sel.get('run','–')} / {sel.get('trial','–')}")
            st.markdown(f"**K:** {sel.get('K','–')}  \n**Outliers (reported):** {human_pct(sel.get('reported_outliers_pct'))}")
        corp = manifest.get("corpus", {})
        st.markdown(f"**Docs:** {corp.get('n_docs','–')}  \n**Anos:** {corp.get('years',{}).get('min','–')}–{corp.get('years',{}).get('max','–')}")
    else:
        st.caption("Manifesto não encontrado (_manifest.json).")

# ----------------------------------------------------------------------
# Carregamento dos dados
# ----------------------------------------------------------------------
docs = load_parquet("docs.parquet")
topics = topics_table().with_columns([
    pl.col("topic").cast(pl.Int64),
    pl.col("label").cast(pl.Utf8),
    pl.col("keywords").cast(pl.Utf8)
])
doc_topics = load_parquet("doc_topics.parquet")
trends = load_parquet("topic_trends.parquet")
advisor_profiles = load_parquet("advisor_profiles.parquet")
advisor_topics = load_parquet("advisor_topics.parquet")

doc_with_topic = (
    doc_topics.join(docs, on="DOC_ID", how="inner")
              .join(topics.select(["topic","label"]), on="topic", how="left")
)

# ----------------------------------------------------------------------
# 1) Visão geral
# ----------------------------------------------------------------------
if page == "Visão geral":
    st.title("Mapeamento Temático dos TCCs – CC@UFCG")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total de TCCs", f"{docs.height}")
    with c2:
        yrs = docs["ano"].drop_nulls()
        st.metric("Período", f"{int(yrs.min())}–{int(yrs.max())}" if yrs.len() else "–")
    with c3:
        st.metric("Temas (sem -1)", f"{topics.height}")
    with c4:
        out_count = doc_topics.filter(pl.col("topic") == -1).height
        st.metric("Outliers (docs)", f"{out_count} ({human_pct(out_count / docs.height)})")

    st.markdown("### Top temas (por participação no período)")
    top_share = (trends.group_by("topic")
                       .agg(pl.col("share").mean().alias("share_medio"),
                            pl.col("n_docs").sum().alias("n_total"))
                       .join(topics.select(["topic","label"]), on="topic", how="left")
                       .sort("share_medio", descending=True)
                       .head(10))
    chart = alt.Chart(top_share.to_pandas()).mark_bar().encode(
        x=alt.X("share_medio:Q", title="Participação média"),
        y=alt.Y("label:N", sort="-x", title="Tema"),
        tooltip=["label:N", alt.Tooltip("share_medio:Q", format=".1%"), "n_total:Q"]
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)

    st.markdown("### Distribuição por ano")
    by_year = (docs.group_by("ano").agg(pl.len().alias("n_docs")).sort("ano"))
    line = alt.Chart(by_year.to_pandas()).mark_line(point=True).encode(
        x=alt.X("ano:O", title="Ano"),
        y=alt.Y("n_docs:Q", title="TCCs no ano"),
        tooltip=["ano:O","n_docs:Q"]
    ).properties(height=280)
    st.altair_chart(line, use_container_width=True)

# ----------------------------------------------------------------------
# 2) Pesquisar orientadores
# ----------------------------------------------------------------------
elif page == "Pesquisar orientadores":
    st.title("Pesquisar orientadores")
    q = st.text_input("Digite parte do nome do orientador", "")
    base = advisor_profiles
    if q.strip():
        base = base.filter(
            pl.col("orientador_nome").str.contains(q, literal=False, case=False)
        )
    st.caption(f"Resultados: {base.height}")
    st.dataframe(base.select(["orientador_nome","n_tccs","anos_atuacao","temas_top"]).sort("n_tccs", descending=True).to_pandas(), use_container_width=True)

# ----------------------------------------------------------------------
# 3) Filtrar TCCs por tema
# ----------------------------------------------------------------------
elif page == "Filtrar TCCs por tema":
    st.title("Filtrar TCCs por tema")
    topics_opts = topics.sort("topic").to_dict(as_series=False)
    display_opts = [f"[{t}] {l}" for t, l in zip(topics_opts["topic"], topics_opts["label"])]
    choice = st.selectbox("Tema", options=display_opts, index=0)
    sel_topic = int(choice.split("]")[0].strip("["))
    st.caption(f"Tema selecionado: {sel_topic}")

    subset = (doc_with_topic.filter(pl.col("topic") == sel_topic)
                           .select(["DOC_ID","ano","titulo","orientador_nome","url","prob"])
                           .sort(["ano","prob"], descending=[False, True]))

    st.write(f"**TCCs no tema [{sel_topic}]** — {subset.height} documentos")
    st.dataframe(subset.to_pandas(), use_container_width=True)

    t_trend = trends.filter(pl.col("topic") == sel_topic).sort("ano")
    if not t_trend.is_empty():
        chart = alt.Chart(t_trend.to_pandas()).mark_line(point=True).encode(
            x=alt.X("ano:O", title="Ano"),
            y=alt.Y("share:Q", title="Participação no ano", axis=alt.Axis(format='%')),
            tooltip=["ano:O", alt.Tooltip("share:Q", format=".1%"), "n_docs:Q"]
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Sem série temporal para este tema.")

# ----------------------------------------------------------------------
# 4) Perfil do orientador
# ----------------------------------------------------------------------
elif page == "Perfil do orientador":
    st.title("Perfil do orientador")
    orient_opts = advisor_profiles.sort("orientador_nome").to_dict(as_series=False)
    if not orient_opts.get("orientador_nome"):
        st.warning("Sem perfis de orientadores disponíveis.")
    else:
        index_default = 0
        choice = st.selectbox("Orientador", options=orient_opts["orientador_nome"], index=index_default)
        oid = advisor_profiles.filter(pl.col("orientador_nome")==choice).select("orientador_id").item()
        perfil = advisor_profiles.filter(pl.col("orientador_id")==oid).to_dicts()[0]

        st.subheader(choice)
        c1, c2, c3 = st.columns(3)
        c1.metric("TCCs orientados", perfil["n_tccs"])
        c2.metric("Anos de atuação", perfil["anos_atuacao"])
        c3.metric("Temas principais", perfil["temas_top"])

        tccs = (doc_with_topic.filter(pl.col("orientador_id")==oid)
                                .select(["DOC_ID","ano","titulo","label","prob","url","topic"])
                                .sort(["ano","prob"], descending=[False, True]))
        st.markdown("#### Trabalhos orientados")
        st.dataframe(tccs.to_pandas(), use_container_width=True)

        dist = (advisor_topics.filter(pl.col("orientador_id")==oid)
                                .join(topics.select(["topic","label"]), on="topic", how="left")
                                .sort("n_docs", descending=True))
        st.markdown("#### Distribuição de temas (no orientador)")
        if not dist.is_empty():
            bar = alt.Chart(dist.to_pandas()).mark_bar().encode(
                x=alt.X("n_docs:Q", title="TCCs no tema"),
                y=alt.Y("label:N", sort="-x", title="Tema"),
                tooltip=["label:N","n_docs:Q", alt.Tooltip("share_no_orientador:Q", format=".1%")]
            ).properties(height=360)
            st.altair_chart(bar, use_container_width=True)
        else:
            st.info("Sem distribuição de temas calculada para este orientador.")

# ----------------------------------------------------------------------
# 5) Evolução de temas (exploração)
# ----------------------------------------------------------------------
elif page == "Evolução de temas":
    st.title("Evolução de temas no período")
    topics_df = topics.select(["topic","label"]).sort("topic")
    opt_labels = topics_df.with_columns(
        (pl.lit("[") + pl.col("topic").cast(pl.Utf8) + pl.lit("] ") + pl.col("label")).alias("display")
    )
    opts = opt_labels.to_dicts()
    labels = [o["display"] for o in opts]
    picks = st.multiselect("Selecione 1–6 temas", options=labels, default=labels[:3], max_selections=6)
    if picks:
        sel_topics = [int(p.split("]")[0][1:]) for p in picks]
        sub = (trends.filter(pl.col("topic").is_in(sel_topics))
                      .join(topics_df, on="topic", how="left")
                      .sort(["topic","ano"]))
        chart = alt.Chart(sub.to_pandas()).mark_line(point=True).encode(
            x=alt.X("ano:O", title="Ano"),
            y=alt.Y("share:Q", title="Participação no ano", axis=alt.Axis(format='%')),
            color=alt.Color("label:N", title="Tema"),
            tooltip=["label:N", "ano:O", alt.Tooltip("share:Q", format=".1%"), "n_docs:Q"]
        ).properties(height=420)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Selecione ao menos um tema para visualizar a evolução.")

# ----------------------------------------------------------------------
# Rodapé com créditos
# ----------------------------------------------------------------------
st.markdown("---")
st.caption("Trabalho de Conclusão de Curso em Ciência da Computação (UFCG) • Mapeamento temático com BERTopic • Dashboard por Daniel Dantas")