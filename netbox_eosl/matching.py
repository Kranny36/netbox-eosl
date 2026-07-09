"""Pure part-number matching logic — no Django/NetBox imports, so it is unit-testable standalone.

Matching is deterministic and conservative: exact first, then a punctuation/case-insensitive
"loose" match, then a **vendor-gated** vendor-abbreviation expansion (e.g. Fortinet FG- -> FortiGate-).
It never does fuzzy/substring matching, and vendor-specific aliases only apply when the NetBox
manufacturer matches that vendor — so it can't cross-match one vendor's part onto another's record.
"""
import re

# Official Fortinet SKU-abbreviation -> product-line prefixes. EOSL.ai stores the long form
# (e.g. "FortiGate-60E"); NetBox device types commonly use the short SKU form (e.g. "FG-60E").
FORTINET_PREFIX = {
    "FG": "FORTIGATE",
    "FS": "FORTISWITCH",
    "FAP": "FORTIAP",
    "FAZ": "FORTIANALYZER",
    "FMG": "FORTIMANAGER",
    "FWB": "FORTIWEB",
    "FAD": "FORTIADC",
    "FML": "FORTIMAIL",
    "FPX": "FORTIPROXY",
    "FEX": "FORTIEXTENDER",
    "FAC": "FORTIAUTHENTICATOR",
    "FDD": "FORTIDDOS",
    "FSA": "FORTISANDBOX",
}


def loose(s):
    """Uppercase, strip every non-alphanumeric char. 'FortiGate-60E' and 'fortigate 60e' -> 'FORTIGATE60E'."""
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def build_index(skus):
    """Return (exact, loose_index): UPPER(pid)->rec and loose(pid)->rec. First writer wins on collisions."""
    exact, loose_index = {}, {}
    for rec in skus:
        pid = (rec.get("p") or "").strip().upper()
        if not pid:
            continue
        exact.setdefault(pid, rec)
        loose_index.setdefault(loose(pid), rec)
    return exact, loose_index


def _is_fortinet(vendor):
    return bool(vendor) and "FORTINET" in vendor.upper()


def candidate_loose_keys(part, vendor=None):
    """Loose keys to try, most-specific first. Vendor-gated aliases only; deterministic, never fuzzy."""
    keys, seen = [], set()

    def add(raw):
        k = loose(raw)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)

    add(part)
    if _is_fortinet(vendor):
        lp = loose(part)
        for ab, full in FORTINET_PREFIX.items():
            # e.g. 'FG60E'.startswith('FG') -> 'FORTIGATE' + '60E'
            if lp.startswith(ab) and len(lp) > len(ab) and not lp.startswith(full):
                add(full + lp[len(ab):])
    return keys


def match(part, vendor, exact, loose_index):
    """Resolve a part number to a record, or None. Exact -> loose -> vendor-gated alias."""
    if not part:
        return None
    u = part.strip().upper()
    if u in exact:
        return exact[u]
    for k in candidate_loose_keys(part, vendor):
        rec = loose_index.get(k)
        if rec:
            return rec
    return None


def classify(rec):
    """(state, label, bootstrap_css) from a lookup record. Templates stay logic-free."""
    if rec.get("a"):
        return ("active", "Active — no EOL announced", "success")
    band = rec.get("xb") or ""
    if band in ("High exposure", "Action recommended"):
        return ("risk", band, "danger")
    if band in ("Plan", "Watch"):
        return ("watch", band, "warning")
    return ("clear", band or "Tracked", "info")
