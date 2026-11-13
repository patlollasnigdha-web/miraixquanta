"""
MIRAI — Alert Manager (M18)
Monitors operational metric thresholds, triggers prioritized alerts,
and tracks system warning/critical events.
"""

from collections import deque
from datetime import datetime
import threading
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger
from src.monitoring.monitoring_schemas import Alert, AlertSeverity

logger = get_logger("AlertManager")


class AlertManager:
    """
    Evaluates system anomalies, operational limits, and risk breaker events.
    Thread-safe alert dispatch and acknowledgment.
    """

    def __init__(
        self,
        latency_threshold_ms: float = 1000.0,
        error_rate_threshold_pct: float = 5.0,
        max_alerts: int = 500,
    ):
        self.latency_threshold_ms = float(latency_threshold_ms)
        self.error_rate_threshold_pct = float(error_rate_threshold_pct)
        self.max_alerts = max_alerts
        self._lock = threading.Lock()
        self._alerts: deque = deque(maxlen=self.max_alerts)

    def trigger_alert(
        self,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: str,
    ) -> Alert:
        """Publishes a new alert to the active stream."""
        alert = Alert(
            title=title,
            description=description,
            severity=severity,
            source=source,
            timestamp=datetime.utcnow(),
        )
        with self._lock:
            self._alerts.append(alert)

        log_fn = logger.critical if severity == AlertSeverity.CRITICAL else (
            logger.warning if severity == AlertSeverity.WARNING else logger.info
        )
        log_fn("[%s Alert from %s] %s: %s", severity.value, source, title, description)
        return alert

    def evaluate_metrics(self, metric_summary: Dict[str, Any]) -> List[Alert]:
        """
        Evaluates current metrics summary against configured thresholds.
        Triggers alerts if violations are detected.
        """
        new_alerts = []

        # 1. Error Rate check
        err_rate = metric_summary.get("error_rate_pct", 0.0)
        if err_rate > self.error_rate_threshold_pct:
            alert = self.trigger_alert(
                title="Elevated API Error Rate",
                description=f"Current API error rate is {err_rate:.2f}%, exceeding threshold {self.error_rate_threshold_pct:.2f}%",
                severity=AlertSeverity.WARNING,
                source="MetricsMonitor",
            )
            new_alerts.append(alert)

        # 2. High latency checks
        timings = metric_summary.get("timings", {})
        for metric_name, stats in timings.items():
            p95 = stats.get("p95_ms", 0.0)
            if p95 > self.latency_threshold_ms:
                alert = self.trigger_alert(
                    title=f"High Latency in {metric_name}",
                    description=f"p95 latency is {p95:.2f}ms, exceeding threshold {self.latency_threshold_ms:.2f}ms",
                    severity=AlertSeverity.WARNING,
                    source="LatencyMonitor",
                )
                new_alerts.append(alert)

        return new_alerts

    def get_all_alerts(self, limit: int = 50, include_acknowledged: bool = True) -> List[Alert]:
        """Returns recent alerts in reverse chronological order."""
        with self._lock:
            alerts = list(self._alerts)
        if not include_acknowledged:
            alerts = [a for a in alerts if not a.acknowledged]
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marks an alert as acknowledged."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    logger.info("Alert %s acknowledged", alert_id)
                    return True
        return False

    def clear(self) -> None:
        """Clears all registered alerts."""
        with self._lock:
            self._alerts.clear()


# Global shared instance
default_alerts = AlertManager()
