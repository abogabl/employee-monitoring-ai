"""
Multi-Camera System - Level 2 Enhancement
نظام كاميرات متعددة متزامن مع تتبع عبر الكاميرات

الميزات:
- مراقبة عدة كاميرات متزامنة
- تتبع الأشخاص عبر الكاميرات
- إدارة موحدة للموارد
- واجهة موحدة للعرض
"""
from __future__ import annotations
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime
import cv2
import numpy as np
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from .smart_camera_processor import SmartCameraProcessor
from .attendance_manager import AttendanceManager
from .performance_monitor import PerformanceMonitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multi_camera_system")


class CrossCameraTracker:
    """تتبع الأشخاص عبر الكاميرات المختلفة"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.global_persons = {}  # معرف عالمي -> بيانات الشخص
        self.camera_mappings = {}  # (camera_id, local_track_id) -> global_id
        self.next_global_id = 1
        self.face_embeddings = {}  # global_id -> face_embedding
        
    def register_person(self, camera_id: str, local_track_id: int, 
                       face_embedding: Optional[np.ndarray] = None,
                       person_data: Optional[Dict] = None) -> int:
        """تسجيل شخص جديد أو ربطه بشخص موجود"""
        
        # البحث عن تطابق موجود
        if face_embedding is not None:
            for global_id, stored_embedding in self.face_embeddings.items():
                similarity = self._calculate_similarity(face_embedding, stored_embedding)
                if similarity > self.similarity_threshold:
                    # ربط بشخص موجود
                    self.camera_mappings[(camera_id, local_track_id)] = global_id
                    self._update_person_data(global_id, camera_id, person_data)
                    logger.info(f"ربط الشخص {local_track_id} في {camera_id} بالمعرف العالمي {global_id}")
                    return global_id
        
        # إنشاء شخص جديد
        global_id = self.next_global_id
        self.next_global_id += 1
        
        self.camera_mappings[(camera_id, local_track_id)] = global_id
        self.global_persons[global_id] = {
            'cameras': {camera_id: person_data or {}},
            'first_seen': datetime.now(),
            'last_seen': datetime.now(),
            'total_duration': 0.0,
            'activities': defaultdict(float),
            'name': person_data.get('name', 'Unknown') if person_data else 'Unknown'
        }
        
        if face_embedding is not None:
            self.face_embeddings[global_id] = face_embedding
        
        logger.info(f"إنشاء شخص جديد: معرف عالمي {global_id} من {camera_id}:{local_track_id}")
        return global_id
    
    def _calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """حساب التشابه بين التضمينات"""
        try:
            # تطبيع التضمينات
            emb1_norm = emb1 / np.linalg.norm(emb1)
            emb2_norm = emb2 / np.linalg.norm(emb2)
            
            # حساب التشابه الجيبي
            similarity = np.dot(emb1_norm, emb2_norm)
            return float(similarity)
        except:
            return 0.0
    
    def _update_person_data(self, global_id: int, camera_id: str, person_data: Optional[Dict]):
        """تحديث بيانات الشخص"""
        if global_id in self.global_persons and person_data:
            person = self.global_persons[global_id]
            person['cameras'][camera_id] = person_data
            person['last_seen'] = datetime.now()
            
            # تحديث الاسم إذا تم التعرف عليه
            if person_data.get('name') != 'Unknown':
                person['name'] = person_data['name']
    
    def get_global_id(self, camera_id: str, local_track_id: int) -> Optional[int]:
        """الحصول على المعرف العالمي"""
        return self.camera_mappings.get((camera_id, local_track_id))
    
    def get_person_summary(self, global_id: int) -> Optional[Dict]:
        """الحصول على ملخص الشخص عبر جميع الكاميرات"""
        if global_id not in self.global_persons:
            return None
        
        person = self.global_persons[global_id]
        
        # حساب الإحصائيات المجمعة
        total_duration = 0.0
        combined_activities = defaultdict(float)
        active_cameras = []
        
        for camera_id, camera_data in person['cameras'].items():
            if 'duration' in camera_data:
                total_duration += camera_data['duration']
            
            if 'activities' in camera_data:
                for activity, duration in camera_data['activities'].items():
                    combined_activities[activity] += duration
            
            # تحديد الكاميرات النشطة (آخر 30 ثانية)
            if 'last_seen' in camera_data:
                if (datetime.now() - camera_data['last_seen']).seconds < 30:
                    active_cameras.append(camera_id)
        
        return {
            'global_id': global_id,
            'name': person['name'],
            'active_cameras': active_cameras,
            'total_cameras': len(person['cameras']),
            'total_duration': total_duration,
            'activities': dict(combined_activities),
            'first_seen': person['first_seen'],
            'last_seen': person['last_seen']
        }


class MultiCameraSystem:
    """نظام كاميرات متعددة متزامن"""
    
    def __init__(self, config_file: str = "config/cameras_config.json"):
        self.config_file = config_file
        self.cameras = {}  # camera_id -> SmartCameraProcessor
        self.camera_threads = {}  # camera_id -> thread
        self.camera_queues = {}  # camera_id -> queue للإطارات
        self.running = False
        
        # تتبع عبر الكاميرات
        self.cross_tracker = CrossCameraTracker()
        
        # إدارة الموارد
        self.attendance_manager = AttendanceManager()
        self.perf_monitor = PerformanceMonitor()
        
        # إحصائيات النظام
        self.system_stats = {
            'total_cameras': 0,
            'active_cameras': 0,
            'total_persons': 0,
            'known_persons': 0,
            'start_time': None
        }
        
        logger.info("تهيئة نظام الكاميرات المتعددة...")
        
    def load_camera_config(self) -> bool:
        """تحميل إعدادات الكاميرات"""
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                # إنشاء إعدادات افتراضية
                self._create_default_config()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.camera_configs = config.get('cameras', [])
            logger.info(f"تم تحميل إعدادات {len(self.camera_configs)} كاميرا")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات الكاميرات: {e}")
            return False
    
    def _create_default_config(self):
        """إنشاء إعدادات افتراضية"""
        default_config = {
            "cameras": [
                {
                    "id": "cam1",
                    "name": "الكاميرا الرئيسية",
                    "source": 0,
                    "location": "المكتب الرئيسي",
                    "enabled": True,
                    "settings": {
                        "yolo_model": "s",
                        "imgsz": 416,
                        "conf_threshold": 0.35,
                        "enable_face_recognition": True,
                        "enable_activity_recognition": True,
                        "enable_attendance": True
                    }
                }
            ],
            "system": {
                "max_concurrent_cameras": 4,
                "cross_camera_tracking": True,
                "auto_restart_failed": True,
                "performance_monitoring": True
            }
        }
        
        config_path = Path(self.config_file)
        config_path.parent.mkdir(exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"تم إنشاء إعدادات افتراضية: {config_path}")
    
    def initialize_cameras(self) -> bool:
        """تهيئة جميع الكاميرات"""
        if not self.load_camera_config():
            return False
        
        success_count = 0
        
        for camera_config in self.camera_configs:
            if not camera_config.get('enabled', True):
                continue
            
            camera_id = camera_config['id']
            
            try:
                # إنشاء معالج الكاميرا
                processor = SmartCameraProcessor(
                    camera_id=camera_id,
                    device=camera_config['settings'].get('device', 'cpu'),
                    imgsz=camera_config['settings'].get('imgsz', 416),
                    conf_threshold=camera_config['settings'].get('conf_threshold', 0.35),
                    enable_face_recognition=camera_config['settings'].get('enable_face_recognition', True),
                    enable_activity_recognition=camera_config['settings'].get('enable_activity_recognition', True),
                    enable_attendance=camera_config['settings'].get('enable_attendance', True),
                    yolo_model=camera_config['settings'].get('yolo_model', 's'),
                    attendance_manager=self.attendance_manager
                )
                
                # إنشاء queue للإطارات
                frame_queue = queue.Queue(maxsize=10)
                
                self.cameras[camera_id] = {
                    'processor': processor,
                    'config': camera_config,
                    'queue': frame_queue,
                    'stats': defaultdict(int),
                    'last_frame_time': 0
                }
                
                success_count += 1
                logger.info(f"✓ تم تهيئة الكاميرا {camera_id}: {camera_config['name']}")
                
            except Exception as e:
                logger.error(f"❌ فشل تهيئة الكاميرا {camera_id}: {e}")
        
        self.system_stats['total_cameras'] = success_count
        logger.info(f"تم تهيئة {success_count} كاميرا بنجاح")
        return success_count > 0
    
    def start_camera_thread(self, camera_id: str) -> bool:
        """بدء خيط معالجة كاميرا"""
        if camera_id not in self.cameras:
            return False
        
        camera_info = self.cameras[camera_id]
        config = camera_info['config']
        
        def camera_worker():
            """دالة العمل للكاميرا"""
            cap = None
            try:
                # فتح مصدر الفيديو
                source = config['source']
                cap = cv2.VideoCapture(source)
                
                if not cap.isOpened():
                    logger.error(f"فشل فتح الكاميرا {camera_id}: {source}")
                    return
                
                # إعدادات الكاميرا
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                
                processor = camera_info['processor']
                frame_queue = camera_info['queue']
                
                logger.info(f"بدء معالجة الكاميرا {camera_id}")
                
                while self.running:
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning(f"فشل قراءة إطار من {camera_id}")
                        break
                    
                    # معالجة الإطار
                    try:
                        processed_frame, frame_stats = processor.process_frame(frame)
                        
                        # تحديث الإحصائيات
                        camera_info['stats']['frames_processed'] += 1
                        camera_info['stats']['persons_detected'] = frame_stats['persons_detected']
                        camera_info['last_frame_time'] = time.time()
                        
                        # تحديث التتبع العبر-كاميرات
                        self._update_cross_camera_tracking(camera_id, processor)
                        
                        # إضافة الإطار للqueue للعرض
                        if not frame_queue.full():
                            frame_queue.put((processed_frame, frame_stats))
                        
                    except Exception as e:
                        logger.error(f"خطأ في معالجة إطار {camera_id}: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"خطأ في خيط الكاميرا {camera_id}: {e}")
            finally:
                if cap:
                    cap.release()
                logger.info(f"تم إغلاق الكاميرا {camera_id}")
        
        # بدء الخيط
        thread = threading.Thread(target=camera_worker, name=f"Camera-{camera_id}")
        thread.daemon = True
        thread.start()
        
        self.camera_threads[camera_id] = thread
        logger.info(f"تم بدء خيط الكاميرا {camera_id}")
        return True
    
    def _update_cross_camera_tracking(self, camera_id: str, processor: SmartCameraProcessor):
        """تحديث التتبع عبر الكاميرات"""
        try:
            for local_track_id, person_data in processor.person_data.items():
                # الحصول على تضمين الوجه إن وجد
                face_embedding = None
                if (processor.face_recognizer and 
                    person_data.get('name') != 'Unknown'):
                    # يمكن الحصول على التضمين من نظام التعرف على الوجوه
                    pass
                
                # تسجيل أو تحديث الشخص في النظام العالمي
                global_id = self.cross_tracker.register_person(
                    camera_id=camera_id,
                    local_track_id=local_track_id,
                    face_embedding=face_embedding,
                    person_data=person_data
                )
                
                # تحديث المعرف العالمي في بيانات المعالج
                person_data['global_id'] = global_id
                
        except Exception as e:
            logger.error(f"خطأ في التتبع العبر-كاميرات: {e}")
    
    def start_all_cameras(self) -> bool:
        """بدء جميع الكاميرات"""
        if not self.initialize_cameras():
            return False
        
        self.running = True
        self.system_stats['start_time'] = datetime.now()
        
        # بدء خيوط الكاميرات
        for camera_id in self.cameras:
            if self.start_camera_thread(camera_id):
                self.system_stats['active_cameras'] += 1
        
        logger.info(f"تم بدء {self.system_stats['active_cameras']} كاميرا")
        return self.system_stats['active_cameras'] > 0
    
    def stop_all_cameras(self):
        """إيقاف جميع الكاميرات"""
        logger.info("إيقاف جميع الكاميرات...")
        self.running = False
        
        # انتظار انتهاء جميع الخيوط
        for camera_id, thread in self.camera_threads.items():
            thread.join(timeout=5)
            logger.info(f"تم إيقاف خيط الكاميرا {camera_id}")
        
        # تنظيف الموارد
        for camera_id, camera_info in self.cameras.items():
            camera_info['processor'].cleanup()
        
        self.system_stats['active_cameras'] = 0
        logger.info("تم إيقاف جميع الكاميرات")
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات النظام"""
        # تحديث إحصائيات الأشخاص
        total_persons = len(self.cross_tracker.global_persons)
        known_persons = sum(1 for p in self.cross_tracker.global_persons.values() 
                          if p['name'] != 'Unknown')
        
        self.system_stats.update({
            'total_persons': total_persons,
            'known_persons': known_persons,
            'uptime': (datetime.now() - self.system_stats['start_time']).seconds 
                     if self.system_stats['start_time'] else 0
        })
        
        # إحصائيات الكاميرات
        camera_stats = {}
        for camera_id, camera_info in self.cameras.items():
            camera_stats[camera_id] = {
                'name': camera_info['config']['name'],
                'location': camera_info['config']['location'],
                'frames_processed': camera_info['stats']['frames_processed'],
                'persons_detected': camera_info['stats']['persons_detected'],
                'last_frame_time': camera_info['last_frame_time'],
                'is_active': time.time() - camera_info['last_frame_time'] < 5
            }
        
        return {
            'system': self.system_stats,
            'cameras': camera_stats,
            'cross_camera_persons': [
                self.cross_tracker.get_person_summary(global_id)
                for global_id in self.cross_tracker.global_persons.keys()
            ]
        }
    
    def get_camera_frame(self, camera_id: str) -> Optional[Tuple[np.ndarray, Dict]]:
        """الحصول على آخر إطار من كاميرا محددة"""
        if camera_id not in self.cameras:
            return None
        
        frame_queue = self.cameras[camera_id]['queue']
        
        try:
            return frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def save_system_report(self, output_file: Optional[str] = None) -> str:
        """حفظ تقرير النظام"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"reports/multi_camera_report_{timestamp}.json"
        
        report_path = Path(output_file)
        report_path.parent.mkdir(exist_ok=True)
        
        stats = self.get_system_statistics()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"تم حفظ تقرير النظام: {report_path}")
        return str(report_path)
