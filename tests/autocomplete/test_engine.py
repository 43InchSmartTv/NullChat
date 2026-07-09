import pytest

from nullchat.autocomplete.engine import AutocompleteEngine

COUNTS = {"hello": 100, "help": 80, "hero": 20, "world": 50}

@pytest.mark.parametrize("backend", ["trie", "tst"])
def test_suggest_last_word(backend):
    engine = AutocompleteEngine.from_counts(COUNTS, backend=backend, limit=3)
    assert engine.suggest("say hel") == ["hello", "help"]

def test_unknown_backend_rejected():
    with pytest.raises(ValueError):
        AutocompleteEngine.from_counts(COUNTS, backend="avl")