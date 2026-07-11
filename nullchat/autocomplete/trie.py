from __future__ import annotations

import heapq


class TrieNode:
    __slots__ = ("children", "frequency", "is_word")

    def __init__(self) -> None:
        self.children: dict[str, TrieNode] = {}
        self.frequency: int = 0
        self.is_word: bool = False


class Trie:
    def __init__(self) -> None:
        self._root = TrieNode()
        self._word_count = 0
        self._node_count = 1  # root

    def __len__(self) -> int:
        return self._word_count

    def __contains__(self, word: str) -> bool:
        node = self._walk(word)
        return node is not None and node.is_word

    def node_count(self) -> int:  # memory comparison
        return self._node_count

    def insert(self, word: str, frequency: int = 1) -> None:
        if not word:
            return
        node = self._root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                child = TrieNode()
                node.children[ch] = child
                self._node_count += 1
            node = child
        if not node.is_word:
            node.is_word = True
            self._word_count += 1
        node.frequency += frequency

    def frequency(self, word: str) -> int:
        node = self._walk(word)
        return node.frequency if node is not None and node.is_word else 0

    def starts_with(self, prefix: str) -> bool:
        return not prefix or self._walk(prefix) is not None

    def suggest(self, prefix: str, limit: int = 5) -> list[tuple[str, int]]:
        # most frequent first
        if not prefix:
            return[]
        start = self._walk(prefix)
        if start is None or limit <= 0:
            return []

        heap: list[tuple[int, str]] = []  # keeps the current top-k
        stack: list[tuple[TrieNode, str]] = [(start, prefix)]
        while stack:
            node, word = stack.pop()
            if node.is_word:
                item = (node.frequency, word)
                if len(heap) < limit:
                    heapq.heappush(heap, item)
                elif item > heap[0]:
                    heapq.heapreplace(heap, item)
            for ch, child in node.children.items():
                stack.append((child, word + ch))

        ranked = sorted(heap, key=lambda it: (-it[0], it[1]))
        return [(word, freq) for freq, word in ranked]

    def _walk(self, prefix: str) -> TrieNode | None:  # follow prefix
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node
