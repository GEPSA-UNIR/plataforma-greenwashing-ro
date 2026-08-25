"""Plataforma Interativa para Detecção de Greenwashing Legislativo Ambiental — RO.

Plataforma SOMENTE-LEITURA: nenhum input grava nada; ela apenas apresenta o que
a esteira produziu (fontes.py). Rodar de dentro de plataforma/:

    uv run streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Greenwashing Legislativo", page_icon="🌳",
                   layout="wide")

# A plataforma roda embarcada em iframe estreito no portal: cada pixel de respiro
# custa conteúdo. Encolhe as margens do bloco central e a largura da barra lateral
# sem esconder o cabeçalho (é ele que traz o botão de reabrir a lateral).
#
# O menu continua sendo um st.radio POR BAIXO — é ele que guarda o estado da
# página e permite a navegação programática (botão "abrir dossiê" escreve o
# destino em session_state). O CSS só troca a aparência: some com a bolinha do
# rádio e transforma cada opção num item de lista com destaque no ativo. Trocar
# por botões quebraria o estado; trocar por st.navigation exigiria reescrever as
# páginas como arquivos de rota.
st.markdown("""
<style>
  .block-container {padding: 1.2rem 1.5rem 1rem !important; max-width: 100% !important;}
  section[data-testid="stSidebar"] {width: 17.5rem !important; min-width: 17.5rem !important;}
  section[data-testid="stSidebar"] > div {padding-top: 1rem;}

  /* menu lateral como lista de navegação */
  section[data-testid="stSidebar"] div[role="radiogroup"] {gap: .1rem !important;}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label {
      width: 100%; padding: .45rem .7rem; margin: 0; border-radius: 7px;
      cursor: pointer; transition: background .12s ease;
  }
  /* a bolinha do rádio */
  section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
      display: none !important;
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] > label p {
      font-size: .95rem !important; line-height: 1.35;
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
      background: rgba(42,120,214,.07);
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
      background: rgba(42,120,214,.13);
  }
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
      font-weight: 600 !important; color: #1a5fb4 !important;
  }

  /* Índice da página Análise: são links de âncora de verdade — botão do
     Streamlit não navega para fragmento, e link_button abriria fora da página.
     O CSS só lhes dá aparência de botão; se esta regra sumir numa atualização,
     continuam links funcionando, só que sublinhados. */
  .st-key-indice_analise a {
      display: inline-block; text-decoration: none !important;
      border: 1px solid rgba(42,120,214,.35); border-radius: 6px;
      padding: .18rem .6rem; margin: 0 .35rem .4rem 0;
      font-size: .87rem; line-height: 1.5; color: #1a5fb4 !important;
      background: rgba(42,120,214,.05); transition: background .12s ease;
  }
  .st-key-indice_analise a:hover,
  .st-key-indice_analise a:focus-visible {
      background: rgba(42,120,214,.16); border-color: rgba(42,120,214,.6);
  }

  /* Campos de escolha de norma/cadeia aceitam DIGITAÇÃO para filtrar, mas o
     widget não mostra isso: com um chevron à direita e nada mais, ele lê como
     lista fechada e o recurso passa despercebido. A lupa à esquerda é o sinal
     convencional de "aqui se digita" — SVG embutido, sem arquivo externo.
     O sinal PRINCIPAL, porém, é o rótulo escrito ("Digite para buscar…"): esta
     regra depende da estrutura interna do Streamlit, que muda sem aviso. A
     versão anterior mirava `div[data-baseweb="select"]`, atributo que o
     Streamlit 1.59 deixou de emitir — a lupa simplesmente não aparecia, e nada
     quebrava para avisar. Se sumir de novo, o rótulo continua dizendo tudo. */
  div[data-testid="stSelectbox"] > div:last-child,
  div[data-testid="stMultiSelect"] > div:last-child { position: relative; }
  div[data-testid="stSelectbox"] > div:last-child::before,
  div[data-testid="stMultiSelect"] > div:last-child::before {
      content: ""; position: absolute; left: 12px; top: 50%;
      transform: translateY(-50%); width: 16px; height: 16px;
      z-index: 3; pointer-events: none; opacity: .75;
      background: url("data:image/svg+xml;utf8,\
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' \
stroke='%23667085' stroke-width='2.2' stroke-linecap='round'>\
<circle cx='11' cy='11' r='7'/><path d='M20 20l-4.2-4.2'/></svg>") no-repeat center / contain;
  }
  div[data-testid="stSelectbox"] > div:last-child > div,
  div[data-testid="stMultiSelect"] > div:last-child > div { padding-left: 26px; }
