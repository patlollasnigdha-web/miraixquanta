"""
MIRAI — System Monitor (M18)
Monitors host resources (CPU, RAM, Disk) and runtime state.
"""

from datetime import datetime
import os
import shutil
from typing import Any, Dict, Optional

from src.utils.logger import get_logger
from src.monitoring.monitoring_schemas import SystemResourceUsage

logger = get_logger("SystemMonitor")


class SystemMonitor:
    """
    Collects system performance and host resource utilization safely.
    """

    def get_resource_usage(self) -> SystemResourceUsage:
        """Collects current host CPU, memory, and disk usage percentages."""
        cpu_pct = 0.0
        mem_pct = 0.0

        # Try psutil if available
        try:
            import psutil
            cpu_pct = float(psutil.cpu_percent(interval=None))
            mem = psutil.virtual_memory()
            mem_pct = float(mem.percent)
        except Exception:
            cpu_pct = 0.0
            mem_pct = 0.0

        # Disk usage via shutil.disk_usage
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            disk_pct = round((used / total) * 100.0, 1) if total > 0 else 0.0
        except Exception:
            disk_pct = 0.0

        return SystemResourceUsage(
            cpu_percent=cpu_pct,
            memory_percent=mem_pct,
            disk_percent=disk_pct,
            timestamp=datetime.utcnow(),
        )

    def get_system_summary(self) -> Dict[str, Any]:
        """Provides high-level system diagnostics dictionary."""
        usage = self.get_resource_usage()
        return {
            "resources": usage.to_dict(),
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global shared instance
default_system_monitor = SystemMonitor()
