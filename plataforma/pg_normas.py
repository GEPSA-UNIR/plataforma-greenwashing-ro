"""Tabela — visão tabular do conjunto (também é a 'table view' de acessibilidade)."""

from __future__ import annotations

import streamlit as st

import fontes


def _resumo_eventos() -> None:
    """Quantas OBSERVAÇÕES INDEPENDENTES existem por trás das linhas da tabela.

    A tabela mostra 114 linhas e isso convida a lê-las como 114 casos. Não são:
    os 11 Decretos Legislativos de 2018 saíram da mesma sessão extraordinária e
    são um ato só. Sem este bloco, o número de linhas vira poder estatístico
    imaginário — e é a primeira coisa que uma banca pergunta.
    """
    ev = fontes.eventos()
    if ev.empty:
        return
    ind = fontes.indicadores().set_index("sapl_id")
    ancora = {s: (ind.loc[s, "categoria"] == "com ADI") for s in ev["sapl_id"]
              if s in ind.index}
    n_eventos = ev["evento_id"].nunique()
    ev_ancora = ev[ev["sapl_id"].map(lambda s: ancora.get(s, False))]["evento_id"].nunique()
    n_ancoras = sum(1 for v in ancora.values() if v)
    tamanhos = ev.groupby("evento_id").size()
    maior = int(tamanhos.max())
    # o maior grupo NÃO é o dos 11 Decretos Legislativos (é a família da Lei
    # 3.686, ligada por cadeia); descrever qual é, em vez de supor
    id_maior = int(tamanhos.idxmax())
    rot_maior = (f"{ind.loc[id_maior, 'tipo']} {ind.loc[id_maior, 'numero']}/"
                 f"{ind.loc[id_maior, 'ano']}" if id_maior in ind.index else f"sapl {id_maior}")
    # maior grupo unido SÓ por sessão (o fatiamento burocrático)
    so_sessao = ev[ev["motivo"] == "sessao"].groupby("sessao_grupo_id").size()
    maior_sessao = int(so_sessao.max()) if len(so_sessao) else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("normas", len(ev), help="uma linha por norma na tabela abaixo")
    c2.metric("atos distintos", n_eventos,
              help="Normas que alteram umas às outras, ou que foram aprovadas na "
                   "mesma sessão plenária, contam como um caso só.")
    c3.metric("contestadas por ADI", f"{n_ancoras} normas = {ev_ancora} atos",
              help="As normas contestadas judicialmente se concentram em poucos "
                   "atos legislativos — é esse número menor que conta.")
    st.caption(
        f"As {len(ev)} normas **não são {len(ev)} observações independentes**: agrupam-se "
        f"em **{n_eventos} atos**. O maior tem **{maior} normas** — a família em torno "
        f"da {rot_maior}, uma década de leis alterando umas às outras. E "
        f"**{maior_sessao} Decretos Legislativos** de 2018 saíram da MESMA sessão "
        "extraordinária: um ato fatiado em peças por exigência formal, não "
        f"{maior_sessao} decisões. As {n_ancoras} normas contestadas por ADI valem, "
        f"portanto, por **{ev_ancora} casos** — e é esse o número que conta em "
        "qualquer comparação. A regra de agrupamento é automática e igual para "
        "todas, sem escolha caso a caso.")


def render() -> None:
    st.header("Tabela das normas")
    st.caption("Normas ambientais de 2010 em diante, mais as de contexto. "
               "Clique numa linha para abrir o dossiê; a coluna SAPL leva à página oficial.")
    df = fontes.indicadores().sort_values(["ano", "sapl_id"], ascending=False)
    so_analise = st.toggle("só as normas ambientais de 2010 em diante", value=True)
    if so_analise:
        df = df[df["na_analise"]]
        _resumo_eventos()
    cols = ["sapl_id", "tipo", "numero", "ano", "categoria", "dias_pl_lei",
            "n_age_sobre", "n_sofre", "tem_transcricao", "ementa", "url_sapl"]
    sel = st.dataframe(
        df[cols], width="stretch", hide_index=True, height=520,
        selection_mode="single-row", on_select="rerun", key="tabela_normas",
        column_config={
            "url_sapl": st.column_config.LinkColumn("SAPL", display_text="abrir"),
            "dias_pl_lei": st.column_config.NumberColumn("PL→lei (dias)"),
            "tem_transcricao": st.column_config.CheckboxColumn("plenário"),
            "n_age_sobre": st.column_config.NumberColumn("age sobre"),
            "n_sofre": st.column_config.NumberColumn("sofre ação"),
            "ementa": st.column_config.TextColumn("ementa", width="large"),
        })
    # o índice selecionado é conferido contra o tamanho ATUAL: a seleção persiste
    # entre reruns, mas o interruptor acima encolhe a tabela — e `iloc` de linha
    # que não existe mais derruba a página com IndexError
    linhas = [i for i in sel.get("selection", {}).get("rows", []) if i < len(df)]
    if linhas:
        escolhida = df.iloc[linhas[0]]
        if st.button(f"Abrir dossiê de {escolhida['tipo']} {escolhida['numero']}/{escolhida['ano']}",
                     type="primary"):
            st.session_state["dossie_sapl"] = int(escolhida["sapl_id"])
            st.session_state["ir_para"] = "Dossiê"
            st.rerun()
