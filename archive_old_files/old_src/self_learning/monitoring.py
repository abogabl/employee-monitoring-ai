"""
نظام مراقبة التعلم الذاتي
Monitoring System for Self-Learning
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from .database import SelfLearningDB

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """مستوى التنبيه"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """تنبيه"""
    
    def __init__(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        timestamp: Optional[datetime] = None
    ):
        self.level = level
        self.title = title
        self.message = message
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
        }


class SystemMonitor:
    """مراقب النظام"""
    
    def __init__(self, db: Optional[SelfLearningDB] = None):
        """تهيئة المراقب
        
        Args:
            db: قاعدة البيانات
        """
        self.db = db or SelfLearningDB()
        self.alerts: List[Alert] = []
        
        logger.info("✓ تم تهيئة مراقب النظام")
    
    def check_data_collection(self) -> List[Alert]:
        """فحص جمع البيانات
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        # 1. معدل الجمع اليومي
        today_stats = self.db.get_stats()
        total_images = today_stats['images']['total']
        
        cursor = self.db.conn.execute("""
            SELECT COUNT(*) FROM training_images
            WHERE date(capture_timestamp) = date('now')
        """)
        today_count = cursor.fetchone()[0]
        
        if today_count == 0:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "لا توجد صور اليوم",
                "لم يتم جمع أي صورة تدريبية اليوم"
            ))
        elif today_count < 10:
            alerts.append(Alert(
                AlertLevel.INFO,
                "جمع بطيء",
                f"تم جمع {today_count} صورة فقط اليوم"
            ))
        
        # 2. التوزيع بين الموظفين
        cursor = self.db.conn.execute("""
            SELECT employee_id, COUNT(*) as count
            FROM training_images
            GROUP BY employee_id
            HAVING count < 5
        """)
        low_count_employees = cursor.fetchall()
        
        if len(low_count_employees) > 0:
            alerts.append(Alert(
                AlertLevel.INFO,
                "موظفون بصور قليلة",
                f"{len(low_count_employees)} موظف لديهم أقل من 5 صور"
            ))
        
        return alerts
    
    def check_queue_status(self) -> List[Alert]:
        """فحص قائمة التأكيد
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        # عدد الحالات المعلقة
        pending_count = self.db.get_pending_count()
        
        if pending_count > 100:
            alerts.append(Alert(
                AlertLevel.ERROR,
                "قائمة مزدحمة",
                f"{pending_count} حالة معلقة - تحتاج مراجعة عاجلة"
            ))
        elif pending_count > 50:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "قائمة ممتلئة",
                f"{pending_count} حالة معلقة"
            ))
        
        # الحالات القديمة جداً
        cursor = self.db.conn.execute("""
            SELECT COUNT(*) FROM confirmation_queue
            WHERE status = 'pending'
            AND created_at < datetime('now', '-7 days')
        """)
        old_pending = cursor.fetchone()[0]
        
        if old_pending > 0:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "حالات قديمة",
                f"{old_pending} حالة معلقة منذ أكثر من 7 أيام"
            ))
        
        return alerts
    
    def check_quality(self) -> List[Alert]:
        """فحص جودة البيانات
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        stats = self.db.get_stats()
        avg_quality = stats['images'].get('avg_quality', 0)
        
        # جودة منخفضة
        if avg_quality < 0.60:
            alerts.append(Alert(
                AlertLevel.ERROR,
                "جودة منخفضة جداً",
                f"متوسط الجودة {avg_quality:.1%} - راجع الإعدادات"
            ))
        elif avg_quality < 0.75:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "جودة متوسطة",
                f"متوسط الجودة {avg_quality:.1%}"
            ))
        
        # صور مرفوضة كثيرة
        cursor = self.db.conn.execute("""
            SELECT COUNT(*) FROM confirmation_queue
            WHERE status = 'rejected'
            AND created_at >= datetime('now', '-7 days')
        """)
        recent_rejected = cursor.fetchone()[0]
        
        cursor = self.db.conn.execute("""
            SELECT COUNT(*) FROM confirmation_queue
            WHERE created_at >= datetime('now', '-7 days')
        """)
        recent_total = cursor.fetchone()[0]
        
        if recent_total > 0:
            reject_rate = recent_rejected / recent_total
            if reject_rate > 0.30:
                alerts.append(Alert(
                    AlertLevel.WARNING,
                    "نسبة رفض عالية",
                    f"{reject_rate:.1%} من الصور تم رفضها هذا الأسبوع"
                ))
        
        return alerts
    
    def check_model_performance(self) -> List[Alert]:
        """فحص أداء النموذج
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        latest = self.db.get_latest_performance()
        
        if not latest:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "لا توجد بيانات أداء",
                "لم يتم تسجيل أي مؤشرات أداء للنموذج"
            ))
            return alerts
        
        # دقة منخفضة
        if latest.accuracy < 0.80:
            alerts.append(Alert(
                AlertLevel.CRITICAL,
                "دقة منخفضة جداً",
                f"دقة النموذج {latest.accuracy:.1%} - يحتاج إعادة تدريب"
            ))
        elif latest.accuracy < 0.90:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "دقة متوسطة",
                f"دقة النموذج {latest.accuracy:.1%}"
            ))
        
        # وقت طويل بدون تدريب
        if latest.training_date:
            days_since = (datetime.now() - latest.training_date).days
            
            if days_since > 30:
                alerts.append(Alert(
                    AlertLevel.WARNING,
                    "تدريب قديم",
                    f"آخر تدريب كان منذ {days_since} يوم"
                ))
        
        # اتجاه سلبي
        history = self.db.get_performance_history(days=60)
        if len(history) >= 2:
            recent = history[0].accuracy
            older = history[-1].accuracy
            
            if recent < older - 0.05:  # انخفاض 5%
                alerts.append(Alert(
                    AlertLevel.ERROR,
                    "تراجع في الأداء",
                    f"الدقة انخفضت من {older:.1%} إلى {recent:.1%}"
                ))
        
        return alerts
    
    def check_corrections(self) -> List[Alert]:
        """فحص التصحيحات البشرية
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        # التصحيحات الحديثة
        recent = self.db.get_recent_corrections(days=7)
        
        if len(recent) > 20:
            alerts.append(Alert(
                AlertLevel.WARNING,
                "تصحيحات كثيرة",
                f"{len(recent)} تصحيح بشري هذا الأسبوع - قد يدل على مشكلة"
            ))
        
        # نمط متكرر في الأخطاء
        error_patterns = {}
        for correction in recent:
            pattern = f"{correction.original_prediction} → {correction.corrected_to}"
            error_patterns[pattern] = error_patterns.get(pattern, 0) + 1
        
        for pattern, count in error_patterns.items():
            if count >= 3:
                alerts.append(Alert(
                    AlertLevel.INFO,
                    "نمط خطأ متكرر",
                    f"الخطأ '{pattern}' تكرر {count} مرات"
                ))
        
        return alerts
    
    def check_storage(self) -> List[Alert]:
        """فحص التخزين
        
        Returns:
            قائمة التنبيهات
        """
        alerts = []
        
        try:
            from .storage import ImageStorage
            storage = ImageStorage()
            
            stats = storage.get_storage_stats()
            size_mb = stats.get('storage_size_mb', 0)
            
            # حجم كبير
            if size_mb > 1000:  # 1 GB
                alerts.append(Alert(
                    AlertLevel.WARNING,
                    "مساحة كبيرة",
                    f"التخزين يستهلك {size_mb:.1f} MB"
                ))
            
        except Exception as e:
            logger.warning(f"تعذر فحص التخزين: {e}")
        
        return alerts
    
    def run_full_check(self) -> List[Alert]:
        """تشغيل فحص شامل
        
        Returns:
            كل التنبيهات
        """
        logger.info("🔍 بدء الفحص الشامل...")
        
        all_alerts = []
        
        # تشغيل كل الفحوصات
        all_alerts.extend(self.check_data_collection())
        all_alerts.extend(self.check_queue_status())
        all_alerts.extend(self.check_quality())
        all_alerts.extend(self.check_model_performance())
        all_alerts.extend(self.check_corrections())
        all_alerts.extend(self.check_storage())
        
        # ترتيب حسب المستوى
        priority_order = {
            AlertLevel.CRITICAL: 0,
            AlertLevel.ERROR: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.INFO: 3,
        }
        
        all_alerts.sort(key=lambda a: priority_order[a.level])
        
        # حفظ في الذاكرة
        self.alerts = all_alerts
        
        logger.info(f"✓ اكتمل الفحص: {len(all_alerts)} تنبيه")
        
        return all_alerts
    
    def get_health_score(self) -> float:
        """حساب درجة صحة النظام
        
        Returns:
            درجة من 0 إلى 100
        """
        alerts = self.run_full_check()
        
        # البدء من 100
        score = 100.0
        
        # خصم نقاط حسب المستوى
        for alert in alerts:
            if alert.level == AlertLevel.CRITICAL:
                score -= 20
            elif alert.level == AlertLevel.ERROR:
                score -= 10
            elif alert.level == AlertLevel.WARNING:
                score -= 5
            elif alert.level == AlertLevel.INFO:
                score -= 2
        
        return max(0.0, min(100.0, score))
    
    def get_monitoring_dashboard_data(self) -> Dict:
        """بيانات لوحة المراقبة
        
        Returns:
            قاموس البيانات
        """
        # تشغيل الفحص
        alerts = self.run_full_check()
        
        # إحصائيات عامة
        stats = self.db.get_stats()
        
        # صحة النظام
        health_score = self.get_health_score()
        
        # حالة الصحة
        if health_score >= 90:
            health_status = "ممتاز"
            health_color = "green"
        elif health_score >= 75:
            health_status = "جيد"
            health_color = "blue"
        elif health_score >= 60:
            health_status = "متوسط"
            health_color = "yellow"
        else:
            health_status = "يحتاج انتباه"
            health_color = "red"
        
        # تصنيف التنبيهات
        alerts_by_level = {
            'critical': [a for a in alerts if a.level == AlertLevel.CRITICAL],
            'error': [a for a in alerts if a.level == AlertLevel.ERROR],
            'warning': [a for a in alerts if a.level == AlertLevel.WARNING],
            'info': [a for a in alerts if a.level == AlertLevel.INFO],
        }
        
        dashboard_data = {
            'health_score': round(health_score, 1),
            'health_status': health_status,
            'health_color': health_color,
            'total_alerts': len(alerts),
            'alerts_by_level': {
                'critical': len(alerts_by_level['critical']),
                'error': len(alerts_by_level['error']),
                'warning': len(alerts_by_level['warning']),
                'info': len(alerts_by_level['info']),
            },
            'alerts': [a.to_dict() for a in alerts],
            'stats': stats,
            'timestamp': datetime.now().isoformat(),
        }
        
        return dashboard_data
