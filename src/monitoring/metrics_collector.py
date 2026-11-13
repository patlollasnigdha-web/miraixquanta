"""
MIRAI — Metrics Collector (M18)
Thread-safe collection and aggregation of API latencies, inference times,
error rates, and quantitative pipeline operational counters.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
from typing import Any, Dict, List, Optional
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("MetricsCollector")


class MetricsCollector:
    """
    Central in-memory metrics aggregation engine.
    Maintains rolling time-series samples for latencies, counts, and error tracking.
    """

    def __init__(self, window_seconds: int = 3600, max_samples_per_metric: int = 2000):
        self.window_seconds = window_seconds
        self.max_samples = max_samples_per_metric
        self._lock = threading.Lock()

        # Storage
        self._timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_samples))
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._recent_errors: deque = deque(maxlen=200)

    def record_timing(self, metric_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Records an execution latency sample in milliseconds."""
        sample = {
            "value": float(duration_ms),
            "timestamp": datetime.utcnow(),
            "tags": tags or {},
        }
        with self._lock:
            self._timings[metric_name].append(sample)

    def increment_counter(self, metric_name: str, count: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        """Increments an operational counter."""
        with self._lock:
            self._counters[metric_name] += float(count)

    def set_gauge(self, metric_name: str, value: float) -> None:
        """Sets current instantaneous value for a gauge."""
        with self._lock:
            self._gauges[metric_name] = float(value)

    def record_error(self, endpoint: str, error_msg: str, status_code: int = 500) -> None:
        """Records an API or subsystem error event."""
        err_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "error": str(error_msg),
            "status_code": status_code,
        }
        with self._lock:
            self._recent_errors.append(err_entry)
            self._counters["api_errors_total"] += 1

    def get_metric_summary(self) -> Dict[str, Any]:
        """
        Computes summary statistics (p50, p95, p99, mean, max) for timings
        and exports current counters and gauges.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        summary: Dict[str, Any] = {
            "timings": {},
            "counters": {},
            "gauges": {},
            "error_rate_pct": 0.0,
            "recent_errors_count": 0,
        }

        with self._lock:
            # 1. Summarize timings
            for name, samples in self._timings.items():
                recent_vals = [s["value"] for s in samples if s["timestamp"] >= cutoff]
                if recent_vals:
                    summary["timings"][name] = {
                        "count": len(recent_vals),
                        "mean_ms": round(float(np.mean(recent_vals)), 2),
                        "median_ms": round(float(np.median(recent_vals)), 2),
                        "p95_ms": round(float(np.percentile(recent_vals, 95)), 2),
                        "max_ms": round(float(np.max(recent_vals)), 2),
                    }
                else:
                    summary["timings"][name] = {"count": 0, "mean_ms": 0.0, "p95_ms": 0.0}

            # 2. Counters
            summary["counters"] = dict(self._counters)

            # 3. Gauges
            summary["gauges"] = dict(self._gauges)

            # 4. Error rate
            total_requests = self._counters.get("api_requests_total", 0.0)
            total_errors = self._counters.get("api_errors_total", 0.0)
            if total_requests > 0:
                summary["error_rate_pct"] = round((total_errors / total_requests) * 100.0, 2)
            summary["recent_errors_count"] = len(self._recent_errors)

        return summary

    def get_recent_errors(self) -> List[Dict[str, Any]]:
        """Returns snapshot of recent error occurrences."""
        with self._lock:
            return list(self._recent_errors)

    def reset(self) -> None:
        """Clears all in-memory metrics."""
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._gauges.clear()
            self._recent_errors.clear()


# Global shared instance
default_metrics = MetricsCollector()
