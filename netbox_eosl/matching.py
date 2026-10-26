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
    """Return (exact, loose_index): UPPER(pid)->rec and loose(pid)->rec.

    A loose key shared by two different families is struck out rather than resolved: stripping
    punctuation collapses distinct products onto one key (UAP-Outdoor / UAP-Outdoor+, and Palo Alto
    GP-100 against Dell GP100, across vendors), and first-writer-wins handed back whichever came first
    in the file. Unresolved is the correct answer to an ambiguous key. Same rule as src/match.js and
    functions/mcp.js (HISTORY §82).
    """
    exact, loose_index, ambiguous = {}, {}, set()
    for rec in skus:
        pid = (rec.get("p") or "").strip().upper()
        if not pid:
            continue
        exact.setdefault(pid, rec)
        lk = loose(pid)
        if lk in loose_index:
            if str(loose_index[lk].get("f")) != str(rec.get("f")):
                ambiguous.add(lk)
        else:
            loose_index[lk] = rec
    for k in ambiguous:
        loose_index.pop(k, None)
    return exact, loose_index


def _vendor_ok(vendor, rec):
    """True when no vendor is named, or the named vendor and the record's vendor contain one another."""
    lv, rv = loose(vendor), loose(rec.get("v"))
    return not lv or lv in rv or rv in lv


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


def match(part, vendor, exact, loose_index, aliases=None):
    """Resolve a part number to a record, or None. Exact -> loose -> Fortinet short code -> variant alias.

    `aliases` is https://eosl.ai/data/aliases.json (optional). Its entries are vetted when the site is
    built: every record an alias could mean has the same vendor and the same dates (EX4300-48T-TAA ->
    EX4300-48T, ASA5506 -> ASA5506-K8). "gated" aliases apply only when a vendor is named, and an alias
    hit must belong to the named vendor, so a Juniper MX80 can never resolve to a Meraki MX80.
    """
    if not part:
        return None
    u = part.strip().upper()
    if u in exact:
        return exact[u]
    keys = candidate_loose_keys(part, vendor)
    for k in keys:
        rec = loose_index.get(k)
        if rec:
            return rec
    if aliases:
        opened, gated = aliases.get("open") or {}, aliases.get("gated") or {}
        for k in keys:
            p = opened.get(k) or (gated.get(k) if loose(vendor) else None)
            rec = exact.get(str(p).upper()) if p else None
            if rec and _vendor_ok(vendor, rec):
                return rec
    return None


def classify(rec):
    """(state, label, bootstrap_css) from a lookup record. Templates stay logic-free."""
    if rec.get("a"):
        return ("active", "Active — no EOL announced", "success")
    band = rec.get("xb") or ""
    # "Little or no runway" is the current name for past-support hardware; "High exposure" is kept
    # for older cached lookup files (HISTORY §82).
    if band in ("Little or no runway", "High exposure", "Action recommended"):
        return ("risk", band, "danger")
    if band in ("Plan", "Watch"):
        return ("watch", band, "warning")
    return ("clear", band or "Tracked", "info")
