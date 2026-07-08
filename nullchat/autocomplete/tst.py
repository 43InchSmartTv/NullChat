from __future__ import annotations

import heapq


class TSTNode:
    __slots__ = ("char", "lo", "eq", "hi", "frequency", "is_word")

    def __init__(self, char: str) -> None:
        self.char = char
        self.lo: TSTNode | None = None   # subtree with chars < self.char
        self.eq: TSTNode | None = None   # subtree for the next character of the key
        self.hi: TSTNode | None = None   # subtree with chars > self.char
        self.frequency: int = 0
        self.is_word: bool = False


class TernarySearchTree:
    def __init__(self) -> None:
        self._root: TSTNode | None = None
        self._word_count = 0
        self._node_count = 0

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
        if self._root is None:
            self._root = TSTNode(word[0])
            self._node_count += 1
        node = self._root
        i = 0
        while True:
            ch = word[i]
            if ch < node.char:
                if node.lo is None:
                    node.lo = TSTNode(ch)
                    self._node_count += 1
                node = node.lo
            elif ch > node.char:
                if node.hi is None:
                    node.hi = TSTNode(ch)
                    self._node_count += 1
                node = node.hi
            elif i + 1 < len(word):
                if node.eq is None:
                    node.eq = TSTNode(word[i + 1])
                    self._node_count += 1
                node = node.eq
                i += 1
            else:
                if not node.is_word:
                    node.is_word = True
                    self._word_count += 1
                node.frequency += frequency
                return

    def frequency(self, word: str) -> int:
        node = self._walk(word)
        return node.frequency if node is not None and node.is_word else 0

    def starts_with(self, prefix: str) -> bool:
        return self._walk(prefix) is not None

    def suggest(self, prefix: str, limit: int = 5) -> list[tuple[str, int]]:
        if not prefix or limit <= 0:
            return []
        end = self._walk(prefix)
        if end is None:
            return []

        heap: list[tuple[int, str]] = []

        def offer(frequency: int, word: str) -> None:
            item = (frequency, word)
            if len(heap) < limit:
                heapq.heappush(heap, item)
            elif item > heap[0]:
                heapq.heapreplace(heap, item)

        if end.is_word:
            offer(end.frequency, prefix)

        # stack traversal
        stack: list[tuple[TSTNode, str]] = []
        if end.eq is not None:
            stack.append((end.eq, prefix))
        while stack:
            node, built = stack.pop()
            if node.is_word:
                offer(node.frequency, built + node.char)
            if node.lo is not None:
                stack.append((node.lo, built))
            if node.hi is not None:
                stack.append((node.hi, built))
            if node.eq is not None:
                stack.append((node.eq, built + node.char))

        ranked = sorted(heap, key=lambda it: (-it[0], it[1]))
        return [(word, freq) for freq, word in ranked]

    def _walk(self, prefix: str) -> TSTNode | None:
        if not prefix:
            return None
        node = self._root
        i = 0
        while node is not None:
            ch = prefix[i]
            if ch < node.char:
                node = node.lo
            elif ch > node.char:
                node = node.hi
            elif i + 1 < len(prefix):
                node = node.eq
                i += 1
            else:
                return node
        return None
