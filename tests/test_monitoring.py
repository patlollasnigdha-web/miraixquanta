"""
Tests for MIRAI Monitoring, Metrics, and Alerting (M18)
"""

import pytest
from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.alert_manager import AlertManager, AlertSeverity
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.system_monitor import SystemMonitor


def test_metrics_collector():
    collector = MetricsCollector()

    # Timing
    collector.record_timing("api_latency", 120.0)
    collector.record_timing("api_latency", 150.0)
    collector.record_timing("api_latency", 80.0)

    # Counter
    collector.increment_counter("api_requests_total", 5)

    # Gauge
    collector.set_gauge("active_sessions", 3.0)

    # Errors
    collector.record_error("/test", "Test error", 500)

    summary = collector.get_metric_summary()
    assert "api_latency" in summary["timings"]
    assert summary["timings"]["api_latency"]["count"] == 3
    assert summary["counters"]["api_requests_total"] == 5.0
    assert summary["gauges"]["active_sessions"] == 3.0
    assert summary["recent_errors_count"] == 1


def test_alert_manager():
    alert_mgr = AlertManager(latency_threshold_ms=200.0, error_rate_threshold_pct=5.0)

    # Trigger manual alert
    a1 = alert_mgr.trigger_alert(
        title="High Memory Usage",
        description="RAM usage exceeded 90%",
        severity=AlertSeverity.WARNING,
        source="HostMonitor",
    )
    assert a1.alert_id is not None
    assert a1.acknowledged is False

    # Acknowledge
    ok = alert_mgr.acknowledge_alert(a1.alert_id)
    assert ok is True
    assert a1.acknowledged is True

    # Threshold evaluation
    metrics = {
        "error_rate_pct": 10.0,
        "timings": {
            "model_inference": {"p95_ms": 350.0}
        }
    }
    new_alerts = alert_mgr.evaluate_metrics(metrics)
    assert len(new_alerts) == 2


def test_health_monitor():
    monitor = HealthMonitor()
    report = monitor.check_all()
    assert report.version is not None
    assert "backend" in report.components
    assert "database" in report.components
    assert "ollama" in report.components
    assert "models" in report.components


def test_system_monitor():
    sys_mon = SystemMonitor()
    usage = sys_mon.get_resource_usage()
    assert usage.disk_percent >= 0.0
    summary = sys_mon.get_system_summary()
    assert "resources" in summary
    assert "pid" in summary
