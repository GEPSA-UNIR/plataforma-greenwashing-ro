"""Dossiê — a história completa de uma norma, em abas.

Honestidade da tela: REGISTRADO × INFERIDO nunca se misturam; situação vem com
a regra de derivação; alertas/lacunas ficam na aba Proveniência (visíveis, com
contagem no topo); sem sinais computados, a aba Análise declara a lacuna.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import componentes
import fontes
import viz
from pg_cadeias import _componentes, dados_cadeia
from pg_mapa import _tema

SELO_REG = "REGISTRADO no SAPL"
SELO_INF = "INFERIDO da ementa (deduzido por regra automática — conferir)"

ROTULOS_SINAIS = {
    "A1_dias_pl_lei": "Velocidade PL→lei (dias)",
    "A2_urgencia": "Regime de urgência",
    "A3_parecer_plenario": "Parecer dado em plenário (sem passar pela comissão temática)",
    "A4_votacao_sem_nominal": "Votação sem registro nominal",
    "A5_unanime": "Aprovação unânime",
    "A6_sem_votacao_registrada": "Nenhuma votação registrada",
    "A7_dezembro": "Promulgada em dezembro",
    "B1_n_alvos_em_escopo": "Age sobre normas ambientais (nº de alvos)",
    "B2_verbo_supressivo": "Ato supressivo (revoga/susta/suspende)",
    "B3_reincidencia_autor": "Reincidência do autor no conjunto (nº de outras normas)",
    "B4_alvo_mais_emendado": "Mexe em lei muito emendada (nº de alterações do alvo)",
    "B5_n_alvos": "Quantidade de alvos",
    "C1_retorica_verde": "Retórica verde na ementa",
    "C2_eufemismo": "Eufemismo na ementa (moderniza/simplifica/flexibiliza…)",
    "C3_delegacao_executivo": "Delegação ao Executivo na ementa",
    "C4_n_revogacoes": "Revogações citadas na ementa (nº)",
}


def _rotulo_outra(o: dict | None) -> str:
    if not o:
        return "—"
    return f"{o.get('tipo')} {o.get('numero')}/{o.get('ano')} (sapl {o.get('sapl_id')})"


def _aba_resumo(f: dict, r: pd.Series) -> None:
    ident, origem = f["identificacao"], f.get("origem") or {}
    st.markdown(f"> {ident.get('ementa') or '—'}")
    CURTO = {"vigente (presumida)": "vigente", "alterada por outra norma": "alterada",
             "revogada/suspensa": "revogada/susp.", "com ADI": "com ADI"}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("situação", CURTO.get(r["categoria"], r["categoria"]),
              help=f"{r['categoria']} — derivação explicada logo abaixo")
    c2.metric("PL→lei", f"{int(r['dias_pl_lei'])} dias" if pd.notna(r["dias_pl_lei"]) else "—",
              help="da apresentação da matéria à data da norma")
    c3.metric("age sobre", int(r["n_age_sobre"]), help="vínculos ativos (registrados + inferidos)")
    c4.metric("sofre ação de", int(r["n_sofre"]), help="vínculos passivos (registrados + inferidos)")
    st.caption(f"como a situação foi derivada: {(f.get('situacao_derivada') or {}).get('regra', '?')}")

    if origem.get("tem_materia"):
        autores = ", ".join(
            a.get("nome", "?") + (f" ({a['partido_na_epoca']} à época)" if a.get("partido_na_epoca") else "")
            for a in origem.get("autores") or []) or "—"
        desc = (origem.get("descricao") or "").strip()
        if str(origem.get("numero") or "") not in desc:
            desc = f"{desc} {origem.get('numero')}/{origem.get('ano')}".strip()
        st.markdown(f"**origem:** {desc} "
                    f"· apresentada em {origem.get('data_apresentacao') or '?'}  \n"
                    f"**autoria:** {autores}")
    else:
        st.markdown("_matéria de origem não vinculada no SAPL (lacuna comum antes de 2010)_")

    const = f.get("constitucionalidade") or {}
    if const.get("declarada_inconstitucional"):
        st.error(f"Declarada inconstitucional — abrangência: {const.get('abrangencia') or '?'}")
    for ax in const.get("anexos_adi") or []:
        st.markdown(f"ADI anexada: *{ax.get('assunto', '?')}* "
                    + (f"([documento]({ax['arquivo_url']}))" if ax.get("arquivo_url") else ""))

    acess = (f.get("acessorios_da_materia") or {}).get("itens") or []
    trans = [i for i in acess if i.get("categoria") == "transcricao_plenario"]
    for t in trans:
        st.markdown(f"**Nota taquigráfica** ({t.get('data') or 's/ data'}): o parecer foi dado "
                    "diretamente EM PLENÁRIO, sem passar pela comissão temática — "
                    "indício de que a análise técnica foi abreviada "
                    + (f"([abrir]({t['arquivo_url']}))" if t.get("arquivo_url") else ""))

    b1, b2 = st.columns(2)
    b1.link_button("Página no SAPL", ident.get("url_sapl") or "https://sapl.al.ro.leg.br")
    url_pdf = ((f.get("textos") or {}).get("lei") or {}).get("url")
    if url_pdf:
        b2.link_button("Texto integral (PDF)", url_pdf)


def _aba_votacao(sapl_id: int) -> None:
    vot = fontes.votacoes()
    nom = fontes.votos_nominais()
    minhas = vot[vot["norma_sapl_id"] == sapl_id] if not vot.empty else pd.DataFrame()
    if minhas.empty:
        st.info("nenhuma votação registrada no SAPL para a matéria desta norma — "
                "pode ser aprovação simbólica ou lacuna do registro; a fonte não distingue.")
        return
    for _, v in minhas.iterrows():
        st.markdown(f"**{v['data'] or 's/ data'}** — {v['resultado'] or 'resultado não registrado'}")
        # contexto da sessão: a data vem da ordem do dia (coletar_sessoes.py), não
        # do carimbo de inserção do SAPL — quando cai no carimbo, isso é dito.
        def _tem(campo: str) -> bool:
            """Valor presente de verdade. `NaN or ''` devolveria NaN, que é
            truthy — daria 'iniciada nan' na tela."""
            x = v.get(campo)
            return pd.notna(x) and str(x).strip() != ""

        ctx = []
        if _tem("sessao_tipo"):
            ctx.append(str(v["sessao_tipo"])
                       + (f" nº {int(v['sessao_numero'])}" if _tem("sessao_numero") else ""))
        if _tem("sessao_hora"):
            ctx.append(f"iniciada {v['sessao_hora']}")
        if _tem("presentes"):
            ctx.append(f"quórum {int(v['presentes'])}")
        elif _tem("sessao_sapl_id"):
            ctx.append("presença não registrada no SAPL")
        if v.get("origem_data") and v["origem_data"] != "sessao":
            ctx.append("ATENÇÃO: data do carimbo de inserção, não da sessão")
        if ctx:
            st.caption(" · ".join(ctx))
        c1, c2, c3 = st.columns(3)
        c1.metric("Sim", int(v["votos_sim"]))
        c2.metric("Não", int(v["votos_nao"]))
        c3.metric("Abstenções", int(v["abstencoes"]))
        meus = nom[(nom["norma_sapl_id"] == sapl_id)
                   & (nom["votacao_sapl_id"] == v["votacao_sapl_id"])] if not nom.empty else pd.DataFrame()
        if meus.empty:
            st.caption("sem registro nominal desta votação no SAPL (só o placar) — "
                       "voto simbólico/sem painel é em si um dado de processo.")
        else:
            st.plotly_chart(viz.fig_votacao_partidos(meus, _tema()),
                            key=f"vot_{sapl_id}_{v['votacao_sapl_id']}")
            with st.expander("votos nominais (tabela)"):
                st.dataframe(meus[["parlamentar", "partido_na_epoca", "voto"]].rename(
                    columns={"partido_na_epoca": "partido à época"}),
                    width="stretch", hide_index=True)


def _bloco_evento(sapl_id: int) -> None:
    """A norma é um ato inteiro ou uma peça de um ato maior?

    Vem de data/eventos/eventos_normas.csv. Não é adorno: é a diferença entre
    ler o Decreto Legislativo 790/2018 como uma decisão e lê-lo como 1 de 11
    peças da MESMA decisão, votadas na mesma sessão extraordinária.
    """
    ev = fontes.eventos()
    if ev.empty:
        return
    minha = ev[ev["sapl_id"] == sapl_id]
    if minha.empty:
        return
    r = minha.iloc[0]
    if int(r["tamanho_evento"]) <= 1:
        st.caption("Ato legislativo: **esta norma sozinha** — nenhuma outra do "
                   "conjunto a altera, é alterada por ela, ou foi votada na mesma sessão.")
        return

    ind = fontes.indicadores().set_index("sapl_id")

    def _rot(x: int) -> str:
        if x not in ind.index:
            return f"sapl {x}"
        h = ind.loc[x]
        return f"{h['tipo']} {h['numero']}/{h['ano']}"

    irmas = ev[(ev["evento_id"] == r["evento_id"]) & (ev["sapl_id"] != sapl_id)]
    st.warning(
        f"**Esta norma é 1 de {int(r['tamanho_evento'])} de um mesmo ato legislativo.** "
        f"Ler o veredito dela isoladamente pode enganar: o que essas normas fazem, "
        f"fazem juntas.")
    por_sessao = [int(x) for x in str(r["companheiros_sessao"]).split(";") if x]
    if por_sessao:
        quando = r["data_votacao"] or "s/ data"
        st.markdown(f"Votada em **{quando}** ({r['sessao_tipo']}"
                    + (f", quórum {r['presentes']}" if str(r["presentes"]) else "")
                    + f") junto com **{len(por_sessao)}** outra(s) do conjunto — "
                      "mesma sessão, mesmo ato de votar.")
    with st.expander(f"as outras {len(irmas)} normas deste ato"):
        st.dataframe(pd.DataFrame([
            {"norma": _rot(int(x["sapl_id"])),
             "ligada por": {"cadeia": "cadeia jurídica", "sessao": "mesma sessão",
                            "cadeia+sessao": "cadeia + mesma sessão"}.get(x["motivo"],
                                                                          x["motivo"]),
             "votada em": x["data_votacao"] or "—",
             "ementa": (ind.loc[int(x["sapl_id"]), "ementa"][:140]
                        if int(x["sapl_id"]) in ind.index else "")}
            for _, x in irmas.iterrows()]), width="stretch", hide_index=True)
    st.caption("Duas normas contam como **um mesmo ato** quando uma altera a outra "
               "ou quando as duas foram aprovadas na mesma sessão plenária. A regra é "
               "automática e igual para todas — não há escolha caso a caso.")
    st.divider()


def _aba_cadeia(sapl_id: int) -> None:
    from pg_mapa import painel_norma, sapl_do_evento
    _bloco_evento(sapl_id)
    comp = next((c for c in _componentes() if sapl_id in c["membros"]), None)
    if comp is None:
        st.info("esta norma não participa de nenhuma cadeia de atos nos grafos gerados "
                "(nenhum vínculo de ação registrado ou inferido).")
        return
    sub_n, sub_a = dados_cadeia(comp["membros"])
    st.caption(f"{comp['rotulo']} · setas cheias = registrado · tracejadas = inferido · "
               "nó destacado = esta norma")
    ev = st.plotly_chart(viz.fig_cadeia(sub_n, sub_a, _tema(), centro=sapl_id),
                         on_select="rerun", selection_mode="points", key=f"dcadeia_{sapl_id}")
    sid = sapl_do_evento(ev)
    if sid is not None and sid != sapl_id:
        painel_norma(sid)


def _aba_linha_tempo(f: dict) -> None:
    lt = f.get("linha_do_tempo") or []
    if not lt:
        st.markdown("_sem eventos_")
        return
    st.dataframe(pd.DataFrame([{"data": e.get("data") or "s/ data", "evento": e.get("evento"),
                                "detalhe": e.get("detalhe"), "fonte": e.get("_fonte")}
                               for e in lt]), width="stretch", hide_index=True)


def _aba_proveniencia(f: dict) -> None:
    rel = f.get("relacoes") or {}
    st.markdown("#### De onde vêm os dados desta norma")
    st.caption("Esta aba existe para que nada seja aceito só porque a tela mostrou: "
               "aqui ficam a origem de cada vínculo, o que foi deduzido em vez de "
               "registrado, e o que **não** se sabe.")
    if rel.get("_definicao"):
        st.caption(f"Alcance das relações listadas: {rel['_definicao']}")
    for chave, titulo, selo in (("ativas", "esta norma AGE sobre", SELO_REG),
                                ("passivas", "AGEM sobre esta norma", SELO_REG),
                                ("correlatas", "correlatas (sem ação)", SELO_REG),
                                ("ativas_inferidas", "citações ativas na ementa", SELO_INF),
                                ("passivas_inferidas", "citada por outras ementas", SELO_INF)):
        itens = rel.get(chave) or []
        if not itens:
            continue
        st.markdown(f"**{titulo}** — {selo}")
        for it in itens:
            verbo = it.get("verbo_na_ementa") or it.get("verbo_na_ementa_do_agente")
            partes = []
            if it.get("rotulo") and "citacao" not in it:
                partes.append(f"- **{it['rotulo']}** → {_rotulo_outra(it.get('outra'))}")
            else:
                partes.append(f"- cita *{it.get('citacao', '?')}*")
                if it.get("outra"):
                    partes.append(f"→ {_rotulo_outra(it['outra'])}")
            if verbo:
                partes.append(f"(verbo: **{verbo}**)")
            for k, pref in (("ambiguidade", "[?]"), ("nao_encontrada", "[?]"), ("sugestao", "[sugestão]")):
                if it.get(k):
                    partes.append(f"{pref} {it[k]}")
            st.markdown(" ".join(partes))

    if f.get("alertas"):
        st.markdown("##### Pontos a conferir nesta ficha")
        for a in f["alertas"]:
            st.warning(a)
    if f.get("lacunas_desta_versao"):
        # uma lacuna por linha. Antes iam todas emendadas por " · " num bloco só:
        # cinco afirmações distintas viravam um parágrafo corrido, e a mais
        # importante ("a situação é DERIVADA, não verificada") ficava no meio,
        # indistinguível das outras. Lista separa o que é separado.
        st.markdown("##### O que esta ficha NÃO sabe")
        st.caption("Declarado de propósito: o que falta é tão parte do resultado "
                   "quanto o que foi encontrado.")
        for lac in f["lacunas_desta_versao"]:
            texto = str(lac).strip()
            titulo, _, resto = texto.partition(":")
            if resto.strip():
                st.markdown(f"- **{titulo.strip()}** — {resto.strip()}")
            else:
                st.markdown(f"- {texto}")


def render() -> None:
    st.header("Dossiê da norma")
    st.caption("Uma norma por inteiro: origem, processo legislativo, votação "
               "nominal, cadeia de alterações e a leitura por IA. Escolha abaixo — "
               "dá para digitar por número ou por assunto.")
    disponiveis = fontes.fichas_existentes()
    if not disponiveis:
        st.error("nenhuma ficha em data/fichas/ — rode scripts/gerar_ficha_norma.py")
        return
    ind = fontes.indicadores().set_index("sapl_id")

    # a lista é o conjunto de análise (normas ambientais de 2010 em diante),
    # fichas de contexto (pré-2010/amostra) só entram quando navegadas via cadeia
    opcoes = [int(s) for s in
              ind[ind["na_analise"]].sort_values(["ano", "data"], ascending=False).index
              if int(s) in disponiveis]
    padrao = st.session_state.get("dossie_sapl")
    if padrao in disponiveis and padrao not in opcoes:
        opcoes = [padrao] + opcoes

    def _fmt(sid: int) -> str:
        # a ementa entra no rótulo porque a busca do selectbox filtra pelo texto
        # EXIBIDO: sem ela só se acha por número, e ninguém lembra que a lei do
        # licenciamento é a 3.686/2015. Com ela, digitar "licenciamento" acha.
        if sid in ind.index:
            r = ind.loc[sid]
            extra = "" if bool(r["na_analise"]) else " · fora do conjunto"
            em = " ".join(str(r["ementa"] or "").split())
            return (f"{r['tipo']} {r['numero']}/{r['ano']} · {r['categoria']}{extra}"
                    + (f" — {em[:90]}" if em else ""))
        return f"sapl {sid}"

    idx = opcoes.index(padrao) if padrao in opcoes else 0
    # rótulo VISÍVEL e escrito no imperativo: o campo é um selectbox, que aceita
    # digitação para filtrar, mas nada na aparência dele diz isso — o chevron
    # sozinho lê como "escolha de lista". Sem o rótulo, o recurso existe e
    # ninguém usa.
    sid = st.selectbox("Digite para buscar — número da lei, tipo ou assunto",
                       opcoes, index=idx, format_func=_fmt,
                       help="Exemplos: 3686 · licenciamento · unidade de conservação "
                            "· Decreto Legislativo")
    st.session_state["dossie_sapl"] = sid

    f = fontes.ficha(sid)
    if f is None or sid not in ind.index:
        st.error(f"ficha_{sid}.json não encontrada")
        return
    r = ind.loc[sid]
    ident = f["identificacao"]
    # subheader, não header: o título da PÁGINA já foi dado acima; este é o nome
    # da norma escolhida, um nível abaixo na hierarquia
    st.subheader(f"{ident['tipo']} nº {ident['numero']}/{ident['ano']}")
    n_avisos = int(r["n_alertas"]) + len(f.get("lacunas_desta_versao") or [])

    abas = st.tabs(["Resumo", "Cadeia", "Votação", "Linha do tempo",
                    f"Proveniência{f' ({n_avisos})' if n_avisos else ''}", "Indícios e leitura"])
    with abas[0]:
        _aba_resumo(f, r)
    with abas[1]:
        _aba_cadeia(sid)
    with abas[2]:
        _aba_votacao(sid)
    with abas[3]:
        _aba_linha_tempo(f)
    with abas[4]:
        _aba_proveniencia(f)
    with abas[5]:
        # Duas camadas epistemicamente distintas moravam nesta aba separadas só
        # por um traço horizontal: fato apurado do registro oficial e juízo de
        # modelo. A separação é o eixo do projeto — a hierarquia da tela tem de
        # dizê-la, não só o texto corrido.
        st.markdown("### Fatos do processo legislativo")
        sin = fontes.sinais()
        if sin is None:
            st.info("Os indicadores de processo legislativo ainda não foram calculados "
                    "para o conjunto — sem o cálculo, não há o que mostrar aqui.")
        else:
            linha = sin[sin["sapl_id"] == sid]
            if linha.empty:
                st.info("Esta norma entrou no conjunto depois do último cálculo de "
                        "indicadores — por isso ela ainda não tem os dados desta aba.")
            else:
                import json as _json
                r_s = linha.iloc[0]
                st.caption("Fatos do processo legislativo extraídos do registro oficial — "
                           "por exemplo, quantos dias o projeto levou até virar lei, se "
                           "houve votação nominal, se o parecer foi dado em plenário. "
                           "São **indícios**, não veredito: a leitura do que significam "
                           "está na seção seguinte.")
                if not bool(r_s.get("conjunto_analise", True)):
                    st.caption("Norma de contexto, fora do recorte principal — os fatos do "
                               "processo dela são reais, mas ela não entra nas contagens "
                               "nem na conferência.")
                if bool(r_s.get("ancora_adi")):
                    st.markdown("**Esta norma foi contestada por ADI.** Ela é usada para "
                                "*conferir* a leitura da IA, não para julgá-la: é por "
                                "isso que o dossiê enviado ao modelo omite qualquer "
                                "menção à ação.")
                evid = _json.loads(r_s.get("evidencias") or "{}")
                cols_sinais = [c for c in sin.columns
                               if c not in ("sapl_id", "tipo", "numero", "ano",
                                            "conjunto_analise", "ancora_adi", "evidencias")]
                ligados: list[tuple[str, float | None]] = []
                for c in cols_sinais:
                    v = r_s[c]
                    if pd.isna(v):
                        continue
                    if sin[c].dtype == bool:
                        if bool(v):
                            ligados.append((c, None))
                    elif float(v) > 0:
                        ligados.append((c, float(v)))
                if not ligados:
                    st.markdown("_nenhum sinal ligado para esta norma_")
                for c, v in ligados:
                    nome = ROTULOS_SINAIS.get(c, c)
                    rotulo = f"**{nome}**" if v is None else f"**{nome}**: {v:g}"
                    ev_txt = evid.get(c.split("_")[0], "")
                    st.markdown(f"- {rotulo}" + (f" — {ev_txt}" if ev_txt else ""))
                with st.expander("todos os sinais (tabela completa)"):
                    tabela = linha[["sapl_id"] + cols_sinais].T.astype(str)
                    tabela.index = [ROTULOS_SINAIS.get(i, i) for i in tabela.index]
                    st.dataframe(tabela, width="stretch")

        st.divider()
        st.markdown("### Leitura por IA — *juízo de modelo, não fato*")
        ia = fontes.analise_ia()
        if ia is None:
            st.caption("A leitura por IA ainda não foi executada para o conjunto.")
        else:
            l_ia = ia[ia["sapl_id"] == sid]
            if l_ia.empty:
                st.caption("Esta norma ainda não passou pela leitura por IA.")
            else:
                r_ia = l_ia.iloc[0]
                if r_ia["status"] == "descartada":
                    st.warning("A leitura desta norma foi **descartada** pela conferência "
                               f"automática e por isso não é exibida. Motivo: "
                               f"{r_ia['problemas']}")
                else:
                    st.caption(f"Modelo {r_ia['modelo']} · roteiro de análise "
                               f"{r_ia['prompt_versao']} · {str(r_ia['quando'])[:10]}")
                    st.markdown(f"**veredito:** {r_ia['veredito']} · "
                                f"retórica {r_ia['retorica']} × efeito {r_ia['efeito']}"
                                + (f" · mecanismos: {r_ia['mecanismos']}" if r_ia["mecanismos"] else ""))
                    # DOIS scores lado a lado, de propósito: o do modelo é
                    # auto-relato sem escala calibrada (o prompt não dá rubrica);
                    # o derivado é R×E por tabela declarada. Mostrar só um deles
                    # esconderia de onde o número vem.
                    c1, c2 = st.columns(2)
                    c1.metric("nota calculada", r_ia["score_derivado"] or "—",
                              help="Calculada a partir dos dois eixos por uma tabela "
                                   "fixa e pública: quanto maior a retórica ambiental "
                                   "E maior o dano ao efeito, maior a nota. Qualquer "
                                   "pessoa refaz a conta e chega ao mesmo número.")
                    c2.metric("nota dada pelo modelo", r_ia["score_greenwashing"] or "—",
                              help="O quanto o próprio modelo diz estar convencido de que há "
                                   "dissimulação. Não seguimos nenhuma régua definida, "
                                   "então este número não é comparável entre normas — "
                                   "fica ao lado do calculado justamente para se poder "
                                   "ver quando os dois discordam.")
                    dif = str(r_ia.get("divergencia_score", ""))
                    if dif not in ("", "None") and float(dif) >= 0.2:
                        st.caption(
                            f"As duas notas diferem em **{float(dif):.2f}** — o modelo "
                            "avaliou de forma "
                            + ("mais severa" if float(r_ia["score_greenwashing"] or 0)
                               > float(r_ia["score_derivado"] or 0) else "mais branda")
                            + " do que os próprios eixos que ele atribuiu indicariam.")
                    st.markdown(r_ia["justificativa"])
                    if r_ia["status"] == "com_ressalvas":
                        st.caption(f"Ressalvas da conferência automática: {r_ia['problemas']}")
                    if r_ia["lacunas"]:
                        st.caption(f"O que o modelo declarou que faltou para decidir melhor: "
                                   f"{r_ia['lacunas']}")
                    st.caption(
                        f"**{r_ia['n_citacoes_evidencia']}** de {r_ia['n_citacoes']} citações "
                        "foram localizadas, palavra por palavra, no documento oficial"
                        + (f" · {r_ia['n_citacoes_editorial']} vieram de texto escrito por nós, "
                           "não do documento"
                           if int(r_ia["n_citacoes_editorial"] or 0) else "")
                        + (f" · {r_ia['n_citacoes_orfas']} não foram encontradas"
                           if int(r_ia["n_citacoes_orfas"] or 0) else "")
                        + " · analisada com "
                        + {"ambos": "o projeto e a lei promulgada",
                           "lei": "apenas o texto da lei",
                           "pl_original": "apenas o texto do projeto",
                           "nenhum": "nenhum texto integral"}.get(
                              str(r_ia["fonte_texto"]), str(r_ia["fonte_texto"]))
                        # o CSV grava "true"/"false"; o pandas converte para bool.
                        # comparar com a string faria o aviso nunca aparecer
                        + (" (TRUNCADO)"
                           if str(r_ia["texto_truncado"]).lower() == "true" else ""))

                    componentes.mostrar_evidencia(sid)
