"""Parser do JSON do Network do ChatGPT."""

from __future__ import annotations

import json
from typing import Any


def _walk(obj: Any, key: str, found: list) -> None:
    if isinstance(obj, dict):
        if key in obj:
            found.append(obj[key])
        for v in obj.values():
            _walk(v, key, found)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, key, found)


def extract_geo_signals(raw: str) -> dict:
    """Extrai sinais do JSON do Network (estrutura varia entre versões do ChatGPT)."""
    result: dict = {
        "valid_json": False,
        "queries": [],
        "domains": [],
        "urls": [],
        "error": None,
    }

    try:
        data = json.loads(raw)
        result["valid_json"] = True
    except json.JSONDecodeError as e:
        result["error"] = str(e)
        return result

    query_blocks: list = []
    _walk(data, "search_model_queries", query_blocks)
    for block in query_blocks:
        if isinstance(block, list):
            for q in block:
                if isinstance(q, str):
                    result["queries"].append(q)
                elif isinstance(q, dict):
                    text = q.get("q") or q.get("query") or q.get("text")
                    if text:
                        result["queries"].append(str(text))

    group_blocks: list = []
    _walk(data, "search_result_groups", group_blocks)
    for block in group_blocks:
        if not isinstance(block, list):
            continue
        for group in block:
            if not isinstance(group, dict):
                continue
            domain = group.get("domain") or group.get("hostname")
            if domain:
                result["domains"].append(str(domain))
            for entry in group.get("entries") or group.get("results") or []:
                if isinstance(entry, dict):
                    url = entry.get("url") or entry.get("link")
                    if url:
                        result["urls"].append(str(url))

    _walk(data, "url", result["urls"])
    result["queries"] = list(dict.fromkeys(result["queries"]))[:20]
    result["domains"] = list(dict.fromkeys(result["domains"]))[:15]
    result["urls"] = list(dict.fromkeys(result["urls"]))[:20]
    return result
