from __future__ import annotations
from typing import List, Tuple, Dict, Any


class ReRankingAgent:
    """Simple re-ranking utility with a short history of updates."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def pick_next(self, ranking: List[Tuple[str, float, Dict[str, Any]]]) -> str:
        """Pick the next candidate to inspect: the top with largest margin over 2nd."""
        if not ranking:
            return ""
        if len(ranking) == 1:
            return ranking[0][0]
        # choose the one with biggest score gap to next item among top-5
        topk = ranking[:5]
        idx = 0
        best_gap = -1.0
        for i in range(min(4, len(topk) - 1)):
            gap = topk[i][1] - topk[i + 1][1]
            if gap > best_gap:
                best_gap = gap
                idx = i
        return topk[idx][0]

    def update(self, ranking: List[Tuple[str, float, Dict[str, Any]]], candidate: str, summary: Dict[str, Any]) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Adjust the candidate's score based on summary confidence (0~1)."""
        conf = float(summary.get("confidence", 0.5))
        bonus = (conf - 0.5) * 0.5  # [-0.25, +0.25]
        new_ranking: List[Tuple[str, float, Dict[str, Any]]] = []
        for nid, score, details in ranking:
            if nid == candidate:
                new_ranking.append((nid, score + bonus, details))
            else:
                new_ranking.append((nid, score, details))
        new_ranking.sort(key=lambda x: x[1], reverse=True)

        self._history.append({"candidate": candidate, "conf": conf, "bonus": bonus})
        return new_ranking

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)


