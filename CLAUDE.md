# CLAUDE.md — PodcastFlow

> Sistema de agentes para geração automatizada de roteiros de podcast e posts para redes sociais a partir de matérias e notícias.

-----

## Stack & Dependências

- **Linguagem:** Python 3.11+
- **Framework de agentes:** LangGraph (LangChain)
- **LLM:** Google Gemini (via `langchain-google-genai`)
- **Fontes de dados:** NewsAPI, Tavily Search
- **Gerenciamento de dependências:** Poetry ou pip + requirements.txt
- **Variáveis de ambiente:** `.env` com `python-dotenv` (nunca commitar `.env`)

-----

## Estrutura do Projeto (LangGraph Template)

```
podcastflow/
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── src/
│   └── podcastflow/
│       ├── __init__.py
│       ├── graph.py              # Definição principal do grafo LangGraph
│       ├── state.py              # Definição do State (TypedDict)
│       ├── configuration.py      # Configurações do agente (modelo, parâmetros)
│       ├── prompts.py            # Todos os prompts centralizados
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── researcher.py     # Nó: coleta e curadoria de matérias
│       │   ├── analyst.py        # Nó: análise e síntese das matérias
│       │   ├── scriptwriter.py   # Nó: geração do roteiro do podcast
│       │   ├── social_media.py   # Nó: geração de posts para redes sociais
│       │   └── reviewer.py       # Nó: revisão e controle de qualidade
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── news_api.py       # Tool: busca via NewsAPI
│       │   ├── tavily_search.py  # Tool: busca via Tavily
│       │   └── formatters.py     # Utilitários de formatação de texto
│       └── utils/
│           ├── __init__.py
│           └── helpers.py
├── outputs/                      # Roteiros e posts gerados
├── tests/
│   ├── __init__.py
│   ├── test_nodes.py
│   ├── test_tools.py
│   └── test_graph.py
└── scripts/
    └── run.py                    # Entrypoint para execução
```

-----

## Fluxo dos Agentes (Grafo LangGraph)

```
[START]
   │
   ▼
[Researcher] ── Coleta matérias via NewsAPI + Tavily sobre o tema
   │
   ▼
[Analyst] ── Analisa, cruza fontes, identifica ângulos e destaques
   │
   ▼
[ScriptWriter] ── Gera o roteiro do podcast (intro, desenvolvimento, encerramento)
   │
   ├──▶ [Reviewer] ── Revisa coerência, tom, fluxo e factualidade
   │       │
   │       ▼ (aprovado?)
   │      SIM ──▶ continua
   │      NÃO ──▶ volta para ScriptWriter com feedback
   │
   ▼
[SocialMedia] ── Gera posts para redes sociais baseados no roteiro
   │
   ▼
[END] ── Retorna roteiro + posts
```

-----

## Convenções de Código

### Estilo

- Seguir **PEP 8** e usar **Black** para formatação (line-length: 100)
- Type hints obrigatórios em todas as funções
- Docstrings no padrão **Google Style**
- Imports organizados com **isort** (profile: black)

### Nomenclatura

- Arquivos e módulos: `snake_case`
- Classes: `PascalCase`
- Funções e variáveis: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Nós do grafo: funções prefixadas com o nome do papel (ex: `researcher_collect`, `analyst_synthesize`)

### Prompts

- Todos os prompts ficam centralizados em `src/podcastflow/prompts.py`
- Usar `ChatPromptTemplate` do LangChain
- Prompts devem ser parametrizáveis (tema, tom, duração, público-alvo)
- Nunca hardcodar prompts dentro dos nós

-----

## State (Estado Compartilhado)

O estado do grafo deve ser definido como `TypedDict` em `state.py`:

```python
from typing import TypedDict, Annotated
from operator import add

class PodcastState(TypedDict):
    topic: str                              # Tema do episódio
    raw_articles: list[dict]                # Matérias brutas coletadas
    analysis: str                           # Síntese e análise das matérias
    script: str                             # Roteiro do podcast
    review_feedback: str                    # Feedback do reviewer
    review_approved: bool                   # Flag de aprovação
    social_posts: dict[str, str]            # Posts por plataforma (twitter, instagram, linkedin)
    metadata: dict                          # Metadados (data, fontes, duração estimada)
```

-----

## Configuração dos Agentes

### Modelo

- Usar `ChatGoogleGenerativeAI` do `langchain-google-genai`
- Modelo padrão: `gemini-2.0-flash` (ou conforme disponibilidade)
- Temperature: `0.7` para geração criativa (roteiro/posts), `0.2` para análise

### Tools

- NewsAPI: limite de 10 artigos por busca, filtrar por relevância e data
- Tavily: usar modo `search` com `max_results=5`
- Sempre incluir atribuição de fontes nos resultados

-----

## Comandos

```bash
# Instalar dependências
pip install -e ".[dev]"

# Rodar o fluxo completo
python scripts/run.py --topic "inteligência artificial" --tone "informal"

# Testes
pytest tests/ -v

# Lint e formatação
black src/ tests/ --line-length 100
isort src/ tests/ --profile black
mypy src/ --ignore-missing-imports

# Verificar grafo (visualização)
python -c "from podcastflow.graph import graph; graph.get_graph().print_ascii()"
```

-----

## Regras Importantes

1. **Cada nó faz UMA coisa bem feita** — não misturar responsabilidades entre nós
1. **Sem lógica de LLM fora dos nós** — tools são para I/O externo, nós processam com LLM
1. **Estado é imutável por convenção** — cada nó recebe o state e retorna apenas os campos que atualiza
1. **Sempre logar** — usar `logging` padrão do Python com nível configurável, logar entrada/saída de cada nó
1. **Tratar erros com graciosidade** — se uma fonte falhar, continuar com as demais; nunca quebrar o fluxo inteiro
1. **Testes antes de PR** — rodar `pytest` e `mypy` antes de qualquer merge
1. **Outputs reproduzíveis** — salvar metadados (timestamp, fontes usadas, parâmetros) junto com cada execução
1. **Roteiro com estrutura clara** — sempre gerar: abertura, desenvolvimento (2-4 blocos temáticos), encerramento
1. **Posts adaptados por plataforma** — Twitter (conciso, com hook), Instagram (visual, com hashtags), LinkedIn (profissional, com insight)
1. **Fontes sempre citadas** — tanto no roteiro quanto nos posts, referenciar as matérias originais

-----

## Variáveis de Ambiente (.env.example)

```env
GOOGLE_API_KEY=your_gemini_api_key
NEWS_API_KEY=your_newsapi_key
TAVILY_API_KEY=your_tavily_api_key
LOG_LEVEL=INFO
```

-----

## Tom e Estilo do Podcast

Parâmetros configuráveis pelo usuário ao executar o fluxo:

|Parâmetro |Opções                                    |Default |
|----------|------------------------------------------|--------|
|`tone`    |informal, formal, humorístico, técnico    |informal|
|`duration`|curto (5min), médio (15min), longo (30min)|médio   |
|`audience`|geral, técnico, executivo                 |geral   |
|`hosts`   |1 (monólogo) ou 2 (diálogo)               |2       |
|`language`|pt-BR, en-US, es                          |pt-BR   |
