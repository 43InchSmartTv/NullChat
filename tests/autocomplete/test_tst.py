import pytest

from nullchat.autocomplete.tst import TernarySearchTree


@pytest.fixture
def tst():
    t = TernarySearchTree()
    for word, freq in [("the", 500), ("they", 200), ("them", 150),
                       ("theme", 40), ("cat", 90), ("cap", 10)]:
        t.insert(word, freq)
    return t

def test_insert_and_contains(tst):
    assert "the" in tst
    assert "theme" in tst
    assert "th" not in tst
    assert "dog" not in tst
    assert len(tst) == 6

def test_starts_with(tst):
    assert tst.starts_with("the")
    assert tst.starts_with("ca")
    assert not tst.starts_with("z")

def test_suggest_ranked_by_frequency(tst):
    assert tst.suggest("the", 3) == [("the", 500), ("they", 200), ("them", 150)]
    assert tst.suggest("zzz") == []
