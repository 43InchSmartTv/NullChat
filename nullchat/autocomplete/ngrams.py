from __future__ import annotations

import gzip
from pathlib import Path

def _open_maybe_gzip(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")

def load_counts_table(path: str | Path) -> dict[str, int]:
    counts = {}
    with _open_maybe_gzip(Path(path)) as f:
        for line in f:
            word, _, count = line.rstrip("\n").partition("\t")
            if not word or not count:
                continue
            try:
                counts[word] = int(count)
            except ValueError:
                continue
    return counts
