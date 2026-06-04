# Várias contas na mesma máquina

O GEO Extractor guarda matérias no SQLite local (`data/`). Cada linha em `articles` tem **`user_id`** ligado à tabela `users`.

## Comportamento

| Ação | Resultado |
|------|-----------|
| Utilizador A gera e guarda | Só A vê no histórico e no dashboard |
| Utilizador B entra (outro e-mail) | Vê apenas as matérias de B |
| B abre `?article=ID` de A | «Matéria não encontrada» |
| B tenta atualizar ID de A | Repositório recusa (sem acesso) |
| Sair e entrar com outra conta | Sessão NiceGUI nova; estado em memória das abas é reposto |

## Sessão

- No login, `user_id` fica em `app.storage.user` (cookie assinado com `GEO_STORAGE_SECRET`).
- Login só por `.env` (`GEO_LOGIN_EMAIL`) também cria/obtém registo em `users` para ter `user_id` estável.
- API REST: matérias do e-mail `GEO_API_OWNER_EMAIL` (ou `GEO_LOGIN_EMAIL`, ou primeiro utilizador).

## Código

- Modelo: `db/models.py` → `Article.user_id`
- Filtro: `ArticleRepository(user_id=…)` via `ui.auth.article_repository()`
- UI: `ui/session_scope.py` (avisos, limpeza de `article_id` em memória)

## Migração

Matérias antigas sem `user_id` passam ao **primeiro utilizador** da base na primeira arrancada após atualizar.

## O que ainda é global

- **Perfil do blog** (`blog_profile`) — um registo partilhado na instalação (nome/e-mail do autor no painel Perfil).
- **Chaves de IA** e ficheiros em `output/` — partilhados no servidor; apenas o histórico SQLite é por conta.
