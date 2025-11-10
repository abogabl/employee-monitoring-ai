"""
معالج اختبار الفيديو مع دمج AI كامل
يستخدم جميع مكونات النظام الحقيقية للحصول على أفضل دقة
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any, Optional

import cv2
import numpy as np

from .detection_tracking import PersonDetector, PersonTracker
from .face_recognition_system import FaceRecognitionSystem
from .simple_activity_detector import SimpleActivityDetector
from .utils import crop_person, draw_text_with_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video_test_processor")


class VideoTestProcessor:
    """معالج فيديو اختبار متكامل مع AI"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 640,
        conf_threshold: float = 0.5,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        detection_only: bool = False
    ):
        self.device = device
        self.imgsz = imgsz
        self.conf_threshold = conf_threshold
        self.enable_face = enable_face_recognition
        self.enable_activity = enable_activity_recognition
        self.hog_detector = None
        self.detection_only = bool(detection_only)
        # هدف قياس للكشف: أعلى جودة عملية لالتقاط الأشخاص البعيدين
        self.detect_target_width = 4096
        
        # تهيئة المكونات
        logger.info("تهيئة معالج الفيديو...")
        
        try:
            # استخدام YOLO مع إعدادات متوازنة
            used_imgsz = max(int(imgsz), 960)
            # رفع حد الثقة لتقليل الكشوفات الخاطئة
            used_conf = max(float(conf_threshold), 0.45)
            self.person_detector = PersonDetector(
                model_size="m",  # متوسط بدلاً من x للتوازن
                device=device,
                imgsz=used_imgsz,
                conf=used_conf
            )
            logger.info("✓ تم تهيئة كاشف الأشخاص (YOLO)")
        except Exception as e:
            logger.warning(f"فشل تهيئة YOLO: {e}")
            logger.info("سيتم استخدام HOG Detector البديل...")
            try:
                import cv2
                self.hog_detector = cv2.HOGDescriptor()
                self.hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                self.person_detector = "HOG"
                logger.info("✓ تم تهيئة HOG Detector")
            except Exception as e2:
                logger.error(f"فشل تهيئة HOG أيضاً: {e2}")
                self.person_detector = None
                self.hog_detector = None
        
        if not self.detection_only:
            self.tracker = PersonTracker()
            logger.info("✓ تم تهيئة نظام التتبع")
        else:
            self.tracker = None
            logger.info("وضع الكشف فقط: سيتم تعطيل التتبع")
        
        if enable_face_recognition:
            try:
                self.face_recognizer = FaceRecognitionSystem()
                logger.info("✓ تم تهيئة نظام التعرف على الوجوه")
            except Exception as e:
                logger.warning(f"فشل تهيئة التعرف على الوجوه: {e}")
                self.face_recognizer = None
        else:
            self.face_recognizer = None
        
        if enable_activity_recognition:
            try:
                self.activity_detector = SimpleActivityDetector(max_distance=300)
                logger.info("✓ تم تهيئة كاشف الأنشطة البسيط")
            except Exception as e:
                logger.warning(f"فشل تهيئة كاشف الأنشطة: {e}")
                self.activity_detector = None
        else:
            self.activity_detector = None
        
        logger.info("✓ جاهز للمعالجة")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,
        max_duration: int = -1
    ) -> Dict[str, Any]:
        """
        معالجة فيديو كامل مع AI
        
        Args:
            input_path: مسار الفيديو المدخل
            output_path: مسار الفيديو الناتج
            frame_skip: عدد الإطارات المتخطاة (1 = كل إطار)
            max_duration: الحد الأقصى للمدة بالثواني (-1 = بدون حد)
        
        Returns:
            قاموس يحتوي على النتائج والإحصائيات
        """
        logger.info(f"بدء معالجة الفيديو: {input_path}")
        start_time = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"فشل فتح الفيديو: {input_path}")
        
        # معلومات الفيديو
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 25
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"معلومات الفيديو: {width}x{height} @ {fps}fps, {total_frames} إطارات")
        
        # إنشاء الفيديو الناتج (استخدام codec متوافق أكثر)
        # تغيير امتداد الملف إلى .avi للتوافق الأفضل
        output_path_str = str(output_path)
        if output_path_str.endswith('.mp4'):
            output_path_str = output_path_str[:-4] + '.avi'
            output_path = Path(output_path_str)
        
        out = None
        for codec in ['XVID', 'MJPG', 'mp4v', 'X264']:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                out = cv2.VideoWriter(output_path_str, fourcc, fps, (width, height))
                if out.isOpened():
                    logger.info(f"تم استخدام codec: {codec}")
                    break
                if out:
                    out.release()
            except Exception as e:
                logger.debug(f"فشل codec {codec}: {e}")
                pass
        
        if out is None or not out.isOpened():
            logger.warning("فشل جميع codecs، محاولة بدون codec محدد")
            out = cv2.VideoWriter(output_path_str, 0, fps, (width, height))
        
        if not out.isOpened():
            raise ValueError("فشل إنشاء ملف الفيديو الناتج")
        
        # ضبط حساسية المتعقب حسب أبعاد الفيديو (مسافة التوفيق بين الإطارات)
        try:
            if hasattr(self, 'tracker') and self.tracker is not None:
                # زيادة المسافة لتجنب تقسيم الشخص الواحد إلى IDs متعددة
                self.tracker.max_distance = max(80.0, float(width) * 0.08)
                # زيادة زمن الاختفاء المسموح
                self.tracker.max_disappeared = 120
        except Exception:
            pass
        
        # إحصائيات  
        frame_count = 1  # نبدأ من 1 بدلاً من 0 لتجنب مشاكل الحساب
        processed_count = 0
        max_frames = fps * max_duration if max_duration > 0 else float('inf')
        # حد أقصى للوقت (ثواني) لتجربة سريعة
        max_wall_time = 90
        concurrent_max = 0
        poor_recall_counter = 0
        switched_to_hog = False
        debug_image_saved = False
        
        # تتبع البيانات
        track_data = {}
        
        all_detections = []
        
        # دالة NMS بسيطة
        def nms_boxes(boxes: List[List[int]], scores: List[float], iou_thresh: float = 0.5) -> List[int]:
            if not boxes:
                return []
            boxes_np = np.array(boxes, dtype=float)
            scores_np = np.array(scores, dtype=float)
            x1 = boxes_np[:, 0]
            y1 = boxes_np[:, 1]
            x2 = boxes_np[:, 2]
            y2 = boxes_np[:, 3]
            areas = (x2 - x1 + 1) * (y2 - y1 + 1)
            order = scores_np.argsort()[::-1]
            keep = []
            while order.size > 0:
                i = order[0]
                keep.append(int(i))
                xx1 = np.maximum(x1[i], x1[order[1:]])
                yy1 = np.maximum(y1[i], y1[order[1:]])
                xx2 = np.minimum(x2[i], x2[order[1:]])
                yy2 = np.minimum(y2[i], y2[order[1:]])
                w = np.maximum(0.0, xx2 - xx1 + 1)
                h = np.maximum(0.0, yy2 - yy1 + 1)
                inter = w * h
                ovr = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
                inds = np.where(ovr <= iou_thresh)[0]
                order = order[inds + 1]
            return keep
        
        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # نسخة للرسم
                display_frame = frame.copy()

                # تعطيل أي تصغير في وضع الكشف القوي
                scale = 1.0
                det_frame = frame
                
                # معالجة إطارات محددة فقط
                if frame_count % frame_skip == 0:
                    processed_count += 1
                    timestamp = frame_count / fps
                    
                    # 1. كشف الأشخاص
                    detections = []
                    if self.person_detector == "HOG":
                        # استخدام HOG Detector مع معاملات محسّنة
                        try:
                            # زيادة frame_skip تلقائياً مع HOG لتسريع الأداء
                            if frame_skip < 3:
                                frame_skip = 3
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            # معاملات محسّنة لزيادة الاستدعاء
                            boxes, weights = self.hog_detector.detectMultiScale(
                                gray,
                                winStride=(4, 4),  # أصغر لكشف أدق
                                padding=(8, 8),    # أكبر للحواف
                                scale=1.03,        # أصغر لمزيد من المقاييس
                                hitThreshold=0.0   # أقل لزيادة الاستدعاء
                            )
                            # HOG يعطي boxes و weights
                            for (x, y, w, h), weight in zip(boxes, weights):
                                detections.append({
                                    'bbox': [int(x), int(y), int(x+w), int(y+h)],
                                    'confidence': float(weight)
                                })
                            # إضافة كشف بمقاييس مختلفة
                            if len(detections) < 4:
                                for scale_factor in [0.5, 0.7, 1.3]:
                                    scaled_w = int(width * scale_factor)
                                    scaled_h = int(height * scale_factor)
                                    if scaled_w < 320 or scaled_h < 240:
                                        continue
                                    scaled = cv2.resize(gray, (scaled_w, scaled_h))
                                    boxes_s, weights_s = self.hog_detector.detectMultiScale(
                                        scaled,
                                        winStride=(4, 4),
                                        padding=(8, 8),
                                        scale=1.03,
                                        hitThreshold=0.0
                                    )
                                    for (x, y, w, h), weight in zip(boxes_s, weights_s):
                                        # إعادة القياس إلى الحجم الأصلي
                                        x = int(x / scale_factor)
                                        y = int(y / scale_factor)
                                        w = int(w / scale_factor)
                                        h = int(h / scale_factor)
                                        detections.append({
                                            'bbox': [x, y, x+w, y+h],
                                            'confidence': float(weight)
                                        })
                                # NMS لإزالة التكرار
                                if detections:
                                    all_boxes = [d['bbox'] for d in detections]
                                    all_scores = [d.get('confidence', 0.0) for d in detections]
                                    keep = nms_boxes(all_boxes, all_scores, iou_thresh=0.4)
                                    detections = [{ 'bbox': all_boxes[i], 'confidence': all_scores[i]} for i in keep]
                        except Exception as e:
                            logger.warning(f"خطأ في HOG: {e}")
                    elif self.person_detector:
                        # استخدام YOLO Detector
                        try:
                            # إن أمكن، نمرر الإطار المصغر
                            dets = self.person_detector.detect(det_frame) or []
                            detections = []
                            for det in dets:
                                # مصادر YOLO تُرجع 'box' و 'conf'
                                if 'bbox' in det:
                                    x1, y1, x2, y2 = det['bbox']
                                else:
                                    x1, y1, x2, y2 = det.get('box', [0,0,0,0])
                                # إعادة القياس للصناديق إذا تم التصغير
                                if scale < 1.0:
                                    x1 = int(x1 / scale); y1 = int(y1 / scale)
                                    x2 = int(x2 / scale); y2 = int(y2 / scale)
                                detections.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'confidence': float(det.get('confidence', det.get('conf', 0.0)))
                                })

                            # كشف بالتقسيم (tiling) إذا كان عدد الكشوفات قليل والأبعاد كبيرة
                            if len(detections) < 4 and max(width, height) >= 1080:
                                tiles = []
                                overlap = 0.15  # 15%
                                tw = int(width * 0.55)
                                th = int(height * 0.55)
                                step_x = int(tw * (1 - overlap))
                                step_y = int(th * (1 - overlap))
                                xs = [0, max(0, width - tw)] if step_x <= 0 else list(range(0, max(1, width - tw + 1), step_x))
                                ys = [0, max(0, height - th)] if step_y <= 0 else list(range(0, max(1, height - th + 1), step_y))
                                # حتى 3×3 كحد أقصى لتفادي البطء الشديد
                                for yy in ys[:3]:
                                    for xx in xs[:3]:
                                        tiles.append((xx, yy, min(xx + tw, width), min(yy + th, height)))
                                tile_dets = []
                                for (tx1, ty1, tx2, ty2) in tiles:
                                    crop = frame[ty1:ty2, tx1:tx2]
                                    if crop.size == 0:
                                        continue
                                    local = self.person_detector.detect(crop) or []
                                    for det in local:
                                        if 'bbox' in det:
                                            lx1, ly1, lx2, ly2 = det['bbox']
                                        else:
                                            lx1, ly1, lx2, ly2 = det.get('box', [0,0,0,0])
                                        gx1 = int(lx1 + tx1); gy1 = int(ly1 + ty1)
                                        gx2 = int(lx2 + tx1)
                                        gy2 = int(ly2 + ty1)
                                        tile_dets.append({
                                            'bbox': [gx1, gy1, gx2, gy2],
                                            'confidence': float(det.get('confidence', det.get('conf', 0.0)))
                                        })
                                # دمج مع NMS أقوى لتقليل التكرار
                                all_boxes = [d['bbox'] for d in (detections + tile_dets)]
                                all_scores = [d.get('confidence', 0.0) for d in (detections + tile_dets)]
                                keep = nms_boxes(all_boxes, all_scores, iou_thresh=0.3)
                                detections = [{ 'bbox': all_boxes[i], 'confidence': all_scores[i]} for i in keep]

                            # في حال بقي العدد قليلاً جداً، جرّب كشفاً إضافياً على الإطار الكامل مرة أخرى
                            if len(detections) < 2:
                                extra = self.person_detector.detect(frame) or []
                                extra_norm = []
                                for det in extra:
                                    if 'bbox' in det:
                                        x1, y1, x2, y2 = det['bbox']
                                    else:
                                        x1, y1, x2, y2 = det.get('box', [0,0,0,0])
                                    extra_norm.append({'bbox': [int(x1), int(y1), int(x2), int(y2)], 'confidence': float(det.get('confidence', det.get('conf', 0.0)))})
                                if extra_norm:
                                    all_boxes = [d['bbox'] for d in (detections + extra_norm)]
                                    all_scores = [d.get('confidence', 0.0) for d in (detections + extra_norm)]
                                    keep = nms_boxes(all_boxes, all_scores, iou_thresh=0.3)
                                    detections = [{ 'bbox': all_boxes[i], 'confidence': all_scores[i]} for i in keep]

                            # كشف متعدد المقاييس: تكبير 1.5x ثم دمج بالـ NMS
                            if len(detections) < 4:
                                try:
                                    up_scale = 1.5
                                    up_w = int(width * up_scale)
                                    up_h = int(height * up_scale)
                                    up_frame = cv2.resize(frame, (up_w, up_h), interpolation=cv2.INTER_CUBIC)
                                    up_dets = self.person_detector.detect(up_frame) or []
                                    up_norm = []
                                    for det in up_dets:
                                        if 'bbox' in det:
                                            ux1, uy1, ux2, uy2 = det['bbox']
                                        else:
                                            ux1, uy1, ux2, uy2 = det.get('box', [0,0,0,0])
                                        # إعادة القياس إلى الأصل
                                        x1 = int(ux1 / up_scale); y1 = int(uy1 / up_scale)
                                        x2 = int(ux2 / up_scale); y2 = int(uy2 / up_scale)
                                        up_norm.append({'bbox': [x1, y1, x2, y2], 'confidence': float(det.get('confidence', det.get('conf', 0.0)))})
                                    if up_norm:
                                        all_boxes = [d['bbox'] for d in (detections + up_norm)]
                                        all_scores = [d.get('confidence', 0.0) for d in (detections + up_norm)]
                                        keep = nms_boxes(all_boxes, all_scores, iou_thresh=0.3)
                                        detections = [{ 'bbox': all_boxes[i], 'confidence': all_scores[i]} for i in keep]
                                except Exception as _:
                                    pass
                        except Exception as e:
                            logger.warning(f"خطأ في الكشف: {e}")
                    
                    # 2. إرجاع الأشخاص حسب الوضع
                    if self.detection_only:
                        # بدون تتبع: كل كشف يعتبر شخصاً في هذا الإطار
                        tracked_persons = []
                        for idx, det in enumerate(detections, start=1):
                            tracked_persons.append((idx, {'box': det['bbox']}))
                    else:
                        # تحويل إلى تنسيق المتعقب
                        tracker_detections = []
                        for det in detections:
                            tracker_detections.append({
                                'box': det['bbox'],
                                'confidence': det.get('confidence', 0.8)
                            })
                        # تتبع (بدون frame parameter)
                        if tracker_detections:
                            tracked_dict = self.tracker.update(tracker_detections)
                            tracked_persons = list(tracked_dict.items())
                        else:
                            tracked_persons = []

                    # [تشخيص] حفظ لقطة واحدة بالصناديق عند أول مرة تكون فيها هناك كشوفات
                    if not debug_image_saved and len(detections) >= 1:
                        try:
                            debug_draw = display_frame.copy()
                            # صناديق الكشوفات الخام باللون السماوي
                            for i, det in enumerate(detections, 1):
                                x1, y1, x2, y2 = map(int, det['bbox'])
                                cv2.rectangle(debug_draw, (x1, y1), (x2, y2), (255, 255, 0), 3)
                                conf = det.get('confidence', 0.0)
                                draw_text_with_background(debug_draw, f"Det#{i} {conf:.2f}", (x1, max(25, y1-5)), color=(255, 255, 0))
                            # صناديق التتبع باللون الأخضر
                            for tid, pdata in tracked_persons:
                                bx = list(map(int, pdata.get('box', [0,0,0,0])))
                                cv2.rectangle(debug_draw, (bx[0], bx[1]), (bx[2], bx[3]), (0, 255, 0), 2)
                                draw_text_with_background(debug_draw, f"ID {tid}", (bx[0], max(15, bx[1])), color=(0, 255, 0))
                            # نص يوضح العدد
                            info_text = f"Detections: {len(detections)} | Tracked: {len(tracked_persons)}"
                            draw_text_with_background(debug_draw, info_text, (10, 30), color=(255, 255, 255), font_scale=0.7)
                            # حفظ الصورة
                            debug_dir = Path("web_app/static/uploads/test_videos")
                            debug_dir.mkdir(parents=True, exist_ok=True)
                            debug_name = f"debug_{int(start_time)}_{frame_count}.jpg"
                            debug_path_full = debug_dir / debug_name
                            cv2.imwrite(str(debug_path_full), debug_draw)
                            last_debug_image = f"uploads/test_videos/{debug_name}"
                            debug_image_saved = True
                            logger.info(f"حُفظت صورة تشخيص: {len(detections)} كشوفات، {len(tracked_persons)} متتبعين")
                        except Exception as e:
                            logger.debug(f"تعذر حفظ لقطة التشخيص: {e}")

                    # 4. معالجة كل شخص
                    for track_id, person_data in tracked_persons:
                        bbox = person_data.get('box', [0, 0, 10, 10])
                        x1, y1, x2, y2 = map(int, bbox)
                        
                        # التأكد من أن المربع داخل الإطار
                        x1 = max(0, x1)
                        y1 = max(0, y1)
                        x2 = min(width, x2)
                        y2 = min(height, y2)
                        
                        # اقتصاص الشخص
                        person_crop = crop_person(frame, bbox)
                        
                        # التعرف على الوجه
                        person_name = "Unknown"
                        face_conf = 0.0
                        if (not self.detection_only) and self.face_recognizer and person_crop is not None:
                            try:
                                face_result = self.face_recognizer.recognize_face(person_crop)
                                if face_result:
                                    person_name = face_result.get('name', 'Unknown')
                                    face_conf = face_result.get('confidence', 0.0)
                            except Exception as e:
                                logger.debug(f"خطأ في التعرف على الوجه: {e}")
                        
                        # التعرف على النشاط البسيط
                        activity = "unknown"
                        activity_conf = 0.0
                        if self.activity_detector and person_crop is not None:
                            try:
                                # كشف الأشياء (كمبيوتر، هاتف، إلخ) للتعرف على الأنشطة
                                yolo_detections = []
                                if hasattr(self.person_detector, 'model') and self.person_detector.model:
                                    try:
                                        # كشف الأشياء: laptop(63), tv(62), keyboard(66), cell phone(67), monitor(72)
                                        obj_classes = [62, 63, 66, 67, 72]  # tv, laptop, keyboard, cell phone, monitor
                                        results = self.person_detector.model.predict(
                                            frame,
                                            imgsz=self.person_detector.imgsz,
                                            conf=0.25,  # حد منخفض للأشياء
                                            device=self.person_detector.device,
                                            classes=obj_classes,
                                            verbose=False
                                        )
                                        if results and results[0].boxes is not None:
                                            obj_names = {62: 'tv', 63: 'laptop', 66: 'keyboard', 67: 'cell phone', 72: 'monitor'}
                                            for b in results[0].boxes:
                                                x1_obj, y1_obj, x2_obj, y2_obj = map(int, b.xyxy[0].tolist())
                                                conf_obj = float(b.conf[0])
                                                cls_obj = int(b.cls[0])
                                                yolo_detections.append({
                                                    'bbox': [x1_obj, y1_obj, x2_obj, y2_obj],
                                                    'box': (x1_obj, y1_obj, x2_obj, y2_obj),
                                                    'confidence': conf_obj,
                                                    'conf': conf_obj,
                                                    'class': cls_obj,
                                                    'name': obj_names.get(cls_obj, f'class_{cls_obj}')
                                                })
                                            if yolo_detections:
                                                detected_objs = [d['name'] for d in yolo_detections]
                                                logger.info(f"📦 Frame {frame_count}: Detected objects: {detected_objs}")
                                    except Exception as e:
                                        logger.debug(f"خطأ في كشف الأشياء: {e}")
                                
                                # استدعاء الكاشف البسيط
                                activity, activity_conf = self.activity_detector.detect_activity(
                                    person_box=(x1, y1, x2, y2),
                                    track_id=track_id,
                                    yolo_detections=yolo_detections,
                                    frame_time=timestamp
                                )
                                logger.info(f"🎯 Frame {frame_count}, Person {track_id}: Activity={activity}, Confidence={activity_conf:.2f}")
                            except Exception as e:
                                logger.warning(f"خطأ في التعرف على النشاط: {e}")
                        
                        # تهيئة بيانات الشخص إذا لم تكن موجودة
                        if track_id not in track_data:
                            logger.info(f"✨ New person detected! Track ID={track_id}, Frame={frame_count}")
                            track_data[track_id] = {
                                'name': 'Unknown',
                                'frames': [],
                                'activities': [],
                                'confidences': [],
                                'first_seen': frame_count,
                                'last_seen': frame_count,
                                'snapshot': None,
                                'activity_frames': {}  # dict عادي
                            }
                        
                        # حفظ البيانات
                        if person_name != "Unknown":
                            track_data[track_id]['name'] = person_name
                        track_data[track_id]['frames'].append(frame_count)
                        track_data[track_id]['activities'].append(activity)
                        track_data[track_id]['confidences'].append(max(face_conf, activity_conf))
                        track_data[track_id]['last_seen'] = frame_count
                        
                        # Logging مفصل لتتبع المشكلة
                        if len(track_data[track_id]['frames']) <= 3:  # أول 3 إطارات فقط
                            logger.info(f"💾 Person {track_id}: Saved frame={frame_count}, activity={activity}, frames_so_far={track_data[track_id]['frames'][-3:]}")
                        
                        # تتبع أرقام الإطارات لكل نشاط
                        if activity != 'unknown':
                            if activity not in track_data[track_id]['activity_frames']:
                                track_data[track_id]['activity_frames'][activity] = []
                            track_data[track_id]['activity_frames'][activity].append(frame_count)
                            logger.debug(f"Recorded activity '{activity}' for person {track_id} at frame {frame_count}")
                        
                        # حفظ snapshot لأول مرة نرى فيها الشخص
                        if track_data[track_id].get('snapshot') is None and person_crop is not None:
                            try:
                                snapshot_dir = Path("web_app/static/uploads/test_videos/snapshots")
                                snapshot_dir.mkdir(parents=True, exist_ok=True)
                                snapshot_name = f"person_{track_id}_{int(start_time)}.jpg"
                                snapshot_path = snapshot_dir / snapshot_name
                                cv2.imwrite(str(snapshot_path), person_crop)
                                track_data[track_id]['snapshot'] = f"uploads/test_videos/snapshots/{snapshot_name}"
                            except Exception as e:
                                logger.debug(f"تعذر حفظ snapshot: {e}")
                        
                        # حفظ التفاصيل
                        all_detections.append({
                            'frame': frame_count,
                            'timestamp': timestamp,
                            'track_id': track_id,
                            'person': person_name,
                            'activity': activity,
                            'face_confidence': face_conf,
                            'activity_confidence': activity_conf
                        })
                        
                        # الرسم على الإطار
                        # اختيار اللون حسب النشاط
                        color_map = {
                            'working': (0, 255, 0),      # أخضر
                            'on_phone': (0, 165, 255),   # برتقالي
                            'sleeping': (0, 0, 255),     # أحمر
                            'unknown': (255, 255, 255)   # أبيض
                        }
                        color = color_map.get(activity, (128, 128, 128))
                        
                        # رسم المربع
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                        
                        # إعداد النصوص
                        texts = []
                        if person_name != "Unknown":
                            texts.append(f"{person_name} ({face_conf:.2f})")
                        else:
                            texts.append(f"Person #{track_id}")
                        
                        # ترجمة الأنشطة للعربية
                        activity_ar = {
                            'working': 'يعمل',
                            'on_phone': 'على الهاتف',
                            'sleeping': 'نائم',
                            'unknown': 'غير محدد'
                        }.get(activity, activity)
                        
                        texts.append(f"{activity_ar} ({activity_conf:.2f})")
                        
                        # رسم النصوص
                        y_offset = y1 - 10
                        for text in texts:
                            draw_text_with_background(
                                display_frame, text,
                                (x1, y_offset),
                                color=color,
                                font_scale=0.5
                            )
                            y_offset -= 25
                
                # تحديث أقصى عدد تواجد متزامن
                try:
                    concurrent_max = max(concurrent_max, len(tracked_persons))
                except Exception:
                    pass

                # قياس جودة الاستدعاء في الإطارات الأولى
                if processed_count <= 20:
                    try:
                        if len(detections) <= 1:
                            poor_recall_counter += 1
                    except Exception:
                        pass

                # كتابة الإطار
                if out and out.isOpened():
                    out.write(display_frame)
                frame_count += 1
                
                # تقدم كل 30 إطار
                if frame_count % 30 == 0:
                    logger.info(f"معالجة: {frame_count}/{min(total_frames, max_frames)} إطار")

                # حد أقصى زمني للحماية من البطء الشديد
                if time.time() - start_time > max_wall_time and processed_count > 0:
                    logger.info("توقف مبكر: تجاوز زمن المعالجة الحد المحدد للتجربة")
                    break
        
        finally:
            cap.release()
            if out:
                out.release()
            
            # التحقق من أن الفيديو تم إنشاؤه بنجاح
            if Path(output_path).exists():
                video_size = Path(output_path).stat().st_size
                logger.info(f"✓ تم إنشاء الفيديو: {output_path.name}, حجم={video_size} bytes")
                if video_size < 1000:
                    logger.warning("⚠ تحذير: الفيديو صغير جدًا!")
            else:
                logger.error("✗ فشل إنشاء الفيديو الناتج")
        
        processing_time = time.time() - start_time
        logger.info("="*80)
        logger.info(f"✓ اكتملت المعالجة في {processing_time:.2f} ثانية")
        logger.info(f"✓ عدد الإطارات المعالجة: {processed_count}, إجمالي الإطارات: {frame_count}")
        logger.info(f"✓ عدد الأشخاص المتتبعين: {len(track_data)}")
        logger.info("="*80)
        
        # إعداد النتائج
        results = self._prepare_results(
            track_data, all_detections, 
            frame_count, processed_count, 
            processing_time, fps, frame_skip
        )
        # في وضع الكشف فقط، نُظهر العدد كأقصى تواجد متزامن
        if self.detection_only:
            results['total_persons'] = int(concurrent_max)
        results['switched_to_hog'] = bool(switched_to_hog)
        return results
    
    def _prepare_results(
        self,
        track_data: Dict,
        all_detections: List[Dict],
        total_frames: int,
        processed_frames: int,
        processing_time: float,
        fps: int,
        frame_skip: int
    ) -> Dict[str, Any]:
        """تحضير النتائج النهائية"""
        
        # إحصائيات الأشخاص
        unique_persons = set()
        known_persons = set()
        
        for track_id, data in track_data.items():
            name = data['name']
            if name != 'Unknown':
                known_persons.add(name)
            unique_persons.add(track_id)
        
        # إحصائيات الأنشطة
        all_activities = []
        for data in track_data.values():
            all_activities.extend(data['activities'])
        
        activity_counts = defaultdict(int)
        for activity in all_activities:
            activity_counts[activity] += 1
        
        # إحصائيات لكل شخص (تركيز على 3 أنشطة رئيسية)
        statistics = []
        logger.info("\n" + "="*80)
        logger.info("📊 حساب مدد الأنشطة لكل شخص:")
        logger.info("="*80)
        
        for track_id, data in track_data.items():
            logger.info(f"\n🔍 Person {track_id} (Track ID):")
            logger.info(f"   - Total frames recorded: {len(data['frames'])}")
            logger.info(f"   - Activities logged: {len(data['activities'])} entries")
            
            # الحل الجذري: استخدام frames list مباشرة بدون first_seen/last_seen
            if not data['frames']:
                logger.warning(f"   ⚠️ No frames recorded for person {track_id}!")
                continue
            
            actual_first_frame = min(data['frames'])
            actual_last_frame = max(data['frames'])
            logger.info(f"   - Actual frame range: {actual_first_frame} to {actual_last_frame}")
            
            # حساب مدة كل نشاط
            activity_durations = {}
            
            # الطريقة الجديدة: استخدام activities + frames مباشرة
            if data['activities'] and len(data['activities']) == len(data['frames']):
                logger.info(f"   - Computing durations from activities+frames alignment...")
                logger.info(f"   - activities list: {data['activities'][:10]}...")  # أول 10
                logger.info(f"   - frames list: {data['frames'][:10]}...")  # أول 10
                
                # بناء activity_frames من activities و frames
                activity_frame_map = {}
                for i, (activity, frame_num) in enumerate(zip(data['activities'], data['frames'])):
                    if activity != 'unknown':
                        if activity not in activity_frame_map:
                            activity_frame_map[activity] = []
                        activity_frame_map[activity].append(frame_num)
                
                logger.info(f"   - activity_frame_map: {activity_frame_map}")
                
                # حساب المدة لكل نشاط
                for activity, frames_list in activity_frame_map.items():
                    if frames_list:
                        first_frame = min(frames_list)
                        last_frame = max(frames_list)
                        duration_seconds = (last_frame - first_frame + 1) / fps
                        activity_durations[activity] = duration_seconds
                        logger.info(f"      ✓ {activity}: {len(frames_list)} occurrences")
                        logger.info(f"         - frames {first_frame} to {last_frame}")
                        logger.info(f"         - calculation: ({last_frame} - {first_frame} + 1) / {fps} = {duration_seconds:.2f}s")
            else:
                logger.warning(f"   ⚠️ Activities/frames mismatch! Using simple estimation...")
                # Fallback بسيط
                if data['activities']:
                    activity_counts = Counter(data['activities'])
                    for activity, count in activity_counts.items():
                        if activity != 'unknown':
                            # عدد مرات الظهور × frame_skip / fps
                            activity_durations[activity] = (count * frame_skip) / fps
                            logger.info(f"      ~ {activity}: {count} times, estimated ≈{activity_durations[activity]:.2f}s")
            
            # الأنشطة الرئيسية
            working_duration = activity_durations.get('working', 0.0)
            sleeping_duration = activity_durations.get('sleeping', 0.0)
            phone_duration = activity_durations.get('on_phone', 0.0)
            
            avg_confidence = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0.0
            
            # المدة الإجمالية من frames list مباشرة
            total_duration = (actual_last_frame - actual_first_frame + 1) / fps
            
            logger.info(f"   📌 Final Durations:")
            logger.info(f"      - Working: {working_duration:.2f}s")
            logger.info(f"      - Sleeping: {sleeping_duration:.2f}s")
            logger.info(f"      - Phone: {phone_duration:.2f}s")
            logger.info(f"      - Total: {total_duration:.2f}s")
            
            statistics.append({
                'name': data['name'],
                'track_id': track_id,
                'snapshot': data.get('snapshot'),
                'total_duration': total_duration,
                'working_duration': working_duration,
                'sleeping_duration': sleeping_duration,
                'phone_duration': phone_duration,
                'avg_confidence': avg_confidence
            })
        
        # ترتيب حسب المدة الإجمالية
        statistics.sort(key=lambda x: x['total_duration'], reverse=True)
        
        # تفاصيل الكشف (أول 50)
        details = []
        for det in all_detections[:50]:
            timestamp_str = f"{int(det['timestamp']//60):02d}:{int(det['timestamp']%60):02d}"
            details.append({
                'person': det['person'] if det['person'] != 'Unknown' else f"Person #{det['track_id']}",
                'timestamp': timestamp_str,
                'activity': det['activity'],
                'confidence': max(det['face_confidence'], det['activity_confidence'])
            })
        
        # محاولة العثور على أحدث صورة تشخيص محفوظة في هذا التشغيل
        debug_image = None
        try:
            # نبحث عن ملفات تبدأ بوقت البدء التقريبي خلال آخر دقائق
            folder = Path("web_app/static/uploads/test_videos")
            candidates = sorted(folder.glob("debug_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                debug_image = f"uploads/test_videos/{candidates[0].name}"
        except Exception:
            pass

        # إعداد معلومات التشخيص
        diagnostic_info = []
        for track_id, data in track_data.items():
            info = {
                'track_id': track_id,
                'name': data['name'],
                'total_frames': len(data['frames']),
                'activities_logged': len(data['activities']),
                'activities_breakdown': dict(Counter(data['activities'])),
                'activity_frames_count': {k: len(v) for k, v in data.get('activity_frames', {}).items()},
                'first_seen': data['first_seen'],
                'last_seen': data['last_seen']
            }
            diagnostic_info.append(info)
        
        return {
            'success': True,
            # نعرض الحد الأقصى للتواجد المتزامن كعدد الأشخاص في المشهد
            'total_persons': max(len(unique_persons), max([len(v['frames'])>0 for v in track_data.values()])) if track_data else 0,
            'known_persons': len(known_persons),
            'total_activities': sum(activity_counts.values()),
            'activity_breakdown': dict(activity_counts),
            'processing_time': processing_time,
            'total_frames': total_frames,
            'processed_frames': processed_frames,
            'details': details,
            'statistics': statistics,
            'debug_image': debug_image,
            'diagnostic_info': diagnostic_info
        }
