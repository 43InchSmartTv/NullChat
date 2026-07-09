# to use: python -m benchmarks.benchmark_autocomplete

import random
import time
import tracemalloc
from pathlib import Path

from nullchat.autocomplete.trie import Trie
from nullchat.autocomplete.tst import TernarySearchTree
from nullchat.autocomplete.ngrams import load_counts_table

VOCAB_PATH = Path(__file__).resolve().parent.parent / "nullchat" / "autocomplete" / "vocab.tsv.gz"
SUGGEST_LIMIT = 5
LOOKUP_SAMPLE = 20_000
PREFIX_SAMPLE = 2_000
SEED = 3530


def check_same_results(counts):
    trie, tst = Trie(), TernarySearchTree()
    for word, count in counts.items():
        trie.insert(word, count)
        tst.insert(word, count)

    rng = random.Random(SEED)
    words = list(counts)
    for _ in range(200):
        prefix = rng.choice(words)[: rng.randint(1, 4)]
        if trie.suggest(prefix, SUGGEST_LIMIT) != tst.suggest(prefix, SUGGEST_LIMIT):
            raise AssertionError(f"structures are different on {prefix!r}")
    print("correctness check passed\n")


def benchmark(name, structure, items, lookup_words, prefixes):
    tracemalloc.start()

    start = time.perf_counter()
    for word, count in items:
        structure.insert(word, count)
    insert_secs = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    start = time.perf_counter()
    for word in lookup_words:
        structure.frequency(word)
    lookup_secs = time.perf_counter() - start

    start = time.perf_counter()
    for prefix in prefixes:
        structure.suggest(prefix, SUGGEST_LIMIT)
    suggest_secs = time.perf_counter() - start

    print(f"{name:<10}{len(items) / insert_secs:>13,.0f}"
          f"{len(lookup_words) / lookup_secs:>13,.0f}"
          f"{len(prefixes) / suggest_secs:>13,.0f}"
          f"{peak / (1024 * 1024):>10.1f}")


def main():
    counts = load_counts_table(VOCAB_PATH)
    print(f"loaded {len(counts):,} words from {VOCAB_PATH.name}\n")

    check_same_results(counts)

    rng = random.Random(SEED)
    items = list(counts.items())
    rng.shuffle(items) # for tst

    words = [word for word, _ in items]
    lookup_words = rng.sample(words, min(LOOKUP_SAMPLE, len(words)))
    prefixes = [rng.choice(words)[: rng.randint(1, 6)] for _ in range(PREFIX_SAMPLE)]

    print(f"{'structure':<10}{'insert/s':>13}{'lookup/s':>13}{'suggest/s':>13}{'peak MB':>10}")
    print("-" * 59)
    benchmark("trie", Trie(), items, lookup_words, prefixes)
    benchmark("tst", TernarySearchTree(), items, lookup_words, prefixes)


if __name__ == "__main__":
    main()