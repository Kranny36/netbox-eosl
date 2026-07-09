"""Client for the EOSL.ai public lookup dataset.

Downloads https://eosl.ai/data/lookup.json (the same compact part-number -> status map that powers
the eosl.ai bulk checker), caches it, and resolves a part number to its lifecycle record via the
deterministic, vendor-gated matcher in `matching.py`. Never fuzzy-matches — a wrong end-of-life date
on the wrong device would defeat the point of a source-backed tool.
"""
import logging

import requests
from django.core.cache import cache
from netbox.plugins import get_plugin_config

from . import matching

logger = logging.getLogger("netbox.plugins.netbox_eosl")

_SKU_CACHE_KEY = "netbox_eosl:skus:v2"
# In-process memo of the built indexes, rebuilt only when the sku set changes.
_MEMO = {"token": None, "idx": (None, None)}


def _cfg(key):
    return get_plugin_config("netbox_eosl", key)


def _load_skus():
    """Return the list of sku records from EOSL.ai, cached. [] on any failure (never raises)."""
    skus = cache.get(_SKU_CACHE_KEY)
    if skus is not None:
        return skus

    url = _cfg("api_url").rstrip("/") + "/data/lookup.json"
    try:
        resp = requests.get(
            url,
            timeout=_cfg("request_timeout"),
            headers={"User-Agent": "netbox-eosl/0.1 (+https://eosl.ai)"},
        )
        resp.raise_for_status()
        skus = resp.json().get("skus", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("netbox-eosl: could not load lookup data from %s: %s", url, exc)
        cache.set(_SKU_CACHE_KEY, [], 300)  # brief negative cache so a broken upstream isn't hammered
        return []

    cache.set(_SKU_CACHE_KEY, skus, _cfg("cache_timeout"))
    return skus


def _indexes():
    """(exact, loose) indexes, rebuilt in-process only when the sku count changes."""
    skus = _load_skus()
    token = len(skus)
    if _MEMO["token"] != token:
        _MEMO["token"] = token
        _MEMO["idx"] = matching.build_index(skus)
    return _MEMO["idx"]


def lookup_part(part_number, vendor=None):
    """Resolve one part number (optionally with its NetBox manufacturer name) to a display dict, or None.

    Passing `vendor` enables vendor-gated aliases (e.g. Fortinet FG-60E -> FortiGate-60E) without risking
    a cross-vendor false match. The returned dict is safe to hand straight to the template.
    """
    if not part_number:
        return None
    exact, loose_index = _indexes()
    rec = matching.match(part_number, vendor, exact, loose_index)
    if not rec:
        return None
    state, label, css = matching.classify(rec)
    slug = rec.get("s")
    return {
        "part": rec.get("p"),
        "vendor": rec.get("v"),
        "family": rec.get("f"),
        "end_of_sale": rec.get("eos"),
        "eosl": rec.get("eol"),
        "source_url": rec.get("src"),
        "exposure_score": rec.get("xs"),
        "exposure_band": rec.get("xb"),
        "active": bool(rec.get("a")),
        "state": state,
        "state_label": label,
        "state_css": css,
        "page_url": (_cfg("api_url").rstrip("/") + "/system/" + slug + "/") if slug else _cfg("api_url"),
    }


def search_url(term):
    """A safe fallback link into eosl.ai when we have no exact match."""
    base = _cfg("api_url").rstrip("/")
    return "{}/?q={}".format(base, requests.utils.quote(term or ""))
