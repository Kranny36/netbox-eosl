# Publishing netbox-eosl — status & remaining steps

## Done ✅
- **GitHub repo:** https://github.com/Kranny36/netbox-eosl (public)
- **PyPI:** https://pypi.org/project/netbox-eosl/ — `pip install netbox-eosl` (v0.1.0)

## Remaining

### 1. Load-test on a real NetBox + add a screenshot
Spin up NetBox 4.3+ (Docker is easiest: `netbox-community/netbox-docker`), then in the NetBox venv:

```bash
pip install netbox-eosl
# add "netbox_eosl" to PLUGINS in configuration.py, then restart NetBox
python manage.py eosl_check
```

Load a Device Type with a real part number (e.g. `WS-C3850-48P-S`, or a Fortinet `FG-60E`) and confirm
the "Hardware End-of-Life" card renders with the correct dates + source link. Grab a screenshot of the
card, drop it in `docs/`, and reference it near the top of `README.md` — the community index and PyPI
page both reward a screenshot.

### 2. Get it listed (paste-ready copy in the site repo: `reports/listings-kit.md`)
- **awesome-netbox** — PR adding the plugin under Plugins: https://github.com/netbox-community/awesome-netbox
- **NetBox Labs plugin catalog** — email `plugincatalog@netboxlabs.com`
- (optional) community wiki plugin list: https://github.com/netbox-community/netbox/wiki/Plugins

Each is a high-authority backlink + reaches the exact infra audience. That distribution is the point.

## Releasing an update later
Bump `version` in `pyproject.toml` and `__version__` in `netbox_eosl/__init__.py`, then:

```bash
cd C:\Users\Mike\netbox-eosl
rm -rf dist build *.egg-info
python -m build
python -m twine upload dist/*
```

Tighten security: after the first upload you can create a **project-scoped** PyPI token (scoped to
`netbox-eosl`) and delete the account-wide one.
