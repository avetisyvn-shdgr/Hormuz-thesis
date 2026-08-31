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

_PROVIDERS: dict[str, type[BaseSource] | None] = {
    "eia": EIASource,
    "fred": FREDSource,
    "portwatch": PortWatchSource,
    "spark": SparkSource,
    "bloomberg_transcription": BloombergTranscriptionSource,
    "wto_hormuz": WTOHormuzLNGSource,
    "importer_customs": ImporterCustomsSource,
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
