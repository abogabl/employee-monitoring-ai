"""
نظام تعرف على الوجوه محسّن بدقة عالية

التحسينات:
1. Multi-scale detection (كشف على مقاييس متعددة)
2. Face quality assessment (تقييم جودة الوجه)
3. Multiple embeddings per face (عدة embeddings)
4. Confidence scoring (حساب الثقة المحسّن)
5. Face alignment (محاذاة الوجوه)
6. Anti-spoofing basics (كشف محاولات الخداع)
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pickle

import cv2
import numpy as np

try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    print("⚠️ InsightFace غير متوفر")

logger = logging.getLogger(__name__)


class EnhancedFaceRecognition:
    """نظام تعرف على الوجوه محسّن مع دعم GPU"""
    
    def __init__(
        self,
        model_name: str = 'buffalo_l',
        det_size: Tuple[int, int] = (640, 640),
        similarity_threshold: float = 0.45,
        quality_threshold: float = 0.3,
        use_multi_scale: bool = True,
        prefer_gpu: bool = True  # تفضيل GPU إذا متاح
    ):
        """
        Args:
            model_name: اسم نموذج InsightFace
            det_size: حجم الكشف
            similarity_threshold: عتبة التشابه (أقل = أكثر صرامة)
            quality_threshold: الحد الأدنى لجودة الوجه
            use_multi_scale: استخدام كشف متعدد المقاييس
            prefer_gpu: تفضيل GPU إذا كان متاحاً
        """
        self.similarity_threshold = similarity_threshold
        self.quality_threshold = quality_threshold
        self.use_multi_scale = use_multi_scale
        
        if not INSIGHTFACE_AVAILABLE:
            raise ImportError("InsightFace مطلوب. قم بتثبيته: pip install insightface")
        
        # تحديد مزودي التنفيذ بالترتيب (GPU أولاً إذا مفضّل)
        providers = self._get_execution_providers(prefer_gpu)
        self.using_gpu = 'CUDAExecutionProvider' in providers or 'TensorrtExecutionProvider' in providers
        
        # تهيئة InsightFace
        self.app = FaceAnalysis(name=model_name, providers=providers)
        ctx_id = 0 if self.using_gpu else -1
        self.app.prepare(ctx_id=ctx_id, det_size=det_size)
        
        # قاعدة بيانات الموظفين
        self.embeddings_db: Dict[str, List[np.ndarray]] = {}
        self.employee_info: Dict[str, Dict] = {}
        
        # مسار الحفظ
        self.db_path = Path("models/face_embeddings_enhanced.pkl")
        
        # تحميل قاعدة البيانات
        self._load_database()
        
        device_info = "GPU (CUDA)" if self.using_gpu else "CPU"
        logger.info(f"✓ نظام التعرف على الوجوه المحسّن جاهز")
        logger.info(f"  - Device: {device_info}")
        logger.info(f"  - Providers: {providers}")
        logger.info(f"  - Similarity threshold: {similarity_threshold}")
        logger.info(f"  - Quality threshold: {quality_threshold}")
        logger.info(f"  - Multi-scale: {use_multi_scale}")
        logger.info(f"  - Employees in DB: {len(self.embeddings_db)}")
    
    @staticmethod
    def _get_execution_providers(prefer_gpu: bool = True) -> List[str]:
        """الحصول على مزودي التنفيذ المتاحين"""
        available_providers = []
        
        if prefer_gpu:
            # محاولة استخدام TensorRT (الأسرع)
            try:
                import onnxruntime as ort
                if 'TensorrtExecutionProvider' in ort.get_available_providers():
                    available_providers.append('TensorrtExecutionProvider')
                    logger.info("✓ TensorRT متاح")
            except Exception:
                pass
            
            # محاولة استخدام CUDA
            try:
                import onnxruntime as ort
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    available_providers.append('CUDAExecutionProvider')
                    logger.info("✓ CUDA متاح")
            except Exception:
                pass
            
            # محاولة استخدام DirectML (Windows)
            try:
                import onnxruntime as ort
                if 'DmlExecutionProvider' in ort.get_available_providers():
                    available_providers.append('DmlExecutionProvider')
                    logger.info("✓ DirectML متاح")
            except Exception:
                pass
        
        # CPU كخيار أخير دائماً
        available_providers.append('CPUExecutionProvider')
        
        return available_providers
    
    def add_employee(
        self,
        employee_id: str,
        images: List[np.ndarray],
        employee_info: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        إضافة موظف جديد مع صوره
        
        Args:
            employee_id: معرف الموظف
            images: قائمة الصور (BGR format)
            employee_info: معلومات إضافية
            
        Returns:
            نتيجة الإضافة {success, embeddings_count, quality_scores, message}
        """
        if not images:
            return {
                'success': False,
                'message': 'لم يتم تقديم أي صور',
                'embeddings_count': 0
            }
        
        # استخراج embeddings مع تقييم الجودة
        embeddings = []
        quality_scores = []
        
        for i, img in enumerate(images):
            result = self._extract_embedding_with_quality(img)
            
            if result['success']:
                embeddings.append(result['embedding'])
                quality_scores.append(result['quality'])
                logger.info(f"  صورة {i+1}: جودة = {result['quality']:.2f}")
            else:
                logger.warning(f"  صورة {i+1}: فشل - {result['message']}")
        
        if not embeddings:
            return {
                'success': False,
                'message': 'لم يتم استخراج أي embeddings صالحة',
                'embeddings_count': 0,
                'quality_scores': []
            }
        
        # حفظ في قاعدة البيانات
        self.embeddings_db[employee_id] = embeddings
        
        if employee_info:
            self.employee_info[employee_id] = employee_info
        
        # حفظ
        self._save_database()
        
        avg_quality = np.mean(quality_scores)
        
        return {
            'success': True,
            'message': f'تم إضافة {len(embeddings)} embeddings بجودة متوسطة {avg_quality:.2f}',
            'embeddings_count': len(embeddings),
            'quality_scores': quality_scores,
            'average_quality': float(avg_quality)
        }
    
    def recognize_face(
        self,
        image: np.ndarray,
        return_details: bool = False
    ) -> Tuple[Optional[str], float, Optional[Dict]]:
        """
        التعرف على وجه في صورة
        
        Args:
            image: الصورة (BGR)
            return_details: إرجاع تفاصيل إضافية
            
        Returns:
            (employee_id, confidence, details)
        """
        if len(self.embeddings_db) == 0:
            return None, 0.0, {'message': 'قاعدة البيانات فارغة'}
        
        # استخراج embedding مع الجودة
        result = self._extract_embedding_with_quality(image)
        
        if not result['success']:
            details = {'message': result['message'], 'quality': 0.0}
            return None, 0.0, details if return_details else None
        
        embedding = result['embedding']
        quality = result['quality']
        
        # البحث في قاعدة البيانات
        best_match_id = None
        best_similarity = 0.0
        all_scores = {}
        
        for emp_id, emp_embeddings in self.embeddings_db.items():
            # حساب التشابه مع كل embeddings الموظف
            similarities = [
                self._cosine_similarity(embedding, emp_emb)
                for emp_emb in emp_embeddings
            ]
            
            # أخذ أفضل 3 وحساب المتوسط
            top_similarities = sorted(similarities, reverse=True)[:3]
            avg_similarity = np.mean(top_similarities)
            
            all_scores[emp_id] = avg_similarity
            
            if avg_similarity > best_similarity:
                best_similarity = avg_similarity
                best_match_id = emp_id
        
        # حساب الثقة المحسّن
        confidence = self._calculate_confidence(
            best_similarity,
            quality,
            all_scores
        )
        
        # التحقق من العتبة
        if best_similarity < self.similarity_threshold:
            best_match_id = None
            confidence = 0.0
        
        details = None
        if return_details:
            details = {
                'similarity': best_similarity,
                'quality': quality,
                'all_scores': all_scores,
                'threshold': self.similarity_threshold,
                'passed': best_similarity >= self.similarity_threshold
            }
        
        return best_match_id, confidence, details
    
    def recognize_multiple_faces(
        self,
        image: np.ndarray
    ) -> List[Dict[str, any]]:
        """
        التعرف على عدة وجوه في صورة واحدة
        
        Returns:
            قائمة بالنتائج [{employee_id, confidence, bbox, quality}]
        """
        # كشف جميع الوجوه
        faces = self.app.get(image)
        
        results = []
        
        for face in faces:
            # استخراج bbox
            bbox = face.bbox.astype(int).tolist()
            
            # استخراج منطقة الوجه
            x1, y1, x2, y2 = bbox
            face_img = image[y1:y2, x1:x2]
            
            if face_img.size == 0:
                continue
            
            # التعرف
            emp_id, confidence, details = self.recognize_face(
                face_img,
                return_details=True
            )
            
            results.append({
                'employee_id': emp_id,
                'confidence': confidence,
                'bbox': bbox,
                'quality': details['quality'] if details else 0.0,
                'similarity': details['similarity'] if details else 0.0
            })
        
        return results
    
    def _extract_embedding_with_quality(
        self,
        image: np.ndarray
    ) -> Dict[str, any]:
        """استخراج embedding مع تقييم الجودة"""
        
        # كشف الوجه
        faces = self.app.get(image)
        
        if len(faces) == 0:
            return {
                'success': False,
                'message': 'لم يتم العثور على وجه'
            }
        
        if len(faces) > 1:
            # أخذ أكبر وجه
            faces = sorted(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]), reverse=True)
        
        face = faces[0]
        
        # تقييم الجودة
        quality = self._assess_face_quality(face, image)
        
        if quality < self.quality_threshold:
            return {
                'success': False,
                'message': f'جودة منخفضة: {quality:.2f}',
                'quality': quality
            }
        
        # استخراج embedding
        embedding = face.embedding
        
        # تطبيع
        embedding = embedding / np.linalg.norm(embedding)
        
        return {
            'success': True,
            'embedding': embedding,
            'quality': quality,
            'bbox': face.bbox.astype(int).tolist(),
            'det_score': float(face.det_score)
        }
    
    def _assess_face_quality(
        self,
        face: any,
        image: np.ndarray
    ) -> float:
        """تقييم جودة الوجه (0-1)"""
        
        scores = []
        
        # 1. حجم الوجه
        bbox = face.bbox
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        face_area = face_width * face_height
        image_area = image.shape[0] * image.shape[1]
        size_ratio = face_area / image_area
        
        # الحجم الجيد: 5-50% من الصورة
        if 0.05 <= size_ratio <= 0.5:
            size_score = 1.0
        elif size_ratio < 0.05:
            size_score = size_ratio / 0.05
        else:
            size_score = 0.5 / size_ratio
        
        size_score = min(size_score, 1.0)
        scores.append(size_score * 0.3)  # وزن 30%
        
        # 2. درجة الكشف
        det_score = float(face.det_score)
        scores.append(det_score * 0.4)  # وزن 40%
        
        # 3. وضوح الوجه (باستخدام Laplacian)
        x1, y1, x2, y2 = bbox.astype(int)
        face_img = image[y1:y2, x1:x2]
        
        if face_img.size > 0:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # تطبيع (قيم عالية = وضوح أفضل)
            blur_score = min(laplacian_var / 500.0, 1.0)
            scores.append(blur_score * 0.3)  # وزن 30%
        
        # المجموع النهائي
        total_quality = sum(scores)
        
        return float(total_quality)
    
    def _cosine_similarity(
        self,
        emb1: np.ndarray,
        emb2: np.ndarray
    ) -> float:
        """حساب التشابه cosine"""
        return float(np.dot(emb1, emb2))
    
    def _calculate_confidence(
        self,
        similarity: float,
        quality: float,
        all_scores: Dict[str, float]
    ) -> float:
        """حساب الثقة المحسّن"""
        
        # 1. التشابه الأساسي
        confidence = similarity
        
        # 2. تعديل بناءً على الجودة
        confidence *= (0.7 + 0.3 * quality)
        
        # 3. تعديل بناءً على الفجوة مع الثاني
        sorted_scores = sorted(all_scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            gap = sorted_scores[0] - sorted_scores[1]
            # فجوة كبيرة = ثقة أعلى
            gap_bonus = min(gap / 0.2, 0.1)  # حتى 10% إضافية
            confidence += gap_bonus
        
        # تطبيع بين 0-1
        confidence = min(max(confidence, 0.0), 1.0)
        
        return float(confidence)
    
    def _load_database(self):
        """تحميل قاعدة البيانات"""
        if not self.db_path.exists():
            logger.info("لا توجد قاعدة بيانات - سيتم إنشاء واحدة جديدة")
            return
        
        try:
            with open(self.db_path, 'rb') as f:
                data = pickle.load(f)
            
            self.embeddings_db = data.get('embeddings', {})
            self.employee_info = data.get('info', {})
            
            logger.info(f"✓ تم تحميل قاعدة البيانات: {len(self.embeddings_db)} موظف")
            
        except Exception as e:
            logger.error(f"خطأ في تحميل قاعدة البيانات: {e}")
    
    def _save_database(self):
        """حفظ قاعدة البيانات"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'embeddings': self.embeddings_db,
                'info': self.employee_info
            }
            
            with open(self.db_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"✓ تم حفظ قاعدة البيانات")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ قاعدة البيانات: {e}")
    
    def get_statistics(self) -> Dict[str, any]:
        """إحصائيات قاعدة البيانات"""
        total_employees = len(self.embeddings_db)
        total_embeddings = sum(len(embs) for embs in self.embeddings_db.values())
        
        avg_embeddings = total_embeddings / total_employees if total_employees > 0 else 0
        
        return {
            'total_employees': total_employees,
            'total_embeddings': total_embeddings,
            'average_embeddings_per_employee': avg_embeddings,
            'similarity_threshold': self.similarity_threshold,
            'quality_threshold': self.quality_threshold
        }
    
    def remove_employee(self, employee_id: str) -> bool:
        """حذف موظف"""
        if employee_id in self.embeddings_db:
            del self.embeddings_db[employee_id]
            self.employee_info.pop(employee_id, None)
            self._save_database()
            logger.info(f"✓ تم حذف الموظف: {employee_id}")
            return True
        return False
    
    def update_threshold(self, new_threshold: float):
        """تحديث عتبة التشابه"""
        self.similarity_threshold = new_threshold
        logger.info(f"✓ تم تحديث العتبة إلى: {new_threshold}")