</style>
""", unsafe_allow_html=True)

import pg_analise
import pg_cadeias
import pg_dossie
import pg_mapa
import pg_normas

PAGINAS = {
    "Análise": pg_analise,
    "Explorar": pg_mapa,
    "Cadeias": pg_cadeias,
    "Dossiê": pg_dossie,
    "Tabela": pg_normas,
}

st.sidebar.markdown("#### Detecção de Greenwashing Legislativo Ambiental")
st.sidebar.caption("Rondônia · PVC1813-2025 · UNIR · dados: SAPL/ALE-RO")

# navegação programática ("abrir dossiê"): o destino é consumido ANTES de o
# radio nascer — escrever na key dele depois de instanciado é proibido
destino = st.session_state.pop("ir_para", None)
if destino in PAGINAS:
    st.session_state["pagina"] = destino

pagina = st.sidebar.radio("página", list(PAGINAS), key="pagina",
                          label_visibility="collapsed")

# Aberto por padrão: é aqui que está a definição sem a qual a plataforma
# inteira é ilegível — que greenwashing é a DISTÂNCIA entre o que a norma diz
# e o que faz. Fechado, o conceito central dependia de curiosidade.
with st.sidebar.expander("o que é este trabalho", expanded=True):
    st.markdown(
        "**Greenwashing legislativo** é a distância entre o que uma norma "
        "*diz ser* e o que ela *faz*. Uma lei que retira proteção ambiental de "
        "forma explícita é retrocesso — grave, mas transparente. Greenwashing "
        "exige **disfarce**: retórica ambiental cobrindo efeito que enfraquece.\n\n"
        "A plataforma percorre as normas ambientais de Rondônia a partir do "
        "**SAPL da Assembleia Legislativa**, monta um dossiê de evidência por "
        "norma (ementa, tramitação, votação nominal, texto do projeto e da lei) "
        "e submete cada dossiê a uma leitura por IA que precisa **citar "
        "literalmente** o que afirma.\n\n"
        "**Ela não decide nada.** Nenhum veredito é definitivo: cada afirmação "
        "vem com a citação que a sustenta e com o rótulo de qual modelo a "
        "produziu.")

with st.sidebar.expander("glossário"):
    st.markdown(
        "**Dossiê** — o conjunto de evidências reunido sobre uma norma: ementa, "
        "tramitação, votação nominal, texto do projeto e da lei. É o único "
        "material que a IA recebe; ela não consulta mais nada.\n\n"
        "**Retórica (eixo)** — o quanto a norma *se apresenta* como ambiental, "
        "na ementa, na justificativa e na fala dos parlamentares.\n\n"
        "**Efeito (eixo)** — o que os dispositivos *fazem* com o nível de "
        "proteção: fortalecem, mantêm ou enfraquecem.\n\n"
        "**Ato** — normas que alteram umas às outras, ou aprovadas "
        "na mesma sessão plenária, contam como **um caso só**.\n\n"
        "**Citação conferida** — trecho que a IA afirmou ter copiado e que a "
        "máquina reencontrou, palavra por palavra, no documento oficial.\n\n"
        "**Acerto na comparação** — junte cada norma contestada por ADI com cada "
        "não contestada. Em quantos desses pares a contestada recebeu nota maior? "
        "**0,50 é o mesmo que sortear**; 1,00 seria separação perfeita.\n\n"
        "**SAPL** — Sistema de Apoio ao Processo Legislativo, o sistema oficial "
        "da Assembleia de onde vêm todos os dados.")

with st.sidebar.expander("como ler os números"):
    st.markdown(
        "**Um ato, não várias normas.** Os 11 Decretos Legislativos de 2018 "
        "saíram da mesma sessão extraordinária: são um ato fatiado em 11 peças "
        "por exigência formal. Contá-los onze vezes distorce qualquer "
        "comparação — por isso a unidade de contagem é o **ato**.\n\n"
        "**A ADI serve para conferir, não para acusar.** Normas contestadas por "
        "Ação Direta de Inconstitucionalidade são a marca externa que usamos "
        "para testar se a leitura da IA faz sentido. Por isso o dossiê enviado "
        "ao modelo omite **qualquer menção a ADI**: ele precisa ler às cegas. Se "
        "a resposta falar nisso, a leitura é descartada.\n\n"
        "**Registrado ≠ inferido.** O vínculo entre normas no SAPL é digitado à "
        "mão e falta muito. O que veio do registro e o que foi deduzido da "
        "ementa aparecem **sempre com rótulos separados**.")

PAGINAS[pagina].render()
