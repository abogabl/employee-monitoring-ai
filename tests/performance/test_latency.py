from __future__ import annotations

import time

from src.performance_monitor import PerformanceMonitor


def test_stage_timers_latency():
    pm = PerformanceMonitor()
    pm.start_timer("stage")
    time.sleep(0.02)
    pm.end_timer("stage")
    stats = pm.get_statistics()
    st = stats["stages"].get("stage", {})
    assert st.get("avg_ms", 0) >= 15  # ~20ms
