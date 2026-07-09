# netbox-eosl

Show **source-backed hardware end-of-service-life (EOSL) status** on your NetBox Devices and
Device Types, straight from [EOSL.ai](https://eosl.ai) — where every date links to the vendor's
own end-of-life bulletin.

A panel appears on the right side of each Device and Device Type page: end-of-sale date,
end-of-service-life date, the EOSL Exposure Score, a link to the vendor bulletin, and a link to
the full EOSL.ai model page. A `manage.py eosl_check` command audits your whole inventory.

Matching is **exact part-number only** — the plugin never fuzzy-matches, so it can't put a wrong
end-of-life date on the wrong device. If a part number isn't in the database, it says so and
offers a search link instead of guessing.

## Requirements

| | |
|---|---|
| NetBox | **4.3** or later (uses the `models` template-extension API) |
| Python | 3.10+ |
| Network | outbound HTTPS to `eosl.ai` from the NetBox host |

## Install

```bash
# In your NetBox virtual environment
source /opt/netbox/venv/bin/activate
pip install netbox-eosl
```

Add it to NetBox's `configuration.py`:

```python
PLUGINS = [
    "netbox_eosl",
]
```

(Optional) tune it:

```python
PLUGINS_CONFIG = {
    "netbox_eosl": {
        "api_url": "https://eosl.ai",   # data source origin
        "cache_timeout": 86400,          # seconds to cache the lookup table (default 24h)
        "request_timeout": 5,            # network timeout in seconds
    },
}
```

Then restart NetBox and run migrations (none are added, but this reloads plugins):

```bash
python /opt/netbox/netbox/manage.py migrate
sudo systemctl restart netbox netbox-rq
```

Add `netbox-eosl` to your `local_requirements.txt` so upgrades keep it installed.

## Use

**In the UI** — open any Device or Device Type that has a **part number** set. The
"Hardware End-of-Life" card appears in the right column.

**Inventory audit** — from the NetBox host:

```bash
python /opt/netbox/netbox/manage.py eosl_check
```

```
EOSL.ai audit — 214 device types
  Past / action recommended:       57
  Ending soon (plan/watch):        18
  Tracked, supported:              44
  Active — no EOL announced:        9
  Not found in EOSL.ai:            79
  No part number set:               7

Past end-of-service-life:
  Cisco Catalyst 3850-48P (WS-C3850-48P-S) — EOSL 2025-10 — 12 in service — https://eosl.ai/system/cisco-catalyst-3850/
  ...
```

Use `--past-only` to print just the past-EOSL list (handy in a cron/report).

## How matching works

The plugin downloads `https://eosl.ai/data/lookup.json` (the same part-number → status map that
powers the eosl.ai bulk checker) and caches it. For each Device Type it resolves the `part_number`
field (a Device inherits it from its Device Type) in three deterministic, conservative steps:

1. **Exact** match (case-insensitive).
2. **Loose** match — ignores spaces/dashes/case, so `FortiGate 60E` resolves `FortiGate-60E`.
3. **Vendor-gated aliases** — expands a manufacturer's short SKU form to the catalogued long form,
   but **only when the NetBox manufacturer matches that vendor**. E.g. a Fortinet `FG-60E` resolves
   `FortiGate-60E`, `FS-148E` → `FortiSwitch-148E`, `FAP-221E` → `FortiAP-221E`. The vendor gate means
   a non-Fortinet `FG-…` can never be mis-resolved onto a Fortinet record.

There is **no fuzzy or substring matching**. No part number, or no confident match → a neutral
"not tracked" panel with a search link. Nothing is inferred.

The matching logic lives in `netbox_eosl/matching.py` (no Django imports) and is unit-tested in
`tests/` — run `python tests/test_matching.py` (or `pytest`).

## Data & trust

- Dates come from EOSL.ai, sourced from each vendor's official end-of-life bulletin and linked
  for verification. Where a vendor publishes no per-model EOSL date, EOSL.ai computes it from the
  vendor's published support-life policy and labels it "computed".
- This plugin **reads** public data; it sends none of your inventory anywhere. The only outbound
  request is fetching the public lookup table.
- Confirm any critical date against the linked vendor bulletin before a purchase, renewal, or
  migration decision.

## License

Apache-2.0. See `LICENSE`.

## Contributing / publishing

Issues and PRs welcome — especially additional vendor SKU aliases (see `FORTINET_PREFIX` in
`matching.py` for the pattern) and screenshots. Maintainers: see `PUBLISHING.md` for the
PyPI + NetBox-community release steps.
