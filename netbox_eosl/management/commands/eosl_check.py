"""`manage.py eosl_check` — audit your NetBox device types against EOSL.ai.

Prints a summary of how many tracked device types are past end-of-service-life, ending soon,
still active, or not found in the EOSL.ai database — plus the list of past-EOSL types with how
many device instances you run. Read-only; changes nothing in NetBox.
"""
from collections import Counter

from dcim.models import DeviceType
from django.core.management.base import BaseCommand

from netbox_eosl.client import lookup_part


class Command(BaseCommand):
    help = "Audit NetBox device types against EOSL.ai end-of-life data (read-only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--past-only",
            action="store_true",
            help="Skip the summary; just list device types past end-of-service-life.",
        )

    def handle(self, *args, **options):
        device_types = DeviceType.objects.select_related("manufacturer").all()
        counts = Counter()
        past_rows = []

        for dt in device_types:
            part = (dt.part_number or "").strip()
            model = (dt.model or "").strip()
            if not part and not model:
                counts["no_part_number"] += 1
                continue
            # The manufacturer turns on vendor-gated forms (Fortinet FG-60E, Meraki MX67C); without it
            # the audit missed parts the device page matched. The model is tried when the part number
            # finds nothing (HISTORY §82).
            mfr = getattr(getattr(dt, "manufacturer", None), "name", "") or ""
            rec = lookup_part(part, mfr, model)
            if not rec:
                counts["not_found"] += 1
                continue
            counts[rec["state"]] += 1
            if rec["state"] == "risk":
                past_rows.append((dt, rec))

        total = sum(counts.values())

        if not options.get("past_only"):
            self.stdout.write(self.style.MIGRATE_HEADING("EOSL.ai audit — {} device types".format(total)))
            label = {
                "risk": "Past / action recommended",
                "watch": "Ending soon (plan/watch)",
                "clear": "Tracked, supported",
                "active": "Active — no EOL announced",
                "not_found": "Not found in EOSL.ai",
                "no_part_number": "No part number set",
            }
            for key in ("risk", "watch", "clear", "active", "not_found", "no_part_number"):
                if counts.get(key):
                    self.stdout.write("  {:<32} {}".format(label[key] + ":", counts[key]))

        if past_rows:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Past end-of-service-life:"))
            for dt, rec in sorted(past_rows, key=lambda r: r[1].get("eosl") or ""):
                try:
                    instances = dt.instances.count()
                except Exception:
                    instances = "?"
                self.stdout.write(
                    "  {vendor} {model} ({part}) — EOSL {eosl} — {n} in service — {url}".format(
                        vendor=rec.get("vendor") or (dt.manufacturer and dt.manufacturer.name) or "",
                        model=dt.model,
                        part=rec.get("part"),
                        eosl=rec.get("eosl") or "n/a",
                        n=instances,
                        url=rec.get("page_url"),
                    )
                )
        elif not options.get("past_only"):
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("No device types are past end-of-service-life. 🎉"))
