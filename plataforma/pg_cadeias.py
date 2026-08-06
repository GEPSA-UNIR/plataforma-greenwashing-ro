"""Cadeias — famílias de normas ligadas por vínculos de AÇÃO, no tempo, clicáveis.

Componentes calculados só sobre arestas norma→norma do grafo v2 (registradas +
inferidas, sempre distinguidas no traço). Matérias e correlatas ficam de fora —
cadeia aqui é 'quem mexeu em quem'.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import fontes
import viz
from pg_mapa import _tema, painel_norma, sapl_do_evento


@st.cache_data
def _componentes() -> list[dict]:
    nos, arestas = fontes.grafo()
    if arestas.empty:
        return []
    aa = arestas[arestas["alvo_kind"] != "materia"].copy()
    aa["fonte_sapl"] = aa["fonte_sapl"].astype(int)
    aa["alvo_sapl"] = aa["alvo_sapl"].astype(int)

    pai: dict[int, int] = {}

    def achar(x: int) -> int:
        pai.setdefault(x, x)
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    for _, a in aa.iterrows():
        ra, rb = achar(a["fonte_sapl"]), achar(a["alvo_sapl"])
        if ra != rb:
            pai[ra] = rb
    grupos: dict[int, set[int]] = {}
    for n in pai:
        grupos.setdefault(achar(n), set()).add(n)

    ind = fontes.indicadores().set_index("sapl_id")
    out = []
    for membros in grupos.values():
        if len(membros) < 2:
            continue
        graus = pd.concat([aa[aa["fonte_sapl"].isin(membros)]["fonte_sapl"],
                           aa[aa["alvo_sapl"].isin(membros)]["alvo_sapl"]]).value_counts()
        hub = int(graus.index[0])
        if hub in ind.index:
            h = ind.loc[hub]
            rotulo = f"família da {h['tipo']} {h['numero']}/{h['ano']} — {len(membros)} normas"
        else:
            nrow = fontes.grafo()[0]
            hn = nrow[nrow["sapl_id"] == hub]
            rotulo = (f"família da {hn.iloc[0]['tipo']} {hn.iloc[0]['numero']}/{hn.iloc[0]['ano']} "
                      f"— {len(membros)} normas") if not hn.empty else f"família sapl {hub} — {len(membros)}"
        n_adi = sum(1 for m in membros if m in ind.index and ind.loc[m, "categoria"] == "com ADI")
        # o ASSUNTO entra no rótulo: a busca do selectbox filtra pelo texto exibido,
        # e "família da Lei 3.686/2015" só é achável por quem já sabe o número
        assunto = ""
        if hub in ind.index:
            assunto = " ".join(str(ind.loc[hub, "ementa"] or "").split())[:70]
        out.append({"rotulo": rotulo + (f" · {n_adi} ADI" if n_adi else "")
                              + (f" — {assunto}" if assunto else ""),
                    "membros": membros, "tamanho": len(membros)})
    out.sort(key=lambda c: -c["tamanho"])
    return out


def dados_cadeia(membros: set[int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    nos, arestas = fontes.grafo()
    ind = fontes.indicadores()[["sapl_id", "categoria"]]
    sub_n = nos[nos["sapl_id"].isin(membros)].merge(ind, on="sapl_id", how="left")
    sub_n["categoria"] = sub_n["categoria"].fillna("vigente (presumida)")
    sub_a = arestas[(arestas["alvo_kind"] != "materia")
                    & arestas["fonte_sapl"].isin(membros) & arestas["alvo_sapl"].isin(membros)]
    return sub_n, sub_a


def render() -> None:
    st.header("Cadeias de normas")
    st.caption("Cada cadeia é uma família ligada por atos (altera, revoga, regulamenta, susta…). "
               "Setas cheias = vínculo registrado no SAPL · tracejadas = inferido da ementa. "
               "Clique num nó para abrir o cartão.")
    comps = _componentes()
    if not comps:
        st.info("nenhuma cadeia nos grafos gerados (data/grafo/)")
        return
    escolha = st.selectbox("Digite para buscar — número da lei principal ou assunto",
                           comps, format_func=lambda c: c["rotulo"],
                           help="Exemplos: 3686 · licenciamento · zoneamento")
    sub_n, sub_a = dados_cadeia(escolha["membros"])
    ev = st.plotly_chart(viz.fig_cadeia(sub_n, sub_a, _tema()), on_select="rerun",
                         selection_mode="points", key=f"cadeia_{escolha['rotulo']}")
    sid = sapl_do_evento(ev)
    if sid is not None:
        painel_norma(sid)

    with st.expander("atos desta cadeia (tabela)"):
        st.dataframe(sub_a[["origem", "fonte_tipo", "fonte_num", "fonte_ano", "relacao",
                            "alvo_tipo", "alvo_num", "alvo_ano", "fonte_data"]],
                     width="stretch", hide_index=True)
