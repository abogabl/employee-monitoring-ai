"""
نظام التعرف على وجوه الموظفين باستخدام InsightFace.
- تحميل نموذج FaceAnalysis (buffalo_l)
- بناء قاعدة بيانات embeddings للموظفين من مجلد الصور
- مطابقة الوجوه باستخدام Cosine Similarity
- حفظ/تحميل التضمينات إلى/من ملف pickle
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from insightface.app import FaceAnalysis  # type: ignore
except Exception as e:  # pragma: no cover - لمكتبة خارجية
    FaceAnalysis = None  # type: ignore

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


@dataclass
class EmployeeEmbedding:
    emp_id: str
    name: str
    embedding: np.ndarray  # شكل (512,) غالباً


class FaceRecognitionSystem:
    """نظام التعرف على الوجوه باستخدام InsightFace.

    المعاملات:
    - model_name: اسم نموذج InsightFace (مثل buffalo_l)
    - threshold: حد التشابه (cosine) لقبول المطابقة
    - det_size: حجم الإدخال للكاشف
    - providers: مزودي onnxruntime (CPU افتراضي)
    """

    def __init__(
        self,
        model_name: str = "buffalo_l",
        threshold: float = 0.6,
        det_size: Tuple[int, int] = (640, 640),
        providers: Optional[List[str]] = None,
    ) -> None:
        if FaceAnalysis is None:
            raise ImportError("insightface غير مثبت. رجاءً ثبِّته من requirements.txt")

        self.model_name = model_name
        self.threshold = float(threshold)
        self.det_size = det_size
        self.providers = providers or ["CPUExecutionProvider"]

        # تحضير التطبيق
        try:
            self.app = FaceAnalysis(name=self.model_name, providers=self.providers)
            self.app.prepare(ctx_id=0, det_size=list(self.det_size))  # ctx_id=0 لـ GPU إن توفر، وإلا CPU
            logger.info("تم تحميل نموذج InsightFace: %s", self.model_name)
        except Exception as e:
            logger.exception("فشل تهيئة InsightFace: %s", e)
            raise

        # قاعدة بيانات التضمينات: emp_id -> {name, embeddings: List[np.ndarray]}
        self.encodings: Dict[str, Dict[str, Any]] = {}
        self.unknown_faces_count: int = 0

    # --------------------------- واجهات عامة ---------------------------
    def load_employees_database(self, faces_dir: str | Path = "employees_database/faces/") -> None:
        """قراءة صور الموظفين من بنية: employees_database/faces/EMP001/*.jpg وبناء قاعدة التضمينات."""
        faces_root = Path(faces_dir)
        if not faces_root.exists():
            logger.warning("مجلد الوجوه غير موجود: %s", faces_root)
            return

        emp_dirs = [p for p in faces_root.iterdir() if p.is_dir()]
        total_images = 0
        built = 0
        for emp_dir in emp_dirs:
            emp_id = emp_dir.name
            images = sorted([p for p in emp_dir.glob("*.*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
            if not images:
                continue

            # اسم الموظف الافتراضي من ملف نصي اختياري name.txt داخل المجلد، وإلا emp_id
            name_file = emp_dir / "name.txt"
            name = name_file.read_text(encoding="utf-8").strip() if name_file.exists() else emp_id

            # جمع كل الوجوه الصالحة أولاً
            valid_faces = []
            for img_path in images:
                img = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    logger.warning("تعذر قراءة الصورة: %s", img_path)
                    continue
                faces = self.detect_faces(img)
                for face in faces:
                    # فلترة جودة الوجه
                    det_score = float(face.get("det_score", 0.0))
                    if det_score < 0.7:  # حد أدنى لجودة الكشف
                        continue
                    
                    # فحص المسافة بين العينين إن توفرت landmarks
                    landmarks = face.get("landmarks", [])
                    if landmarks and len(landmarks) >= 2:
                        eye_dist = np.linalg.norm(np.array(landmarks[0]) - np.array(landmarks[1]))
                        if eye_dist < 70:  # حد أدنى للمسافة بين العينين
                            continue
                    
                    valid_faces.append((face, det_score, str(img_path)))
            
            # ترتيب حسب الجودة والاحتفاظ بأفضل 10
            valid_faces.sort(key=lambda x: x[1], reverse=True)
            top_faces = valid_faces[:10]  # أفضل 10 وجوه
            
            for face, score, path in top_faces:
                emb = face["embedding"]
                self._add_embedding(emp_id, name, emb)
                total_images += 1
                logger.debug("تم قبول وجه من %s بدرجة %.3f", path, score)
            if emp_id in self.encodings:
                built += 1

        logger.info("تم بناء التضمينات: موظفون=%d | صور معالجة=%d", built, total_images)

    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """كشف الوجوه وإرجاع قائمة قواميس: {box, landmarks, embedding, det_score}."""
        if image is None or image.size == 0:
            return []
        try:
            faces = self.app.get(image)
        except Exception as e:
            logger.exception("خطأ أثناء كشف الوجوه: %s", e)
            return []

        results: List[Dict[str, Any]] = []
        for f in faces:
            box = f.bbox.astype(int).tolist()  # [x1,y1,x2,y2]
            kps = f.kps.astype(int).tolist() if hasattr(f, "kps") else []
            # بعض إصدارات insightface تضع embedding في f.normed_embedding أو f.embedding
            emb = getattr(f, "normed_embedding", None)
            if emb is None:
                emb = getattr(f, "embedding", None)
            if emb is None:
                # استخراج embedding عبر عرض f.normed_embedding من app
                try:
                    # عادة app.get يُرجع normed_embedding جاهزاً، إذا لم يتوفر نتخطى
                    continue
                except Exception:
                    continue
            emb = np.array(emb, dtype=np.float32)
            det_score = float(getattr(f, "det_score", 0.0))
            results.append({"box": box, "landmarks": kps, "embedding": emb, "det_score": det_score})
        return results

    def recognize_face(self, face_embedding: np.ndarray) -> Tuple[Optional[str], float, Optional[str]]:
        """مطابقة embedding مع قاعدة البيانات وإرجاع (emp_id, similarity, name)."""
        if face_embedding is None or face_embedding.size == 0 or not self.encodings:
            return None, 0.0, None
        best_emp: Optional[str] = None
        best_sim: float = -1.0
        best_name: Optional[str] = None

        # طبيع embedding لتوافق cosine
        a = face_embedding.astype(np.float32)
        a = a / (np.linalg.norm(a) + 1e-8)

        for emp_id, info in self.encodings.items():
            embs: List[np.ndarray] = info.get("embeddings", [])
            name = info.get("name", emp_id)
            if not embs:
                continue
            # مصفوفة (N, D)
            M = np.stack(embs, axis=0)
            M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-8)
            sims = (M @ a)
            sim = float(np.max(sims))
            if sim > best_sim:
                best_sim = sim
                best_emp = emp_id
                best_name = name

        if best_sim >= self.threshold:
            return best_emp, best_sim, best_name
        else:
            self.unknown_faces_count += 1
            return None, best_sim, None

    def add_employee(self, emp_id: str, name: str, images_list: List[str | Path]) -> bool:
        """إضافة موظف جديد إلى قاعدة التضمينات من قائمة صور."""
        added = 0
        for img_path in images_list:
            p = Path(img_path)
            img = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                logger.warning("تعذر قراءة الصورة: %s", p)
                continue
            faces = self.detect_faces(img)
            if not faces:
                continue
            best = max(faces, key=lambda f: float(f.get("det_score", 0.0)))
            self._add_embedding(emp_id, name, best["embedding"])
            added += 1
        logger.info("تمت إضافة %d تضمينات جديدة للموظف %s", added, emp_id)
        return added > 0

    def save_encodings(self, path: str | Path = "models/face_encodings.pkl") -> None:
        """حفظ قاعدة التضمينات في ملف pickle."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            emp_id: {"name": info.get("name", emp_id), "embeddings": [e.astype(np.float32) for e in info.get("embeddings", [])]}
            for emp_id, info in self.encodings.items()
        }
        with path.open("wb") as f:
            pickle.dump(payload, f)
        logger.info("تم حفظ التضمينات إلى: %s", path)

    def load_encodings(self, path: str | Path = "models/face_encodings.pkl") -> None:
        """تحميل قاعدة التضمينات من ملف pickle."""
        path = Path(path)
        if not path.exists():
            logger.warning("ملف التضمينات غير موجود: %s", path)
            return
        with path.open("rb") as f:
            payload = pickle.load(f)
        self.encodings = {}
        for emp_id, info in payload.items():
            name = info.get("name", emp_id)
            embs = [np.array(e, dtype=np.float32) for e in info.get("embeddings", [])]
            if embs:
                self.encodings[emp_id] = {"name": name, "embeddings": embs}
        logger.info("تم تحميل التضمينات: موظفون=%d", len(self.encodings))

    def get_unknown_faces_count(self) -> int:
        """عدد الوجوه غير المعروفة التي لم تتجاوز العتبة منذ آخر تشغيل."""
        return int(self.unknown_faces_count)

    # --------------------------- داخلي ---------------------------
    def _add_embedding(self, emp_id: str, name: str, emb: np.ndarray) -> None:
        emb = np.array(emb, dtype=np.float32)
        if emp_id not in self.encodings:
            self.encodings[emp_id] = {"name": name, "embeddings": []}
        self.encodings[emp_id]["embeddings"].append(emb)
