# `ui/` — Content Studio (NiceGUI)

## Estrutura

| Pasta / ficheiro | Função |
|------------------|--------|
| `pages/` | Rotas `@ui.page` — fino; chama `render_page` + `build_tab_*` |
| `tab_*.py` | Conteúdo de cada ecrã (formulários, grelhas, ações) |
| `components/` | Blocos reutilizáveis (checklist, CMS, jobs, FAQ JSON-LD) |
| `auth.py` | Login, sessão, `ArticleRepository` por utilizador |
| `layout.py` | `apply_styles()`, painel da sidebar |
| `pages/shell.py` | Sidebar + área principal |
| `pages/routes.py` | Paths e itens de navegação |
| `widgets.py` | `page_header`, inputs partilhados |
| `constants.py` | Rótulos e opções de select |
| `state.py` | `AppConfig` partilhado entre páginas |
| `design_tokens.css` | Cores e tipografia (Manrope) |
| `style.css` | Layout, scroll viewport, componentes |

## Fluxo de uma página

```
main.py → ui/pages/__init__.py → ui/pages/blog.py
  → shell.render_page → tab_blog.build_tab_blog
```

## Auth (sem sidebar)

`pages/auth_pages.py` → `tab_login.py` / `tab_signup.py`

## Legado

Não adicionar lógica em `modules/` nem `pipelines/` — ver [AGENTS.md](../AGENTS.md).
