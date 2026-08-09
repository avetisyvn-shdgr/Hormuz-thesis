"""Provider registry. Maps the `provider:` string in config/sources.yaml
to a concrete BaseSource implementation."""
from __future__ import annotations

from .base import BaseSource
from .bloomberg_transcription import BloombergTranscriptionSource
from .eia import EIASource
from .fred import FREDSource
from .importer_customs import ImporterCustomsSource
from .portwatch import PortWatchSource
from .spark import SparkSource
from .wto_hormuz import WTOHormuzLNGSource

# Providers that are not yet implemented map to None so the resolver can give
# a clear "this needs a backend / proprietary access" error instead of a
# cryptic KeyError.
_PROVIDERS: dict[str, type[BaseSource] | None] = {
    "eia": EIASource,
    "fred": FREDSource,
    "portwatch": PortWatchSource,
    # PRIMARY freight target. Wired and ready, but only invoked once the spark*
    # targets are flipped to `status: primary` in sources.yaml (access pending);
    # it requires OAuth2 credentials and fails loudly without them.
    "spark": SparkSource,
    # User-authorized, provenance-limited local workbooks. These are explicit
    # opt-ins and do not enter the default free-data pipeline.
    "bloomberg_transcription": BloombergTranscriptionSource,
    "wto_hormuz": WTOHormuzLNGSource,
    # V-layer national customs snapshots (Korea/Taiwan/China/India by-origin).
    "importer_customs": ImporterCustomsSource,
    # not yet wired / require paid access (no verified free historical feed):
    "ice_settlement": None,
    "eex_settlement": None,
    "platts": None,
    "bloomberg": None,
    "ais_vendor": None,
}


def get_provider(name: str) -> BaseSource:
    if name not in _PROVIDERS:
        raise KeyError(f"Unknown provider {name!r}. Add it to sources/__init__.py.")
    cls = _PROVIDERS[name]
    if cls is None:
        raise NotImplementedError(
            f"Provider {name!r} has no verified accessible backend. It maps to "
            f"a proprietary feed or an unbuilt settlement candidate. Acquire "
            f"access, document the terms, and implement it before use."
        )
    return cls()
