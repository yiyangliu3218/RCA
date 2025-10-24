from __future__ import annotations
from typing import List, Dict, Any, Iterable
import time


class Event(dict):
    pass


class Streamer:
    """Placeholder file-based streamer: yields empty batches at fixed interval."""

    def __init__(self, every_seconds: float = 5.0):
        self.every_seconds = every_seconds

    def iter_batches(self, max_iters: int = 1) -> Iterable[List[Event]]:
        for _ in range(max_iters):
            time.sleep(max(0.0, self.every_seconds))
            yield []


