"""LRU cache for parsed schedules, keyed by (path, mtime, size)."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LruCache(Generic[K, V]):
    """A small ordered-dict LRU (thread safety not required: MCP servers are
    single-threaded per session; HTTP mode uses per-request event-loop tasks)."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        self._data: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V | None:
        v = self._data.get(key)
        if v is not None:
            self._data.move_to_end(key)
        return v

    def put(self, key: K, value: V) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def pop(self, key: K) -> V | None:
        return self._data.pop(key, None)

    def clear(self) -> int:
        n = len(self._data)
        self._data.clear()
        return n

    def values(self) -> list[V]:
        return list(self._data.values())

    def __len__(self) -> int:
        return len(self._data)
