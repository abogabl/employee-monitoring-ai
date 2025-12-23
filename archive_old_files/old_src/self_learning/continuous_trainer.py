"""
نظام التدريب المستمر
Continuous Training System
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .database import SelfLearningDB
from .models import ModelPerformance

logger = logging.getLogger(__name__)


class ContinuousTrainer:
    """نظام التدريب المستمر التلقائي"""
    
    def __init__(
        self,
        db: Optional[SelfLearningDB] = None,
        min_new_images: int = 50,
        min_corrections: int = 10,
        auto_retrain: bool = True,
        training_interval_hours: int = 24
    ):
        """تهيئة نظام التدريب
        
        Args:
            db: قاعدة البيانات
            min_new_images: الحد الأدنى للصور الجديدة لبدء التدريب
            min_corrections: الحد الأدنى للتصحيحات لبدء التدريب
            auto_retrain: التدريب التلقائي
            training_interval_hours: الفاصل الزمني للتدريب (ساعات)
        """
        self.db = db or SelfLearningDB()
        self.min_new_images = min_new_images
        self.min_corrections = min_corrections
        self.auto_retrain = auto_retrain
        self.training_interval_hours = training_interval_hours
        
        self.last_training_time: Optional[datetime] = None
        
        logger.info("✓ تم تهيئة نظام التدريب المستمر")
    
    def should_retrain(self) -> tuple[bool, str]:
        """هل يجب إعادة التدريب؟
        
        Returns:
            (should_retrain, reason)
        """
        # 1. التحقق من الفاصل الزمني
        latest_perf = self.db.get_latest_performance()
        if latest_perf and latest_perf.training_date:
            last_training = latest_perf.training_date
            hours_since = (datetime.now() - last_training).total_seconds() / 3600
            
            if hours_since < self.training_interval_hours:
                return False, f"آخر تدريب منذ {hours_since:.1f} ساعة فقط"
        
        # 2. التحقق من الصور الجديدة
        stats = self.db.get_stats()
        total_images = stats['images']['total']
        validated_images = stats['images']['validated']
        
        # الصور الجديدة = غير المستخدمة في التدريب
        cursor = self.db.conn.execute(
            "SELECT COUNT(*) FROM training_images WHERE used_in_training = 0 AND validated = 1"
        )
        new_images_count = cursor.fetchone()[0]
        
        if new_images_count >= self.min_new_images:
            return True, f"يوجد {new_images_count} صورة جديدة مؤكدة"
        
        # 3. التحقق من التصحيحات
        recent_corrections = self.db.get_recent_corrections(days=30)
        if len(recent_corrections) >= self.min_corrections:
            return True, f"يوجد {len(recent_corrections)} تصحيح بشري"
        
        # 4. التحقق من الأداء المنخفض
        if latest_perf and latest_perf.accuracy < 0.85:
            return True, f"الدقة منخفضة ({latest_perf.accuracy:.1%})"
        
        return False, "لا يوجد سبب لإعادة التدريب حالياً"
    
    def prepare_training_data(self) -> Dict:
        """إعداد بيانات التدريب
        
        Returns:
            قاموس معلومات البيانات
        """
        # جلب كل الصور المؤكدة
        cursor = self.db.conn.execute("""
            SELECT employee_id, image_path, confidence, quality_score
            FROM training_images
            WHERE validated = 1
            ORDER BY capture_timestamp DESC
        """)
        
        rows = cursor.fetchall()
        
        # تنظيم حسب الموظف
        employee_images: Dict[str, List] = {}
        for row in rows:
            emp_id = row[0]
            if emp_id not in employee_images:
                employee_images[emp_id] = []
            
            employee_images[emp_id].append({
                'path': row[1],
                'confidence': row[2],
                'quality': row[3]
            })
        
        # إحصائيات
        total_images = sum(len(imgs) for imgs in employee_images.values())
        total_employees = len(employee_images)
        
        avg_images_per_emp = total_images / total_employees if total_employees > 0 else 0
        
        info = {
            'total_images': total_images,
            'total_employees': total_employees,
            'avg_images_per_employee': round(avg_images_per_emp, 1),
            'employee_images': employee_images,
            'min_images': min(len(imgs) for imgs in employee_images.values()) if employee_images else 0,
            'max_images': max(len(imgs) for imgs in employee_images.values()) if employee_images else 0,
        }
        
        logger.info(f"✓ تم إعداد البيانات: {total_images} صورة لـ {total_employees} موظف")
        
        return info
    
    def simulate_training(self, training_data: Dict) -> ModelPerformance:
        """محاكاة التدريب (سيتم استبداله بالتدريب الفعلي)
        
        Args:
            training_data: بيانات التدريب
            
        Returns:
            مؤشرات الأداء
        """
        logger.info("🔄 بدء محاكاة التدريب...")
        
        total_images = training_data['total_images']
        total_employees = training_data['total_employees']
        
        # محاكاة: تحسين بسيط بناءً على عدد البيانات
        base_accuracy = 0.85
        data_bonus = min(0.10, (total_images / 1000) * 0.05)
        employee_bonus = min(0.03, (total_employees / 50) * 0.02)
        
        accuracy = min(0.98, base_accuracy + data_bonus + employee_bonus)
        precision = accuracy - 0.02
        recall = accuracy - 0.01
        f1_score = 2 * (precision * recall) / (precision + recall)
        
        # إضافة بعض العشوائية
        accuracy += np.random.uniform(-0.02, 0.02)
        precision += np.random.uniform(-0.02, 0.02)
        recall += np.random.uniform(-0.02, 0.02)
        f1_score = 2 * (precision * recall) / (precision + recall)
        
        # إنشاء إصدار جديد
        latest = self.db.get_latest_performance()
        if latest and latest.model_version:
            # استخراج الرقم من v1.2.3
            parts = latest.model_version.replace('v', '').split('.')
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            new_version = f"v{major}.{minor}.{patch + 1}"
        else:
            new_version = "v1.0.0"
        
        performance = ModelPerformance(
            model_version=new_version,
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1_score, 4),
            test_samples=total_images,
            training_date=datetime.now(),
            notes=f"تدريب تلقائي - {total_images} صورة، {total_employees} موظف"
        )
        
        logger.info(f"✓ اكتمل التدريب: {new_version} - دقة {accuracy:.1%}")
        
        return performance
    
    def train(self, force: bool = False) -> Optional[ModelPerformance]:
        """تدريب النموذج
        
        Args:
            force: إجبار التدريب حتى لو لم تتحقق الشروط
            
        Returns:
            مؤشرات الأداء أو None
        """
        # التحقق من الحاجة للتدريب
        should_train, reason = self.should_retrain()
        
        if not force and not should_train:
            logger.info(f"⏸️  تخطي التدريب: {reason}")
            return None
        
        logger.info(f"🚀 بدء التدريب: {reason}")
        
        try:
            # 1. إعداد البيانات
            training_data = self.prepare_training_data()
            
            if training_data['total_images'] < 10:
                logger.warning("⚠️ بيانات غير كافية للتدريب")
                return None
            
            # 2. التدريب (محاكاة حالياً)
            performance = self.simulate_training(training_data)
            
            # 3. حفظ مؤشرات الأداء
            perf_id = self.db.insert_performance(performance)
            logger.info(f"✓ تم حفظ مؤشرات الأداء: #{perf_id}")
            
            # 4. تعليم الصور كمستخدمة
            cursor = self.db.conn.execute(
                "SELECT id FROM training_images WHERE validated = 1 AND used_in_training = 0"
            )
            new_image_ids = [row[0] for row in cursor.fetchall()]
            
            if new_image_ids:
                self.db.mark_as_used_in_training(new_image_ids)
                logger.info(f"✓ تم تعليم {len(new_image_ids)} صورة كمستخدمة")
            
            # 5. تحديث وقت التدريب
            self.last_training_time = datetime.now()
            
            logger.info("✅ اكتمل التدريب بنجاح!")
            
            return performance
            
        except Exception as e:
            logger.error(f"❌ خطأ في التدريب: {e}")
            return None
    
    def get_training_stats(self) -> Dict:
        """الحصول على إحصائيات التدريب
        
        Returns:
            قاموس الإحصائيات
        """
        # آخر تدريب
        latest = self.db.get_latest_performance()
        
        # تاريخ التدريبات
        history = self.db.get_performance_history(days=90)
        
        # الصور غير المستخدمة
        cursor = self.db.conn.execute(
            "SELECT COUNT(*) FROM training_images WHERE validated = 1 AND used_in_training = 0"
        )
        unused_images = cursor.fetchone()[0]
        
        # التصحيحات الحديثة
        recent_corrections = self.db.get_recent_corrections(days=30)
        
        # الحاجة للتدريب
        should_train, reason = self.should_retrain()
        
        stats = {
            'latest_performance': latest.to_dict() if latest else None,
            'total_trainings': len(history),
            'unused_images': unused_images,
            'recent_corrections': len(recent_corrections),
            'should_retrain': should_train,
            'retrain_reason': reason,
            'last_training_date': latest.training_date.isoformat() if latest and latest.training_date else None,
        }
        
        # اتجاه التحسن
        if len(history) >= 2:
            recent_accuracy = history[0].accuracy
            older_accuracy = history[-1].accuracy
            improvement = recent_accuracy - older_accuracy
            stats['accuracy_trend'] = 'improving' if improvement > 0 else 'declining'
            stats['improvement_rate'] = round(improvement * 100, 2)
        
        return stats


class TrainingScheduler:
    """جدولة التدريب التلقائي"""
    
    def __init__(
        self,
        trainer: Optional[ContinuousTrainer] = None,
        schedule_hours: List[int] = None
    ):
        """تهيئة الجدولة
        
        Args:
            trainer: نظام التدريب
            schedule_hours: ساعات التدريب (0-23)
        """
        self.trainer = trainer or ContinuousTrainer()
        self.schedule_hours = schedule_hours or [2, 14]  # 2 صباحاً، 2 ظهراً
        
        self.last_check_date: Optional[datetime] = None
        
        logger.info(f"✓ تم تهيئة جدولة التدريب: {self.schedule_hours}")
    
    def should_run_now(self) -> bool:
        """هل يجب التشغيل الآن؟
        
        Returns:
            True إذا كان الوقت مناسب
        """
        now = datetime.now()
        current_hour = now.hour
        
        # التحقق من الساعة
        if current_hour not in self.schedule_hours:
            return False
        
        # التحقق من عدم التشغيل اليوم
        if self.last_check_date:
            if self.last_check_date.date() == now.date():
                if self.last_check_date.hour == current_hour:
                    return False
        
        return True
    
    def check_and_train(self) -> Optional[ModelPerformance]:
        """التحقق والتدريب إذا لزم الأمر
        
        Returns:
            مؤشرات الأداء أو None
        """
        if not self.should_run_now():
            return None
        
        logger.info("⏰ حان وقت التدريب المجدول")
        
        # التدريب
        performance = self.trainer.train()
        
        # تحديث آخر فحص
        self.last_check_date = datetime.now()
        
        return performance
