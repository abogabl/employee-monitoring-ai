"""
قاعدة بيانات نظام التعلم الذاتي
Self-Learning System Database

الجداول:
- training_images: الصور التدريبية المجمعة تلقائياً
- human_corrections: التصحيحات البشرية
- confirmation_queue: قائمة الانتظار للتأكيد
- model_performance: مؤشرات أداء النموذج
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import (
    ConfirmationQueue,
    HumanCorrection,
    ModelPerformance,
    QualityMetrics,
    TrainingImage,
)

logger = logging.getLogger(__name__)


class SelfLearningDB:
    """قاعدة بيانات نظام التعلم الذاتي"""
    
    def __init__(self, db_path: str | Path = "attendance_db/self_learning.db"):
        """تهيئة قاعدة البيانات
        
        Args:
            db_path: مسار ملف قاعدة البيانات
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connect()
        self._init_db()
        
        logger.info(f"✓ تم تهيئة قاعدة بيانات التعلم الذاتي: {self.db_path}")
    
    def _connect(self) -> None:
        """الاتصال بقاعدة البيانات"""
        self.conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
    
    @contextmanager
    def tx(self):
        """معاملة قاعدة بيانات"""
        try:
            yield
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"خطأ في المعاملة: {e}")
            raise
    
    def _init_db(self) -> None:
        """إنشاء الجداول"""
        with self.tx():
            # جدول الصور التدريبية
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS training_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id VARCHAR(50) NOT NULL,
                    image_path TEXT NOT NULL,
                    capture_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confidence FLOAT,
                    quality_score FLOAT,
                    quality_details TEXT,
                    metadata TEXT,
                    validated BOOLEAN DEFAULT 0,
                    used_in_training BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول التصحيحات البشرية
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS human_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER NOT NULL,
                    original_prediction VARCHAR(50),
                    corrected_to VARCHAR(50),
                    confidence FLOAT,
                    corrected_by VARCHAR(50),
                    correction_reason TEXT,
                    corrected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (image_id) REFERENCES training_images(id)
                )
            """)
            
            # جدول قائمة التأكيد
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS confirmation_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_id INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    top_predictions TEXT,
                    assigned_to VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    FOREIGN KEY (image_id) REFERENCES training_images(id)
                )
            """)
            
            # جدول أداء النموذج
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version VARCHAR(50) NOT NULL,
                    accuracy FLOAT,
                    precision FLOAT,
                    recall FLOAT,
                    f1_score FLOAT,
                    test_samples INTEGER,
                    training_date DATETIME,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # الفهارس لتحسين الأداء
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_images_employee "
                "ON training_images(employee_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_training_images_timestamp "
                "ON training_images(capture_timestamp)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_confirmation_queue_status "
                "ON confirmation_queue(status, priority)"
            )
    
    # ==================== training_images ====================
    
    def insert_training_image(self, image: TrainingImage) -> int:
        """إضافة صورة تدريبية
        
        Args:
            image: الصورة التدريبية
            
        Returns:
            معرف الصورة المضافة
        """
        with self.tx():
            quality_json = json.dumps(image.quality_details.to_dict()) if image.quality_details else None
            metadata_json = json.dumps(image.metadata) if image.metadata else "{}"
            
            cursor = self.conn.execute("""
                INSERT INTO training_images 
                (employee_id, image_path, capture_timestamp, confidence, 
                 quality_score, quality_details, metadata, validated, used_in_training)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image.employee_id,
                image.image_path,
                image.capture_timestamp or datetime.now(),
                image.confidence,
                image.quality_score,
                quality_json,
                metadata_json,
                image.validated,
                image.used_in_training,
            ))
            
            image_id = cursor.lastrowid
            logger.debug(f"✓ تم إضافة صورة تدريبية: {image_id} للموظف {image.employee_id}")
            return image_id
    
    def get_training_image(self, image_id: int) -> Optional[TrainingImage]:
        """الحصول على صورة تدريبية
        
        Args:
            image_id: معرف الصورة
            
        Returns:
            الصورة أو None
        """
        cursor = self.conn.execute(
            "SELECT * FROM training_images WHERE id = ?",
            (image_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_training_image(row)
    
    def get_employee_images(
        self,
        employee_id: str,
        validated_only: bool = False,
        limit: Optional[int] = None
    ) -> List[TrainingImage]:
        """الحصول على صور موظف
        
        Args:
            employee_id: معرف الموظف
            validated_only: فقط الصور المؤكدة
            limit: حد أقصى للنتائج
            
        Returns:
            قائمة الصور
        """
        query = "SELECT * FROM training_images WHERE employee_id = ?"
        params = [employee_id]
        
        if validated_only:
            query += " AND validated = 1"
        
        query += " ORDER BY capture_timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_training_image(row) for row in rows]
    
    def get_recent_images(
        self,
        days: int = 7,
        min_quality: float = 0.0
    ) -> List[TrainingImage]:
        """الحصول على الصور الحديثة
        
        Args:
            days: عدد الأيام
            min_quality: الحد الأدنى للجودة
            
        Returns:
            قائمة الصور
        """
        cursor = self.conn.execute("""
            SELECT * FROM training_images
            WHERE capture_timestamp >= datetime('now', '-' || ? || ' days')
            AND quality_score >= ?
            ORDER BY capture_timestamp DESC
        """, (days, min_quality))
        
        rows = cursor.fetchall()
        return [self._row_to_training_image(row) for row in rows]
    
    def count_employee_images_today(self, employee_id: str) -> int:
        """عدد صور الموظف اليوم
        
        Args:
            employee_id: معرف الموظف
            
        Returns:
            عدد الصور
        """
        cursor = self.conn.execute("""
            SELECT COUNT(*) FROM training_images
            WHERE employee_id = ?
            AND date(capture_timestamp) = date('now')
        """, (employee_id,))
        
        return cursor.fetchone()[0]
    
    def mark_as_validated(self, image_id: int) -> None:
        """تعليم صورة كمؤكدة"""
        with self.tx():
            self.conn.execute(
                "UPDATE training_images SET validated = 1 WHERE id = ?",
                (image_id,)
            )
    
    def mark_as_used_in_training(self, image_ids: List[int]) -> None:
        """تعليم صور كمستخدمة في التدريب"""
        with self.tx():
            placeholders = ','.join(['?' for _ in image_ids])
            self.conn.execute(
                f"UPDATE training_images SET used_in_training = 1 WHERE id IN ({placeholders})",
                image_ids
            )
    
    # ==================== human_corrections ====================
    
    def insert_correction(self, correction: HumanCorrection) -> int:
        """إضافة تصحيح بشري
        
        Args:
            correction: التصحيح
            
        Returns:
            معرف التصحيح
        """
        with self.tx():
            cursor = self.conn.execute("""
                INSERT INTO human_corrections
                (image_id, original_prediction, corrected_to, confidence,
                 corrected_by, correction_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                correction.image_id,
                correction.original_prediction,
                correction.corrected_to,
                correction.confidence,
                correction.corrected_by,
                correction.correction_reason,
            ))
            
            # تحديث الصورة كمؤكدة
            self.mark_as_validated(correction.image_id)
            
            correction_id = cursor.lastrowid
            logger.info(f"✓ تم إضافة تصحيح: {correction_id}")
            return correction_id
    
    def get_corrections_for_image(self, image_id: int) -> List[HumanCorrection]:
        """الحصول على تصحيحات صورة"""
        cursor = self.conn.execute(
            "SELECT * FROM human_corrections WHERE image_id = ?",
            (image_id,)
        )
        rows = cursor.fetchall()
        
        return [self._row_to_correction(row) for row in rows]
    
    def get_recent_corrections(self, days: int = 30) -> List[HumanCorrection]:
        """الحصول على التصحيحات الحديثة"""
        cursor = self.conn.execute("""
            SELECT * FROM human_corrections
            WHERE corrected_at >= datetime('now', '-' || ? || ' days')
            ORDER BY corrected_at DESC
        """, (days,))
        
        rows = cursor.fetchall()
        return [self._row_to_correction(row) for row in rows]
    
    # ==================== confirmation_queue ====================
    
    def add_to_confirmation_queue(
        self,
        image_id: int,
        top_predictions: List[Dict],
        priority: int = 5
    ) -> int:
        """إضافة إلى قائمة التأكيد
        
        Args:
            image_id: معرف الصورة
            top_predictions: أفضل التوقعات
            priority: الأولوية (1-10)
            
        Returns:
            معرف العنصر في القائمة
        """
        with self.tx():
            predictions_json = json.dumps(top_predictions)
            
            cursor = self.conn.execute("""
                INSERT INTO confirmation_queue
                (image_id, status, priority, top_predictions)
                VALUES (?, 'pending', ?, ?)
            """, (image_id, priority, predictions_json))
            
            queue_id = cursor.lastrowid
            logger.debug(f"✓ تم إضافة للقائمة: {queue_id}, أولوية {priority}")
            return queue_id
    
    def get_pending_confirmations(
        self,
        limit: int = 50,
        min_priority: int = 1
    ) -> List[ConfirmationQueue]:
        """الحصول على حالات التأكيد المعلقة
        
        Args:
            limit: الحد الأقصى
            min_priority: الحد الأدنى للأولوية
            
        Returns:
            قائمة الحالات
        """
        cursor = self.conn.execute("""
            SELECT * FROM confirmation_queue
            WHERE status = 'pending'
            AND priority >= ?
            ORDER BY priority ASC, created_at ASC
            LIMIT ?
        """, (min_priority, limit))
        
        rows = cursor.fetchall()
        return [self._row_to_confirmation_queue(row) for row in rows]
    
    def get_pending_count(self) -> int:
        """عدد الحالات المعلقة"""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM confirmation_queue WHERE status = 'pending'"
        )
        return cursor.fetchone()[0]
    
    def update_confirmation_status(
        self,
        queue_id: int,
        status: str,
        assigned_to: Optional[str] = None
    ) -> None:
        """تحديث حالة التأكيد
        
        Args:
            queue_id: معرف العنصر
            status: الحالة الجديدة
            assigned_to: المسند إليه (اختياري)
        """
        with self.tx():
            if status in ['confirmed', 'rejected']:
                self.conn.execute("""
                    UPDATE confirmation_queue
                    SET status = ?, assigned_to = ?, processed_at = ?
                    WHERE id = ?
                """, (status, assigned_to, datetime.now(), queue_id))
            else:
                self.conn.execute("""
                    UPDATE confirmation_queue
                    SET status = ?, assigned_to = ?
                    WHERE id = ?
                """, (status, assigned_to, queue_id))
    
    # ==================== model_performance ====================
    
    def insert_performance(self, performance: ModelPerformance) -> int:
        """إضافة مؤشرات أداء
        
        Args:
            performance: مؤشرات الأداء
            
        Returns:
            معرف السجل
        """
        with self.tx():
            cursor = self.conn.execute("""
                INSERT INTO model_performance
                (model_version, accuracy, precision, recall, f1_score,
                 test_samples, training_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                performance.model_version,
                performance.accuracy,
                performance.precision,
                performance.recall,
                performance.f1_score,
                performance.test_samples,
                performance.training_date or datetime.now(),
                performance.notes,
            ))
            
            perf_id = cursor.lastrowid
            logger.info(f"✓ تم حفظ مؤشرات الأداء: {perf_id}, دقة {performance.accuracy:.1%}")
            return perf_id
    
    def get_latest_performance(self) -> Optional[ModelPerformance]:
        """الحصول على آخر مؤشرات أداء"""
        cursor = self.conn.execute("""
            SELECT * FROM model_performance
            ORDER BY training_date DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return self._row_to_performance(row)
    
    def get_performance_history(self, days: int = 90) -> List[ModelPerformance]:
        """الحصول على تاريخ الأداء"""
        cursor = self.conn.execute("""
            SELECT * FROM model_performance
            WHERE training_date >= datetime('now', '-' || ? || ' days')
            ORDER BY training_date DESC
        """, (days,))
        
        rows = cursor.fetchall()
        return [self._row_to_performance(row) for row in rows]
    
    # ==================== إحصائيات ====================
    
    def get_stats(self) -> Dict:
        """الحصول على إحصائيات عامة
        
        Returns:
            قاموس الإحصائيات
        """
        stats = {}
        
        # إحصائيات الصور
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN validated = 1 THEN 1 END) as validated,
                AVG(quality_score) as avg_quality,
                AVG(confidence) as avg_confidence
            FROM training_images
        """)
        row = cursor.fetchone()
        stats['images'] = {
            'total': row[0],
            'validated': row[1],
            'avg_quality': row[2] or 0.0,
            'avg_confidence': row[3] or 0.0,
        }
        
        # إحصائيات قائمة التأكيد
        cursor = self.conn.execute("""
            SELECT status, COUNT(*) as count
            FROM confirmation_queue
            GROUP BY status
        """)
        stats['queue'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # إحصائيات التصحيحات
        cursor = self.conn.execute("SELECT COUNT(*) FROM human_corrections")
        stats['corrections'] = cursor.fetchone()[0]
        
        # آخر أداء
        latest_perf = self.get_latest_performance()
        if latest_perf:
            stats['latest_performance'] = latest_perf.to_dict()
        
        return stats
    
    # ==================== دوال مساعدة ====================
    
    def _row_to_training_image(self, row: sqlite3.Row) -> TrainingImage:
        """تحويل سطر إلى TrainingImage"""
        quality_details = None
        if row['quality_details']:
            quality_data = json.loads(row['quality_details'])
            quality_details = QualityMetrics.from_dict(quality_data)
        
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return TrainingImage(
            id=row['id'],
            employee_id=row['employee_id'],
            image_path=row['image_path'],
            capture_timestamp=datetime.fromisoformat(row['capture_timestamp']) if row['capture_timestamp'] else None,
            confidence=row['confidence'],
            quality_score=row['quality_score'],
            quality_details=quality_details,
            metadata=metadata,
            validated=bool(row['validated']),
            used_in_training=bool(row['used_in_training']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        )
    
    def _row_to_correction(self, row: sqlite3.Row) -> HumanCorrection:
        """تحويل سطر إلى HumanCorrection"""
        return HumanCorrection(
            id=row['id'],
            image_id=row['image_id'],
            original_prediction=row['original_prediction'],
            corrected_to=row['corrected_to'],
            confidence=row['confidence'],
            corrected_by=row['corrected_by'],
            correction_reason=row['correction_reason'],
            corrected_at=datetime.fromisoformat(row['corrected_at']) if row['corrected_at'] else None,
        )
    
    def _row_to_confirmation_queue(self, row: sqlite3.Row) -> ConfirmationQueue:
        """تحويل سطر إلى ConfirmationQueue"""
        top_predictions = json.loads(row['top_predictions']) if row['top_predictions'] else []
        
        return ConfirmationQueue(
            id=row['id'],
            image_id=row['image_id'],
            status=row['status'],
            priority=row['priority'],
            top_predictions=top_predictions,
            assigned_to=row['assigned_to'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            processed_at=datetime.fromisoformat(row['processed_at']) if row['processed_at'] else None,
        )
    
    def _row_to_performance(self, row: sqlite3.Row) -> ModelPerformance:
        """تحويل سطر إلى ModelPerformance"""
        return ModelPerformance(
            id=row['id'],
            model_version=row['model_version'],
            accuracy=row['accuracy'],
            precision=row['precision'],
            recall=row['recall'],
            f1_score=row['f1_score'],
            test_samples=row['test_samples'],
            training_date=datetime.fromisoformat(row['training_date']) if row['training_date'] else None,
            notes=row['notes'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
        )
    
    def close(self) -> None:
        """إغلاق الاتصال"""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("✓ تم إغلاق اتصال قاعدة البيانات")
