"""Inject an EOSL.ai lifecycle panel into Device and Device Type detail pages."""
from netbox.plugins import PluginTemplateExtension

from .client import lookup_part, search_url

_TEMPLATE = "netbox_eosl/eosl_panel.html"


def _manufacturer_name(device_type):
    mfr = getattr(device_type, "manufacturer", None)
    return getattr(mfr, "name", "") or ""


def _panel(extension, part_number, vendor):
    """Shared renderer for both models."""
    return extension.render(
        _TEMPLATE,
        extra_context={
            "eosl": lookup_part(part_number, vendor),
            "queried_part": part_number,
            "search_url": search_url(part_number),
        },
    )


class DeviceEOSL(PluginTemplateExtension):
    models = ["dcim.device"]

    def right_page(self):
        device = self.context["object"]
        # A device's ordering PID + manufacturer live on its device type.
        device_type = getattr(device, "device_type", None)
        part = getattr(device_type, "part_number", "") or ""
        return _panel(self, part, _manufacturer_name(device_type))


class DeviceTypeEOSL(PluginTemplateExtension):
    models = ["dcim.devicetype"]

    def right_page(self):
        device_type = self.context["object"]
        part = getattr(device_type, "part_number", "") or ""
        return _panel(self, part, _manufacturer_name(device_type))


template_extensions = [DeviceEOSL, DeviceTypeEOSL]
