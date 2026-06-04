# Executável Windows (GEO Extractor)

## Gerar o .exe

```powershell
cd geo-extractor
.\scripts\build_exe.ps1
```

Saída: `dist\GEO-Extractor\GEO-Extractor.exe`

## Primeira execução

1. Abra a pasta `dist\GEO-Extractor\`
2. Copie `.env.example` → `.env` e configure chaves de IA
3. Em deploy exposto à rede: `GEO_ENV=production` e `GEO_STORAGE_SECRET` (ver [PRODUCAO_SESSOES.md](PRODUCAO_SESSOES.md))
4. Execute `GEO-Extractor.exe` — o browser abre em `http://localhost:8080`
5. Configure o **webhook** na aba **Dashboard** (secção «Webhook»)

## Pastas ao lado do .exe

| Pasta | Uso |
|-------|-----|
| `data/` | Base SQLite (histórico) |
| `output/` | Artigos exportados |
| `config/` | Opcional — sobrescreve `ai_providers.yaml` empacotado |
| `.env` | Chaves e integrações |

## Webhook

Configure na UI (Dashboard) ou no `.env`:

```
GEO_WEBHOOK_URL=https://hooks.n8n.cloud/webhook/...
GEO_WEBHOOK_SECRET=opcional
```

Disparo automático ao gerar matéria via `POST /api/v1/articles/generate` com `notify_webhook: true`.

## Requisitos de build

- Python 3.11+ e `venv` com `requirements.txt` instalado
- `pip install pyinstaller`
- Opcional: `python -m spacy download pt_core_news_sm`

## Docker (alternativa)

```powershell
docker compose up --build
```
