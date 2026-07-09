"""Unit tests for the pure matching logic. Runnable without NetBox/Django:  python -m pytest  (or the
plain-python fallback at the bottom:  python tests/test_matching.py)."""
import importlib.util
import os
import sys

# Load matching.py directly by path so we don't trigger netbox_eosl/__init__.py (which imports NetBox).
_MATCHING = os.path.join(os.path.dirname(__file__), "..", "netbox_eosl", "matching.py")
_spec = importlib.util.spec_from_file_location("netbox_eosl_matching", _MATCHING)
matching = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(matching)

# A tiny fixture mirroring the shape of eosl.ai's lookup.json "skus" records.
SKUS = [
    {"p": "WS-C3850-48P-S", "v": "Cisco", "f": "Catalyst 3850 Series", "s": "cisco-catalyst-3850",
     "eos": "2020-10", "eol": "2025-10", "xb": "High exposure", "xs": 23, "a": 0},
    {"p": "FortiGate-60E", "v": "Fortinet", "f": "FortiGate 60E", "s": "fortinet-fortigate-60e",
     "eos": "2023-06", "eol": "2028-06", "xb": "Plan", "xs": 60, "a": 0},
    {"p": "FortiSwitch-124E", "v": "Fortinet", "f": "FortiSwitch 124E", "s": "fortinet-fortiswitch-124e",
     "eos": "2024-01", "eol": "2029-01", "xb": "Watch", "xs": 75, "a": 0},
    {"p": "J9856A", "v": "HPE", "f": "Aruba 2530", "s": "hpe-aruba-2530", "eol": "2027-01",
     "xb": "Action recommended", "xs": 45, "a": 0},
    {"p": "PA-220", "v": "Palo Alto Networks", "f": "PA-220", "s": "palo-alto-pa-220", "a": 1, "xb": "Current"},
]


def _idx():
    return matching.build_index(SKUS)


def check(part, vendor, expected_pid):
    exact, loose = _idx()
    rec = matching.match(part, vendor, exact, loose)
    got = rec["p"] if rec else None
    status = "ok " if got == expected_pid else "FAIL"
    print(f"  [{status}] match({part!r}, {vendor!r}) -> {got!r} (expected {expected_pid!r})")
    return got == expected_pid


def run():
    print("matching tests:")
    ok = True
    # Exact matches (any case / punctuation)
    ok &= check("WS-C3850-48P-S", "Cisco", "WS-C3850-48P-S")
    ok &= check("ws-c3850-48p-s", "Cisco", "WS-C3850-48P-S")
    ok &= check("WS C3850 48P S", "Cisco", "WS-C3850-48P-S")          # loose (spaces)
    # Fortinet short SKU -> long form, vendor-gated
    ok &= check("FG-60E", "Fortinet", "FortiGate-60E")
    ok &= check("fg-60e", "Fortinet", "FortiGate-60E")
    ok &= check("FortiGate 60E", "Fortinet", "FortiGate-60E")
    ok &= check("FS-124E", "Fortinet", "FortiSwitch-124E")
    # HPE J-number exact
    ok &= check("J9856A", "HPE", "J9856A")
    # Active/noEol product still resolves
    ok &= check("PA-220", "Palo Alto Networks", "PA-220")
    # Safety: the FG- alias must NOT fire for a non-Fortinet vendor (no cross-match)
    ok &= check("FG-60E", "Acme", None)
    ok &= check("FG-60E", None, None)
    # Unknown part -> None
    ok &= check("DOES-NOT-EXIST", "Cisco", None)
    # classify sanity
    assert matching.classify(SKUS[0])[0] == "risk"
    assert matching.classify(SKUS[4])[0] == "active"
    print("classify: ok")
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


# pytest entrypoints
def test_matching():
    assert run()


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
