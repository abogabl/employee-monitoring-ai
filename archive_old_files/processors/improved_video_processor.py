"""
معالج فيديو محسّن مع نظام التعلم الذاتي
Improved Video Processor with Self-Learning Integration
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

from .level2_video_processor import Level2VideoProcessor, make_json_serializable

logger = logging.getLogger("improved_video_processor")


class PersonIdentity:
    """هوية شخص ثابتة عبر الفيديو"""
    
    def __init__(self, person_id: int, name: str = "Unknown"):
        self.person_id = person_id  # معرف ثابت
        self.name = name
        self.track_ids = set()  # كل track IDs المرتبطة بهذا الشخص
        self.embeddings = []  # Face embeddings للمطابقة
        self.best_snapshot = None  # أفضل صورة
        self.best_quality = 0.0  # جودة أفضل صورة
        self.first_seen = None
        self.last_seen = None
        self.total_frames = 0
        self.activities = defaultdict(int)
        
    def add_track_id(self, track_id: int):
        """إضافة track ID جديد لنفس الشخص"""
        self.track_ids.add(track_id)
    
    def add_embedding(self, embedding: np.ndarray):
        """إضافة embedding للمطابقة"""
        if len(self.embeddings) < 5:  # احتفظ بأحدث 5
            self.embeddings.append(embedding)
        else:
            self.embeddings.pop(0)
            self.embeddings.append(embedding)
    
    def matches_embedding(self, embedding: np.ndarray, threshold: float = 0.75) -> bool:
        """هل هذا embedding يطابق الشخص؟"""
        if not self.embeddings:
            return False
        
        from scipy.spatial.distance import cosine
        
        for stored_emb in self.embeddings:
            similarity = 1 - cosine(embedding, stored_emb)
            if similarity > threshold:
                return True
        
        return False
    
    def update_best_snapshot(self, snapshot, quality: float):
        """تحديث أفضل صورة"""
        if quality > self.best_quality:
            self.best_snapshot = snapshot
            self.best_quality = quality


class ImprovedVideoProcessor(Level2VideoProcessor):
    """معالج فيديو محسّن مع تتبع ذكي ونظام التعلم الذاتي"""
    
    def __init__(
        self,
        device: str = "cpu",
        imgsz: int = 416,
        conf_threshold: float = 0.35,
        enable_face_recognition: bool = True,
        enable_activity_recognition: bool = True,
        enable_advanced_ai: bool = True,
        enable_self_learning: bool = True,
        yolo_model: str = "s",
        activity_window: int = 15,
        random_seed: int = None
    ):
        super().__init__(
            device=device,
            imgsz=imgsz,
            conf_threshold=conf_threshold,
            enable_face_recognition=enable_face_recognition,
            enable_activity_recognition=enable_activity_recognition,
            enable_advanced_ai=enable_advanced_ai,
            yolo_model=yolo_model,
            activity_window=activity_window,
            random_seed=random_seed
        )
        
        # نظام إدارة الهويات
        self.enable_self_learning = enable_self_learning
        self.person_identities: Dict[int, PersonIdentity] = {}  # person_id -> PersonIdentity
        self.track_to_person: Dict[int, int] = {}  # track_id -> person_id
        self.next_person_id = 1
        
        # نظام التعلم الذاتي
        self.data_collector = None
        self.quality_assessor = None
        if enable_self_learning:
            try:
                from .self_learning import DataCollector, QualityAssessor
                self.data_collector = DataCollector(
                    min_confidence=0.70,  # أقل قليلاً للفيديو
                    max_images_per_day=50  # حد أعلى للفيديو
                )
                self.quality_assessor = QualityAssessor()
                logger.info("✓ تم تفعيل نظام التعلم الذاتي")
            except Exception as e:
                logger.warning(f"تعذر تفعيل التعلم الذاتي: {e}")
                self.data_collector = None
                self.quality_assessor = None
        
        logger.info("✓ تم تهيئة المعالج المحسّن")
    
    def _calculate_image_quality(self, image: np.ndarray, bbox: tuple) -> float:
        """حساب جودة الصورة"""
        if self.quality_assessor:
            try:
                metrics = self.quality_assessor.assess_image(image, bbox)
                return metrics.overall_score
            except:
                pass
        
        # حساب بسيط بدون QualityAssessor
        # 1. الحجم
        h, w = image.shape[:2]
        size_score = min(1.0, (h * w) / (200 * 200))
        
        # 2. الوضوح (تباين)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(1.0, sharpness / 100.0)
        
        # 3. الإضاءة
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 130) / 130.0
        brightness_score = max(0.0, brightness_score)
        
        # المتوسط
        return (size_score * 0.3 + sharpness_score * 0.4 + brightness_score * 0.3)
    
    def _find_or_create_person_identity(
        self,
        track_id: int,
        face_embedding: Optional[np.ndarray],
        name: str = "Unknown"
    ) -> int:
        """إيجاد أو إنشاء هوية للشخص"""
        
        # 1. إذا كان track_id معروف بالفعل
        if track_id in self.track_to_person:
            return self.track_to_person[track_id]
        
        # 2. إذا كان لدينا embedding، ابحث عن شخص مطابق
        if face_embedding is not None:
            for person_id, identity in self.person_identities.items():
                if identity.matches_embedding(face_embedding):
                    # وجدنا الشخص! ربط track_id الجديد به
                    identity.add_track_id(track_id)
                    self.track_to_person[track_id] = person_id
                    logger.info(f"✓ ربط track {track_id} بالشخص {person_id} ({identity.name})")
                    return person_id
        
        # 3. شخص جديد
        person_id = self.next_person_id
        self.next_person_id += 1
        
        identity = PersonIdentity(person_id, name)
        identity.add_track_id(track_id)
        if face_embedding is not None:
            identity.add_embedding(face_embedding)
        
        self.person_identities[person_id] = identity
        self.track_to_person[track_id] = person_id
        
        logger.info(f"✓ شخص جديد: {person_id} (track {track_id})")
        return person_id
    
    def _update_person_snapshot(
        self,
        person_id: int,
        frame: np.ndarray,
        bbox: tuple,
        snapshots_dir: Path
    ) -> Optional[str]:
        """تحديث صورة الشخص إذا كانت أفضل"""
        identity = self.person_identities.get(person_id)
        if not identity:
            return None
        
        try:
            x1, y1, x2, y2 = bbox
            person_crop = frame[y1:y2, x1:x2]
            
            if person_crop.size == 0:
                return None
            
            # حساب جودة الصورة
            quality = self._calculate_image_quality(person_crop, bbox)
            
            # تحديث إذا كانت أفضل
            if quality > identity.best_quality:
                timestamp = int(time.time())
                snapshot_name = f"person_{person_id}_{timestamp}.jpg"
                snapshot_path = snapshots_dir / snapshot_name
                
                cv2.imwrite(str(snapshot_path), person_crop)
                snapshot_url = f"uploads/test_videos/snapshots/{snapshot_name}"
                
                identity.update_best_snapshot(snapshot_url, quality)
                
                logger.info(f"✓ تحديث صورة الشخص {person_id}: جودة {quality:.2f}")
                return snapshot_url
            
            return identity.best_snapshot
            
        except Exception as e:
            logger.debug(f"فشل تحديث صورة الشخص {person_id}: {e}")
            return None
    
    def _collect_for_self_learning(
        self,
        frame: np.ndarray,
        person_id: int,
        name: str,
        confidence: float,
        bbox: tuple,
        predictions: List[Dict]
    ):
        """جمع صورة لنظام التعلم الذاتي"""
        if not self.data_collector:
            return
        
        # جمع فقط للأشخاص المعروفين
        if name == "Unknown":
            return
        
        try:
            # جمع الصورة
            image_id = self.data_collector.collect_face(
                frame=frame,
                employee_id=name,
                confidence=confidence,
                bbox=bbox,
                predictions=predictions,
                metadata={
                    'source': 'video_processor',
                    'person_id': person_id,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            if image_id:
                logger.debug(f"✓ جمع صورة للتعلم الذاتي: {name} (#{image_id})")
                
        except Exception as e:
            logger.debug(f"فشل جمع صورة للتعلم الذاتي: {e}")
    
    def _process_tracked_person(
        self,
        track_id: int,
        track_data: dict,
        processing_frame: np.ndarray,
        frame: np.ndarray,
        person_data: dict,
        snapshots_dir: Path,
        current_time: float,
        processed_frames: int
    ) -> Optional[int]:
        """معالجة شخص مُتتبع وإرجاع person_id الثابت"""
        
        x1, y1, x2, y2 = track_data['box']
        
        # استخراج embedding للتعرف
        face_embedding = None
        recognized_name = "Unknown"
        confidence = 0.0
        
        if self.face_recognizer:
            try:
                person_crop = processing_frame[y1:y2, x1:x2]
                if person_crop.size > 0:
                    faces = self.face_recognizer.detect_faces(person_crop)
                    if faces:
                        best_face = max(faces, key=lambda f: f.get('det_score', 0.0))
                        if best_face.get('det_score', 0.0) > 0.5:
                            face_embedding = best_face['embedding']
                            
                            matches = self.face_recognizer.recognize_face(face_embedding)
                            if matches and matches[0]['similarity'] > 0.6:
                                recognized_name = matches[0]['name']
                                confidence = matches[0]['similarity']
            except Exception as e:
                logger.debug(f"خطأ في التعرف: {e}")
        
        # إيجاد أو إنشاء هوية ثابتة
        person_id = self._find_or_create_person_identity(
            track_id, face_embedding, recognized_name
        )
        
        # تحديث معلومات الهوية
        identity = self.person_identities[person_id]
        identity.last_seen = current_time
        identity.total_frames += 1
        if recognized_name != "Unknown":
            identity.name = recognized_name
        
        # تحديث/حفظ أفضل صورة
        snapshot = self._update_person_snapshot(
            person_id, processing_frame, (x1, y1, x2, y2), snapshots_dir
        )
        
        # جمع للتعلم الذاتي
        if self.data_collector and recognized_name != "Unknown" and confidence > 0:
            # جمع كل 30 إطار لتجنب الحمل الزائد
            if processed_frames % 30 == 0:
                predictions = [{
                    'employee_id': recognized_name,
                    'name': recognized_name,
                    'confidence': confidence
                }]
                self._collect_for_self_learning(
                    processing_frame, person_id, recognized_name,
                    confidence, (x1, y1, x2, y2), predictions
                )
        
        return person_id
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        frame_skip: int = 1,
        max_duration: int = None,
        task_id: str = None,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """معالجة فيديو مع التحسينات"""
        
        # إعادة تعيين حالة الهويات
        self.person_identities.clear()
        self.track_to_person.clear()
        self.next_person_id = 1
        
        logger.info("🎬 بدء معالجة الفيديو المحسّن...")
        logger.info(f"  - التعلم الذاتي: {'مفعّل' if self.data_collector else 'معطّل'}")
        logger.info(f"  - تتبع ذكي: مفعّل")
        
        # استدعاء معالجة الفيديو الأساسية
        result = super().process_video(
            input_path,
            output_path,
            frame_skip,
            max_duration,
            task_id,
            enable_progress_tracking
        )
        
        # إضافة معلومات الهويات
        result['unique_persons_detected'] = len(self.person_identities)
        result['total_persons_raw'] = result.get('total_persons', 0)  # track IDs القديمة
        result['total_persons'] = len(self.person_identities)  # العدد الصحيح
        
        result['person_identities'] = {
            str(pid): {
                'name': ident.name,
                'total_frames': ident.total_frames,
                'snapshot': ident.best_snapshot,
                'quality': round(ident.best_quality, 2),
                'track_ids': list(ident.track_ids)
            }
            for pid, ident in self.person_identities.items()
        }
        
        # إحصائيات التعلم الذاتي
        if self.data_collector:
            stats = self.data_collector.get_session_stats()
            result['self_learning_stats'] = stats
        
        logger.info(f"✅ اكتمل: {len(self.person_identities)} شخص فريد")
        logger.info(f"   (كان {result['total_persons_raw']} track IDs قبل التحسين)")
        
        return result
