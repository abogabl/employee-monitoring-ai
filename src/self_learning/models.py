"""
نماذج البيانات لنظام التعلم الذاتي
Data models for Self-Learning System
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class QualityMetrics:
    """مقاييس جودة الصورة"""
    
    sharpness: float  # 0.0 - 100+
    brightness: float  # 0 - 255
    face_size: int  # pixels
    face_angle: float  # degrees
    overall_score: float  # 0.0 - 1.0
    
    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'sharpness': self.sharpness,
            'brightness': self.brightness,
            'face_size': self.face_size,
            'face_angle': self.face_angle,
            'overall_score': self.overall_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> QualityMetrics:
        """إنشاء من قاموس"""
        return cls(
            sharpness=data['sharpness'],
            brightness=data['brightness'],
            face_size=data['face_size'],
            face_angle=data['face_angle'],
            overall_score=data['overall_score'],
        )


@dataclass
class TrainingImage:
    """صورة تدريبية"""
    
    id: Optional[int] = None
    employee_id: str = ""
    image_path: str = ""
    capture_timestamp: Optional[datetime] = None
    confidence: float = 0.0
    quality_score: float = 0.0
    quality_details: Optional[QualityMetrics] = None
    metadata: Dict = field(default_factory=dict)
    validated: bool = False
    used_in_training: bool = False
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'image_path': self.image_path,
            'capture_timestamp': self.capture_timestamp.isoformat() if self.capture_timestamp else None,
            'confidence': self.confidence,
            'quality_score': self.quality_score,
            'quality_details': self.quality_details.to_dict() if self.quality_details else None,
            'metadata': self.metadata,
            'validated': self.validated,
            'used_in_training': self.used_in_training,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class HumanCorrection:
    """تصحيح بشري"""
    
    id: Optional[int] = None
    image_id: int = 0
    original_prediction: str = ""
    corrected_to: str = ""
    confidence: float = 0.0
    corrected_by: str = ""
    correction_reason: str = ""
    corrected_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'image_id': self.image_id,
            'original_prediction': self.original_prediction,
            'corrected_to': self.corrected_to,
            'confidence': self.confidence,
            'corrected_by': self.corrected_by,
            'correction_reason': self.correction_reason,
            'corrected_at': self.corrected_at.isoformat() if self.corrected_at else None,
        }


@dataclass
class ConfirmationQueue:
    """حالة في قائمة التأكيد"""
    
    id: Optional[int] = None
    image_id: int = 0
    status: str = "pending"  # pending, confirmed, rejected
    priority: int = 5  # 1 (highest) - 10 (lowest)
    top_predictions: List[Dict] = field(default_factory=list)
    assigned_to: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'image_id': self.image_id,
            'status': self.status,
            'priority': self.priority,
            'top_predictions': self.top_predictions,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }


@dataclass
class ModelPerformance:
    """أداء النموذج"""
    
    id: Optional[int] = None
    model_version: str = ""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    test_samples: int = 0
    training_date: Optional[datetime] = None
    notes: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'model_version': self.model_version,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'test_samples': self.test_samples,
            'training_date': self.training_date.isoformat() if self.training_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
