"""
Extração avançada: KeyBERT, spaCy NER, sumarização, embeddings.

Carregamento lazy — se dependências faltarem, métodos fazem fallback.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

# --- NLP opcional (lazy) ---
_nlp = None
_embedder = None
_kw_model = None
_nlp_available: bool | None = None


def _load_nlp():
    global _nlp, _nlp_available
    if _nlp_available is False:
        return None
    if _nlp is not None:
        return _nlp
    try:
        import spacy

        for model in ("pt_core_news_lg", "pt_core_news_sm", "pt_core_news_md"):
            try:
                _nlp = spacy.load(model)
                _nlp_available = True
                return _nlp
            except OSError:
                continue
        _nlp_available = False
    except ImportError:
        _nlp_available = False
    return None


def _load_keybert():
    global _embedder, _kw_model
    if _kw_model is not None:
        return _kw_model
    try:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        _kw_model = KeyBERT(model=_embedder)
        return _kw_model
    except Exception:
        return None


class AdvancedExtractor:
    """Pipeline NLP para matérias em português."""

    def extract_key_phrases(self, text: str, top_n: int = 12) -> list[str]:
        kw = _load_keybert()
        if kw and len(text) > 80:
            try:
                pairs = kw.extract_keywords(
                    text,
                    keyphrase_ngram_range=(1, 3),
                    stop_words="portuguese",
                    top_n=top_n,
                    use_mmr=True,
                )
                return [p for p, _ in pairs]
            except Exception:
                pass
        return _basic_keywords(text, top_n)

    def extract_entities(self, text: str) -> dict[str, list[str]]:
        nlp = _load_nlp()
        buckets: dict[str, list[str]] = {
            "ORG": [],
            "PER": [],
            "LOC": [],
            "MISC": [],
        }
        if nlp:
            try:
                doc = nlp(text[:100_000])
                for ent in doc.ents:
                    label = ent.label_
                    key = label if label in buckets else "MISC"
                    if label == "PERSON":
                        key = "PER"
                    buckets[key].append(ent.text.strip())
            except Exception:
                pass
        return {k: list(dict.fromkeys(v))[:15] for k, v in buckets.items() if v}

    def extract_claims(self, text: str) -> list[str]:
        patterns = [
            r"(?:de acordo com|segundo|conforme|estudos mostram que|pesquisas indicam que)\s+(.+?)[.!?]",
            r"(\d+[\.,]?\d*\s*(?:%|por cento|milhões?|bilhões?))",
            r"(?:pode|podem)\s+(?:levar a|resultar em|causar)\s+(.+?)[.!?]",
        ]
        claims: list[str] = []
        for pat in patterns:
            for m in re.finditer(pat, text, re.I):
                g = m.group(1) if m.lastindex else m.group(0)
                if isinstance(g, tuple):
                    g = g[-1]
                s = str(g).strip()
                if 20 < len(s) < 200:
                    claims.append(s)
        return list(dict.fromkeys(claims))[:12]

    def summarize(self, text: str, sentences_count: int = 4) -> str:
        sents = _split_sentences(text)
        if len(sents) <= sentences_count:
            return " ".join(sents)
        try:
            from sumy.nlp.tokenizers import Tokenizer
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.summarizers.text_rank import TextRankSummarizer

            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            summarizer = TextRankSummarizer()
            summary = summarizer(parser.document, sentences_count)
            return " ".join(str(s) for s in summary)
        except Exception:
            return " ".join(sents[:sentences_count])

    def key_sentences(self, text: str, n: int = 6) -> list[str]:
        sents = _split_sentences(text)
        if len(sents) <= n:
            return sents
        kw = _load_keybert()
        if not kw or not _embedder:
            return sents[:n]
        try:
            import numpy as np

            doc_vec = _embedder.encode(text[:2000])
            scored: list[tuple[float, str]] = []
            for s in sents:
                if 40 < len(s) < 400:
                    sim = float(np.dot(doc_vec, _embedder.encode(s)) /
                               (np.linalg.norm(doc_vec) * np.linalg.norm(_embedder.encode(s)) + 1e-9))
                    scored.append((sim, s))
            scored.sort(reverse=True)
            return [s for _, s in scored[:n]]
        except Exception:
            return sents[:n]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 40]


def _basic_keywords(text: str, top_n: int) -> list[str]:
    from collections import Counter

    stop = {
        "para", "como", "mais", "muito", "sobre", "entre", "quando", "onde",
        "pelo", "pela", "isso", "essa", "esse", "ainda", "também", "porque",
    }
    words = re.findall(r"[a-záàâãéêíóôõúç]{4,}", text.lower())
    words = [w for w in words if w not in stop]
    return [w for w, _ in Counter(words).most_common(top_n)]


@lru_cache(maxsize=1)
def get_extractor() -> AdvancedExtractor:
    return AdvancedExtractor()
