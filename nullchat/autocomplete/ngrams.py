# !! this is the connection between the backend and frontend

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from nullchat.autocomplete.trie import Trie
from nullchat.autocomplete.tst import TernarySearchTree


class SuggestionStructure(Protocol):
    def insert(self, word: str, frequency: int = ...) -> None: ...
    def suggest(self, prefix: str, limit: int = ...) -> list[tuple[str, int]]: ...


class AutocompleteEngine:
    def __init__(self, structure: SuggestionStructure | None = None, limit: int = 5):
        self._structure: SuggestionStructure = structure if structure is not None else Trie()
        self._limit = limit

    @classmethod
    def from_counts(
        cls,
        counts: Mapping[str, int],
        backend: str = "trie",
        limit: int = 5,
    ) -> AutocompleteEngine:
        structure: SuggestionStructure
        if backend == "trie":
            structure = Trie()
        elif backend == "tst":
            structure = TernarySearchTree()
        else:
            raise ValueError(f"unknown backend: {backend!r}")
        engine = cls(structure, limit=limit)
        for word, count in counts.items():
            structure.insert(word, count)
        return engine

    def suggest(self, draft: str) -> list[str]:
        # !! complete the word currently being typed !! call on every keystroke
        if not draft or draft[-1].isspace():
            return []
        prefix = draft.split()[-1].lower()
        if not prefix.isalpha():
            return []
        return [word for word, _ in self._structure.suggest(prefix, self._limit)]
