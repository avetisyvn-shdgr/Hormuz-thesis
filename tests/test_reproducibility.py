import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from freeze_reproducibility import raw_hashes, sha256_file


def test_sha256_file_is_stable(tmp_path):
    path = tmp_path / "x.txt"
    path.write_text("abc", encoding="utf-8")
    assert sha256_file(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_raw_hashes_excludes_manifests(tmp_path):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    (raw / "source.csv").write_text("x\n1\n", encoding="utf-8")
    (raw / ".gitkeep").write_text("", encoding="utf-8")
    (raw / "SHA256SUMS").write_text("old", encoding="utf-8")
    (raw / "provenance.jsonl").write_text("{}\n", encoding="utf-8")
    assert list(raw_hashes(tmp_path)) == ["data/raw/source.csv"]
