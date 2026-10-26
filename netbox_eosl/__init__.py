"""netbox-eosl — surface source-backed hardware end-of-service-life status inside NetBox.

Data comes from EOSL.ai's public API (https://eosl.ai), where every date links to the
vendor's own end-of-life bulletin. Matching is exact part-number only — the plugin never
guesses, so it cannot assert an end-of-life date NetBox isn't certain about.
"""
from netbox.plugins import PluginConfig

__version__ = "0.2.1"


class EOSLConfig(PluginConfig):
    name = "netbox_eosl"
    verbose_name = "EOSL.ai — Hardware End-of-Life"
    description = "Show source-backed end-of-sale / end-of-service-life status on Devices and Device Types, from EOSL.ai."
    version = __version__
    author = "EOSL.ai"
    author_email = "hello@eosl.ai"
    base_url = "eosl"
    # PluginTemplateExtension.models (plural) is required from NetBox 4.3 onward.
    min_version = "4.3.0"
    default_settings = {
        # Base origin of the EOSL.ai data source. Override only if you mirror the dataset.
        "api_url": "https://eosl.ai",
        # How long (seconds) to cache the downloaded lookup table. Default: 24h.
        "cache_timeout": 86400,
        # Network timeout (seconds) for fetching the lookup table.
        "request_timeout": 5,
    }


config = EOSLConfig
