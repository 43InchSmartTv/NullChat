from __future__ import annotations

import gzip
import random
import string
from collections.abc import Iterable
from pathlib import Path

def _clean_token(token: str) -> str | None:
    word = token.lower()
    if not word.isalpha() or not word.isascii():
        return None
    return word


def _parse_line(line: str) -> tuple[str, int] | None:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2:
        return None

    word = _clean_token(parts[0])
    if word is None:
        return None

    total = 0
    if "," in parts[1]:
        #v3 format is l word \t year,match_count,volume_count
        for triple in parts[1:]:
            fields = triple.split(",")
            if len(fields) >= 2:
                try:
                    total += int(fields[1])
                except ValueError:
                    continue
    else:
        return None

    return (word, total) if total > 0 else None



def _open_maybe_gzip(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, "r", encoding="utf-8", errors="ignore")


def load_ngram_counts(
    ## reserved for using .gz files // benchmarking
    paths: Iterable[str | Path],
    min_count: int = 1,
    max_words: int | None = None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_path in paths:
        path = Path(raw_path)
        with _open_maybe_gzip(path) as handle:
            for line in handle:
                parsed = _parse_line(line)
                if parsed is None:
                    continue
                word, count = parsed
                counts[word] = counts.get(word, 0) + count

    if min_count > 1:
        counts = {w: c for w, c in counts.items() if c >= min_count}
    if max_words is not None and len(counts) > max_words:
        top = sorted(counts.items(), key=lambda it: -it[1])[:max_words]
        counts = dict(top)
    return counts

def load_counts_table(path):
    ## reserved for vocab.tsv.gz file // app
    counts = {}
    with _open_maybe_gzip(Path(path)) as f:
        for line in f:
            word, _, count = line.rstrip("\n").partition("\t")
            if word and count:
                counts[word] = int(count)
    return counts
