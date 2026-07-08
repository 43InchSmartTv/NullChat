import pytest

from nullchat.autocomplete.trie import Trie

@pytest.fixture
def trie():
    t = Trie()
    for word, freq in [("the", 500), ("they", 200), ("them", 150),
                       ("theme", 40), ("cat", 90), ("cap", 10)]:
        t.insert(word, freq)
    return t

def test_insert_and_contains(trie):
    assert "the" in trie
    assert "them" in trie
    assert "th" not in trie
    assert "dog" not in trie
    assert len(trie) == 6

def test_starts_with(trie):
    assert trie.starts_with("the")
    assert trie.starts_with("ca")
    assert not trie.starts_with("z")

def test_suggest_ranked_frequency(trie):
    assert trie.suggest("the", 3) == [("the", 500), ("they", 200), ("them", 150)]
