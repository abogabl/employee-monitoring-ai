"""
main_production.py
السكريبت الرئيسي لتشغيل بايبلاين النظام في وضع الإنتاج:
Frame → Person Detection → Tracking → Face Recognition → Activity Recognition → Time Tracking → Attendance Update → Display/Save

خيارات:
python main_production.py \
    --source video.mp4 \
    --camera-id cam1 \
    --device cpu \
    --imgsz 640 \
    --conf 0.5 \
    --enable-face-recognition \
    --enable-activity-recognition \
    --enable-attendance \
    --grace-seconds 60 \
    --report-interval 300 \
    --output-video results/output.mp4 \
    --display \
    --fps-limit 30
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from tqdm import tqdm

from .detection_tracking import PersonDetector, PersonTracker
from .face_recognition_system import FaceRecognitionSystem
from .activity_recognition import ActivityRecognizer
from .level2_video_processor import Level2VideoProcessor
from .reid import ReIDSystem
from .attendance_system import AttendanceSystem
from .attendance_manager import AttendanceManager
from .performance_monitor import PerformanceMonitor
from .error_handler import ErrorHandler, RetryPolicy
from .time_tracking import TimeTracker
from .utils import crop_person, draw_text_with_background

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("main_production")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI Employee Monitoring - Production")
    p.add_argument("--source", default="videos/sample.mp4", help="فيديو/كاميرا: مسار ملف أو 0 للكاميرا أو rtsp://")
    p.add_argument("--camera-id", default="cam1", help="معرف الكاميرا")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="جهاز تنفيذ YOLO")
    p.add_argument("--yolo-size", default="m", choices=["n", "s", "m", "l", "x"], help="حجم نموذج YOLO")
    p.add_argument("--imgsz", type=int, default=640, help="حجم الإدخال لليولو")
    p.add_argument("--conf", type=float, default=0.35, help="عتبة الثقة لليولو")
    p.add_argument("--iou", type=float, default=0.5, help="عتبة IOU لـ NMS")
    p.add_argument("--enable-face-recognition", action="store_true")
    p.add_argument("--enable-activity-recognition", action="store_true")
    p.add_argument("--enable-attendance", action="store_true")
    p.add_argument("--grace-seconds", type=int, default=60)
    p.add_argument("--report-interval", type=int, default=300, help="بالثواني")
    p.add_argument("--output-video", default="", help="مسار حفظ الفيديو الناتج (اختياري)")
    p.add_argument("--display", action="store_true", help="عرض الفيديو")
    p.add_argument("--fps-limit", type=float, default=0.0, help="حد أقصى FPS، 0 لتعطيله")
    p.add_argument("--threads", type=int, default=0, help="عدد خيوط المعالجة الإضافية (0 = تسلسلي)")
    p.add_argument("--activity-window", type=int, default=15, help="نافذة التنعيم الزمني للأنشطة (إطارات)")
    p.add_argument("--use-ema", action="store_true", help="استخدام EMA بدلاً من majority vote للتنعيم")
    p.add_argument("--ema-alpha", type=float, default=0.2, help="معامل alpha لـ EMA")
    return p.parse_args()


def open_source(src: str) -> cv2.VideoCapture:
    try:
        if src.isdigit():
            cap = cv2.VideoCapture(int(src))
        else:
            cap = cv2.VideoCapture(src)
        return cap
    except Exception as e:
        logger.exception("تعذّر فتح المصدر %s: %s", src, e)
        raise


class GracefulKiller:
    def __init__(self) -> None:
        self.stop = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args: Any) -> None:  # noqa: ARG002
        self.stop = True


def main() -> None:
    args = parse_args()

    # تحميل إعدادات من config.json إن أردت (اختياري)
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            # تطبيق قيم افتراضية فقط إن لم يمرر المستخدم
            if args.imgsz == 640:
                args.imgsz = int(cfg.get("yolo", {}).get("imgsz", args.imgsz))
            if args.conf == 0.5:
                args.conf = float(cfg.get("yolo", {}).get("confidence", args.conf))
        except Exception:
            pass

    # مكونات أساسية
    perf = PerformanceMonitor()
    errors = ErrorHandler()

    detector = PersonDetector(model_size=args.yolo_size, device=args.device, conf=args.conf, iou=args.iou, imgsz=args.imgsz, half=(args.device == "cuda"))
    # تتبع أكثر ثباتاً: تحمّل اختفاء أطول ومسافة مطابقة أصغر
    tracker = PersonTracker(max_disappeared=60, max_distance=25)

    frs = None
    if args.enable_face_recognition:
        try:
            # تحميل إعدادات التعرف على الوجوه من config إن وجدت
            face_threshold = 0.7  # القيمة الافتراضية المُحسَّنة (كانت 0.8)
            face_config_path = project_root / "config" / "face_recognition_config.json"
            if face_config_path.exists():
                try:
                    face_cfg = json.loads(face_config_path.read_text(encoding="utf-8"))
                    face_threshold = float(face_cfg.get("face_recognition", {}).get("threshold", face_threshold))
                except Exception:
                    pass
            
            frs = FaceRecognitionSystem(model_name="buffalo_l", threshold=face_threshold)
            logger.info(f"Face Recognition threshold: {face_threshold}")
            
            # تحميل التضمينات إن وُجدت
            enc_pkl = project_root / "models" / "face_encodings.pkl"
            if enc_pkl.exists():
                frs.load_encodings(enc_pkl)
                logger.info(f"Loaded {len(frs.encodings)} employees from {enc_pkl}")
            else:
                logger.warning(f"⚠️  ملف التضمينات غير موجود: {enc_pkl}")
                logger.warning("💡 قم بتدريب النموذج أولاً: python train_faces.py")
        except Exception as e:
            errors.log_error(e, context="FaceRecognitionSystem init")
            frs = None

    recognizer = None
    if args.enable_activity_recognition:
        try:
            recognizer = ActivityRecognizer(use_pose=True, use_objects=True, use_motion=True, smoothing_seconds=5.0, fps_hint=25, window_size=args.activity_window, use_ema=args.use_ema, ema_alpha=args.ema_alpha)
        except Exception as e:
            errors.log_error(e, context="ActivityRecognizer init")
            recognizer = None

    attendance_sys = None
    attendance_mgr = None
    if args.enable_attendance:
        try:
            attendance_sys = AttendanceSystem()
            attendance_mgr = AttendanceManager(attendance_sys, grace_seconds=args.grace_seconds)
        except Exception as e:
            errors.log_error(e, context="Attendance init")
            attendance_sys = None

    time_tracker = TimeTracker(min_segment_duration=5)

    # مكوّن ReID للمظهر
    reid = ReIDSystem(device=args.device)

    # فتح المصدر
    cap = open_source(str(args.source))
    if not cap.isOpened():
        logger.error("تعذر فتح المصدر: %s", args.source)
        return

    # كاتب الفيديو (اختياري)
    writer = None
    if args.output_video:
        out_p = Path(args.output_video)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        fps_src = cap.get(cv2.CAP_PROP_FPS) or 25.0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out_p), fourcc, fps_src, (width, height))

    # معلومات الفيديو لتقدم tqdm
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    pbar = tqdm(total=total_frames if total_frames > 0 else None, desc="Processing", unit="frame")

    # إدارة الخرائط
    track_to_emp: Dict[int, str] = {}  # track_id -> employee_id
    track_last_seen: Dict[int, float] = {}
    track_display_name: Dict[int, str] = {}
    # تثبيت الهوية: تصويت أقوى وهستيريсис لمنع تبديل الهوية بسهولة
    SMOOTH_K = 5
    MIN_SIM = 0.85
    MARGIN = 0.05  # هامش إضافي عند محاولة تبديل هوية مثبتة
    from collections import defaultdict
    recog_votes: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))  # tid -> {emp_id: votes}

    # تعدد الخيوط (اختياري)
    pool = ThreadPoolExecutor(max_workers=max(1, args.threads)) if args.threads > 0 else None

    # مؤقتات
    last_report_time = time.time()
    killer = GracefulKiller()

    try:
        while not killer.stop:
            perf.mark_frame()
            perf.start_timer("read")
            ret, frame = cap.read()
            perf.end_timer("read")
            if not ret or frame is None:
                break

            now = datetime.now()

            # 1) كشف
            perf.start_timer("detect")
            detections = detector.detect(frame)
            perf.end_timer("detect")

            # 2) تتبع
            perf.start_timer("track")
            tracks = tracker.update(detections)
            perf.end_timer("track")

            # 3) معالجة لكل شخص
            perf.start_timer("per-person")
            obj_dets = []
            if recognizer is not None:
                # يمكن أيضاً كشف أشياء هنا لكن لتقليل التكلفة، نعتمد دوال recognizer على yolo_detections الخارجية إن تم تمريرها
                obj_dets = []  # placeholder: يمكن دمج كاشف الأشياء من test_activities لاحقاً

            vis = frame.copy()
            for tid, t in tracks.items():
                box = t["box"]
                x1, y1, x2, y2 = box

                # Face Recognition (اختياري)
                emp_id = track_to_emp.get(tid)
                name = track_display_name.get(tid, "Unknown")
                if frs is not None:
                    try:
                        face_crop = crop_person(frame, box, padding=10)
                        faces = frs.detect_faces(face_crop)
                        if faces:
                            # اختيار أفضل وجه داخل القص
                            best = max(faces, key=lambda f: float(f.get("det_score", 0.0)))
                            eid, sim, ename = frs.recognize_face(best["embedding"])  # type: ignore[index]
                            face_candidate = (eid, float(sim) if sim is not None else 0.0, ename)
                    except Exception as e:
                        errors.log_error(e, context="face_recognition")

                # Appearance ReID: يُستخدم دائماً لمساعدة الاستقرار
                x1, y1, x2, y2 = box
                person_crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                reid_emb = reid.embed(person_crop)
                reid_eid, reid_sim = reid.match(reid_emb)

                # دمج الدرجات: نرجّح ReID لثبات أعلى، والوجه عند توفره
                w_face, w_reid = 0.4, 0.6
                candidate_id = None
                combined_sim = 0.0
                # استخلاص نتائج الوجه إن وُجدت
                if 'face_candidate' in locals() and face_candidate[0]:
                    fe_id, fe_sim, fe_name = face_candidate
                    # إن لم توجد نتيجة ReID، نعتمد الوجه فقط
                    if reid_eid is None:
                        candidate_id, combined_sim, name = fe_id, fe_sim, (fe_name or fe_id)
                    else:
                        # إذا اختلفا، نقارن الدرجات المدمجة لكل مرشح
                        scores: Dict[str, float] = {}
                        scores[fe_id] = w_face * fe_sim + (w_reid * (reid_sim if reid_eid == fe_id else 0.0))
                        scores[reid_eid] = w_face * (fe_sim if fe_id == reid_eid else 0.0) + w_reid * reid_sim
                        candidate_id = max(scores.items(), key=lambda kv: kv[1])[0]
                        combined_sim = scores[candidate_id]
                        if candidate_id == fe_id:
                            name = fe_name or fe_id
                        else:
                            name = candidate_id
                else:
                    # لا يوجد وجه موثوق؛ نعتمد ReID فقط
                    candidate_id, combined_sim, name = (reid_eid, reid_sim, (reid_eid or "Unknown"))

                # تثبيت عبر التصويت والهستيريِسِس باستخدام similarity المدمج
                if candidate_id and combined_sim >= MIN_SIM:
                    recog_votes[tid][candidate_id] += 1
                    current = track_to_emp.get(tid)
                    if current is None and recog_votes[tid][candidate_id] >= SMOOTH_K:
                        emp_id = candidate_id
                        track_to_emp[tid] = emp_id
                        track_display_name[tid] = name
                        for k in list(recog_votes[tid].keys()):
                            if k != candidate_id:
                                recog_votes[tid][k] = 0
                    elif current is not None and current != candidate_id:
                        if recog_votes[tid][candidate_id] >= SMOOTH_K and combined_sim >= (MIN_SIM + MARGIN):
                            emp_id = candidate_id
                            track_to_emp[tid] = emp_id
                            track_display_name[tid] = name
                            for k in list(recog_votes[tid].keys()):
                                if k != candidate_id:
                                    recog_votes[tid][k] = 0
                else:
                    for k in list(recog_votes[tid].keys()):
                        recog_votes[tid][k] = max(0, recog_votes[tid][k] - 1)

                # نمو المعرض تلقائياً: إذا ثبتت هوية من الوجه بدرجة عالية، أضف embedding الحالي
                if 'face_candidate' in locals() and face_candidate[0] and face_candidate[1] >= (MIN_SIM + 0.1):
                    try:
                        reid.add_to_gallery(face_candidate[0], [reid_emb])
                    except Exception as e:
                        errors.log_error(e, context="reid_gallery_add")

                # Activity Recognition (اختياري)
                activity = "idle"
                conf_a = 0.0
                if recognizer is not None:
                    try:
                        res = recognizer.process_person(frame, box, t, obj_dets, track_id=tid, curr_time=time.time())
                        activity = res.activity
                        conf_a = float(res.confidence)
                    except Exception as e:
                        errors.log_error(e, context="activity_recognition")

                # Time Tracking: يحتاج track_id وemp_id (إن عرف)
                if emp_id:
                    if tid not in time_tracker.tracks or time_tracker.tracks[str(tid)].current_activity is None:
                        # بدء نشاط
                        time_tracker.start_activity(str(tid), emp_id, activity, now, camera_id=args.camera_id)
                    else:
                        time_tracker.update_activity(str(tid), activity, now)

                # Attendance Update
                if attendance_mgr is not None and emp_id:
                    try:
                        attendance_mgr.process_person_detection(emp_id, args.camera_id, activity, now, employee_name=name)
                        track_last_seen[tid] = time.time()
                    except Exception as e:
                        errors.log_error(e, context="attendance_update")

                # رسم
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"ID {tid}"
                if emp_id:
                    label += f" | {emp_id}"
                label += f" | {activity} ({conf_a:.2f})"
                draw_text_with_background(vis, label, (x1, max(15, y1 - 5)))

            perf.end_timer("per-person")

            # 4) عرض/حفظ
            perf.start_timer("io")
            if writer is not None:
                writer.write(vis)
            if args.display:
                cv2.imshow("Production", vis)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
            perf.end_timer("io")

            # 5) تقارير دورية
            if args.enable_attendance and attendance_sys is not None:
                if (time.time() - last_report_time) >= max(60, args.report_interval):
                    try:
                        df = attendance_sys.generate_daily_report()
                        out = project_root / "reports" / f"daily_{datetime.now().date().isoformat()}.csv"
                        out.parent.mkdir(parents=True, exist_ok=True)
                        df.to_csv(out, index=False, encoding="utf-8-sig")
                        logger.info("[Report] تم تحديث تقرير اليوم: %s", out)
                    except Exception as e:
                        errors.log_error(e, context="generate_report")
                    last_report_time = time.time()

            # 6) معالجة الاختفاء (grace period)
            if attendance_mgr is not None:
                for tid, last in list(track_last_seen.items()):
                    emp = track_to_emp.get(tid)
                    if emp and (time.time() - last) >= args.grace_seconds:
                        try:
                            attendance_mgr.handle_disappearance(emp, datetime.fromtimestamp(last), grace_seconds=args.grace_seconds)
                            track_last_seen.pop(tid, None)
                        except Exception as e:
                            errors.log_error(e, context="handle_disappearance")

            # 7) FPS limit
            if args.fps_limit and args.fps_limit > 0:
                perf.end_timer("frame")  # للمطابقة الشكلية
                # حساب وقت إطار بسيط
                time.sleep(max(0.0, (1.0 / args.fps_limit) - 0.0))

            # تقدم وقياسات
            pbar.update(1)
            if pbar.n % 30 == 0:
                perf.print_report()

            # تحقق من التوقف اللطيف
            if killer.stop:
                break

    except Exception as e:
        errors.log_error(e, context="main_loop")

    finally:
        try:
            cap.release()
        except Exception:
            pass
        if writer is not None:
            try:
                writer.release()
            except Exception:
                pass
        cv2.destroyAllWindows()
        pbar.close()
        # حفظ تلقائي لأي حالة مطلوبة (اختياري: يمكن حفظ ملخص time_tracker)
        try:
            results_dir = project_root / "reports"
            results_dir.mkdir(parents=True, exist_ok=True)
            # حفظ ملخص بسيط لكل track
            for tid in list(time_tracker.tracks.keys()):
                summary = time_tracker.get_activity_summary(str(tid))
                seg_csv = results_dir / f"segments_track_{tid}.csv"
                csv_text = time_tracker.export_segments(str(tid), format="csv")
                seg_csv.write_text(csv_text, encoding="utf-8-sig")
                logger.info("[AutoSave] Saved segments for track %s -> %s (total %.1fs)", tid, seg_csv, summary.get("total", 0.0))
            # حفظ معرض ReID
            try:
                reid.save_gallery()
            except Exception:
                pass
        except Exception as e:
            errors.log_error(e, context="autosave")
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()
