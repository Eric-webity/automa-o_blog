# Sessões da interface em produção (`GEO_STORAGE_SECRET`)

O Content Studio (NiceGUI) guarda o estado de login no navegador através de cookies assinados. O parâmetro `storage_secret` passado a `ui.run()` é a chave que **impede falsificação** desses cookies.

Se o segredo for previsível ou partilhado entre instalações, um atacante pode fabricar uma sessão autenticada (`authenticated`, `email`, `user_id`, `role`) sem conhecer a senha.

---

## O que fica protegido

| Dado na sessão | Uso |
|----------------|-----|
| `authenticated` | Acesso às rotas após login |
| `email` / `name` | Identidade na UI |
| `user_id` | Histórico e matérias isolados por conta |
| `role` | Permissões (`user` / `admin`) |

Isto **não substitui** HTTPS nem senhas fortes; complementa o login local.

---

## Desenvolvimento vs produção

| `GEO_ENV` | `GEO_STORAGE_SECRET` | Comportamento |
|-----------|----------------------|---------------|
| `development` (padrão) | vazio | Usa segredo interno de dev (`geo-extractor-local-dev`) — aceitável só em `localhost` |
| `production` | **obrigatório** | Mínimo 32 caracteres; não pode ser o valor de dev |
| `production` | ausente ou curto | A aplicação **não arranca** (mensagem no terminal) |

---

## Configurar em produção

1. Defina o ambiente:

```env
GEO_ENV=production
```

2. Gere um segredo forte (uma vez por servidor ou por deploy):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

3. Coloque no `.env` do servidor (ou variável de ambiente do Docker/systemd), **sem aspas desnecessárias**:

```env
GEO_STORAGE_SECRET=o_valor_gerado_aqui_com_48_ou_mais_caracteres
```

4. Reinicie o processo (`python main.py`, container, serviço Windows).

5. **Não** versionar o `.env` com este valor no Git.

---

## Checklist de deploy

- [ ] `GEO_ENV=production`
- [ ] `GEO_STORAGE_SECRET` com ≥ 32 caracteres, único neste servidor
- [ ] HTTPS na frente da app (reverse proxy: nginx, Caddy, Traefik, etc.)
- [ ] `GEO_API_KEY` definida (API REST exige chave em produção)
- [ ] Credenciais `GEO_LOGIN_*` apenas se usar login por ambiente; preferir contas em `users` (SQLite)
- [ ] Backup de `data/` (SQLite) incluído no plano de recuperação

---

## Rotação do segredo

Ao **alterar** `GEO_STORAGE_SECRET`:

- Todas as sessões ativas deixam de ser válidas.
- Utilizadores terão de **entrar de novo** no login.

Planeie a rotação em janela de manutenção ou avise a equipa.

---

## Docker / executável

**Docker Compose:** injete o segredo via `env_file` ou secrets do orchestrator, não na imagem.

**`GEO-Extractor.exe`:** o `.env` ao lado do executável deve incluir `GEO_STORAGE_SECRET` quando `GEO_ENV=production`.

---

## Relação com outras variáveis

| Variável | Função |
|----------|--------|
| `GEO_STORAGE_SECRET` | Assinatura de cookies da **UI** |
| `GEO_API_KEY` | Autenticação da **API REST** (`X-API-Key`) |
| `GEO_WEBHOOK_SECRET` | Assinatura opcional de webhooks de saída |
| `GEO_LOGIN_EMAIL` / `GEO_LOGIN_PASSWORD` | Login fixo por ambiente (legado); independente do segredo de sessão |

---

## Referência técnica

- Implementação: `config/production.py` → `resolve_storage_secret()`
- Arranque: `main.py` → `ui.run(storage_secret=…)`
- Documentação NiceGUI: [User storage](https://nicegui.io/documentation/storage#user_storage)
