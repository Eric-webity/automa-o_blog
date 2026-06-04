"""Gestão multi-provider de IA (OpenAI, Anthropic, OpenRouter, Ollama, LM Studio)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

from services.ai_usage import UsageTokens, record_ai_usage

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "ai_providers.yaml"


@dataclass
class _ChatResult:
    text: str
    usage: UsageTokens


class AIManager:
    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path) if config_path else DEFAULT_CONFIG
        with open(path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.providers: dict[str, Any] = self.config.get("providers", {})

    def list_enabled_providers(self) -> list[str]:
        return [n for n, cfg in self.providers.items() if cfg.get("enabled")]

    def list_ready_providers(self) -> list[str]:
        """Providers habilitados com credenciais válidas ou servidores locais."""
        ready: list[str] = []
        bad = ("placeholder", "sua-chave", "sk-sua-chave", "sk-ant-...", "sk-or-v1-...")
        for name, cfg in self.providers.items():
            if not cfg.get("enabled"):
                continue
            if cfg.get("local") or cfg.get("api_key_optional"):
                ready.append(name)
                continue
            env_name = cfg.get("api_key_env", "")
            key = os.getenv(env_name, "").strip() if env_name else ""
            if not key or len(key) < 8:
                continue
            low = key.lower()
            if any(p in low for p in bad):
                continue
            ready.append(name)
        return ready

    def test_provider(self, provider: str, overrides: dict | None = None) -> tuple[bool, str]:
        """Testa conexão. `overrides` permite testar valores do formulário antes de salvar."""
        mgr = self
        if overrides:
            import copy

            mgr = copy.deepcopy(self)
            cfg = mgr.providers.setdefault(provider, {})
            cfg.update({k: v for k, v in overrides.items() if k != "models"})
            if "models" in overrides:
                cfg.setdefault("models", {}).update(overrides["models"])
            cfg["enabled"] = True

        try:
            text, used = mgr.call(
                provider=provider,
                task="rewrite",
                prompt="Responda apenas: OK",
                system="Resposta de uma palavra.",
                max_tokens=10,
                source="test",
            )
            return True, f"{used}: {text.strip()[:40]}"
        except Exception as exc:
            return False, str(exc)

    def diagnose_provider(self, provider: str, overrides: dict | None = None) -> dict:
        """Compara configuração vs servidor (URLs, modelos, estado)."""
        cfg = dict(self.providers.get(provider, {}))
        if overrides:
            cfg.update({k: v for k, v in overrides.items() if k != "models"})
            if "models" in overrides:
                cfg.setdefault("models", {}).update(overrides["models"])

        report: dict = {
            "provider": provider,
            "enabled_saved": bool(self.providers.get(provider, {}).get("enabled")),
            "checks": [],
            "ok": True,
        }

        def add(ok: bool, label: str, expected: str, actual: str, hint: str = "") -> None:
            report["checks"].append(
                {"ok": ok, "label": label, "expected": expected, "actual": actual, "hint": hint}
            )
            if not ok:
                report["ok"] = False

        if provider == "lmstudio":
            base = (cfg.get("base_url") or "http://localhost:1234/v1").rstrip("/")
            if not base.endswith("/v1"):
                add(
                    False,
                    "URL base (formato)",
                    "…:1234/v1",
                    base,
                    "LM Studio OpenAI-compat usa sufixo /v1 (ex.: http://192.168.50.179:1234/v1)",
                )
            model = (cfg.get("models") or {}).get("rewrite", "")
            try:
                resp = requests.get(f"{base}/models", timeout=8)
                resp.raise_for_status()
                ids = [m.get("id", "") for m in resp.json().get("data", [])]
                add(True, "Servidor acessível", "HTTP 200", str(resp.status_code))
                add(
                    bool(model and model in ids),
                    "Modelo configurado",
                    model or "(vazio)",
                    ", ".join(ids[:5]) or "(nenhum)",
                    "Use o ID exato listado pelo servidor" if model not in ids else "",
                )
            except Exception as exc:
                add(False, "Servidor acessível", "HTTP 200", str(exc), "Verifique IP, porta e se o servidor está Running")
            add(
                report["enabled_saved"],
                "Provedor habilitado (salvo)",
                "Sim",
                "Sim" if report["enabled_saved"] else "Não — marque e clique em Salvar e aplicar",
            )

        elif provider == "ollama":
            base = (cfg.get("base_url") or "http://localhost:11434").rstrip("/")
            port = base.rsplit(":", 1)[-1].split("/")[0]
            add(
                port != "1234",
                "Porta Ollama",
                "11434 (padrão)",
                port,
                "Porta 1234 é do LM Studio — Ollama usa 11434" if port == "1234" else "",
            )
            model = (cfg.get("models") or {}).get("rewrite", "")
            try:
                resp = requests.get(f"{base}/api/tags", timeout=8)
                resp.raise_for_status()
                names = [m.get("name", "") for m in resp.json().get("models", [])]
                add(True, "Servidor acessível", "HTTP 200", str(resp.status_code))
                add(
                    bool(model and any(model in n for n in names)),
                    "Modelo configurado",
                    model or "(vazio)",
                    ", ".join(names[:5]) or "(nenhum)",
                )
            except Exception as exc:
                add(False, "Servidor acessível", "HTTP 200", str(exc))

        return report

    def get_model(self, provider: str, task: str) -> str | None:
        cfg = self.providers.get(provider, {})
        models = cfg.get("models") or {}
        if task in models:
            return models[task]
        if task == "blog_long" and "rewrite" in models:
            return models["rewrite"]
        return models.get(task)

    def call(
        self,
        task: str,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 3500,
        provider: str | None = None,
        source: str = "general",
    ) -> tuple[str, str]:
        """
        Chama um provider. Retorna (texto, nome_do_provider_usado).
        Se provider for None, tenta todos os habilitados em ordem.
        """
        order = [provider] if provider else list(self.providers.keys())
        errors: list[str] = []

        for name in order:
            if name is None:
                continue
            cfg = self.providers.get(name, {})
            if not cfg:
                errors.append(f"{name}: provedor desconhecido")
                continue
            if not cfg.get("enabled"):
                if provider:
                    errors.append(f"{name}: desabilitado — marque o checkbox e salve")
                continue
            model = self.get_model(name, task)
            if not model:
                continue
            try:
                result = self._dispatch(name, cfg, model, prompt, system, max_tokens)
                record_ai_usage(
                    provider=name,
                    model=model,
                    task=task,
                    usage=result.usage,
                    prompt_text=prompt,
                    completion_text=result.text,
                    source=source,
                )
                return result.text, name
            except Exception as e:
                errors.append(self._describe_error(name, cfg, e))
                continue

        raise RuntimeError("Nenhum provedor respondeu. " + "; ".join(errors[:4]))

    @staticmethod
    def _describe_error(name: str, cfg: dict, exc: Exception) -> str:
        """Converte exceções de provedores em mensagens claras para o usuário."""
        env_name = cfg.get("api_key_env", "API_KEY")
        text = str(exc).strip()
        lowered = text.lower()

        status = getattr(exc, "status_code", None)
        if status is None:
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)

        if "não definida" in lowered or "nao definida" in lowered:
            return f"{name}: defina {env_name} no .env"

        is_auth = (
            status == 401
            or "401" in text
            or "unauthorized" in lowered
            or "invalid_api_key" in lowered
            or "invalid x-api-key" in lowered
            or "authentication" in exc.__class__.__name__.lower()
        )
        if is_auth:
            return (
                f"{name}: chave de IA inválida (401) — verifique {env_name} no .env"
            )

        if status == 429 or "429" in text or "rate limit" in lowered:
            return f"{name}: limite de requisições atingido (429)"

        if status in (500, 502, 503, 504) or "connection" in lowered or "timeout" in lowered:
            return f"{name}: provedor indisponível no momento"

        return f"{name}: {text}"

    def _dispatch(
        self,
        name: str,
        cfg: dict,
        model: str,
        prompt: str,
        system: str | None,
        max_tokens: int,
    ) -> _ChatResult:
        if name == "openai":
            return self._openai_chat(cfg, model, prompt, system, max_tokens)
        if name == "anthropic":
            return self._anthropic_chat(cfg, model, prompt, system, max_tokens)
        if name == "openrouter" or name == "lmstudio":
            return self._openai_compatible(cfg, model, prompt, system, max_tokens)
        if name == "ollama":
            return self._ollama_chat(cfg, model, prompt, system, max_tokens)
        raise ValueError(f"Provider desconhecido: {name}")

    def _resolve_api_key(self, cfg: dict) -> str:
        env_name = cfg.get("api_key_env", "API_KEY")
        key = os.getenv(env_name, "").strip() if env_name else ""
        if key:
            return key
        if cfg.get("api_key_optional") or cfg.get("local"):
            return cfg.get("default_api_key", "not-needed")
        raise ValueError(f"Variável {env_name} não definida")

    def _api_key(self, cfg: dict) -> str:
        return self._resolve_api_key(cfg)

    def _messages(self, prompt: str, system: str | None) -> list[dict]:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    @staticmethod
    def _usage_from_openai(usage_obj: Any) -> UsageTokens:
        if not usage_obj:
            return UsageTokens(0, 0, estimated=True)
        return UsageTokens(
            prompt_tokens=int(getattr(usage_obj, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage_obj, "completion_tokens", 0) or 0),
            estimated=False,
        )

    def _openai_chat(self, cfg, model, prompt, system, max_tokens) -> _ChatResult:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key(cfg), base_url=cfg.get("base_url"))
        r = client.chat.completions.create(
            model=model,
            messages=self._messages(prompt, system),
            max_tokens=max_tokens,
            temperature=0.6,
        )
        text = r.choices[0].message.content or ""
        return _ChatResult(text=text, usage=self._usage_from_openai(r.usage))

    def _anthropic_chat(self, cfg, model, prompt, system, max_tokens) -> _ChatResult:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key(cfg))
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        r = client.messages.create(**kwargs)
        text = r.content[0].text
        usage = UsageTokens(0, 0, estimated=True)
        if getattr(r, "usage", None):
            usage = UsageTokens(
                prompt_tokens=int(getattr(r.usage, "input_tokens", 0) or 0),
                completion_tokens=int(getattr(r.usage, "output_tokens", 0) or 0),
                estimated=False,
            )
        return _ChatResult(text=text, usage=usage)

    def _openai_compatible(self, cfg, model, prompt, system, max_tokens) -> _ChatResult:
        headers = {
            "Authorization": f"Bearer {self._api_key(cfg)}",
            "Content-Type": "application/json",
        }
        headers.update(cfg.get("extra_headers") or {})
        url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
        resp = requests.post(
            url,
            headers=headers,
            json={
                "model": model,
                "messages": self._messages(prompt, system),
                "max_tokens": max_tokens,
                "temperature": 0.6,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage_raw = data.get("usage") or {}
        usage = UsageTokens(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
            estimated=not usage_raw,
        )
        return _ChatResult(text=text, usage=usage)

    def _ollama_chat(self, cfg, model, prompt, system, max_tokens) -> _ChatResult:
        base = cfg.get("base_url", "http://localhost:11434").rstrip("/")
        resp = requests.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": self._messages(prompt, system),
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        prompt_eval = int(data.get("prompt_eval_count") or 0)
        eval_count = int(data.get("eval_count") or 0)
        usage = UsageTokens(
            prompt_tokens=prompt_eval,
            completion_tokens=eval_count,
            estimated=not (prompt_eval or eval_count),
        )
        return _ChatResult(text=text, usage=usage)
