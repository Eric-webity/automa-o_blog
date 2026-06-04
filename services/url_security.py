"""Validação de URLs públicas — mitiga SSRF e abuso na API."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
from urllib.parse import urlparse, urlunparse

# Hostnames sempre bloqueados (metadados cloud, rede local).
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "metadata.google",
        "instance-data",
    }
)

_BLOCKED_HOST_SUFFIXES: tuple[str, ...] = (
    ".localhost",
    ".local",
    ".internal",
    ".lan",
    ".home",
    ".corp",
    ".intranet",
)

_BLOCKED_HOST_RE = re.compile(
    r"^(localhost|127\.\d+\.\d+\.\d+|0\.0\.0\.0|::1|::ffff:127\.\d+\.\d+\.\d+|"
    r"169\.254\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|"
    r"172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$",
    re.I,
)

# IP em notação decimal (ex.: 2130706433 = 127.0.0.1).
_DECIMAL_IP_HOST_RE = re.compile(r"^\d+$")


class URLValidationError(ValueError):
    """URL rejeitada por política de segurança."""


def max_reference_urls() -> int:
    """Limite de URLs de referência por pedido (API / lote)."""
    try:
        return max(1, min(100, int(os.getenv("GEO_MAX_REFERENCE_URLS", "20"))))
    except ValueError:
        return 20


def max_url_length() -> int:
    try:
        return max(128, min(8192, int(os.getenv("GEO_MAX_URL_LENGTH", "2048"))))
    except ValueError:
        return 2048


def max_redirect_hops() -> int:
    """0 = sem seguir redirects (mais seguro contra SSRF)."""
    try:
        return max(0, min(5, int(os.getenv("GEO_URL_MAX_REDIRECTS", "2"))))
    except ValueError:
        return 2


_DISALLOWED_PREFIXES = (
    "javascript:",
    "data:",
    "file:",
    "ftp:",
    "gopher:",
    "mailto:",
    "tel:",
)


def _normalize_url(raw: str) -> str:
    u = raw.strip()
    if not u:
        raise URLValidationError("URL vazia")
    if len(u) > max_url_length():
        raise URLValidationError(f"URL excede {max_url_length()} caracteres")
    lower = u.lower()
    for prefix in _DISALLOWED_PREFIXES:
        if lower.startswith(prefix):
            raise URLValidationError(f"Esquema não permitido: {prefix.rstrip(':')}")
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _host_is_blocked_literal(host: str) -> bool:
    h = host.lower().rstrip(".")
    if not h:
        return True
    if h in _BLOCKED_HOSTNAMES:
        return True
    if _BLOCKED_HOST_RE.match(h):
        return True
    if any(h.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES):
        return True
    if _DECIMAL_IP_HOST_RE.match(h):
        try:
            val = int(h)
            if 0 <= val <= 0xFFFFFFFF:
                ip = ipaddress.ip_address(val)
                return (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_reserved
                    or ip.is_multicast
                )
        except ValueError:
            pass
    return False


def _resolve_host_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    try:
        for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
            ips.append(ipaddress.ip_address(info[4][0]))
    except (socket.gaierror, ValueError, OSError):
        return []
    return ips


def _ip_is_unsafe(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return True
    if ip.is_reserved or ip.is_multicast:
        return True
    if isinstance(ip, ipaddress.IPv4Address):
        # CGNAT / benchmark / IETF protocol assignments often abused in SSRF.
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        if ip in ipaddress.ip_network("192.0.0.0/24"):
            return True
        if ip in ipaddress.ip_network("198.18.0.0/15"):
            return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip == ipaddress.IPv6Address("::1"):
            return True
        if ip.is_site_local or (hasattr(ip, "is_private") and ip.is_private):
            return True
    return False


def _check_dns_resolution(host: str) -> None:
    """Bloqueia hostnames que resolvem para IPs internos (DNS rebinding)."""
    try:
        ip = ipaddress.ip_address(host)
        if _ip_is_unsafe(ip):
            raise URLValidationError(f"IP bloqueado (SSRF): {host}")
        return
    except ValueError:
        pass

    ips = _resolve_host_ips(host)
    if not ips:
        return
    for ip in ips:
        if _ip_is_unsafe(ip):
            raise URLValidationError(
                f"Hostname «{host}» resolve para rede privada ({ip})"
            )


def validate_url(url: str, *, resolve_dns: bool = True) -> str:
    """
    Valida e normaliza uma URL HTTP(S) pública.

    Raises:
        URLValidationError: se a URL for insegura ou inválida.
    """
    normalized = _normalize_url(url)
    parsed = urlparse(normalized)

    if parsed.scheme not in ("http", "https"):
        raise URLValidationError(f"Esquema não permitido: {parsed.scheme or '(vazio)'}")

    if parsed.username or parsed.password:
        raise URLValidationError("Credenciais embutidas na URL não são permitidas")

    host = (parsed.hostname or "").lower()
    if not host:
        raise URLValidationError("URL sem hostname")

    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443):
        raise URLValidationError(f"Porta não permitida: {port}")

    if _host_is_blocked_literal(host):
        raise URLValidationError(f"Hostname bloqueado (SSRF): {host}")

    if resolve_dns:
        _check_dns_resolution(host)

    # URL canónica sem fragmento nem query maliciosa extrema — mantém path/query úteis.
    clean = urlunparse(
        (
            parsed.scheme,
            host if not port or (parsed.scheme == "https" and port == 443)
            or (parsed.scheme == "http" and port == 80)
            else f"{host}:{port}",
            parsed.path or "/",
            "",
            parsed.query,
            "",
        )
    )
    return clean


def validate_reference_urls(
    urls: list[str],
    *,
    resolve_dns: bool = True,
    max_count: int | None = None,
) -> tuple[list[str], list[str]]:
    """
    Valida lista de URLs de referência.

    Returns:
        (urls_normalizadas, mensagens_de_erro por URL inválida)
    """
    limit = max_count if max_count is not None else max_reference_urls()
    errors: list[str] = []
    valid: list[str] = []
    seen: set[str] = set()

    if len(urls) > limit:
        raise URLValidationError(
            f"Máximo de {limit} URL(s) de referência por pedido "
            f"(recebidas: {len(urls)})."
        )

    for raw in urls:
        item = (raw or "").strip()
        if not item:
            continue
        try:
            normalized = validate_url(item, resolve_dns=resolve_dns)
        except URLValidationError as exc:
            errors.append(f"{item[:120]}: {exc}")
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        valid.append(normalized)

    return valid, errors


def safe_http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15,
) -> "requests.Response":
    """
    GET HTTP(S) com validação em cada redirect (mitiga SSRF via Location).

    Raises:
        URLValidationError: redirect para destino bloqueado.
    """
    import requests
    from urllib.parse import urljoin

    session = requests.Session()
    session.headers.update(headers or {})
    current = validate_url(url)
    hops = max_redirect_hops()
    redirect_codes = {301, 302, 303, 307, 308}

    for _ in range(hops + 1):
        resp = session.get(current, allow_redirects=False, timeout=timeout)
        if resp.status_code not in redirect_codes or not hops:
            return resp
        location = resp.headers.get("Location")
        if not location:
            return resp
        current = validate_url(urljoin(current, location))
        hops -= 1

    raise URLValidationError("Demasiados redirects HTTP")
