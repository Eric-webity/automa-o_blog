# GEO Extractor — Visão do sistema e plano de organização

**Atualizado:** junho/2026  
**Público:** quem desenvolve ou mantém o projeto  
**Relacionados:** [Manual de uso](MANUAL.md) · [Resumo técnico](RESUMO_TECNICO.md)

Este documento descreve **o que o software faz**, **como o código está organizado hoje**, **o que pode melhorar** e **os próximos passos** para deixar a base mais limpa e fácil de evoluir.

---

## 1. O que é o GEO Extractor?

É uma ferramenta que roda no seu computador (ou em um servidor seu) para **criar textos pensados para serem citados por IAs** — ChatGPT, Perplexity, resumos do Google com IA, etc.

Além do SEO tradicional (aparecer no Google), o foco é **GEO (Generative Engine Optimization)**: estruturar o conteúdo com títulos claros, blocos de confiança, evidências, comparativos e perguntas frequentes, no estilo que motores generativos costumam preferir ao citar uma fonte.

### O que o usuário faz na prática

1. Informa **tema**, **links de referência**, palavras-chave e preferências (tom, tamanho do texto).
2. O sistema **lê as páginas**, extrai ideias principais e monta um **esqueleto** do artigo.
3. Com IA (ou em modo rascunho, sem IA), **gera a matéria** em Markdown, com metadados para SEO.
4. Pode **salvar no histórico**, exportar arquivos e, em produção, chamar a **API** ou publicar em um CMS externo.

### Como abrir o programa

```powershell
python main.py
```

Abre o **Content Studio** no navegador (por exemplo `http://localhost:8080`).  
Há login local; as matérias ficam no banco SQLite em `data/`.

> A interface antiga em Streamlit está em [`legacy/app.py`](../legacy/app.py) (congelada). O desenvolvimento deve priorizar `main.py` (NiceGUI).

---

## 2. Partes principais do sistema

```
┌─────────────────────────────────────────────────────────────┐
│  Navegador — Content Studio (NiceGUI)                        │
│  Login · abas · formulários · histórico · configurações        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  API REST (/api/...) — mesmo processo que a interface        │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  Pipelines — orquestram “gerar matéria” e “processar URLs”   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   services/            core/              db/ + output/
   (IA, blog, fetch)    (regras GEO)       (SQLite, .md/.json)
```

| Pasta | Papel em linguagem simples |
|-------|----------------------------|
| `main.py` | Ponto de entrada: sobe a interface e registra a API |
| `ui/` | Telas, estilos, login, abas e componentes visuais |
| `api/` | Endpoints para integrar com outros sistemas |
| `services/` | Regras de negócio: chamar IA, buscar URLs, gerar blog, estatísticas |
| `core/` | Motor GEO: esqueleto, índice IA, extração de insights |
| `db/` | Guardar usuários, perfil do blog e matérias no histórico |
| `config/` | Provedores de IA (`ai_providers.yaml`) e ajustes de produção |
| `skills/` | Textos de orientação para a IA (prompts em Markdown) |
| `data/` | Banco SQLite (não vai para o Git) |
| `output/` | Arquivos exportados após cada geração |
| `tests/` | Testes automatizados |

### Abas da interface

| Aba | Para que serve |
|-----|----------------|
| Dashboard | Números do uso, saúde da API, webhooks |
| Criar matéria | Fluxo principal do blog (tema + referências) |
| URLs | Artigo a partir de links |
| Texto manual | Artigo a partir de texto colado |
| JSON ChatGPT | Analisar JSON da aba Network do ChatGPT |
| Histórico | Matérias já geradas |
| Perfil | Dados do autor/blog |
| Settings | Chaves de API e provedores de IA |

Na barra lateral: **extração avançada** (NLP), **gerar com IA** e escolha do **provedor** (OpenAI, Anthropic, Ollama, etc.).

---

## 3. Como o código está hoje (e o que confunde)

### O que já funciona bem

- Geração de matérias longas (1.500 a 6.000 palavras), inclusive modo “artigo longo” em duas etapas com IA.
- Vários provedores de IA configuráveis.
- Histórico local, API REST, Docker e webhooks para produção.
- Interface moderna com autenticação de usuário.
- Prompts versionados em `skills/`.

### Pontos de atenção na organização

**1. Pastas que se sobrepõem**

Existem três “lugares” com lógica parecida:

- `services/` — **caminho preferido** para código novo (interface e API usam isto).
- `core/` — regras centrais de GEO e insights.
- `modules/` — mistura de **atalhos** (reexporta `core` e `services`) com **arquivos antigos** ainda duplicados.

Risco: corrigir um bug em `services/` e o Streamlit ou um teste ainda usar cópia em `modules/`.

**2. Duas interfaces**

- **NiceGUI** (`main.py`) — oficial.
- **Streamlit** (`legacy/app.py`) — legado; não recebe features novas.

**3. Pasta `pipelines/`**

Só redireciona para `services`. Quem procura o fluxo real deve ir a `services/blog_pipeline.py`.

**4. Autenticação em dois modos**

- Na interface: login com e-mail e senha (sessão no navegador).
- Na API: chave `GEO_API_KEY`.

Ainda não há vínculo claro “cada usuário da interface tem sua chave de API”.

