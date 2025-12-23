"""
Face Recognition System - InsightFace integration
Phase 3 Implementation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import pickle
from pathlib import Path
import cv2

logger = logging.getLogger(__name__)


class FaceRecognitionSystem:
    """نظام التعرف على الوجوه باستخدام InsightFace"""
    
    def __init__(
        self,
        model_name: str = "buffalo_sc",  # أخف نموذج
        ctx_id: int = -1,  # -1 = CPU, 0+ = GPU
        det_size: Tuple[int, int] = (320, 320),
        similarity_threshold: float = 0.5
    ):
        """
        تهيئة نظام التعرف على الوجوه
        
        Args:
            model_name: اسم النموذج (buffalo_l للدقة، buffalo_sc للسرعة)
            ctx_id: -1 للـ CPU، 0 للـ GPU
            det_size: حجم الصورة للكشف
            similarity_threshold: عتبة التشابه للتعرف
        """
        self.similarity_threshold = similarity_threshold
        self.model_name = model_name
        self.ctx_id = ctx_id
        self.det_size = det_size
        
        # قاعدة بيانات الوجوه المعروفة
        self.known_faces: Dict[str, np.ndarray] = {}
        self.database_path = Path("attendance_db/faces.pkl")
        
        # تحميل InsightFace
        self._init_model()
        
        # تحميل قاعدة البيانات
        self._load_database()
    
    def _init_model(self):
        """تهيئة نموذج InsightFace"""
        try:
            from insightface.app import FaceAnalysis
            
            self.app = FaceAnalysis(
                name=self.model_name,
                allowed_modules=['detection', 'recognition']
            )
            self.app.prepare(ctx_id=self.ctx_id, det_size=self.det_size)
            logger.info(f"✓ تم تحميل InsightFace: {self.model_name}")
            self.initialized = True
            
        except ImportError:
            logger.warning("⚠️ InsightFace غير مثبت - استخدم: pip install insightface onnxruntime")
            self.app = None
            self.initialized = False
        except Exception as e:
            logger.error(f"✗ فشل تحميل InsightFace: {e}")
            self.app = None
            self.initialized = False
    
    def _load_database(self):
        """تحميل قاعدة بيانات الوجوه"""
        if self.database_path.exists():
            try:
                with open(self.database_path, 'rb') as f:
                    self.known_faces = pickle.load(f)
                logger.info(f"✓ تم تحميل {len(self.known_faces)} وجه من قاعدة البيانات")
            except Exception as e:
                logger.warning(f"فشل تحميل قاعدة البيانات: {e}")
                self.known_faces = {}
    
    def _save_database(self):
        """حفظ قاعدة بيانات الوجوه"""
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.database_path, 'wb') as f:
                pickle.dump(self.known_faces, f)
            logger.info(f"✓ تم حفظ {len(self.known_faces)} وجه في قاعدة البيانات")
        except Exception as e:
            logger.error(f"فشل حفظ قاعدة البيانات: {e}")
    
    def detect_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        كشف الوجوه في الصورة
        
        Args:
            frame: صورة BGR
            
        Returns:
            قائمة بالوجوه المكتشفة
        """
        if not self.initialized or self.app is None:
            return []
        
        try:
            # تحويل BGR إلى RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # كشف الوجوه
            faces = self.app.get(rgb_frame)
            
            results = []
            for face in faces:
                results.append({
                    'box': face.bbox.astype(int).tolist(),  # [x1, y1, x2, y2]
                    'det_score': float(face.det_score),
                    'embedding': face.embedding,
                    'landmark': face.landmark if hasattr(face, 'landmark') else None
                })
            
            return results
            
        except Exception as e:
            logger.error(f"خطأ في كشف الوجوه: {e}")
            return []
    
    def recognize_face(self, embedding: np.ndarray) -> Optional[Tuple[str, float]]:
        """
        التعرف على وجه من embedding
        
        Args:
            embedding: بصمة الوجه
            
        Returns:
            (اسم الشخص, نسبة التشابه) أو None
        """
        if len(self.known_faces) == 0:
            return None
        
        best_match = None
        best_similarity = 0.0
        
        for name, known_embedding in self.known_faces.items():
            similarity = self._compute_similarity(embedding, known_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = name
        
        if best_similarity >= self.similarity_threshold:
            return (best_match, best_similarity)
        
        return None
    
    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """حساب التشابه بين بصمتين (Cosine Similarity)"""
        emb1 = emb1 / np.linalg.norm(emb1)
        emb2 = emb2 / np.linalg.norm(emb2)
        return float(np.dot(emb1, emb2))
    
    def register_face(self, name: str, frame: np.ndarray) -> bool:
        """
        تسجيل وجه جديد
        
        Args:
            name: اسم الشخص
            frame: صورة تحتوي على الوجه
            
        Returns:
            True إذا نجح التسجيل
        """
        faces = self.detect_faces(frame)
        
        if len(faces) == 0:
            logger.warning(f"لم يتم العثور على وجه لتسجيل: {name}")
            return False
        
        if len(faces) > 1:
            logger.warning(f"تم العثور على أكثر من وجه - استخدام الأول")
        
        # استخدام أفضل وجه (أعلى ثقة)
        best_face = max(faces, key=lambda f: f['det_score'])
        
        self.known_faces[name] = best_face['embedding']
        self._save_database()
        
        logger.info(f"✓ تم تسجيل الوجه: {name}")
        return True
    
    def register_face_from_embedding(self, name: str, embedding: np.ndarray) -> bool:
        """تسجيل وجه من embedding مباشرة"""
        self.known_faces[name] = embedding
        self._save_database()
        logger.info(f"✓ تم تسجيل الوجه: {name}")
        return True
    
    def remove_face(self, name: str) -> bool:
        """حذف وجه من قاعدة البيانات"""
        if name in self.known_faces:
            del self.known_faces[name]
            self._save_database()
            logger.info(f"✓ تم حذف الوجه: {name}")
            return True
        return False
    
    def list_registered_faces(self) -> List[str]:
        """قائمة الوجوه المسجلة"""
        return list(self.known_faces.keys())
    
    def get_registered_count(self) -> int:
        """عدد الوجوه المسجلة"""
        return len(self.known_faces)
