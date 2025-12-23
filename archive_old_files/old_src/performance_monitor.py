"""
PerformanceMonitor: مراقبة الأداء وزمن المراحل مع كشف عنق الزجاجة.
- قياس FPS
- استخدام CPU/Memory (وGPU إن توفرت عبر torch)
- زمن كل مرحلة start/end
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

import psutil

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class StageStat:
    total_time: float = 0.0
    count: int = 0
    last_start: Optional[float] = None


class PerformanceMonitor:
    """مدير قياس أداء بسيط."""

    def __init__(self, fps_window: int = 60) -> None:
        self.stage_stats: Dict[str, StageStat] = defaultdict(StageStat)
        self.frame_times: Deque[float] = deque(maxlen=fps_window)
        self.last_frame_time: Optional[float] = None

    def start_timer(self, stage_name: str) -> None:
        s = self.stage_stats[stage_name]
        s.last_start = time.perf_counter()

    def end_timer(self, stage_name: str) -> None:
        now = time.perf_counter()
        s = self.stage_stats[stage_name]
        if s.last_start is None:
            return
        dt = now - s.last_start
        s.total_time += dt
        s.count += 1
        s.last_start = None

    def mark_frame(self) -> None:
        now = time.perf_counter()
        if self.last_frame_time is not None:
            self.frame_times.append(now - self.last_frame_time)
        self.last_frame_time = now

    def _gpu_usage(self) -> Optional[float]:
        try:
            if torch is not None and torch.cuda.is_available():
                # لا يوجد API رسمي سهل ل% الاستهلاك بدون NVML. نرجّع None لتبسيط.
                return None
        except Exception:
            return None
        return None

    def get_statistics(self) -> Dict[str, object]:
        # FPS متوسط على النافذة
        fps = 0.0
        if self.frame_times:
            avg_dt = sum(self.frame_times) / len(self.frame_times)
            if avg_dt > 0:
                fps = 1.0 / avg_dt
        # CPU/Memory
        cpu = float(psutil.cpu_percent(interval=0.0))
        mem = float(psutil.virtual_memory().percent)
        # أزمنة المراحل
        stages = {}
        for k, v in self.stage_stats.items():
            avg = (v.total_time / v.count) if v.count else 0.0
            stages[k] = {"avg_ms": round(avg * 1000, 3), "count": v.count}
        # عنق الزجاجة: أكبر متوسط زمن
        bottleneck = None
        if stages:
            bottleneck = max(stages.items(), key=lambda x: x[1]["avg_ms"])[0]
        return {"fps": round(fps, 2), "cpu_percent": cpu, "mem_percent": mem, "stages": stages, "bottleneck": bottleneck}

    def print_report(self) -> None:
        stats = self.get_statistics()
        logger.info("FPS=%.2f | CPU=%.0f%% | MEM=%.0f%% | Bottleneck=%s", stats["fps"], stats["cpu_percent"], stats["mem_percent"], stats.get("bottleneck"))
        for name, s in stats["stages"].items():
            logger.info(" - %s: avg %.2f ms (%d)", name, s["avg_ms"], s["count"]) 
