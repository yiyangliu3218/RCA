from __future__ import annotations
from typing import List, Tuple, Dict, Any


class TwistScorer:
    """
    Minimal TWIST-like scorer: combines simple proxies for four components.
    Returns list of (service_id, score, details)
    """

    def rank(self, kg) -> List[Tuple[str, float, Dict[str, Any]]]:
        G = kg.G
        scores: Dict[str, Dict[str, float]] = {}

        # self anomaly: count MetricEvent/LogEvent children
        for nid, data in G.nodes(data=True):
            if data.get("type") == "Service":
                scores[nid] = {"self": 0.0, "impact": 0.0, "spread": 0.0, "latency": 0.0}

        for u, v, d in G.edges(data=True):
            t = d.get("type")
            if t == "has_metric_anomaly" or t == "has_log":
                if u in scores:
                    scores[u]["self"] += 1.0

        # impact/spread: outgoing calls count and 2-hop neighborhood size
        for nid in scores.keys():
            out_calls = [e for e in G.out_edges(nid, data=True) if e[2].get("type") == "calls"]
            scores[nid]["impact"] = float(len(out_calls))
            # approximate spread: unique nodes within 2 hops via calls
            lvl1 = set(v for _, v, d in out_calls)
            lvl2 = set()
            for x in lvl1:
                lvl2.update(v for _, v, d in G.out_edges(x, data=True) if d.get("type") == "calls")
            scores[nid]["spread"] = float(len(lvl1 | lvl2))

        # latency severity proxy: average dt on precedes edges of its events
        from statistics import mean
        for nid in scores.keys():
            # find events belonging to this service
            events = [v for _, v, d in G.out_edges(nid, data=True) if d.get("type") in ("has_log", "has_metric_anomaly")]
            event_ids = set(events)
            dts = []
            for e in event_ids:
                for _u2, v2, d2 in G.out_edges(e, data=True):
                    if d2.get("type") == "precedes":
                        dt = d2.get("dt_seconds")
                        if isinstance(dt, (int, float)):
                            dts.append(float(dt))
            scores[nid]["latency"] = float(mean(dts)) if dts else 0.0

        # linear fusion
        result: List[Tuple[str, float, Dict[str, Any]]] = []
        for nid, comp in scores.items():
            score = 0.4 * comp["self"] + 0.3 * comp["impact"] + 0.2 * comp["spread"] + 0.1 * comp["latency"]
            result.append((nid, score, comp))

        result.sort(key=lambda x: x[1], reverse=True)
        return result


