# Publishing netbox-eosl

This plugin is scaffolded inside the EOSL.ai site repo for convenience. To get the real value —
a listing on PyPI and the NetBox community plugins index (a high-authority backlink + distribution
to exactly the infra teams who are your TPM-referral audience) — extract it to its own repo.

## 1. Extract to its own GitHub repo

```bash
# from anywhere
cp -r C:/Users/Mike/EOSL/netbox-eosl ~/netbox-eosl
cd ~/netbox-eosl
git init && git add -A && git commit -m "netbox-eosl 0.1.0"
gh repo create Kranny36/netbox-eosl --public --source=. --push
```

Before the first release:
- Replace `LICENSE` with the full Apache-2.0 text.
- Remove the maintainer note at the bottom of `README.md`.
- Add a screenshot of the panel to `README.md` (drop the PNG in `docs/` and reference it) — the
  community index and PyPI page both reward a screenshot.

## 2. Test on a real NetBox

Spin up NetBox 4.3+ (Docker is easiest: `netbox-community/netbox-docker`), then in the NetBox venv:

```bash
pip install -e ~/netbox-eosl
# add "netbox_eosl" to PLUGINS in configuration.py, restart
python manage.py eosl_check
```

Load a Device Type with a real Cisco/HPE part number (e.g. `WS-C3850-48P-S`) and confirm the
"Hardware End-of-Life" card renders with the correct dates + source link.

## 3. Publish to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

## 4. Get it listed

- Open a PR / submission to the NetBox community plugins list (netbox-community docs "Plugins"
  index) and the awesome-netbox list.
- Post it to the NetBox Slack `#plugins` channel and r/networking / r/sysadmin when relevant.

Each listing is a do-follow-ish backlink from a high-authority domain and puts EOSL.ai in front of
NetBox operators. That distribution — not the code — is the reason this exists.
