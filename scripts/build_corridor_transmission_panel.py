"""Build and freeze the corridor-transmission input panel without forecasting."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hormuz_throughput import config  # noqa: E402
from hormuz_throughput.corridor_panel import (  # noqa: E402
    build_corridor_panel,
    load_corridor_panel_protocol,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    protocol = load_corridor_panel_protocol()
    panel, metadata, quality, audit = build_corridor_panel(protocol)
    paths = {key: config.ROOT / value for key, value in protocol.outputs.items()}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)

    panel.to_csv(paths["panel"], index=False, date_format="%Y-%m-%d")
    metadata.to_csv(paths["metadata"], index=False)
    quality.to_csv(paths["quality"], index=False)
    paths["audit"].write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    inputs = {
        "data/raw/portwatch/Daily_Chokepoints_Data.csv": config.ROOT
        / config.settings()["paths"]["portwatch_csv"],
        "config/corridor_transmission.yaml": config.CONFIG_DIR
        / "corridor_transmission.yaml",
        "config/corridor_basins.yaml": config.CONFIG_DIR / "corridor_basins.yaml",
        "src/hormuz_throughput/corridor_panel.py": config.ROOT
        / "src/hormuz_throughput/corridor_panel.py",
    }
    output_hashes = {
        path.relative_to(config.ROOT).as_posix(): _sha256(path)
        for key, path in paths.items()
        if key != "manifest"
    }
    manifest = {
        "schema_version": 1,
        "status": protocol.status,
        "artifact_scope": "corridor_input_panel_only_no_forecasts",
        "python": platform.python_version(),
        "input_sha256": {
            name: _sha256(path) for name, path in sorted(inputs.items())
        },
        "output_sha256": output_hashes,
        "audit": audit,
    }
    paths["manifest"].write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(audit, indent=2, sort_keys=True))
    for key, path in paths.items():
        print(f"wrote {key}: {path}")
    print("No forecasts or post-period deviations were computed.")


if __name__ == "__main__":
    main()
