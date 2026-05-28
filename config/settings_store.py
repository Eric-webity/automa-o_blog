"""Persistência de configuração (.env e ai_providers.yaml)."""

from __future__ import annotations

import os

import yaml

from config.paths import AI_PROVIDERS_YAML, ENV_PATH

YAML_PATH = AI_PROVIDERS_YAML

PLACEHOLDER_PATTERNS = (
    "sk-sua-chave",
    "sk-...",
    "sk-ant-...",
    "sk-or-v1-...",
    "sua-chave",
    "placeholder",
)


def _is_valid_key(value: str) -> bool:
    v = value.strip()
    if len(v) < 8:
        return False
    low = v.lower()
    return not any(p in low for p in PLACEHOLDER_PATTERNS)


def read_env_keys() -> dict[str, str]:
    keys = {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "LMSTUDIO_API_KEY": "",
    }
    if not ENV_PATH.exists():
        return keys
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip()
        if name in keys:
            keys[name] = val.strip()
    return keys


def write_env_keys(updates: dict[str, str]) -> None:
    """Atualiza ou adiciona chaves no .env (preserva outras variáveis)."""
    existing: dict[str, str] = {}
    other_lines: list[str] = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
            else:
                other_lines.append(line)

    for k, v in updates.items():
        if v and v.strip():
            existing[k] = v.strip()
            os.environ[k] = v.strip()

    lines = other_lines + [f"{k}={v}" for k, v in sorted(existing.items()) if v]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_provider_flags() -> dict[str, bool]:
    if not YAML_PATH.exists():
        return {}
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    return {name: bool(cfg.get("enabled")) for name, cfg in data.get("providers", {}).items()}


def write_provider_flags(flags: dict[str, bool]) -> None:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    providers = data.setdefault("providers", {})
    for name, enabled in flags.items():
        if name in providers:
            providers[name]["enabled"] = bool(enabled)
    YAML_PATH.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def read_ollama_url() -> str:
    return _read_provider_value("ollama", "base_url", "http://localhost:11434")


def write_ollama_url(url: str) -> None:
    _write_provider_base_url("ollama", url)


def read_lmstudio_url() -> str:
    return _read_provider_value("lmstudio", "base_url", "http://localhost:1234/v1")


def read_lmstudio_model() -> str:
    if not YAML_PATH.exists():
        return "local-model"
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    models = data.get("providers", {}).get("lmstudio", {}).get("models") or {}
    return models.get("rewrite") or models.get("blog_long") or "local-model"


def normalize_lmstudio_url(url: str) -> str:
    u = url.strip().rstrip("/")
    if not u:
        return "http://localhost:1234/v1"
    if u.endswith("/v1"):
        return u
    return f"{u}/v1"


def write_lmstudio_settings(url: str, model: str) -> None:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    providers = data.setdefault("providers", {})
    lm = providers.setdefault("lmstudio", {})
    lm["base_url"] = normalize_lmstudio_url(url)
    lm.setdefault("models", {})
    lm["models"]["rewrite"] = model.strip() or "local-model"
    lm["models"]["blog_long"] = model.strip() or "local-model"
    YAML_PATH.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _read_provider_value(provider: str, key: str, default: str) -> str:
    if not YAML_PATH.exists():
        return default
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    return data.get("providers", {}).get(provider, {}).get(key, default)


def _write_provider_base_url(provider: str, url: str) -> None:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    providers = data.setdefault("providers", {})
    providers.setdefault(provider, {})["base_url"] = url.rstrip("/")
    YAML_PATH.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def mask_key(value: str) -> str:
    if not value or not _is_valid_key(value):
        return ""
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "••••" + value[-4:]


_INTEGRATION_KEYS = (
    "GEO_WEBHOOK_URL",
    "GEO_WEBHOOK_SECRET",
    "GEO_API_KEY",
    "GEO_CMS_PUBLISH_URL",
    "GEO_CMS_PUBLISH_TOKEN",
)


def read_integration_env() -> dict[str, str]:
    """Lê variáveis de integração (webhook, API, CMS) do .env."""
    keys = {name: "" for name in _INTEGRATION_KEYS}
    if not ENV_PATH.exists():
        return keys
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, val = line.partition("=")
        name = name.strip()
        if name in keys:
            keys[name] = val.strip()
    return keys


def write_integration_env(updates: dict[str, str]) -> None:
    """Atualiza variáveis de integração no .env (permite limpar valores)."""
    existing: dict[str, str] = {}
    other_lines: list[str] = []
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
            else:
                other_lines.append(line)

    for key in _INTEGRATION_KEYS:
        if key in updates:
            value = (updates[key] or "").strip()
            existing[key] = value
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)

    lines = other_lines + [f"{k}={v}" for k, v in sorted(existing.items())]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
