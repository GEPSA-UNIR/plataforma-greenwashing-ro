"""Contrato de dados da plataforma — a UI lê SOMENTE estas fontes.

escopo/fichas/grafo são gerados pela esteira (scripts/); decisões humanas
vivem em data/decisoes/ (ver decisoes.py). CSVs de curadoria crus NUNCA
entram aqui — lição da contaminação da amostra. A tabela de sinais (motor E6)
ainda não existe: sinais() devolve None e a UI declara a lacuna.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"


@st.cache_data
def escopo() -> pd.DataFrame:
    df = pd.read_csv(DADOS / "escopo" / "escopo_normas.csv")
    df["sapl_id"] = df["sapl_id"].astype(int)
    return df


@st.cache_data
def nucleo_proposto() -> pd.DataFrame:
    df = pd.read_csv(DADOS / "escopo" / "nucleo_semente_proposto.csv")
    df["sapl_id"] = df["sapl_id"].astype(int)
    return df


@st.cache_data
def ids_analise() -> list[int]:
    return pd.read_csv(DADOS / "escopo" / "analise_ids.csv")["sapl_id"].astype(int).tolist()


@st.cache_data
def fichas_existentes() -> set[int]:
    return {int(p.stem.split("_")[1]) for p in (DADOS / "fichas").glob("ficha_*.json")}


def ficha(sapl_id: int) -> dict | None:
    p = DADOS / "fichas" / f"ficha_{sapl_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data
def grafo() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Nós e arestas dos grafos gerados (prefixos analise + amostra, deduplicados)."""
    nos, arestas = [], []
    for prefixo in ("analise", "amostra"):
        pn = DADOS / "grafo" / f"{prefixo}_nos.csv"
        pa = DADOS / "grafo" / f"{prefixo}_arestas.csv"
        if pn.exists():
            nos.append(pd.read_csv(pn))
        if pa.exists():
            arestas.append(pd.read_csv(pa))
    if not nos:
        return pd.DataFrame(), pd.DataFrame()
    dfn = pd.concat(nos, ignore_index=True).drop_duplicates(subset=["sapl_id"], keep="first")
    dfa = pd.concat(arestas, ignore_index=True).drop_duplicates(
        subset=["origem", "fonte_sapl", "alvo_sapl", "alvo_kind", "relacao"], keep="first")
    return dfn, dfa


def sinais() -> pd.DataFrame | None:
    """Tabela do motor E6 (computador de sinais). None = motor ainda não rodou."""
    p = DADOS / "sinais" / "sinais_normas.csv"
    return pd.read_csv(p) if p.exists() else None


def analise_ia() -> pd.DataFrame | None:
    """Análises validadas da IA (E7). None = ainda não rodou. Juízo de modelo, não fato."""
    p = DADOS / "ia" / "analise_normas.csv"
    return pd.read_csv(p, keep_default_na=False) if p.exists() else None


@st.cache_data
def resposta_ia(sapl_id: int) -> dict | None:
    """A resposta CRUA do modelo para uma norma — com as citações literais.

    O CSV consolidado guarda só as contagens (quantas citações, quantas
    conferidas). As citações em si — o trecho que o modelo copiou e a seção de
    onde tirou — só existem aqui. São elas que sustentam cada afirmação: sem
    mostrá-las, a plataforma pede que se acredite nela, que é exatamente o que o
    projeto diz não fazer.
    """
    p = DADOS / "ia" / "respostas" / f"resposta_{sapl_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


@st.cache_data
def eventos() -> pd.DataFrame:
    """Agrupamento das normas em EVENTOS legislativos (E4.1).

    Uma linha por norma, com o evento a que ela pertence — componente conexo de
    *cadeia jurídica ∪ mesma sessão plenária*. Existe porque as 114 normas não
    são 114 observações independentes: os 11 Decretos Legislativos de 2018 são um
    ato só, fatiado em 11 peças. Ver `data/eventos/RELATORIO.md`.
    """
    p = DADOS / "eventos" / "eventos_normas.csv"
    return pd.read_csv(p, keep_default_na=False) if p.exists() else pd.DataFrame()


def _categoria(f: dict) -> str:
    """Categoria visual da norma — derivada da ficha, com a mesma prudência dela."""
    const = f.get("constitucionalidade") or {}
    if const.get("declarada_inconstitucional") or const.get("anexos_adi"):
        return "com ADI"
    valor = ((f.get("situacao_derivada") or {}).get("valor") or "").lower()
    if "revoga" in valor or "suspen" in valor:
        return "revogada/suspensa"
    rel = f.get("relacoes") or {}
    if rel.get("passivas") or rel.get("passivas_inferidas"):
        return "alterada por outra norma"
    return "vigente (presumida)"


@st.cache_data
def indicadores() -> pd.DataFrame:
    """Uma linha por ficha: fatos derivados da ficha canônica (nada é inventado aqui)."""
    linhas = []
    for p in sorted((DADOS / "fichas").glob("ficha_*.json")):
        f = json.loads(p.read_text())
        ident, origem = f["identificacao"], f.get("origem") or {}
        rel = f.get("relacoes") or {}
        dias = None
        if ident.get("data") and origem.get("data_apresentacao"):
            dias = (pd.Timestamp(ident["data"]) - pd.Timestamp(origem["data_apresentacao"])).days
        autores = ", ".join(
            a.get("nome", "?") + (f" ({a['partido_na_epoca']})" if a.get("partido_na_epoca") else "")
            for a in origem.get("autores") or [])
        acess = (f.get("acessorios_da_materia") or {}).get("itens") or []
        linhas.append({
            "sapl_id": ident["sapl_id"], "tipo": ident["tipo"], "numero": ident["numero"],
            "ano": ident["ano"], "data": ident.get("data"), "ementa": ident.get("ementa") or "",
            "categoria": _categoria(f), "situacao": (f.get("situacao_derivada") or {}).get("valor"),
            "dias_pl_lei": dias, "autores": autores,
            "n_age_sobre": len(rel.get("ativas") or []) + len(rel.get("ativas_inferidas") or []),
            "n_sofre": len(rel.get("passivas") or []) + len(rel.get("passivas_inferidas") or []),
            "tem_transcricao": any(i.get("categoria") == "transcricao_plenario" for i in acess),
            "n_alertas": len(f.get("alertas") or []),
            "url_sapl": ident.get("url_sapl"),
        })
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["na_analise"] = df["sapl_id"].isin(set(ids_analise()))
    return df


@st.cache_data
def votacoes() -> pd.DataFrame:
    p = DADOS / "ui" / "votacoes.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def votos_nominais() -> pd.DataFrame:
    p = DADOS / "ui" / "votos_nominais.csv"
    df = pd.read_csv(p, keep_default_na=False) if p.exists() else pd.DataFrame()
    return df
