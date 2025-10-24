from __future__ import annotations
from typing import Any


class SlidingWindow:
    def __init__(self, size_minutes: int = 60, gc_strategy: str = "none"):
        self.size_minutes = size_minutes
        self.gc_strategy = gc_strategy

    def evict_old(self, kg: Any):
        # Placeholder: no-op for now
        return


