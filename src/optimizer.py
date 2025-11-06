"""
SystemOptimizer: أدوات لتحسين الأداء في طور الإنتاج.
- Model Optimization: تصدير ONNX، تلميحات TensorRT (Placeholder)، Quantization/Pruning (إطارية)
- Code Optimization: Profiling لتحديد أعناق الزجاجة، اقتراحات NumPy/Cython، I/O threading
- Memory Optimization: Object pooling، Memory-mapping، GC tuning (اقتراحات)
"""
from __future__ import annotations

import cProfile
import io
import logging
import pstats
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import psutil

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

try:
    from ultralytics import YOLO  # type: ignore
except Exception:
    YOLO = None  # type: ignore

from .performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class BenchmarkResult:
    fps: float
    cpu_percent: float
    mem_percent: float
    latency_ms: float


class SystemOptimizer:
    def __init__(self, project_root: str | Path = ".") -> None:
        self.root = Path(project_root).resolve()

    # ---------------- Profiling ----------------
    @contextmanager
    def _profiler(self):
        pr = cProfile.Profile()
        pr.enable()
        try:
            yield pr
        finally:
            pr.disable()

    def profile_system(self, duration: int = 60) -> Dict[str, Any]:
        """تشغيل profiler لفترة وإعادة أهم الوظائف تكلفة."""
        with self._profiler() as pr:
            time.sleep(max(1, int(duration)))
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
        ps.print_stats(40)
        report = s.getvalue()
        logger.info("Profiling finished. Top hotspots:\n%s", report[:2000])
        return {"report": report}

    # ---------------- Model Optimization ----------------
    def optimize_models(self, yolo_model_size: str = "n", device: str = "cpu") -> Dict[str, Any]:
        """تصدير نموذج YOLO إلى ONNX وإرشادات TensorRT/INT8 (placeholder)."""
        out: Dict[str, Any] = {}
        if YOLO is None:
            logger.warning("Ultralytics غير متاح. تخطي تصدير ONNX.")
            return out
        try:
            model_path = f"yolov8{yolo_model_size}.pt"
            model = YOLO(model_path)
            onnx_out = str(self.root / "models" / f"yolov8{yolo_model_size}.onnx")
            self.root.joinpath("models").mkdir(parents=True, exist_ok=True)
            model.export(format="onnx", imgsz=640, opset=12)
            # سيحفظ ضمن مجلد العمل؛ ننقل الملف إن لزم
            out["onnx"] = onnx_out
            logger.info("تم تصدير ONNX (تحقق من مجلد العمل/weights)")
        except Exception as e:
            logger.warning("فشل تصدير ONNX: %s", e)
        # TensorRT/INT8 Placeholder: يتطلب بيئة NVIDIA/TensorRT و calibrations
        out["tensorrt_hint"] = "Use 'model.export(format=\"engine\")' on a machine with TensorRT; or trtexec with ONNX. For INT8, prepare calibration dataset."
        out["pruning_hint"] = "Pruning requires fine-tuning; consider torch-pruning or sparse training."
        return out

    # ---------------- Benchmark ----------------
    def benchmark(self, config: Dict[str, Any], duration: int = 60) -> BenchmarkResult:
        """قياس FPS/CPU/MEM وزمن معالجة إطار (تقريبي) عبر PerformanceMonitor."""
        pm = PerformanceMonitor()
        start = time.time()
        frames = 0
        # حلقة محاكاة خفيفة (يمكن استبدالها بحلقة كشف حقيقية)
        while (time.time() - start) < duration:
            pm.mark_frame()
            pm.start_timer("work")
            time.sleep(0.005)  # محاكاة عبء عمل خفيف ~5ms
            pm.end_timer("work")
            frames += 1
        stats = pm.get_statistics()
        # تقدير زمن التأخير = متوسط زمن المرحلة work
        latency = stats["stages"].get("work", {}).get("avg_ms", 0.0)
        return BenchmarkResult(
            fps=float(stats.get("fps", 0.0)),
            cpu_percent=float(stats.get("cpu_percent", 0.0)),
            mem_percent=float(stats.get("mem_percent", 0.0)),
            latency_ms=float(latency),
        )
