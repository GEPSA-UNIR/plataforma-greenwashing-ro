"""Blocos de interface usados por mais de uma página.

Existe porque `fontes.py` é contrato de dados e `viz.py` é figura plotly —
nenhum dos dois é lugar para um componente de tela. Sem este módulo, a
alternativa seria uma página importar a outra, e as duas passariam a depender
da ordem em que o `app.py` as carrega.
"""

from __future__ import annotations

import streamlit as st

import fontes

# As seções do dossiê que contam como DOCUMENTO. Citação vinda de fora delas
# saiu do texto editorial que nós mesmos escrevemos, e não da fonte oficial —
# é a distinção que o validador usa para aceitar ou não a citação como prova.
SECOES_CITAVEIS = ("## Ementa", "## Texto integral da LEI", "## Texto integral da norma",
                   "## Texto do PROJETO original", "## Transcrição da sessão plenária")


def mostrar_evidencia(sapl_id: int) -> None:
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
        """O prefixo 'fonte:' não é enfeite: sem ele o rótulo fica sozinho embaixo
        da citação, em cinza-azulado de corpo pequeno, e lê como link — que ele
        não é. Com o prefixo, lê como metadado, que é o que ele é."""
        return "fonte: " + ("documento oficial" if secao.startswith(SECOES_CITAVEIS)
                            else f"seção declarada — {secao}" if secao
                            else "seção não declarada")

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
        # Sem "lá em cima": o bloco aparece em duas páginas, e a contagem fica
        # em lugares diferentes em cada uma.
        st.caption("Os trechos acima foram copiados pelo modelo do dossiê e "
                   "reconferidos, palavra por palavra, contra o documento oficial. "
                   "Divergiu? Vira citação não localizada, e entra na contagem "
                   "de conferência.")