**5. Matérias e usuários**

Convém confirmar se cada matéria no histórico pertence ao usuário logado (importante se mais de uma pessoa usar a mesma instalação).

---

## 4. Organização desejada (alvo)

Objetivo: **uma estrutura fácil de entender** e com dependências em uma só direção.

```
projeto/
├── main.py              ← única entrada da interface
├── api/                 ← API REST
├── ui/                  ← telas
├── core/                ← GEO puro (sem chamar rede nem banco)
├── services/            ← IA, blog, busca de URLs, CMS, métricas
├── db/                  ← modelos e acesso ao SQLite
├── config/
├── skills/
├── data/
├── output/
├── tests/
├── docs/
└── legacy/              ← opcional: app.py Streamlit, congelado
```

**Regra de dependência**

```
ui  →  services  →  core
api →  services  →  db
```

A interface e a API **não** devem importar código legado de `modules/` diretamente.

---

## 5. Próximos passos — plano por fases

### Fase A — Organização do código (prioridade alta)

| # | Tarefa | Resultado esperado |
|---|--------|-------------------|
| A1 | Mapear imports: tudo que ainda usa `modules.*` | Lista de arquivos a migrar |
| A2 | Apontar testes e `app.py` para `services` e `core` | Um só lugar com a lógica |
| A3 | Remover duplicatas em `modules/` ou deixar só reexportações finas | Menos risco de divergência |
| A4 | Mover `app.py` para `legacy/` ou marcar como descontinuado no README | Documentação alinhada |
| A5 | Centralizar rótulos da UI (provedores, status) em um arquivo | Menos repetição em `tab_*.py` |
| A6 | Atualizar README com estrutura alvo e link para este doc | Onboarding mais rápido |

**Critério de “feito”:** `pytest tests/ -q` verde; `main.py` sem import de `modules`.

---

### Fase B — Qualidade do conteúdo gerado

| # | Tarefa | Resultado esperado |
|---|--------|-------------------|
| B1 | Aviso se o texto ficou com menos de 85% das palavras pedidas | Usuário sabe quando revisar |
| B2 | Checklist na aba “Criar matéria” (H1, FAQ, tamanho) | Revisão humana guiada |
| B3 | Cache de URLs já buscadas | Menos tempo e custo em novas matérias |
| B4 | Alerta de texto muito parecido com a fonte | Mais segurança editorial |
| B5 | (Opcional) Busca com navegador headless para sites em JavaScript | Menos falhas ao ler páginas |

---

### Fase C — Produto e uso diário

| # | Tarefa | Resultado esperado |
|---|--------|-------------------|
| C1 | Modelos por área (saúde, finanças, SaaS) | Blocos GEO prontos por nicho |
| C2 | Exportar FAQ em JSON-LD | SEO técnico automático |
| C3 | Lote: planilha CSV → vários `.md` em `output/` | Produção em escala |
| C4 | Log de tokens/custo no Dashboard | Controle de gastos com IA |

---

### Fase D — Plataforma e segurança

| # | Tarefa | Resultado esperado |
|---|--------|-------------------|
| D1 | Validar URLs na API (evitar abuso se exposto na rede) | Menos risco de SSRF |
| D2 | Fila em segundo plano para textos muito longos | Interface não trava |
| D3 | `user_id` em cada matéria do histórico | Dados isolados por conta |
| D4 | Documentar `GEO_STORAGE_SECRET` para produção | Sessões mais seguras |

---

## 6. Ordem sugerida de trabalho

Para quem for implementar, esta sequência costuma dar menos retrabalho:

1. **Fase A** (organização) — base estável antes de features novas.  
2. **B1 + B2** (validação e checklist) — ganho rápido para quem usa o blog.  
3. **D3** (matérias por usuário) — se houver mais de um login na mesma máquina.  
4. **B3, B4** (cache e similaridade).  
5. Demais itens conforme necessidade (CMS, lote, fila assíncrona).

---

## 7. Glossário rápido

| Termo | Significado |
|-------|-------------|
| **GEO** | Otimização para ser citado por IAs generativas, não só ranquear no Google. |
| **Esqueleto GEO** | Estrutura de títulos e blocos (confiança, ciência, comparativo) antes da redação final. |
| **Índice IA** | Representação de como o tema poderia ser “indexado” por uma IA; é inferido localmente, não é dado real do ChatGPT. |
| **Pipeline** | Sequência automática: buscar fontes → extrair ideias → montar esqueleto → gerar texto → salvar. |
| **Provedor** | Serviço de IA (OpenAI, Anthropic, Ollama, etc.). |
| **Modo local** | Gera rascunho sem chamar IA (texto genérico; serve para testes ou offline). |

---

## 8. Documentos do projeto

| Documento | Conteúdo |
|-----------|----------|
| [MANUAL.md](MANUAL.md) | Como usar cada aba e fluxo |
| [RESUMO_TECNICO.md](RESUMO_TECNICO.md) | Detalhes técnicos, limitações e roadmap antigo |
| [EXECUTABLE.md](EXECUTABLE.md) | Gerar executável Windows |
| **Este arquivo** | Visão geral, organização e próximos passos de estruturação |

---

*Documento vivo: atualizar quando concluir uma fase do plano (especialmente A e B).*
