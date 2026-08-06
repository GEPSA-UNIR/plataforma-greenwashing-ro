"""Figuras plotly da plataforma — paleta validada (skill dataviz, jul/2026).

Categorias de situação: cor + SÍMBOLO próprios (identidade nunca só por cor).
Conjunto {azul, aqua, vermelho-crítico} passou o validador all-pairs nos dois
temas; cinza = neutro deliberado (norma revogada recua) com símbolo quadrado.
Votação usa o par divergente azul↔vermelho com neutros cinza.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

CAT_ORDEM = ["vigente (presumida)", "alterada por outra norma", "revogada/suspensa", "com ADI"]
_CORES = {
    "light": {"vigente (presumida)": "#2a78d6", "alterada por outra norma": "#1baf7a",
              "revogada/suspensa": "#898781", "com ADI": "#d03b3b",
              "Sim": "#2a78d6", "Não": "#d03b3b", "Abstenção": "#52514e",
              "Ausente/Não votou": "#c3c2b7",
              "aresta": "#c3c2b7", "aresta_inferida": "#eda100", "ink": "#0b0b0b"},
    "dark": {"vigente (presumida)": "#3987e5", "alterada por outra norma": "#199e70",
             "revogada/suspensa": "#898781", "com ADI": "#d03b3b",
             "Sim": "#3987e5", "Não": "#d03b3b", "Abstenção": "#c3c2b7",
             "Ausente/Não votou": "#52514e",
             "aresta": "#52514e", "aresta_inferida": "#c98500", "ink": "#ffffff"},
}
SIMBOLOS = {"vigente (presumida)": "circle", "alterada por outra norma": "diamond",
            "revogada/suspensa": "square", "com ADI": "x"}


def cores(tema: str) -> dict:
    return _CORES["dark" if tema == "dark" else "light"]


def _jitter(sapl_id: int) -> float:
    """Deslocamento pseudoaleatório estável, para pontos que NÃO colidem."""
    return ((sapl_id * 37) % 100) / 100 * 0.80 - 0.40


def _y_por_norma(df: pd.DataFrame, ypos: dict[str, int], n_tipos: int) -> dict[int, float]:
    """Posição vertical de cada norma, garantindo alvo de clique separável.

    Só na VERTICAL: o eixo x é a data e não pode ser mexido — os 11 Decretos
    Legislativos de 2018 saíram todos no mesmo dia, e espalhá-los na horizontal
    faria a figura afirmar datas que não existem.

    Quem cai na MESMA data e no mesmo tipo é distribuído por igual dentro da
    faixa, e não por dispersão aleatória: com hash, dois dos onze Decretos
    ficavam a 3 pixels um do outro enquanto o marcador tem 13 — na prática um
    ponto só, e o clique virava loteria. A distribuição uniforme garante a maior
    distância possível para o número de pontos que ali existe. Quem não colide
    mantém o deslocamento pseudoaleatório, que evita a fileira rígida.
    """
    out: dict[int, float] = {}
    for (tipo, data), g in df.groupby(["tipo", "data"], dropna=False):
        base = ypos.get(tipo, n_tipos)
        ids = sorted(int(s) for s in g["sapl_id"])
        if len(ids) == 1:
            out[ids[0]] = base + _jitter(ids[0])
            continue
        passo = 0.80 / (len(ids) - 1)
        for k, sid in enumerate(ids):
            out[sid] = base - 0.40 + k * passo
    return out


def _pydt(serie: pd.Series) -> list:
    """Timestamps → datetime puro (o renderizador de imagem não aceita Timestamp)."""
    return [None if pd.isna(d) else pd.Timestamp(d).to_pydatetime() for d in serie]


def fig_mapa(df: pd.DataFrame, tema: str,
             eventos: pd.DataFrame | None = None) -> go.Figure:
    """Mapa das normas: x=data, y=tipo (com jitter estável), cor/símbolo=situação.

    `eventos` (data/eventos/eventos_normas.csv) serve para NÃO mentir na leitura
    visual. Um aglomerado de marcadores parece um aglomerado de casos, e em
    março/2018 ele não é: os 11 Decretos Legislativos ali saíram da mesma sessão
    extraordinária, contra decretos do mesmo pacote, e respondem a UMA ação. Sem
    marcação, o olho conta 11 e conclui "houve muita contestação em 2018".
    Grupos com 3+ normas do mesmo evento ganham cerco e rótulo.
    """
    c = cores(tema)
    tipos = [t for t in ("Lei ordinária", "Lei Complementar", "Decreto Legislativo",
                         "Emenda Constitucional", "Resolução") if t in set(df["tipo"])]
    ypos = {t: i for i, t in enumerate(tipos)}
    ycoord = _y_por_norma(df, ypos, len(tipos))

    tam_evento: dict[int, int] = {}
    if eventos is not None and not eventos.empty:
        tam_evento = {int(r["sapl_id"]): int(r["tamanho_evento"])
                      for _, r in eventos[["sapl_id", "tamanho_evento"]].iterrows()}

    fig = go.Figure()
    # FAIXAS, não linhas — e desenhadas ANTES de qualquer outra forma, porque
    # entre shapes do mesmo layer a última fica por cima: se pintadas no fim,
    # cobririam o cerco tracejado dos eventos.
    # A linha de grade ficava no centro do tipo e os pontos, espalhados ±0,40
    # para não se cobrirem, caíam dos dois lados dela — um ponto em 2,4 parecia
    # estar ENTRE "Decreto Legislativo" e "Resolução", quando é Decreto
    # Legislativo. Com a faixa pintada, pertencer é estar DENTRO.
    for _t, _i in ypos.items():
        if _i % 2:
            continue   # alterna: uma sim, uma não, para as faixas se distinguirem
        fig.add_shape(type="rect", xref="paper", x0=0, x1=1,
                      y0=_i - 0.5, y1=_i + 0.5, layer="below", line=dict(width=0),
                      fillcolor="rgba(0,0,0,0.035)" if tema != "dark"
                                else "rgba(255,255,255,0.05)")

    for cat in CAT_ORDEM:
        sub = df[df["categoria"] == cat]
        if sub.empty:
            continue
        extra = []
        for s in sub["sapl_id"]:
            n = tam_evento.get(int(s), 1)
            extra.append(f"<br><i>1 de {n} do mesmo evento legislativo</i>"
                         if n > 1 else "")
        fig.add_trace(go.Scatter(
            x=_pydt(sub["data"]),
            y=[ycoord[int(s)] for s in sub["sapl_id"]],
            mode="markers", name=f"{cat} ({len(sub)})",
            marker=dict(size=13, symbol=SIMBOLOS[cat], color=c[cat],
                        line=dict(width=1.5, color="rgba(255,255,255,0.75)" if tema != "dark"
                                  else "rgba(0,0,0,0.55)")),
            customdata=[int(s) for s in sub["sapl_id"]],
            text=[(f"{t} {n}/{a}<br>{e[:120]}…" if len(e) > 120
                   else f"{t} {n}/{a}<br>{e}") + x
                  for t, n, a, e, x in zip(sub["tipo"], sub["numero"], sub["ano"],
                                           sub["ementa"], extra)],
            hovertemplate="%{text}<extra>" + cat + "</extra>"))

    # cerco dos aglomerados que são UM evento só
    if eventos is not None and not eventos.empty:
        vis = set(df["sapl_id"].astype(int))
        ev = eventos[eventos["sapl_id"].astype(int).isin(vis)]
        pos = df.set_index("sapl_id")
        for eid, g in ev.groupby("evento_id"):
            ids = [int(s) for s in g["sapl_id"] if int(s) in pos.index]
            if len(ids) < 3:
                continue
            com_data = [i for i in ids if pd.notna(pos.loc[i, "data"])]
            # exigir que quase todos tenham data: com 1 de 3 datada, o cerco seria
            # desenhado a partir de um ponto e sugeriria proximidade inexistente
            if len(com_data) < 3 or len(com_data) < len(ids) - 1:
                continue
            datas = [pd.Timestamp(pos.loc[i, "data"]) for i in com_data]
            if (max(datas) - min(datas)).days > 120:
                continue   # evento espalhado no tempo não é aglomerado enganoso
            ys = [ycoord[i] for i in com_data]

            # o rótulo tem de dizer o que LIGOU estas normas, e não sempre é a
            # sessão: o evento da Jaci-Paraná junta 4 normas por CADEIA, votadas
            # em sessões distintas. Escrever "mesma sessão" ali seria falso.
            motivos = set(str(m) for m in g["motivo"])
            sess = {s for m in g["sessoes"] for s in str(m).split(";") if s}
            uma_sessao = len(sess) <= 2 and all("sessao" in m for m in motivos)
            legenda = ("mesma sessão plenária" if uma_sessao else
                       "mesma cadeia de alterações" if motivos == {"cadeia"} else
                       "cadeia + mesma sessão")

            folga = pd.Timedelta(days=95)
            fig.add_shape(type="rect", x0=min(datas) - folga, x1=max(datas) + folga,
                          y0=min(ys) - 0.34, y1=max(ys) + 0.34,
                          line=dict(color=c["aresta_inferida"], width=2, dash="dot"),
                          fillcolor="rgba(0,0,0,0)", layer="below")
            # com o eixo limitado a [-0.5, n-0.5], um rótulo acima do último tipo
            # sairia da área visível — nesse caso ele vai para baixo do cerco
            acima = max(ys) + 0.42 < len(tipos) - 0.55
            fig.add_annotation(
                x=(min(datas) + (max(datas) - min(datas)) / 2),
                y=(max(ys) + 0.42) if acima else (min(ys) - 0.42),
                xanchor="center", yanchor="bottom" if acima else "top",
                text=f"<b>{len(ids)} normas · 1 evento</b><br>"
                     f"<span style='font-size:10px'>{legenda}</span>",
                showarrow=False, align="left", font=dict(size=11, color=c["ink"]),
                bgcolor="rgba(255,255,255,0.82)" if tema != "dark"
                        else "rgba(20,20,20,0.82)",
                bordercolor=c["aresta_inferida"], borderwidth=1, borderpad=3)

    fig.update_yaxes(tickvals=list(ypos.values()), ticktext=list(ypos.keys()),
                     showgrid=False, zeroline=False, automargin=True,
                     range=[-0.5, len(tipos) - 0.5])
    fig.update_xaxes(showgrid=False, automargin=True)
    # a altura sai do PIOR aglomerado, não de um número fixo: onze normas na
    # mesma faixa precisam de faixa alta o bastante para que os marcadores não
    # se cubram. Com marcador de 13px, ~15px por ponto empilhado é o mínimo
    # para cada um continuar sendo um alvo de clique próprio.
    pior = max([len(g) for _, g in df.groupby(["tipo", "data"], dropna=False)] or [1])
    alt_faixa = max(120, int(15 * pior / 0.80))
    # teto de 700px: acima disso a figura vira rolagem e o ganho de separação
    # deixa de compensar — o plotly escolhe o ponto MAIS PRÓXIMO do clique, então
    # ~12px de distância entre centros já dá alvo próprio a cada norma
    fig.update_layout(height=min(700, max(430, alt_faixa * max(1, len(tipos)))),
                      margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02),
                      dragmode="pan", hovermode="closest")
    return fig


def _lanes(nos: pd.DataFrame) -> dict[int, float]:
    """Distribui nós em pistas: ordena por data e evita sobreposição horizontal."""
    fim_da_pista: list[pd.Timestamp] = []
    pos: dict[int, float] = {}
    folga = pd.Timedelta(days=540)
    for _, r in nos.sort_values("data").iterrows():
        alocada = None
        for i, fim in enumerate(fim_da_pista):
            if pd.isna(r["data"]) or r["data"] - fim > folga:
                alocada = i
                break
        if alocada is None:
            alocada = len(fim_da_pista)
            fim_da_pista.append(pd.Timestamp.min)
        fim_da_pista[alocada] = r["data"] if not pd.isna(r["data"]) else fim_da_pista[alocada]
        pos[int(r["sapl_id"])] = float(alocada)
    return pos


def fig_cadeia(nos: pd.DataFrame, arestas: pd.DataFrame, tema: str,
               centro: int | None = None) -> go.Figure:
    """Cadeia clicável: x=data, setas fonte→alvo (cheia=registrada, tracejada=inferida)."""
    c = cores(tema)
    nos = nos.copy()
    nos["data"] = pd.to_datetime(nos["data"], errors="coerce")
    sem_data = nos["data"].isna()
    if sem_data.any():
        base = nos["data"].min() if nos["data"].notna().any() else pd.Timestamp("2010-01-01")
        nos.loc[sem_data, "data"] = base - pd.Timedelta(days=365)
    pos = _lanes(nos)
    xy = {int(r["sapl_id"]): (pd.Timestamp(r["data"]).to_pydatetime(), pos[int(r["sapl_id"])])
          for _, r in nos.iterrows()}

    fig = go.Figure()
    setas = []
    for _, a in arestas.iterrows():
        f_id, a_id = int(a["fonte_sapl"]), int(a["alvo_sapl"])
        if f_id not in xy or a_id not in xy:
            continue
        inf = a["origem"] == "inferido"
        (x0, y0), (x1, y1) = xy[f_id], xy[a_id]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines", showlegend=False, hoverinfo="skip",
            line=dict(width=2, color=c["aresta_inferida"] if inf else c["aresta"],
                      dash="dash" if inf else "solid")))
        setas.append(dict(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                          showarrow=True, arrowhead=3, arrowsize=1.2, arrowwidth=1.5,
                          arrowcolor=c["aresta_inferida"] if inf else c["aresta"],
                          standoff=12, startstandoff=10, text=""))
    for cat in CAT_ORDEM:
        sub = nos[nos["categoria"] == cat]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=_pydt(sub["data"]), y=[pos[int(s)] for s in sub["sapl_id"]],
            mode="markers+text", name=cat,
            marker=dict(size=[18 if int(s) == centro else 13 for s in sub["sapl_id"]],
                        symbol=SIMBOLOS[cat], color=c[cat],
                        line=dict(width=[2.5 if int(s) == centro else 1 for s in sub["sapl_id"]],
                                  color=c["ink"])),
            text=[f"{t.replace('Lei Complementar', 'LC').replace('Lei ordinária', 'Lei')} {n}"
                  for t, n in zip(sub["tipo"], sub["numero"])],
            textposition="top center", textfont=dict(size=10),
            customdata=[int(s) for s in sub["sapl_id"]],
            hovertemplate="%{text}<br>%{x|%d/%m/%Y}<extra>" + cat + "</extra>"))
    fig.update_layout(annotations=setas, height=max(340, 90 + 62 * (max(pos.values()) + 1)),
                      margin=dict(l=10, r=10, t=28, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    fig.update_yaxes(visible=False)
    fig.update_xaxes(showgrid=True, automargin=True)
    return fig


def fig_votacao_partidos(votos: pd.DataFrame, tema: str) -> go.Figure:
    """Barras horizontais empilhadas por partido: Sim | Não | Abstenção | Ausente/Não votou."""
    c = cores(tema)
    v = votos.copy()
    v["voto_agr"] = v["voto"].replace({"Não Votou": "Ausente/Não votou",
                                       "Ausente": "Ausente/Não votou"})
    v["partido"] = v["partido_na_epoca"].replace("", "sem filiação resolvida")
    tab = v.pivot_table(index="partido", columns="voto_agr", aggfunc="size", fill_value=0)
    ordem_votos = [x for x in ("Sim", "Não", "Abstenção", "Ausente/Não votou") if x in tab.columns]
    tab = tab.loc[tab.sum(axis=1).sort_values().index]
    fig = go.Figure()
    for voto in ordem_votos:
        fig.add_trace(go.Bar(
            y=tab.index, x=tab[voto], name=voto, orientation="h",
            marker=dict(color=c[voto], line=dict(width=2, color="rgba(0,0,0,0)")),
            hovertemplate="%{y}: %{x} voto(s)<extra>" + voto + "</extra>"))
    fig.update_layout(barmode="stack", height=max(240, 60 + 28 * len(tab)),
                      margin=dict(l=10, r=10, t=10, b=45),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                  traceorder="normal"),
                      xaxis_title="votos (partido conforme filiação NA DATA da votação)")
    fig.update_yaxes(automargin=True)
    fig.update_xaxes(automargin=True)
    return fig


# ── Análise com IA ──────────────────────────────────────────────────────────
# Cor por VEREDITO. A escala não é decorativa: ela ordena por dissimulação, que
# é o objeto do trabalho. Vermelho = greenwashing (retórica verde + efeito que
# enfraquece); laranja = retrocesso assumido (tira proteção, mas sem disfarce —
# grave, e ainda assim OUTRA coisa); ocre = simbólica (promete e não entrega);
# azul = proteção genuína; cinza = fora do objeto ou indecidível.
CORES_VEREDITO = {
    "greenwashing": "#d03b3b",
    "retrocesso_transparente": "#e07b39",
    "simbolica": "#c9a227",
    "protecao_genuina": "#2a78d6",
    "nao_ambiental": "#898781",
    "indeterminado": "#c3c2b7",
}
ORDEM_VEREDITO = ["greenwashing", "simbolica", "retrocesso_transparente",
                  "protecao_genuina", "nao_ambiental", "indeterminado"]

# GREENWASHING É O GÊNERO; estes dois são as espécies.
#
# A definição do projeto é "a distância entre o que a norma DIZ ser e o que ela
# FAZ". Uma norma simbólica tem essa distância: diz que protege e não faz nada.
# O que separa greenwashing de retrocesso transparente é o DISFARCE (retórica
# ambiental presente), não o dano — e as 29 simbólicas do conjunto têm todas
# retórica > 0. Tratá-las como categoria à parte contradizia a própria
# definição; por isso aparecem juntas, com a espécie sempre visível.
#
# Não se colapsa num número só: prometer e não entregar (esvaziamento) e
# prometer enquanto retira (regressão) têm gravidades muito diferentes, e somar
# as duas sem mostrar a divisão inflaria a manchete.
ESPECIES_DISFARCE = {
    "greenwashing": "por regressão — promete e retira proteção",
    "simbolica": "por esvaziamento — promete e não entrega nada",
}

ORDEM_R = ["nenhuma", "leve", "forte"]
ORDEM_E = ["fortalece", "neutro", "misto", "enfraquece", "indeterminado"]


ROTULO_VEREDITO = {
    "greenwashing": "greenwashing<br><sup>por regressão</sup>",
    "simbolica": "greenwashing<br><sup>por esvaziamento</sup>",
    "retrocesso_transparente": "retrocesso assumido",
    "protecao_genuina": "proteção genuína",
    "nao_ambiental": "não ambiental",
    "indeterminado": "indeterminado",
}


def fig_vereditos(contagem: dict[str, int], tema: str) -> go.Figure:
    """Barras por veredito, na ordem conceitual (não por frequência).

    As duas espécies de greenwashing ficam adjacentes e recebem um colchete que
    as marca como um gênero só — ver ESPECIES_DISFARCE para o porquê. Sem essa
    marcação, a leitura visual seria "greenwashing 40" quando o total com
    disfarce é 69.
    """
    c = cores(tema)
    itens = [(v, contagem.get(v, 0)) for v in ORDEM_VEREDITO if contagem.get(v)]
    itens.reverse()   # plotly desenha de baixo para cima
    # customdata carrega a CHAVE crua ("retrocesso_transparente"), não o rótulo
    # exibido: quem clica na barra recebe algo que dá para filtrar no CSV sem
    # desfazer a formatação de volta
    fig = go.Figure(go.Bar(
        y=[ROTULO_VEREDITO.get(v, v.replace("_", " ")) for v, _ in itens],
        x=[n for _, n in itens],
        orientation="h", marker=dict(color=[CORES_VEREDITO[v] for v, _ in itens]),
        text=[str(n) for _, n in itens], textposition="outside",
        customdata=[v for v, _ in itens],
        hovertemplate="%{y}: %{x} norma(s)<br><i>clique para ver quais</i><extra></extra>"))

    # colchete unindo as duas espécies do gênero
    idx = {v: i for i, (v, _) in enumerate(itens)}
    if "greenwashing" in idx and "simbolica" in idx:
        a, b = sorted((idx["greenwashing"], idx["simbolica"]))
        total = contagem.get("greenwashing", 0) + contagem.get("simbolica", 0)
        fig.add_shape(type="line", xref="paper", x0=1.005, x1=1.005,
                      y0=a - 0.42, y1=b + 0.42,
                      line=dict(color=CORES_VEREDITO["greenwashing"], width=2.5))
        fig.add_annotation(
            xref="paper", x=1.02, y=(a + b) / 2, xanchor="left", yanchor="middle",
            text=f"<b>{total}</b><br><sup>com disfarce</sup>", showarrow=False,
            align="left", font=dict(size=11, color=CORES_VEREDITO["greenwashing"]))

    fig.update_layout(height=max(200, 52 * len(itens) + 60),
                      margin=dict(l=10, r=80, t=10, b=30), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=c["ink"]))
    fig.update_xaxes(automargin=True, showgrid=False, title="normas")
    fig.update_yaxes(automargin=True)
    return fig


def fig_matriz_re(tabela: dict[tuple[str, str], int], tema: str) -> go.Figure:
    """Matriz retórica × efeito — a decomposição de dois eixos, visível.

    O ponto do trabalho está na geometria: greenwashing NÃO é uma linha nem uma
    coluna, é o CANTO onde retórica forte encontra efeito que enfraquece. Uma
    norma pode enfraquecer proteção sem disfarce (coluna à direita, linha de
    baixo) e isso é retrocesso transparente, não greenwashing. A intensidade da
    cor é o score derivado R×E; o número é quantas normas caíram na célula.
    """
    c = cores(tema)
    peso_r = {"nenhuma": 0.0, "leve": 0.5, "forte": 1.0}
    peso_e = {"fortalece": 0.0, "neutro": 0.25, "misto": 0.6,
              "enfraquece": 1.0, "indeterminado": None}
    z, txt, hover = [], [], []
    for r in ORDEM_R:
        lz, lt, lh = [], [], []
        for e in ORDEM_E:
            n = tabela.get((r, e), 0)
            pe = peso_e[e]
            s = None if pe is None else peso_r[r] * pe
            lz.append(s)
            lt.append(str(n) if n else "")
            lh.append(f"retórica <b>{r}</b> × efeito <b>{e}</b><br><b>{n}</b> norma(s)"
                      + (f"<br>nota calculada {s:.2f}" if s is not None else
                         "<br>sem nota (efeito indeterminado)")
                      + ("<br><i>clique para ver quais</i>" if n else ""))
        z.append(lz), txt.append(lt), hover.append(lh)
    fig = go.Figure(go.Heatmap(
        z=z, x=ORDEM_E, y=ORDEM_R, text=txt, texttemplate="%{text}",
        textfont=dict(size=17), hovertext=hover, hoverinfo="text",
        colorscale=[[0, "#eef2f7"], [0.35, "#f7d9c4"], [0.7, "#e8916b"],
                    [1, CORES_VEREDITO["greenwashing"]]],
        zmin=0, zmax=1, showscale=True,
        colorbar=dict(title="score<br>R×E", thickness=12, len=0.85),
        xgap=3, ygap=3))
    fig.update_layout(height=290, margin=dict(l=10, r=10, t=30, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=c["ink"]),
                      xaxis_title="EFEITO — o que faz com a proteção",
                      yaxis_title="RETÓRICA")
    fig.update_xaxes(side="top", automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def fig_mecanismos(contagem: dict[str, int], tema: str) -> go.Figure:
    """Frequência dos mecanismos de dissimulação (multi-rótulo: soma > n)."""
    c = cores(tema)
    rot = {"M1_norma_programatica_vazia": "M1 · programática vazia",
           "M2_reframing_de_regressao": "M2 · reframing de regressão",
           "M3_revogacao_tacita": "M3 · revogação tácita",
           "M4_insercao_heterogenea": "M4 · inserção heterogênea",
           "M5_delegacao_desregulamentadora": "M5 · delegação desregulamentadora"}
    itens = sorted(contagem.items(), key=lambda kv: kv[1])
    fig = go.Figure(go.Bar(
        y=[rot.get(k, k) for k, _ in itens], x=[v for _, v in itens], orientation="h",
        marker=dict(color=CORES_VEREDITO["simbolica"]),
        text=[str(v) for _, v in itens], textposition="outside",
        customdata=[k for k, _ in itens],
        hovertemplate="%{y}: %{x} norma(s)<br><i>clique para ver quais</i><extra></extra>"))
    fig.update_layout(height=max(200, 44 * len(itens) + 50),
                      margin=dict(l=10, r=40, t=10, b=30), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=c["ink"]))
    fig.update_xaxes(automargin=True, showgrid=False, title="normas (uma pode ter vários)")
    fig.update_yaxes(automargin=True)
    return fig
