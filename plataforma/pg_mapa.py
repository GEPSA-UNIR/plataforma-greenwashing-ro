"""Explorar — o mapa das normas ambientais: clicável, filtrável, com atalhos."""

from __future__ import annotations

import streamlit as st

import fontes
import viz


def _tema() -> str:
    try:
        return st.context.theme.type or "light"
    except Exception:
        return "light"


def sapl_do_evento(ev) -> int | None:
    """Extrai o sapl_id do evento de seleção do plotly, tolerante ao formato."""
    for p in ev.get("selection", {}).get("points", []):
        cd = p.get("customdata")
        if isinstance(cd, (list, tuple)):
            cd = cd[0] if cd else None
        if isinstance(cd, dict):
            cd = next(iter(cd.values()), None)
        if cd is not None:
            try:
                return int(cd)
            except (TypeError, ValueError):
                continue
    return None


def painel_norma(sapl_id: int) -> None:
    """Cartão de detalhe + ações — usado pelo mapa e pelas cadeias."""
    df = fontes.indicadores()
    r = df[df["sapl_id"] == sapl_id]
    if r.empty:
        st.caption(f"sapl {sapl_id}: sem ficha gerada ainda")
        return
    r = r.iloc[0]
    with st.container(border=True):
        st.markdown(f"**{r['tipo']} nº {r['numero']}/{r['ano']}** · {r['categoria']}")
        st.markdown(r["ementa"][:400] + ("…" if len(r["ementa"]) > 400 else ""))
        detalhes = []
        if r["autores"]:
            detalhes.append(f"autoria: {r['autores']}")
        if r["dias_pl_lei"] is not None and r["dias_pl_lei"] == r["dias_pl_lei"]:
            detalhes.append(f"PL→lei em {int(r['dias_pl_lei'])} dias")
        if r["tem_transcricao"]:
            detalhes.append("parecer em plenário")
        if detalhes:
            st.caption(" · ".join(detalhes))
        c1, c2 = st.columns([1, 1])
        if c1.button("Abrir dossiê", key=f"pn_dossie_{sapl_id}", type="primary"):
            st.session_state["dossie_sapl"] = int(sapl_id)
            st.session_state["ir_para"] = "Dossiê"
            st.rerun()
        c2.link_button("Ver no SAPL", r["url_sapl"] or "https://sapl.al.ro.leg.br")


def render() -> None:
    st.header("Explorar as normas ambientais")
    st.caption("Todas as normas do conjunto no tempo. Cada ponto é uma norma; cor "
               "e símbolo indicam a situação. Clique num ponto para abrir o cartão.")
    df = fontes.indicadores()
    ja = df[df["na_analise"]]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("normas ambientais", len(ja),
              help="Normas do recorte: ambientais, de 2010 em diante.")
    m2.metric("contestadas por ADI", int((ja["categoria"] == "com ADI").sum()),
              help="Ação Direta de Inconstitucionalidade — tentativa de retrocesso barrada")
    m3.metric("revogadas/suspensas", int((ja["categoria"] == "revogada/suspensa").sum()))
    m4.metric("parecer em plenário", int(ja["tem_transcricao"].sum()),
              help="O parecer foi dado direto no plenário, não na comissão "
                   "temática — indício de que a discussão técnica foi abreviada.")
    m5.metric("tempo típico projeto→lei", f"{int(ja['dias_pl_lei'].median())} dias"
              if ja["dias_pl_lei"].notna().any() else "—")

    f1, f2, f3 = st.columns([2, 1, 2])
    cats = f1.multiselect("situação", viz.CAT_ORDEM, default=viz.CAT_ORDEM)
    anos = f2.slider("anos", int(df["ano"].min()), int(df["ano"].max()),
                     (2010, int(df["ano"].max())))
    busca = f3.text_input("buscar na ementa", placeholder="ex.: licenciamento, ZSEE, queimadas…")
    # sem este recorte o mapa mostra TODAS as fichas (inclusive as de contexto,
    # fora do conjunto) e o rodapé diz "125 normas · 24 com ADI" enquanto o resto
    # da plataforma diz 114 e 21 — a mesma tela contando duas histórias
    so_analise = st.toggle("só as normas ambientais de 2010 em diante", value=True,
                           help="Desmarque para incluir normas de contexto: as que estão "
                                "fora do recorte, mas foram levantadas para completar "
                                "cadeias de alteração. Todos os números da página "
                                "Análise usam apenas o recorte.")

    vis = df[df["categoria"].isin(cats) & df["ano"].between(*anos)]
    if so_analise:
        vis = vis[vis["na_analise"]]
    if busca.strip():
        vis = vis[vis["ementa"].str.contains(busca.strip(), case=False, regex=False)]
    st.caption(f"{len(vis)} normas no mapa — cada ponto é uma norma; clique para detalhes. "
               "Fonte: fichas canônicas geradas do SAPL.")

    ev = st.plotly_chart(viz.fig_mapa(vis, _tema(), fontes.eventos()),
                         on_select="rerun", selection_mode="points", key="mapa_normas")
    sid = sapl_do_evento(ev)
    if sid is not None:
        painel_norma(sid)
    else:
        st.caption("Arraste para navegar, roda do mouse para zoom. O cerco tracejado "
                   "marca normas que **são um evento só** — aprovadas na mesma sessão "
                   "plenária, contam como um caso, não como vários.")
