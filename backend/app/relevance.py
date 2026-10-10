"""Does a tender fit a business? A plain keyword check, no AI call, so the inbox stays instant."""
import re
from functools import lru_cache

from app import pdf_reader

# Words that say nothing about what a business makes.
GENERIC = {
    "with", "from", "that", "this", "and", "the", "for", "made", "making", "other", "items", "item", "products",
    "product", "goods", "services", "service", "supply", "supplies", "work", "works", "various", "all", "kind",
    "kinds", "type", "types", "etc", "also", "including", "like", "such", "high", "quality", "good", "new",
    "small", "large", "based", "near", "india", "indian", "limited", "private", "pvt",
}


def _stem(word: str) -> str:
    """Drop a plural ending: desks -> desk, benches -> bench, glass stays glass."""
    if word.endswith(("ches", "shes", "xes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _stems(text: str) -> set[str]:
    """Lowercase words of 4+ letters, plurals dropped, generic words removed."""
    return {w for w in map(_stem, re.findall(r"[a-z]{4,}", text.lower())) if len(w) >= 3 and w not in GENERIC}


@lru_cache(maxsize=256)
def _tender_stems(pdf_path: str, title: str) -> frozenset[str]:
    """Words in the title and PDF. Cached: a tender's PDF never changes (a corrigendum gets a new path)."""
    try:
        text = " ".join(pdf_reader.pdf_to_pages(pdf_path))
    except Exception:
        text = ""
    return frozenset(_stems(f"{title} {text}"))


def match_tender(company: dict, pdf_path: str, title: str) -> dict:
    """{"fits": a product word of the business appears in the tender, "matched": those words,
    "in_area": the business's place name appears in the tender}."""
    words = _tender_stems(pdf_path, title)
    matched = sorted(_stems(company["products"]) & words)
    return {"fits": bool(matched), "matched": matched, "in_area": bool(_stems(company["location"]) & words)}
