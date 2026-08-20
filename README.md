# Plataforma Interativa para Detecção de Greenwashing Legislativo Ambiental — Rondônia

Interface de consulta pública sobre a legislação ambiental do estado de Rondônia,
construída a partir do registro oficial do processo legislativo da Assembleia
Legislativa (SAPL/ALE-RO).

**Greenwashing legislativo** é a distância entre o que uma norma *diz ser* e o que ela
*faz*. Uma lei que retira proteção ambiental de forma explícita é retrocesso — grave,
mas transparente. Greenwashing exige que a regressão esteja disfarçada.

Projeto PVC1813-2025 · PIBIC/PIBITI 2025-2026 · **Grupo de Estudos em Processos
Socioambientais da Amazônia (GEPSA)** · Universidade Federal de Rondônia.

## O que está aqui

- **114 normas ambientais** promulgadas a partir de 2010, triadas por critério
  auditável a partir das 11.663 normas do registro da ALE-RO
- **130 fichas canônicas** — as 114 da análise mais fichas de contexto, alcançáveis
  apenas ao navegar por uma cadeia e sempre marcadas como *fora do conjunto*
- **grafo de vínculos** entre normas (altera, revoga, suspende, julga inconstitucional)
- **votação nominal** com o partido do parlamentar **à época do voto**, não o atual
- **leitura por modelo de linguagem** de cada norma, com as citações conferidas contra
  o documento oficial

## Como ler o que está na tela

A distinção abaixo não é decorativa — é a regra que permite dizer o que é fato e o que
é leitura:

- **Determinístico** — o que vem do registro oficial e de contas reproduzíveis. Fichas,
  vínculos, votações, indícios de processo. Qualquer pessoa refaz e chega ao mesmo
  resultado.
- **Juízo de modelo** — a página *Análise* e a seção *Leitura por IA* do dossiê. Sempre
  exibidas com o modelo, a versão do roteiro e a data ao lado, e sob o rótulo
  *"juízo de modelo, não fato"*.

A leitura publicada aqui foi produzida pelo modelo `google/gemini-3.1-flash-lite` com o
roteiro de análise `v2.2`. Das 114 análises, **5 foram descartadas** pela conferência
automática e **54 saíram com ressalvas** — o estado de cada uma aparece na tela.

Cada citação que o modelo faz é reconferida, palavra por palavra, contra o documento de
origem. Citação que não é encontrada é sinalizada; citação que veio de texto editorial
nosso, e não do documento, também.

**O que esta plataforma não faz:** não afirma que uma norma é inconstitucional, não
substitui análise jurídica, e não mede efeito ambiental no território — o cruzamento
entre norma e dado de desmatamento não foi executado.

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run plataforma/app.py
```

Sempre a partir da raiz do repositório: o Streamlit lê `.streamlit/config.toml` do
diretório onde foi executado, e é ele que fixa o tema claro e a cor de destaque.

## As cinco páginas

| página | o que mostra |
|---|---|
| **Análise** | painel da leitura por modelo: vereditos, os dois eixos (retórica × efeito), citações conferidas |
| **Explorar** | mapa clicável das normas no tempo, com filtros e busca |
| **Cadeias** | famílias de normas ligadas por vínculos de ação |
| **Dossiê** | uma norma por inteiro: origem, processo, votação nominal, linha do tempo, proveniência |
| **Tabela** | visão tabular, que também é a *table view* de acessibilidade |

## De onde vem o dado

Fonte primária: **SAPL da Assembleia Legislativa de Rondônia**, API pública.

Este repositório é um **artefato derivado**: contém apenas o código da interface e os
arquivos que ela lê. A esteira de coleta, triagem e análise que produz esses arquivos é
mantida separadamente.

Nenhuma página grava dado. A plataforma é somente-leitura.

## Licença e uso

Os dados normativos são públicos e provêm do SAPL/ALE-RO. Ao reutilizar material desta
plataforma, cite o projeto e distinga o que é registro oficial do que é juízo de modelo.
