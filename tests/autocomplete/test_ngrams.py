import gzip

from nullchat.autocomplete.ngrams import load_counts_table


def test_load_plain_tsv(tmp_path):
    f = tmp_path / "vocab.tsv"
    f.write_text("hello\t500\nworld\t200\nhelp\t80\n")
    assert load_counts_table(f) == {"hello": 500, "world": 200, "help": 80}

def test_load_gzipped_tsv(tmp_path):
    f = tmp_path / "vocab.tsv.gz"
    with gzip.open(f, "wt", encoding="utf-8") as handle:
        handle.write("chat\t25\nnull\t7\n")
    assert load_counts_table(f) == {"chat": 25, "null": 7}

def test_blank_and_malformed_lines_skipped(tmp_path):
    f = tmp_path / "vocab.tsv"
    f.write_text("good\t10\n\nnocount\nalso_good\t5\n")
    assert load_counts_table(f) == {"good": 10, "also_good": 5}

def test_empty_file(tmp_path):
    f = tmp_path / "vocab.tsv"
    f.write_text("")
    assert load_counts_table(f) == {}