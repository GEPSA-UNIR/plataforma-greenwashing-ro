"""Análise — o painel de resultados: o que a leitura por IA encontrou, e o quanto ela vale.

Esta página existe para ser lida por quem NÃO acompanhou a construção. Por isso
cada bloco traz o resultado e, junto, a escolha metodológica que o produziu — não
num anexo, ao lado do número. Um painel que mostra só o resultado convida a
tratá-lo como fato; aqui o veredito é juízo de modelo, e a página diz isso.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
import streamlit as st

import fontes
import viz
from pg_mapa import _tema


FILTROS = ("f_veredito", "f_mecanismo", "f_retorica", "f_efeito")


def _clique_novo(chave: str, selecao: dict) -> list[dict]:
    """Pontos clicados, e SÓ quando a seleção mudou desde o ciclo anterior.

    A seleção de um gráfico plotly **persiste** entre reruns: sem esta guarda, o
    filtro seria reaplicado a cada ciclo e o botão "limpar filtros" nunca
    pegaria — o clique antigo o desfaria no ciclo seguinte. Guardando a
    impressão do que já foi consumido, o clique age uma vez, como um gesto.
    """
    pontos = (selecao.get("selection", {}) or {}).get("points", [])
    marca = repr([(p.get("x"), p.get("y"), p.get("customdata")) for p in pontos])
    if st.session_state.get(f"_visto_{chave}") == marca:
        return []
    st.session_state[f"_visto_{chave}"] = marca
    return pontos


def _aplicar_filtro(**campos) -> None:
    """Clique num gráfico define o filtro da lista de normas.

    Escrever em `session_state` só funciona ANTES de o widget correspondente
    nascer no ciclo — por isso as chamadas ficam junto dos gráficos, que vêm
    antes da seção de lista. Um clique SUBSTITUI o filtro anterior em vez de
    somar: o gesto natural é "quero ver ESTES", não "acrescente estes".
    """
    for chave in FILTROS:
        st.session_state[chave] = []
    for nome, chave in (("veredito", "f_veredito"), ("mecanismo", "f_mecanismo"),
                        ("retorica", "f_retorica"), ("efeito", "f_efeito")):
        if campos.get(nome):
            st.session_state[chave] = campos[nome]
    st.rerun()


SECOES_CITAVEIS = ("## Ementa", "## Texto integral da LEI", "## Texto integral da norma",
                   "## Texto do PROJETO original", "## Transcrição da sessão plenária")


def _mostrar_evidencia(sapl_id: int) -> None:
    """As citações literais que sustentam a leitura desta norma.

    É a peça que faltava: o painel contava quantas citações havia e nunca
    mostrava uma. Contagem pede que se acredite; o trecho deixa conferir. Cada
    citação vem com a seção de onde o modelo diz tê-la tirado e com a marca de
    ter sido reencontrada, ou não, no documento oficial.
    """
    resp = fontes.resposta_ia(sapl_id)
    a = (resp or {}).get("analise")
    if not a:
        return

    disp = (a.get("eixo_efeito") or {}).get("dispositivos") or []
    cits = (a.get("eixo_retorica") or {}).get("citacoes") or []
    if not disp and not cits:
        return

    def _par(c) -> tuple[str, str]:
        """(trecho, seção) — aceita a forma antiga (string) e a nova (objeto)."""
        if isinstance(c, dict):
            return str(c.get("citacao") or ""), str(c.get("secao") or "")
        return str(c), ""

    def _selo(secao: str) -> str:
        return ("documento oficial" if secao.startswith(SECOES_CITAVEIS)
                else f"seção declarada: {secao}" if secao else "seção não declarada")

    with st.expander(f"a evidência que o modelo usou — {len(disp)} dispositivo(s), "
                     f"{len(cits)} citação(ões) de retórica", expanded=True):
        if disp:
            st.markdown("**O que os dispositivos fazem** — eixo do efeito")
            for d in disp:
                trecho, secao = _par(d)
                nome = str(d.get("dispositivo") or "dispositivo não identificado")
                st.markdown(f"**{nome}** — {d.get('efeito') or ''}")
                if trecho:
                    st.markdown(
                        f"> {trecho}\n\n"
                        f"<span style='font-size:.8em;color:#667085'>{_selo(secao)}"
                        "</span>", unsafe_allow_html=True)
        if cits:
            st.markdown("**Como a norma se apresenta** — eixo da retórica")
            for c in cits:
                trecho, secao = _par(c)
                if not trecho:
                    continue
                st.markdown(
                    f"> {trecho}\n\n"
                    f"<span style='font-size:.8em;color:#667085'>{_selo(secao)}</span>",
                    unsafe_allow_html=True)
        st.caption("Os trechos acima foram copiados pelo modelo do dossiê e "
                   "reconferidos, palavra por palavra, contra o documento oficial. "
                   "Divergiu? Vira citação não localizada, e aparece na contagem "
                   "de conferência lá em cima.")


def _cartao(titulo: str, corpo: str, cor: str = "#2a78d6") -> None:
    """Bloco de explicação com barra colorida — separa 'o que é' de 'o que achamos'."""
    st.markdown(
        f"""<div style="border-left:4px solid {cor};background:#f7f9fc;
        padding:.6rem .9rem;margin:.2rem 0 .9rem;border-radius:0 6px 6px 0;">
        <b>{titulo}</b><br><span style="font-size:.9em;">{corpo}</span></div>""",
        unsafe_allow_html=True)


def render() -> None:
    st.header("Análise com IA — resultados")
    st.caption("O que a leitura por IA encontrou em cada norma do conjunto — e o "
               "quanto essa leitura vale. Cada bloco traz o resultado e, ao lado, "
               "a escolha metodológica que o produziu.")

    ia = fontes.analise_ia()
    if ia is None or ia.empty:
        st.info("A análise ainda não foi executada. Os dossiês de evidência estão "
                "prontos em `data/ia/dossies/`; rode `scripts/analisar_ia.py`.")
        return

    ok = ia[ia["status"] != "descartada"]
    ind = fontes.indicadores().set_index("sapl_id")
    ev = fontes.eventos()

    modelo = ia["modelo"].dropna().unique()
    quando = str(ia["quando"].dropna().max())[:10] if ia["quando"].notna().any() else "?"
    prompt_v = ia["prompt_versao"].dropna().unique()
    st.caption(
        f"**Juízo de modelo, não fato.** Leitura produzida pelo modelo de linguagem "
        f"`{', '.join(modelo)}` em {quando}, seguindo um roteiro de análise fixo "
        f"(versão `{', '.join(prompt_v)}`). Cada afirmação do modelo foi "
        "conferida contra o documento oficial — o painel de honestidade abaixo "
        "mostra o resultado dessa conferência.")

    # ── 1. o que saiu ────────────────────────────────────────────────────────
    # NADA de `delta=` aqui: o st.metric sempre desenha ↑/↓ nesse campo, mesmo com
    # delta_color="off". Nenhum destes números é uma VARIAÇÃO — "5 descartadas" é
    # parte do total, não um aumento —, e a seta afirmava movimento que não existe.
    # O contexto vai em legenda abaixo, onde é lido como contexto.
    # greenwashing é o GÊNERO: soma as duas espécies (ver viz.ESPECIES_DISFARCE).
    # Mostrar só a regressão (40) escondia 29 normas que também prometem proteção
    # e não entregam — a mesma distância entre discurso e prática.
    n_regressao = int((ok["veredito"] == "greenwashing").sum())
    n_esvazia = int((ok["veredito"] == "simbolica").sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("normas analisadas", len(ia))
    c2.metric("leituras aproveitadas", len(ok))
    c3.metric("com disfarce ambiental", n_regressao + n_esvazia,
              help="Normas que se apresentam como ambientais e não entregam o que "
                   "prometem — seja retirando proteção (regressão), seja não "
                   "entregando nada (esvaziamento).")
    if not ev.empty:
        c4.metric("atos distintos", ev["evento_id"].nunique(),
                  help="Normas que alteram umas às outras, ou aprovadas na mesma "
                       "sessão plenária, contam como um caso só.")

    partes = []
    if len(ia) - len(ok):
        partes.append(f"**{len(ia) - len(ok)}** leitura(s) foram reprovadas pela "
                      "conferência automática e não entram em nenhum número desta "
                      "página")
    if not ev.empty:
        partes.append(f"as **{len(ev)}** normas correspondem a **{ev['evento_id'].nunique()}** "
                      "atos legislativos distintos")
    if partes:
        st.caption(" · ".join(partes).capitalize() + ".")

    st.divider()

    # ── 2. a decomposição de dois eixos ──────────────────────────────────────
    st.subheader("A decomposição: retórica × efeito")
    _cartao("Por que dois eixos, e não uma nota",
            "Greenwashing não é <i>fazer mal ao meio ambiente</i> — é a <b>distância</b> "
            "entre o que a norma diz ser e o que ela faz. O que o define é o "
            "<b>disfarce</b>: uma norma que retira proteção de forma explícita é "
            "retrocesso, e grave, mas não se disfarça de nada.<br><br>"
            "Essa distância aparece de <b>duas formas</b>, e as duas são greenwashing: "
            "a norma promete e <b>retira</b> proteção (regressão), ou promete e "
            "<b>não entrega nada</b> — sem prazo, sem sanção, sem orçamento "
            "(esvaziamento). Mudam a gravidade e o remédio, não a natureza.<br><br>"
            "Por isso o modelo responde <b>dois eixos separados</b> e o veredito nasce "
            "do cruzamento: na matriz, a dissimulação está onde a retórica é alta e o "
            "efeito não a acompanha — nunca uma linha ou coluna inteira.",
            viz.CORES_VEREDITO["greenwashing"])

    esq, dir_ = st.columns([3, 2])
    with esq:
        tabela = Counter(zip(ok["retorica"], ok["efeito"]))
        sel_m = st.plotly_chart(viz.fig_matriz_re(dict(tabela), _tema()),
                                on_select="rerun", selection_mode="points",
                                key="matriz_re")
    with dir_:
        sel_v = st.plotly_chart(viz.fig_vereditos(Counter(ok["veredito"]), _tema()),
                                on_select="rerun", selection_mode="points",
                                key="vereditos")

    # O clique nos gráficos ALIMENTA o filtro da lista lá embaixo. Isto tem de
    # acontecer ANTES de os widgets de filtro nascerem: escrever em session_state
    # numa chave já instanciada no mesmo ciclo é erro no Streamlit.
    for p in _clique_novo("matriz", sel_m):
        if p.get("x") and p.get("y"):
            _aplicar_filtro(retorica=[str(p["y"])], efeito=[str(p["x"])])
    for p in _clique_novo("vereditos", sel_v):
        cd = p.get("customdata")
        cd = cd[0] if isinstance(cd, (list, tuple)) and cd else cd
        if cd:
            _aplicar_filtro(veredito=[str(cd)])

    st.markdown(
        f"**Como ler os vereditos.** As duas primeiras barras são espécies do mesmo "
        f"gênero — juntas, **{n_regressao + n_esvazia} normas com disfarce ambiental**.\n\n"
        "- **greenwashing por regressão** — promete proteção e *retira* proteção.\n"
        "- **greenwashing por esvaziamento** — promete proteção e *não entrega nada*: "
        "institui programa ou política sem prazo, sem sanção e sem orçamento.\n"
        "- **retrocesso assumido** — enfraquece a proteção, mas sem se disfarçar de "
        "norma ambiental. Grave, e honesto quanto ao que faz.\n"
        "- **proteção genuína** — fortalece de fato.\n"
        "- **não ambiental** — a norma não trata de meio ambiente.\n"
        "- **indeterminado** — evidência insuficiente para decidir; é resposta válida "
        "e preferível ao chute.")

    st.divider()

    # ── 3. mecanismos ────────────────────────────────────────────────────────
    st.subheader("Como a dissimulação aparece")
    mec = Counter(m for s in ok["mecanismos"] for m in str(s).split(";") if m)
    if mec:
        e2, d2 = st.columns([3, 2])
        with e2:
            sel_x = st.plotly_chart(viz.fig_mecanismos(dict(mec), _tema()),
                                    on_select="rerun", selection_mode="points",
                                    key="mecanismos")
            for p in _clique_novo("mecanismos", sel_x):
                cd = p.get("customdata")
                cd = cd[0] if isinstance(cd, (list, tuple)) and cd else cd
                if cd:
                    _aplicar_filtro(mecanismo=[str(cd)])
        with d2:
            _cartao("Os cinco mecanismos que o projeto procura",
                    "<b>M1</b> institui política sem prazo, sanção ou orçamento.<br>"
                    "<b>M2</b> reduz proteção enquadrando como avanço "
                    "(“modernização”, “desburocratização”).<br>"
                    "<b>M3</b> revoga proteção sem nomeá-la.<br>"
                    "<b>M4</b> dispositivo ambiental nocivo enfiado em norma de outro "
                    "tema (jabuti).<br>"
                    "<b>M5</b> transfere a regra dura para instância mais fraca "
                    "(lei→decreto, controle→autodeclaração).<br><br>"
                    "Uma mesma norma pode usar mais de um mecanismo — por isso a soma das barras "
                    "passa do número de normas.",
                    viz.CORES_VEREDITO["simbolica"])
            if {"M3_revogacao_tacita", "M4_insercao_heterogenea"} & set(mec):
                st.caption("Os mecanismos M3 e M4 só podem ser apontados quando o dossiê "
                           "traz **o projeto e a lei promulgada lado a lado** — sem os "
                           "dois textos, a comparação seria conjectura, e a conferência "
                           "automática recusa a alegação.")

        # o par que mais se repete não é decoração: é a receita recorrente que o
        # conjunto revela, e ela só aparece cruzando os mecanismos entre si
        pares = Counter()
        for linha_m in ok["mecanismos"]:
            ms = sorted({m for m in str(linha_m).split(";") if m})
            for i in range(len(ms)):
                for j in range(i + 1, len(ms)):
                    pares[(ms[i], ms[j])] += 1
        if pares:
            (m_a, m_b), n_par = pares.most_common(1)[0]
            n_a = int(ok["mecanismos"].str.contains(m_a, regex=False).sum())
            n_b = int(ok["mecanismos"].str.contains(m_b, regex=False).sum())
            menor = min(n_a, n_b)
            curto = {"M1_norma_programatica_vazia": "instituir política sem prazo, "
                                                    "sanção ou orçamento",
                     "M2_reframing_de_regressao": "enquadrar a redução como avanço",
                     "M3_revogacao_tacita": "revogar proteção sem nomeá-la",
                     "M4_insercao_heterogenea": "enfiar dispositivo em norma de outro tema",
                     "M5_delegacao_desregulamentadora": "deixar a regra dura para decreto "
                                                        "ou autodeclaração"}
            st.info(
                f"**A combinação mais frequente do conjunto: {m_a.split('_')[0]} + "
                f"{m_b.split('_')[0]}, em {n_par} normas.** "
                f"*{curto.get(m_a, m_a)}* somado a *{curto.get(m_b, m_b)}* — "
                + (f"{100 * n_par / menor:.0f}% das normas que usam o mecanismo menos "
                   f"comum dos dois também usam o outro. " if menor else "")
                + "Os dois se apoiam: o reenquadramento dá a justificativa pública, e a "
                  "delegação move a decisão para onde há menos controle.")

    st.divider()

    # ── 4. honestidade: o que a plataforma faz contra si mesma ───────────────
    st.subheader("O que foi conferido")
    _cartao("O modelo tem de mostrar de onde tirou",
            "Toda afirmação relevante exige <b>citação literal</b>, e a máquina confere "
            "cada uma contra o texto oficial dentro do próprio dossiê. Citação que não "
            "existe é marcada como não localizada; se a maioria não for localizada, a "
            "análise inteira é descartada e não aparece em lugar nenhum. A conferência "
            "é feita só contra "
            "as seções de <b>documento</b> — não contra o texto que nós escrevemos no "
            "dossiê, senão o modelo poderia citar a nossa própria opinião e passar.",
            "#2a78d6")

    tot = int(ia["n_citacoes"].sum())
    if tot:
        h1, h2, h3, h4 = st.columns(4)
        anc = int(ia["n_citacoes_evidencia"].sum())
        edt = int(ia["n_citacoes_editorial"].sum())
        orf = int(ia["n_citacoes_orfas"].sum())
        h1.metric("citações verificadas", tot)
        h2.metric("localizadas no documento", f"{anc}  ({100*anc/tot:.0f}%)")
        h3.metric("vindas de texto nosso", edt,
                  help="Zero é o resultado esperado: significa que o modelo não usou "
                       "a nossa própria redação como se fosse fonte oficial.")
        h4.metric("não localizadas", f"{orf}  ({100*orf/tot:.0f}%)",
                  help="O modelo reescreveu com as próprias palavras em vez de copiar. "
                       "A afirmação continua podendo estar certa, mas deixa de ser "
                       "verificável — e por isso não é aceita como prova.")

    # A confiança é AUTO-DECLARADA e satura no topo — mostrar isso é parte da
    # honestidade da página: um número que quase nunca varia não informa, e
    # apresentá-lo como se informasse seria pior do que omiti-lo.
    conf = pd.to_numeric(ok["confianca"], errors="coerce").dropna()
    if len(conf):
        alta = int((conf >= 0.9).sum())
        if alta / len(conf) >= 0.75:
            st.warning(
                f"**O modelo quase nunca se diz inseguro.** Ele declarou confiança de "
                f"0,9 ou mais em **{alta} das {len(conf)}** leituras "
                f"({100 * alta / len(conf):.0f}%), e a menor de todas foi "
                f"{conf.min():.2f}. Um número que não varia não distingue leitura sólida "
                "de leitura frágil — por isso a confiança **não é usada** em nenhum "
                "cálculo desta página. O que serve para separar as duas é a conferência "
                "das citações, acima, que é medida contra o documento e não pelo modelo.")

    desc = ia[ia["status"] == "descartada"]
    resv = ia[ia["status"] == "com_ressalvas"]
    if len(desc) or len(resv):
        with st.expander(f"o que a conferência automática reprovou — {len(desc)} "
                         f"descartadas, {len(resv)} com ressalva"):
            st.markdown(
                "**Descartada** não entra em nenhum número desta página. "
                "**Com ressalva** entra, mas o problema fica visível no dossiê da norma.")
            vaz = ia[ia["vazamento"].astype(str).str.lower() == "true"]
            if len(vaz):
                por_origem = Counter(vaz["vazamento_origem"])
                st.markdown(
                    f"**Menção indevida à ADI ({len(vaz)}).** O dossiê é montado sem nenhuma "
                    "referência a ADI, de propósito: a ADI é o critério de conferência, "
                    "e o modelo precisa ler a norma **sem saber** se ela foi contestada. "
                    "Se a resposta fala em inconstitucionalidade, a leitura deixou de "
                    "ser às cegas e é descartada. "
                    + (f"Origem: **{por_origem.get('dossie', 0)}** repetindo o que já estava "
                       "no próprio dossiê — falha nossa: o filtro cobre os campos que "
                       "montamos, mas não o texto integral dos documentos. E "
                       f"**{por_origem.get('externo', 0)}** trazendo de fora, o que o "
                       "roteiro de análise proíbe expressamente."))
            cols = ["sapl_id", "status", "veredito", "problemas"]
            st.dataframe(pd.concat([desc, resv])[cols], width="stretch",
                         hide_index=True, height=260,
                         column_config={"problemas": st.column_config.TextColumn(
                             "o que a conferência apontou", width="large")})

    st.divider()

    # ── 5. o teste contra as ADIs, com a correção de independência ───────────
    st.subheader("Conferindo a leitura contra um critério externo")
    _cartao("Como se testa uma leitura destas",
            "Se o modelo lê bem, as normas que ele aponta como dissimuladas deveriam "
            "coincidir com normas que a Justiça já contestou. Usamos como <b>critério "
            "de conferência</b> as normas alvo de <b>Ação Direta de "
            "Inconstitucionalidade</b>: elas são a única marca externa e verificável de "
            "que houve tentativa de retrocesso.<br><br>"
            "Mas há uma armadilha de contagem. Os 11 Decretos Legislativos de 2018 "
            "saíram da <b>mesma sessão extraordinária</b>, contra decretos do mesmo "
            "pacote, e respondem a <b>uma</b> ação — são um ato fatiado em 11 peças por "
            "exigência formal. Contá-los onze vezes não apenas infla a amostra: "
            "<b>inverte a conclusão</b>. Por isso a tabela mostra as duas contagens.",
            viz.CORES_VEREDITO["retrocesso_transparente"])

    sin = fontes.sinais()
    if sin is not None and not ev.empty:
        anc = {int(r["sapl_id"]): r["ancora_adi"] for _, r in
               sin[["sapl_id", "ancora_adi"]].iterrows()}
        evd = {int(r["sapl_id"]): int(r["evento_id"]) for _, r in
               ev[["sapl_id", "evento_id"]].iterrows()}

        def _auc(p, n):
            if not p or not n:
                return None
            maior = sum(1 for a in p for b in n if a > b)
            emp = sum(1 for a in p for b in n if a == b)
            return (maior + emp / 2) / (len(p) * len(n))

        linhas = []
        for rot_s, col in (("dada pelo próprio modelo", "score_greenwashing"),
                           ("calculada dos dois eixos", "score_derivado")):
            base = ok[pd.to_numeric(ok[col], errors="coerce").notna()].copy()
            base["_v"] = pd.to_numeric(base[col])
            base = base[base["sapl_id"].isin(anc)]
            if base.empty:
                continue
            p_n = [r["_v"] for _, r in base.iterrows() if anc[int(r["sapl_id"])]]
            n_n = [r["_v"] for _, r in base.iterrows() if not anc[int(r["sapl_id"])]]
            g: dict[int, list] = {}
            for _, r in base.iterrows():
                g.setdefault(evd.get(int(r["sapl_id"]), int(r["sapl_id"])), []).append(r)
            p_e = [pd.Series([x["_v"] for x in ms]).median() for ms in g.values()
                   if any(anc[int(x["sapl_id"])] for x in ms)]
            n_e = [pd.Series([x["_v"] for x in ms]).median() for ms in g.values()
                   if not any(anc[int(x["sapl_id"])] for x in ms)]
            for rot_u, p, n in (("cada norma conta 1", p_n, n_n),
                                ("cada ato conta 1", p_e, n_e)):
                a = _auc(p, n)
                if a is not None:
                    linhas.append({"nota usada": rot_s, "contagem": rot_u,
                                   "acerto": round(a, 2),
                                   "casos comparados": f"{len(p)} contestadas × "
                                                       f"{len(n)} não contestadas"})
        if linhas:
            t = pd.DataFrame(linhas)
            st.dataframe(
                t, width="stretch", hide_index=True,
                column_config={"acerto": st.column_config.ProgressColumn(
                    "acerto na comparação", min_value=0, max_value=1, format="%.2f",
                    help="Forme todos os pares possíveis entre uma norma contestada e "
                         "uma não contestada. Em que fração deles a contestada recebeu "
                         "a nota mais alta? 0,50 é o mesmo que sortear no cara-ou-coroa; "
                         "1,00 seria separação perfeita.")})
            st.caption(
                "**Como ler a coluna de acerto.** Junte cada norma contestada com cada "
                "norma não contestada, uma a uma. Em quantos desses pares a contestada "
                "recebeu nota maior? É essa fração. **0,50 significa nenhum poder de "
                "distinguir** — o mesmo que sortear.")
            n_pos_ev = len({evd.get(int(s), int(s)) for s in ok["sapl_id"]
                            if anc.get(int(s))})
            st.warning(
                f"**O número é frágil, e isso é parte do resultado.** Existem apenas "
                f"**{n_pos_ev} atos contestados** no conjunto inteiro — Rondônia não "
                "produziu mais ADIs ambientais que isso. Reclassificar **um único** "
                f"deles muda o acerto em cerca de **{1/max(1,n_pos_ev):.2f}**, mais do "
                "que separa várias linhas desta tabela. Serve para descrever o "
                "conjunto, não para provar uma tese.")
            st.markdown(
                "**E há um limite que nenhuma amostra maior resolve.** O critério mede "
                "*ter sido contestada por ADI*, não *ser greenwashing* — são coisas "
                "diferentes. Os 11 Decretos Legislativos foram contestados, e o modelo "
                "corretamente os lê como retrocesso **assumido**, não disfarçado. "
                "Contra esse critério, acertar aparece como errar. Por isso ele serve "
                "para **reprovar** uma leitura ruim, nunca para aprovar uma boa.")

    st.divider()

    # ── 6. com o que o modelo trabalhou, e o que ficou de fora ───────────────
    st.subheader("Com que material o modelo trabalhou")
    idx_col = ia["fonte_texto"].value_counts().to_dict()
    trunc = int((ia["texto_truncado"].astype(str).str.lower() == "true").sum())
    n_ambos = idx_col.get("ambos", 0)
    n_so_lei = idx_col.get("lei", 0)
    n_so_pl = idx_col.get("pl_original", 0)

    st.markdown(
        f"Para **{n_ambos} das {len(ia)} normas**, o dossiê levou os **dois textos "
        "lado a lado**: o projeto como foi apresentado e a lei como foi promulgada. "
        "É o que permite ver o que mudou durante a tramitação — um dispositivo que "
        "aparece só na versão final não estava no projeto original, e alguém o "
        "inseriu no caminho.")
    cob = pd.DataFrame([
        {"material disponível": "projeto e lei, lado a lado", "normas": n_ambos,
         "o que permite ver": "o que mudou entre o projeto e a lei"},
        {"material disponível": "apenas a lei promulgada", "normas": n_so_lei,
         "o que permite ver": "só o resultado final, sem comparação"},
        {"material disponível": "apenas o projeto", "normas": n_so_pl,
         "o que permite ver": "só a intenção inicial; a lei pode ter mudado"},
    ])
    st.dataframe(cob[cob["normas"] > 0], width="stretch", hide_index=True)

    st.subheader("O que esta análise não alcança")
    st.markdown(
        f"**Anexos de tabela em {trunc} leis extensas.** Três leis do licenciamento "
        "ambiental passam de 80 páginas, quase todas de tabelas que classificam "
        "atividades por porte e potencial poluidor. O texto enviado ao modelo é "
        "cortado antes desses anexos. **Nenhum artigo se perde** — o corte cai "
        "inteiro sobre as tabelas —, mas uma mudança escondida numa célula (trocar "
        "uma faixa de “até 250” para “até 2.000” desregulamenta sem alterar uma "
        "vírgula do texto) fica fora do alcance desta leitura.\n\n"
        "**Documentos antigos mal digitalizados.** Os PDFs mais antigos são imagens "
        "escaneadas, e a conversão para texto erra. Numa das normas, apenas cerca de "
        "13% das palavras saem reconhecíveis — a leitura dela não é confiável, e "
        "isso está dito no dossiê dessa norma.\n\n"
        "**O veredito é de um modelo, não de um juízo.** Não é decisão judicial nem "
        "perícia técnica. Toda tela mostra qual modelo produziu a leitura e quando, "
        "e cada afirmação guarda a citação que a sustenta — para que qualquer pessoa "
        "possa conferir ou discordar com o documento na mão.")

    # ── 7. das contagens para as normas ──────────────────────────────────────
    # Um painel que só mostra agregados é uma parede: "40 indícios de
    # greenwashing" não vale nada se não der para ver QUAIS 40 e conferir uma a
    # uma. Esta seção é a ponte — recebe o clique dos gráficos acima, permite
    # filtrar à mão, e leva ao dossiê onde está a evidência.
    st.divider()
    st.subheader("Ver as normas por trás dos números")
    st.caption("Clique numa célula da matriz, numa barra de veredito ou de "
               "mecanismo para filtrar esta lista — ou use os campos abaixo. "
               "Selecionando uma linha, abre-se o dossiê completo da norma.")

    # o pedido de limpar chega como BANDEIRA, consumida aqui — antes de os
    # multiselects nascerem. Escrever direto na chave de um widget já
    # instanciado no mesmo ciclo é erro no Streamlit, e era o que o botão fazia.
    if st.session_state.pop("_limpar_filtros", False):
        for chave in FILTROS:
            st.session_state[chave] = []
    for chave in FILTROS:
        st.session_state.setdefault(chave, [])

    ROTULO_MEC = {"M1_norma_programatica_vazia": "M1 · programática vazia",
                  "M2_reframing_de_regressao": "M2 · reframing de regressão",
                  "M3_revogacao_tacita": "M3 · revogação tácita",
                  "M4_insercao_heterogenea": "M4 · inserção heterogênea",
                  "M5_delegacao_desregulamentadora": "M5 · delegação desregulamentadora"}

    g1, g2, g3, g4 = st.columns(4)
    g1.multiselect("veredito", viz.ORDEM_VEREDITO, key="f_veredito",
                   format_func=lambda v: v.replace("_", " "))
    g2.multiselect("mecanismo", list(ROTULO_MEC), key="f_mecanismo",
                   format_func=lambda m: ROTULO_MEC.get(m, m))
    g3.multiselect("retórica", viz.ORDEM_R, key="f_retorica")
    g4.multiselect("efeito", viz.ORDEM_E, key="f_efeito")

    b1, b2, b3 = st.columns([2, 2, 1])
    busca = b1.text_input("buscar na ementa ou na justificativa",
                          placeholder="ex.: licenciamento, unidade de conservação…")
    so_adi = b2.toggle("só as contestadas por ADI", value=False,
                       help="Normas alvo de Ação Direta de Inconstitucionalidade — "
                            "as que servem para conferir a leitura.")
    if b3.button("limpar filtros", width="stretch"):
        st.session_state["_limpar_filtros"] = True
        st.rerun()

    vis = ok.copy()
    if st.session_state["f_veredito"]:
        vis = vis[vis["veredito"].isin(st.session_state["f_veredito"])]
    if st.session_state["f_retorica"]:
        vis = vis[vis["retorica"].isin(st.session_state["f_retorica"])]
    if st.session_state["f_efeito"]:
        vis = vis[vis["efeito"].isin(st.session_state["f_efeito"])]
    if st.session_state["f_mecanismo"]:
        alvo = set(st.session_state["f_mecanismo"])
        vis = vis[vis["mecanismos"].map(
            lambda s: bool(alvo & {m for m in str(s).split(";") if m}))]
    if so_adi:
        sin2 = fontes.sinais()
        if sin2 is not None:
            com_adi = {int(r["sapl_id"]) for _, r in sin2.iterrows()
                       if str(r["ancora_adi"]).lower() == "true"}
            vis = vis[vis["sapl_id"].isin(com_adi)]

    vis = vis.merge(ind[["tipo", "numero", "ano", "ementa"]],
                    left_on="sapl_id", right_index=True, how="left")
    if busca.strip():
        alvo_txt = busca.strip()
        vis = vis[vis["ementa"].fillna("").str.contains(alvo_txt, case=False, regex=False)
                  | vis["justificativa"].fillna("").str.contains(alvo_txt, case=False,
                                                                 regex=False)]

    # o resumo tem de contar TODOS os filtros, inclusive busca e ADI: antes
    # dizia "nenhum filtro; mostrando todas" com 26 de 109 na tela
    ativos = [f"{c.replace('f_', '')}: " + ", ".join(st.session_state[c])
              for c in FILTROS if st.session_state[c]]
    if so_adi:
        ativos.append("só contestadas por ADI")
    if busca.strip():
        ativos.append(f"texto: “{busca.strip()}”")
    st.markdown(f"**{len(vis)} de {len(ok)} norma(s)**"
                + (f" — filtrando por {' · '.join(ativos)}" if ativos else
                   " — todas as leituras aproveitadas, sem filtro"))

    if vis.empty:
        st.info("Nenhuma norma combina com esses filtros. Use *limpar filtros* "
                "para recomeçar.")
        return

    vis = vis.sort_values("score_derivado", ascending=False, na_position="last")
    mostrar = vis.assign(
        norma=lambda d: d["tipo"].astype(str) + " " + d["numero"].astype(str)
                        + "/" + d["ano"].astype(str),
        veredito_=lambda d: d["veredito"].str.replace("_", " "),
        mecanismos_=lambda d: d["mecanismos"].map(
            lambda s: ", ".join(m.split("_")[0] for m in str(s).split(";") if m)),
    )[["sapl_id", "norma", "veredito_", "score_derivado", "mecanismos_",
       "n_citacoes_evidencia", "n_citacoes", "status", "ementa"]]

    # altura acompanha o resultado: com 1 norma filtrada, a tabela fixa em 340px
    # desenhava vinte linhas vazias e empurrava o botão do dossiê para fora da tela
    altura = min(360, 45 + 36 * max(1, len(mostrar)))
    sel = st.dataframe(
        mostrar, width="stretch", hide_index=True, height=altura,
        selection_mode="single-row", on_select="rerun", key="tab_analise",
        column_config={
            "sapl_id": st.column_config.NumberColumn("id", format="%d", width="small"),
            "norma": st.column_config.TextColumn("norma", width="medium"),
            "veredito_": st.column_config.TextColumn("veredito", width="medium"),
            "score_derivado": st.column_config.NumberColumn(
                "nota calculada", format="%.2f",
                help="Calculada dos dois eixos; 0 significa sem dissimulação."),
            "mecanismos_": st.column_config.TextColumn("mecanismos", width="small"),
            "n_citacoes_evidencia": st.column_config.NumberColumn("citações OK",
                                                                  format="%d"),
            "n_citacoes": st.column_config.NumberColumn("citações", format="%d"),
            "status": st.column_config.TextColumn("conferência", width="small"),
            "ementa": st.column_config.TextColumn("ementa", width="large"),
        })

    # A seleção de linha PERSISTE entre reruns, mas a tabela encolhe quando o
    # filtro muda: com a linha 7 marcada e um filtro que passa a devolver 2
    # normas, `iloc[7]` estoura com IndexError e derruba a página inteira. O
    # índice tem de ser conferido contra o tamanho ATUAL, não presumido válido.
    linhas = [i for i in sel.get("selection", {}).get("rows", []) if i < len(mostrar)]
    if not linhas:
        st.caption("Marque a caixa à esquerda de uma linha para abrir o dossiê "
                   "completo daquela norma — com a evidência, a votação nominal e "
                   "as citações que sustentam a leitura.")
        return

    esc = mostrar.iloc[linhas[0]]
    with st.container(border=True):
        e1, e2 = st.columns([3, 1])
        with e1:
            st.markdown(f"**{esc['norma']}** · {esc['veredito_']}")
            st.caption(str(esc["ementa"])[:320])
        with e2:
            if st.button("Abrir dossiê", type="primary", width="stretch",
                         key="ir_dossie_analise"):
                st.session_state["dossie_sapl"] = int(esc["sapl_id"])
                st.session_state["ir_para"] = "Dossiê"
                st.rerun()

    _mostrar_evidencia(int(esc["sapl_id"]))
