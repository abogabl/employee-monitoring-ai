"""
نظام التعلم الذاتي لتحسين دقة التعرف على الموظفين
Self-Learning System for Face Recognition Improvement

المكونات:
- database: قاعدة بيانات التعلم الذاتي
- storage: نظام تخزين الصور
- quality_assessor: تقييم جودة الصور
- data_collector: جمع البيانات التلقائي
- active_learner: التعلم النشط
- continuous_trainer: التدريب المستمر
"""

__version__ = "0.2.0"
__author__ = "AI Assistant"

from .database import SelfLearningDB
from .models import (
    TrainingImage,
    HumanCorrection,
    ConfirmationQueue,
    ModelPerformance,
    QualityMetrics,
)
from .storage import ImageStorage
from .quality_assessor import QualityAssessor
from .data_collector import DataCollector, CollectionPolicy
from .continuous_trainer import ContinuousTrainer, TrainingScheduler
from .monitoring import SystemMonitor, Alert, AlertLevel

__all__ = [
    "SelfLearningDB",
    "TrainingImage",
    "HumanCorrection",
    "ConfirmationQueue",
    "ModelPerformance",
    "QualityMetrics",
    "ImageStorage",
    "QualityAssessor",
    "DataCollector",
    "CollectionPolicy",
    "ContinuousTrainer",
    "TrainingScheduler",
    "SystemMonitor",
    "Alert",
    "AlertLevel",
]
