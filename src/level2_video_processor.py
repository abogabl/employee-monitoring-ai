"""
Level 2 Video Processor
معالج فيديو المستوى الثاني مع الذكاء الاصطناعي المتقدم

يدمج جميع تحسينات المستوى الثاني:
- الذكاء الاصطناعي المتقدم
- كشف الشذوذ
- التنبؤ بالسلوك
- تحليل المخاطر
- توصيات ذكية
"""
from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, deque
from datetime import datetime
import cv2
import numpy as np

from .smart_video_processor import SmartVideoProcessor
from .advanced_behavior_ai import AdvancedBehaviorAI
from .utils import draw_text_with_background

def make_json_serializable(obj):
    """تحويل الكائن إلى شكل قابل للتسلسل في JSON"""
    import numpy as np
    
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("level2_video_processor")


class Level2VideoProcessor(SmartVideoProcessor):
    """معالج فيديو المستوى الثاني مع الذكاء الاصطناعي المتقدم"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 416,
        conf_threshold: float = 0.35,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        enable_advanced_ai: bool = True,
        yolo_model: str = "s",
        activity_window: int = 15
    ):
        # تهيئة المعالج الأساسي
        super().__init__(
            device=device,
            imgsz=imgsz,
            conf_threshold=conf_threshold,
            enable_face_recognition=enable_face_recognition,
            enable_activity_recognition=enable_activity_recognition,
            yolo_model=yolo_model,
            activity_window=activity_window
        )
        
        # الذكاء الاصطناعي المتقدم
        self.enable_advanced_ai = enable_advanced_ai
        self.behavior_ai = None
        
        if enable_advanced_ai:
            try:
                self.behavior_ai = AdvancedBehaviorAI()
                logger.info("✓ تم تهيئة الذكاء الاصطناعي المتقدم")
            except Exception as e:
                logger.warning(f"فشل تهيئة الذكاء الاصطناعي المتقدم: {e}")
                self.behavior_ai = None
        
        # إحصائيات متقدمة
        self.ai_insights = {
            'anomalies_detected': 0,
            'high_risk_persons': 0,
            'predictions_made': 0,
            'behavior_patterns': [],
            'recommendations': []
        }
        
        # تاريخ التحليلات
        self.analysis_history = deque(maxlen=100)
        
        logger.info("✓ تم تهيئة معالج الفيديو المستوى الثاني")
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 2,  # أقل تخطي للدقة
        max_duration: int = 60,  # مدة أطول
        task_id: Optional[str] = None,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """معالجة الفيديو مع التحليل المتقدم"""
        
        logger.info(f"🎬 بدء معالجة الفيديو المستوى الثاني: {input_path}")
        start_time = time.time()
        
        # فتح الفيديو
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"فشل في فتح الفيديو: {input_path}")
        
        # معلومات الفيديو
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # حساب المدة الفعلية
        video_duration = total_frames / fps if fps > 0 else 0
        if max_duration > 0 and video_duration > max_duration:
            total_frames = int(max_duration * fps)
            logger.info(f"تحديد المدة إلى {max_duration} ثانية")
        elif total_frames <= 0:
            logger.error(f"فيديو غير صالح: عدد الإطارات = {total_frames}")
            raise ValueError(f"الفيديو لا يحتوي على إطارات صالحة")
        
        # إعداد كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps // frame_skip, (width, height))
        
        # متغيرات المعالجة
        frame_count = 0
        processed_frames = 0
        person_data = {}
        prev_boxes = {}
        
        # إحصائيات متقدمة
        all_person_data_for_ai = []
        frame_analyses = []
        
        # مجلد حفظ الصور
        snapshots_dir = Path("web_app/static/uploads/test_videos/snapshots")
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"معالجة {total_frames} إطار بمعدل تخطي {frame_skip}")
        
        # قراءة إطار تجريبي للتأكد من صحة الفيديو
        test_ret, test_frame = cap.read()
        if not test_ret or test_frame is None:
            raise ValueError("فشل في قراءة الإطار الأول - الفيديو قد يكون تالفاً")
        
        # إعادة تعيين موضع الفيديو
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        try:
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret or frame is None:
                    logger.warning(f"انتهى الفيديو عند الإطار {frame_count}")
                    break
                
                frame_count += 1
                
                # تخطي الإطارات
                if frame_count % frame_skip != 0:
                    continue
                
                processed_frames += 1
                current_time = processed_frames / (fps / frame_skip)
                
                # نسخة للمعالجة
                processing_frame = frame.copy()
                
                # تصغير للمعالجة إذا لزم الأمر
                if frame.shape[1] > 720:
                    scale = 720 / frame.shape[1]
                    new_width = int(frame.shape[1] * scale)
                    new_height = int(frame.shape[0] * scale)
                    processing_frame = cv2.resize(frame, (new_width, new_height))
                
                # كشف الأشخاص
                if self.person_detector:
                    detections = self.person_detector.detect(processing_frame)
                    tracked_objects = self.tracker.update(detections)
                    
                    # معالجة كل شخص
                    for track_id, track_data in tracked_objects.items():
                        x1, y1, x2, y2 = track_data['box']
                        conf = 0.8
                        
                        # تحديث بيانات الشخص
                        if track_id not in person_data:
                            person_data[track_id] = {
                                'name': 'Unknown',
                                'first_seen': current_time,
                                'last_seen': current_time,
                                'detection_count': 0,
                                'total_confidence': 0.0,
                                'activities': defaultdict(list),
                                'positions': [],
                                'snapshot': None,  # مثل المستوى الأول
                                'risk_level': 'low',
                                'anomaly_detected': False,
                                'predicted_activity': 'unknown',
                                'ai_analysis': {}
                            }
                        person_info = person_data[track_id]
                        person_info['last_seen'] = current_time
                        person_info['total_confidence'] += conf
                        person_info['detection_count'] += 1
                        
                        
                        # التعرف على الوجه
                        if self.face_recognizer and person_info['name'] == 'Unknown':
                            try:
                                person_crop = processing_frame[y1:y2, x1:x2]
                                if person_crop.size > 0:
                                    faces = self.face_recognizer.detect_faces(person_crop)
                                    if faces:
                                        best_face = max(faces, key=lambda f: f.get('det_score', 0.0))
                                        if best_face.get('det_score', 0.0) > 0.5:
                                            matches = self.face_recognizer.recognize_face(best_face['embedding'])
                                            if matches and matches[0]['similarity'] > 0.6:
                                                person_info['name'] = matches[0]['name']
                                                logger.info(f"✓ تم التعرف على الشخص {track_id}: {matches[0]['name']}")
                            except Exception as e:
                                if processed_frames % 100 == 0:
                                    logger.debug(f"خطأ في التعرف على الوجه: {e}")
                        
                        # حساب الحركة
                        motion_level = 0.0
                        if track_id in prev_boxes:
                            prev_x1, prev_y1, prev_x2, prev_y2 = prev_boxes[track_id]
                            dx = abs(x1 - prev_x1) + abs(x2 - prev_x2)
                            dy = abs(y1 - prev_y1) + abs(y2 - prev_y2)
                            motion_level = (dx + dy) / max(processing_frame.shape[1], 1)
                        prev_boxes[track_id] = (x1, y1, x2, y2)
                        
                        # كشف النشاط
                        activity = 'idle'
                        activity_conf = 0.5
                        
                        if self.activity_detector:
                            try:
                                result = self.activity_detector.process_person(
                                    processing_frame,
                                    (x1, y1, x2, y2),
                                    {},
                                    detections,
                                    track_id,
                                    current_time
                                )
                                activity = result.activity
                                activity_conf = result.confidence
                            except Exception as e:
                                activity, activity_conf = self.smart_classify_activity(
                                    x1, y1, x2, y2, 
                                    processing_frame.shape[0], 
                                    processing_frame.shape[1], 
                                    motion_level
                                )
                        else:
                            activity, activity_conf = self.smart_classify_activity(
                                x1, y1, x2, y2, 
                                processing_frame.shape[0], 
                                processing_frame.shape[1], 
                                motion_level
                            )
                        
                        # إضافة النشاط للتاريخ
                        person_info['activities'][activity].append({
                            'confidence': activity_conf,
                            'timestamp': current_time
                        })
                        
                        # التحليل المتقدم بالذكاء الاصطناعي
                        if self.behavior_ai and processed_frames % 10 == 0:  # كل 10 إطارات
                            try:
                                # إعداد بيانات الشخص للتحليل
                                analysis_data = self._prepare_person_data_for_ai(
                                    person_info, x1, y1, x2, y2, motion_level, processing_frame.shape
                                )
                                
                                # التحليل المتقدم
                                ai_analysis = self.behavior_ai.analyze_person_behavior(
                                    f"video_{track_id}", analysis_data
                                )
                                
                                # تحديث بيانات الشخص
                                person_info['ai_analysis'] = ai_analysis
                                person_info['risk_level'] = ai_analysis['risk_level']
                                person_info['anomaly_detected'] = ai_analysis['anomaly_detected']
                                person_info['predicted_activity'] = ai_analysis['predicted_next_activity']
                                
                                # تحديث الإحصائيات
                                if ai_analysis['anomaly_detected']:
                                    self.ai_insights['anomalies_detected'] += 1
                                
                                if ai_analysis['risk_level'] == 'high':
                                    self.ai_insights['high_risk_persons'] += 1
                                
                                if ai_analysis['predicted_next_activity'] != 'unknown':
                                    self.ai_insights['predictions_made'] += 1
                                
                                # حفظ التحليل
                                frame_analyses.append({
                                    'frame': processed_frames,
                                    'person_id': track_id,
                                    'analysis': ai_analysis
                                })
                                
                                # إضافة للبيانات العامة
                                all_person_data_for_ai.append(analysis_data)
                                
                            except Exception as e:
                                logger.error(f"خطأ في التحليل المتقدم: {e}")
                        
                        # رسم المعلومات المحسنة على الإطار
                        self._draw_enhanced_person_info(
                            frame, x1, y1, x2, y2, person_info, activity, activity_conf
                        )
                        
                        # حفظ snapshot بنفس طريقة المستوى الأول (بسيط ومباشر)
                        if person_info.get('snapshot') is None:
                            try:
                                person_crop = processing_frame[y1:y2, x1:x2]
                                if person_crop.size > 0:
                                    timestamp = int(time.time())
                                    snapshot_name = f"person_{track_id}_{timestamp}.jpg"
                                    snapshot_path = snapshots_dir / snapshot_name
                                    cv2.imwrite(str(snapshot_path), person_crop)
                                    person_info['snapshot'] = f"uploads/test_videos/snapshots/{snapshot_name}"
                                    logger.info(f"✓ تم حفظ صورة الشخص {track_id}: {snapshot_name}")
                            except Exception as e:
                                logger.debug(f"فشل حفظ صورة الشخص {track_id}: {e}")
                
                # رسم معلومات الإطار
                self._draw_frame_info(frame, processed_frames, current_time)
                
                # كتابة الإطار
                out.write(frame)
                
                # تقرير التقدم
                if processed_frames % 50 == 0:
                    progress = (frame_count / total_frames) * 100
                    logger.info(f"التقدم: {progress:.1f}% - إطار {processed_frames}")
        
        finally:
            cap.release()
            out.release()
        
        # التحقق من وجود بيانات
        if processed_frames == 0:
            logger.error("لم يتم معالجة أي إطار - الفيديو قد يكون تالفاً أو فارغاً")
            raise ValueError("فشل في معالجة الفيديو - لا توجد إطارات صالحة")
        
        
        # تحديث النماذج بالبيانات الجديدة
        if self.behavior_ai and all_person_data_for_ai:
            try:
                self.behavior_ai.update_models(all_person_data_for_ai)
                logger.info(f"تم تحديث نماذج الذكاء الاصطناعي بـ {len(all_person_data_for_ai)} عينة")
            except Exception as e:
                logger.error(f"خطأ في تحديث النماذج: {e}")
        
        # إنشاء الإحصائيات النهائية
        processing_time = time.time() - start_time
        statistics = self._generate_enhanced_statistics(
            person_data, processing_time, processed_frames, fps, frame_analyses
        )
        
        logger.info(f"✅ تم الانتهاء من معالجة الفيديو في {processing_time:.2f} ثانية")
        logger.info(f"📊 تم معالجة {processed_frames} إطار، اكتشاف {len(person_data)} شخص")
        
        return statistics
    
    def _prepare_person_data_for_ai(self, person_info: Dict, x1: int, y1: int, x2: int, y2: int, 
                                   motion_level: float, frame_shape: Tuple) -> Dict[str, Any]:
        """إعداد بيانات الشخص للتحليل بالذكاء الاصطناعي"""
        
        # حساب الأنشطة
        activities = defaultdict(float)
        if person_info['activities']:
            for activity_record in person_info['activities'][-20:]:  # آخر 20 نشاط
                activities[activity_record['activity']] += 1
        
        # حساب المواقع
        center_x = (x1 + x2) / 2 / frame_shape[1]
        center_y = (y1 + y2) / 2 / frame_shape[0]
        
        return {
            'person_id': f"video_{id(person_info)}",
            'name': person_info['name'],
            'activities': dict(activities),
            'duration': person_info['last_seen'] - person_info['first_seen'],
            'detection_count': person_info['detection_count'],
            'avg_confidence': person_info['total_confidence'] / max(person_info['detection_count'], 1),
            'avg_motion': motion_level,
            'motion_variance': motion_level * 0.1,  # تقدير
            'position_changes': len(person_info['activities']),
            'avg_x_position': center_x,
            'avg_y_position': center_y,
            'position_stability': 1.0 - motion_level,
            'current_activity': person_info['activities'][-1]['activity'] if person_info['activities'] else 'idle'
        }
    
    def _draw_enhanced_person_info(self, frame: np.ndarray, x1: int, y1: int, x2: int, y2: int,
                                 person_info: Dict, activity: str, confidence: float):
        """رسم معلومات محسنة للشخص"""
        
        # لون المربع حسب مستوى المخاطر
        risk_colors = {
            'low': (0, 255, 0),      # أخضر
            'medium': (0, 255, 255), # أصفر
            'high': (0, 0, 255)      # أحمر
        }
        
        risk_level = person_info.get('risk_level', 'low')
        box_color = risk_colors.get(risk_level, (0, 255, 0))
        
        # رسم المربع
        thickness = 3 if risk_level == 'high' else 2
        cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, thickness)
        
        # معلومات أساسية
        name = person_info['name']
        info_text = f"ID: {name}"
        
        # معلومات النشاط
        activity_text = f"{activity} ({confidence:.2f})"
        
        # معلومات الذكاء الاصطناعي
        ai_info = []
        if person_info.get('anomaly_detected'):
            ai_info.append("⚠️ شذوذ")
        
        if person_info.get('predicted_activity', 'unknown') != 'unknown':
            ai_info.append(f"توقع: {person_info['predicted_activity']}")
        
        # رسم النصوص
        y_offset = y1 - 10
        
        # الاسم والمعرف
        draw_text_with_background(frame, info_text, (x1, y_offset), 
                                color=(255, 255, 255), font_scale=0.6)
        y_offset -= 25
        
        # النشاط
        activity_color = {
            'working': (0, 255, 0),
            'sleeping': (0, 0, 255),
            'on_phone': (0, 255, 255),
            'idle': (128, 128, 128)
        }.get(activity, (255, 255, 255))
        
        draw_text_with_background(frame, activity_text, (x1, y_offset),
                                color=activity_color, font_scale=0.5)
        y_offset -= 20
        
        # معلومات الذكاء الاصطناعي
        if ai_info:
            ai_text = " | ".join(ai_info)
            draw_text_with_background(frame, ai_text, (x1, y_offset),
                                    color=(255, 0, 255), font_scale=0.4)
    
    def _draw_frame_info(self, frame: np.ndarray, frame_num: int, timestamp: float):
        """رسم معلومات الإطار"""
        
        # معلومات الإطار
        frame_info = f"Frame: {frame_num} | Time: {timestamp:.1f}s"
        draw_text_with_background(frame, frame_info, (10, 30),
                                font_scale=0.7, color=(255, 255, 255))
        
        # معلومات الذكاء الاصطناعي
        ai_info = f"AI: شذوذ={self.ai_insights['anomalies_detected']} | مخاطر={self.ai_insights['high_risk_persons']} | تنبؤات={self.ai_insights['predictions_made']}"
        draw_text_with_background(frame, ai_info, (10, 60),
                                font_scale=0.5, color=(255, 255, 255))
    
    def _generate_enhanced_statistics(self, person_data: Dict, processing_time: float, 
                                    processed_frames: int, fps: int, 
                                    frame_analyses: List) -> Dict[str, Any]:
        """إنشاء إحصائيات محسنة"""
        
        statistics = []
        
        for track_id, person_info in person_data.items():
            # حساب الأنشطة
            activities = defaultdict(float)
            
            # التعامل مع الأنشطة سواء كانت قائمة أو defaultdict
            activity_data = person_info.get('activities', {})
            if isinstance(activity_data, defaultdict) or isinstance(activity_data, dict):
                # إذا كانت defaultdict من القوائم، نحسب المدة لكل نشاط
                for activity_name, activity_list in activity_data.items():
                    if isinstance(activity_list, list):
                        activities[activity_name] = len(activity_list) / fps
                    else:
                        activities[activity_name] = float(activity_list)
            elif isinstance(activity_data, list):
                # إذا كانت قائمة من السجلات
                for activity_record in activity_data:
                    if isinstance(activity_record, dict):
                        activities[activity_record.get('activity', 'idle')] += 1.0 / fps
            
            # النشاط الأكثر شيوعاً
            top_activity = max(activities.keys(), key=lambda k: activities[k]) if activities else 'idle'
            
            # مدة الظهور
            duration = person_info['last_seen'] - person_info['first_seen']
            avg_confidence = person_info['total_confidence'] / max(person_info['detection_count'], 1)
            
            # إحصائيات الذكاء الاصطناعي
            ai_analysis = person_info.get('ai_analysis', {})
            
            # مسار الصورة (مثل المستوى الأول)
            snapshot_path = person_info.get('snapshot', f"uploads/test_videos/snapshots/person_{track_id}_placeholder.jpg")
            
            person_stats = {
                'track_id': int(track_id),
                'name': str(person_info['name']),
                'duration': float(duration),
                'working_duration': float(activities.get('working', 0)),
                'sleeping_duration': float(activities.get('sleeping', 0)),
                'idle_duration': float(activities.get('idle', 0)),
                'phone_duration': float(activities.get('on_phone', 0)),
                'top_activity': str(top_activity),
                'avg_confidence': float(avg_confidence),
                'count': int(person_info['detection_count']),
                'snapshot': str(snapshot_path),
                
                # معلومات الذكاء الاصطناعي المتقدم
                'risk_level': str(person_info.get('risk_level', 'low')),
                'anomaly_detected': bool(person_info.get('anomaly_detected', False)),
                'anomaly_confidence': float(ai_analysis.get('anomaly_confidence', 0.0)),
                'predicted_next_activity': str(person_info.get('predicted_activity', 'unknown')),
                'prediction_confidence': float(ai_analysis.get('prediction_confidence', 0.0)),
                'behavior_patterns': [dict(pattern) if hasattr(pattern, '__dict__') else pattern for pattern in ai_analysis.get('behavior_patterns', [])],
                'recommendations': [str(rec) for rec in ai_analysis.get('recommendations', [])]
            }
            
            statistics.append(person_stats)
        
        # إحصائيات عامة محسنة
        result = {
            'success': True,
            'statistics': statistics,
            'processing_time': float(processing_time),
            'processed_frames': int(processed_frames),
            'total_persons': int(len(statistics)),
            'known_persons': int(sum(1 for s in statistics if s['name'] != 'Unknown')),
            'total_activities': int(sum(s['count'] for s in statistics)),
            
            # إحصائيات الذكاء الاصطناعي
            'ai_insights': {
                'anomalies_detected': int(self.ai_insights['anomalies_detected']),
                'high_risk_persons': int(len([s for s in statistics if s['risk_level'] == 'high'])),
                'medium_risk_persons': int(len([s for s in statistics if s['risk_level'] == 'medium'])),
                'predictions_made': int(self.ai_insights['predictions_made']),
                'behavior_patterns_found': int(len(self.ai_insights['behavior_patterns'])),
                'ai_enabled': bool(self.behavior_ai is not None)
            },
            
            # تحليلات الإطارات
            'frame_analyses': frame_analyses[-10:] if frame_analyses else [],  # آخر 10 تحليلات
            
            # توصيات عامة
            'system_recommendations': [str(rec) for rec in self._generate_system_recommendations(statistics)]
        }
        
        # تحويل النتيجة إلى شكل قابل للتسلسل في JSON
        return make_json_serializable(result)
    
    
    def _generate_system_recommendations(self, statistics: List[Dict]) -> List[str]:
        """إنشاء توصيات النظام"""
        recommendations = []
        
        if not statistics:
            return ["لا توجد بيانات كافية للتوصيات"]
        
        # تحليل الأنشطة
        total_working = sum(s['working_duration'] for s in statistics)
        total_sleeping = sum(s['sleeping_duration'] for s in statistics)
        total_duration = sum(s['duration'] for s in statistics)
        
        if total_duration > 0:
            working_ratio = total_working / total_duration
            sleeping_ratio = total_sleeping / total_duration
            
            if working_ratio < 0.3:
                recommendations.append("مستوى الإنتاجية منخفض - يُنصح بتحفيز الموظفين")
            
            if sleeping_ratio > 0.2:
                recommendations.append("نسبة النوم عالية - يُنصح بمراجعة بيئة العمل")
        
        # تحليل المخاطر
        high_risk_count = len([s for s in statistics if s['risk_level'] == 'high'])
        if high_risk_count > 0:
            recommendations.append(f"يوجد {high_risk_count} أشخاص بمستوى مخاطر عالي - يتطلب تدخل فوري")
        
        # تحليل الشذوذ
        anomaly_count = len([s for s in statistics if s['anomaly_detected']])
        if anomaly_count > 0:
            recommendations.append(f"تم اكتشاف {anomaly_count} حالة شذوذ - يُنصح بالمراجعة")
        
        # تحليل التعرف على الوجوه
        unknown_count = len([s for s in statistics if s['name'] == 'Unknown'])
        if unknown_count > 0:
            recommendations.append(f"يوجد {unknown_count} أشخاص غير معروفين - يُنصح بتحديث قاعدة بيانات الوجوه")
        
        if not recommendations:
            recommendations.append("النظام يعمل بشكل طبيعي - لا توجد مشاكل مكتشفة")
        
        return recommendations
