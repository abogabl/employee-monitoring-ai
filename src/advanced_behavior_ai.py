"""
Advanced Behavior AI - Level 2 Enhancement
ذكاء اصطناعي متقدم لتحليل السلوك والأنماط

الميزات:
- تحليل السلوك المعقد
- كشف الأنماط غير الطبيعية
- تعلم تلقائي من البيانات
- تنبؤات ذكية
- تحليل الاتجاهات
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, deque
import json
from pathlib import Path
import pickle

# مكتبات التعلم الآلي
try:
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("مكتبات التعلم الآلي غير متوفرة. سيتم استخدام التحليل الأساسي فقط.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("advanced_behavior_ai")


class BehaviorPattern:
    """نمط سلوكي"""
    
    def __init__(self, pattern_id: str, name: str, description: str):
        self.pattern_id = pattern_id
        self.name = name
        self.description = description
        self.occurrences = []
        self.confidence = 0.0
        self.last_detected = None
        self.frequency = 0.0
    
    def add_occurrence(self, timestamp: datetime, person_id: str, 
                      context: Dict[str, Any]):
        """إضافة حدوث للنمط"""
        self.occurrences.append({
            'timestamp': timestamp,
            'person_id': person_id,
            'context': context
        })
        self.last_detected = timestamp
        self.frequency = len(self.occurrences)
    
    def calculate_confidence(self) -> float:
        """حساب مستوى الثقة في النمط"""
        if len(self.occurrences) < 2:
            return 0.0
        
        # حساب الثقة بناءً على التكرار والاتساق
        recent_occurrences = [
            occ for occ in self.occurrences 
            if (datetime.now() - occ['timestamp']).days <= 7
        ]
        
        if len(recent_occurrences) >= 3:
            self.confidence = min(0.9, len(recent_occurrences) * 0.2)
        else:
            self.confidence = len(recent_occurrences) * 0.1
        
        return self.confidence


class AnomalyDetector:
    """كاشف الشذوذ في السلوك"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_history = deque(maxlen=1000)
        
        if ML_AVAILABLE:
            self.model = IsolationForest(
                contamination=0.1,  # نسبة الشذوذ المتوقعة
                random_state=42,
                n_estimators=100
            )
    
    def extract_features(self, person_data: Dict[str, Any]) -> np.ndarray:
        """استخراج الميزات من بيانات الشخص"""
        features = []
        
        # ميزات النشاط
        activities = person_data.get('activities', {})
        total_time = sum(activities.values()) or 1
        
        features.extend([
            activities.get('working', 0) / total_time,
            activities.get('sleeping', 0) / total_time,
            activities.get('idle', 0) / total_time,
            activities.get('on_phone', 0) / total_time,
        ])
        
        # ميزات الحركة
        features.extend([
            person_data.get('avg_motion', 0),
            person_data.get('motion_variance', 0),
            person_data.get('position_changes', 0),
        ])
        
        # ميزات زمنية
        current_hour = datetime.now().hour
        features.extend([
            current_hour / 24.0,  # وقت اليوم
            person_data.get('duration', 0) / 3600.0,  # المدة بالساعات
            person_data.get('detection_count', 0) / 100.0,  # عدد الاكتشافات
        ])
        
        # ميزات الموقع
        features.extend([
            person_data.get('avg_x_position', 0.5),
            person_data.get('avg_y_position', 0.5),
            person_data.get('position_stability', 0.5),
        ])
        
        return np.array(features)
    
    def update_model(self, person_data_list: List[Dict[str, Any]]):
        """تحديث نموذج كشف الشذوذ"""
        if not ML_AVAILABLE or len(person_data_list) < 10:
            return
        
        # استخراج الميزات
        features_list = []
        for person_data in person_data_list:
            features = self.extract_features(person_data)
            features_list.append(features)
            self.feature_history.append(features)
        
        if len(features_list) < 5:
            return
        
        try:
            X = np.array(features_list)
            
            # تطبيع البيانات
            X_scaled = self.scaler.fit_transform(X)
            
            # تدريب النموذج
            self.model.fit(X_scaled)
            self.is_trained = True
            
            logger.info(f"تم تحديث نموذج كشف الشذوذ بـ {len(features_list)} عينة")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث نموذج كشف الشذوذ: {e}")
    
    def detect_anomaly(self, person_data: Dict[str, Any]) -> Tuple[bool, float]:
        """كشف الشذوذ في سلوك شخص"""
        if not ML_AVAILABLE or not self.is_trained:
            return False, 0.0
        
        try:
            features = self.extract_features(person_data)
            features_scaled = self.scaler.transform([features])
            
            # التنبؤ
            anomaly_score = self.model.decision_function(features_scaled)[0]
            is_anomaly = self.model.predict(features_scaled)[0] == -1
            
            # تحويل النتيجة إلى احتمالية
            confidence = abs(anomaly_score)
            
            return is_anomaly, confidence
            
        except Exception as e:
            logger.error(f"خطأ في كشف الشذوذ: {e}")
            return False, 0.0


class BehaviorPredictor:
    """متنبئ السلوك"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.behavior_history = defaultdict(list)
        
        if ML_AVAILABLE:
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
    
    def add_behavior_data(self, person_id: str, timestamp: datetime,
                         activity: str, context: Dict[str, Any]):
        """إضافة بيانات سلوكية للتاريخ"""
        self.behavior_history[person_id].append({
            'timestamp': timestamp,
            'activity': activity,
            'context': context,
            'hour': timestamp.hour,
            'day_of_week': timestamp.weekday(),
            'features': self._extract_context_features(context)
        })
        
        # الاحتفاظ بآخر 100 سجل لكل شخص
        if len(self.behavior_history[person_id]) > 100:
            self.behavior_history[person_id] = self.behavior_history[person_id][-100:]
    
    def _extract_context_features(self, context: Dict[str, Any]) -> List[float]:
        """استخراج ميزات من السياق"""
        return [
            context.get('motion_level', 0),
            context.get('position_x', 0.5),
            context.get('position_y', 0.5),
            context.get('confidence', 0.5),
            context.get('face_detected', 0),
        ]
    
    def train_model(self):
        """تدريب نموذج التنبؤ"""
        if not ML_AVAILABLE:
            return False
        
        # جمع البيانات التدريبية
        X, y = [], []
        
        for person_id, history in self.behavior_history.items():
            if len(history) < 10:
                continue
            
            for i in range(len(history) - 1):
                current = history[i]
                next_activity = history[i + 1]['activity']
                
                # ميزات الإدخال
                features = [
                    current['hour'] / 24.0,
                    current['day_of_week'] / 7.0,
                ] + current['features']
                
                X.append(features)
                y.append(next_activity)
        
        if len(X) < 20:
            logger.warning("بيانات غير كافية لتدريب نموذج التنبؤ")
            return False
        
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            self.model.fit(X_train, y_train)
            self.is_trained = True
            
            # تقييم النموذج
            y_pred = self.model.predict(X_test)
            report = classification_report(y_test, y_pred, output_dict=True)
            
            logger.info(f"تم تدريب نموذج التنبؤ بدقة: {report['accuracy']:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تدريب نموذج التنبؤ: {e}")
            return False
    
    def predict_next_activity(self, person_id: str, 
                            current_context: Dict[str, Any]) -> Tuple[str, float]:
        """التنبؤ بالنشاط التالي"""
        if not ML_AVAILABLE or not self.is_trained:
            return "unknown", 0.0
        
        if person_id not in self.behavior_history:
            return "unknown", 0.0
        
        try:
            now = datetime.now()
            features = [
                now.hour / 24.0,
                now.weekday() / 7.0,
            ] + self._extract_context_features(current_context)
            
            # التنبؤ
            prediction = self.model.predict([features])[0]
            probabilities = self.model.predict_proba([features])[0]
            confidence = max(probabilities)
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"خطأ في التنبؤ: {e}")
            return "unknown", 0.0


class AdvancedBehaviorAI:
    """النظام المتقدم لتحليل السلوك"""
    
    def __init__(self, models_dir: str = "models/behavior"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # المكونات الرئيسية
        self.anomaly_detector = AnomalyDetector()
        self.behavior_predictor = BehaviorPredictor()
        self.behavior_patterns = {}
        
        # إحصائيات وتحليلات
        self.person_profiles = defaultdict(dict)
        self.daily_summaries = defaultdict(list)
        self.trend_analysis = {}
        
        # تحميل النماذج المحفوظة
        self.load_models()
        
        logger.info("تم تهيئة النظام المتقدم لتحليل السلوك")
    
    def analyze_person_behavior(self, person_id: str, 
                              person_data: Dict[str, Any]) -> Dict[str, Any]:
        """تحليل شامل لسلوك شخص"""
        analysis = {
            'person_id': person_id,
            'timestamp': datetime.now().isoformat(),
            'anomaly_detected': False,
            'anomaly_confidence': 0.0,
            'predicted_next_activity': 'unknown',
            'prediction_confidence': 0.0,
            'behavior_patterns': [],
            'risk_level': 'low',
            'recommendations': []
        }
        
        try:
            # كشف الشذوذ
            is_anomaly, anomaly_conf = self.anomaly_detector.detect_anomaly(person_data)
            analysis['anomaly_detected'] = is_anomaly
            analysis['anomaly_confidence'] = float(anomaly_conf)
            
            # التنبؤ بالنشاط التالي
            next_activity, pred_conf = self.behavior_predictor.predict_next_activity(
                person_id, person_data
            )
            analysis['predicted_next_activity'] = next_activity
            analysis['prediction_confidence'] = float(pred_conf)
            
            # تحليل الأنماط
            patterns = self._detect_behavior_patterns(person_id, person_data)
            analysis['behavior_patterns'] = patterns
            
            # تقييم مستوى المخاطر
            risk_level = self._assess_risk_level(person_data, is_anomaly, patterns)
            analysis['risk_level'] = risk_level
            
            # توصيات
            recommendations = self._generate_recommendations(
                person_data, is_anomaly, risk_level
            )
            analysis['recommendations'] = recommendations
            
            # تحديث الملف الشخصي
            self._update_person_profile(person_id, person_data, analysis)
            
        except Exception as e:
            logger.error(f"خطأ في تحليل سلوك الشخص {person_id}: {e}")
        
        return analysis
    
    def _detect_behavior_patterns(self, person_id: str, 
                                person_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """كشف أنماط السلوك"""
        patterns = []
        
        # نمط العمل المكثف
        activities = person_data.get('activities', {})
        working_ratio = activities.get('working', 0) / max(sum(activities.values()), 1)
        
        if working_ratio > 0.8:
            patterns.append({
                'pattern': 'intensive_work',
                'name': 'عمل مكثف',
                'confidence': working_ratio,
                'description': 'الشخص يعمل بكثافة عالية'
            })
        
        # نمط الخمول
        idle_ratio = activities.get('idle', 0) / max(sum(activities.values()), 1)
        if idle_ratio > 0.6:
            patterns.append({
                'pattern': 'high_idle',
                'name': 'خمول عالي',
                'confidence': idle_ratio,
                'description': 'الشخص خامل لفترة طويلة'
            })
        
        # نمط النوم المتكرر
        sleeping_ratio = activities.get('sleeping', 0) / max(sum(activities.values()), 1)
        if sleeping_ratio > 0.3:
            patterns.append({
                'pattern': 'frequent_sleeping',
                'name': 'نوم متكرر',
                'confidence': sleeping_ratio,
                'description': 'الشخص ينام بشكل متكرر'
            })
        
        return patterns
    
    def _assess_risk_level(self, person_data: Dict[str, Any], 
                          is_anomaly: bool, patterns: List[Dict]) -> str:
        """تقييم مستوى المخاطر"""
        risk_score = 0
        
        # الشذوذ يزيد المخاطر
        if is_anomaly:
            risk_score += 3
        
        # الأنماط السلبية
        for pattern in patterns:
            if pattern['pattern'] in ['high_idle', 'frequent_sleeping']:
                risk_score += 2
            elif pattern['pattern'] == 'intensive_work':
                risk_score += 1  # قد يكون إيجابي أو سلبي
        
        # مستوى النشاط
        activities = person_data.get('activities', {})
        total_time = sum(activities.values())
        if total_time > 0:
            working_ratio = activities.get('working', 0) / total_time
            if working_ratio < 0.2:  # عمل قليل جداً
                risk_score += 2
        
        # تحديد مستوى المخاطر
        if risk_score >= 5:
            return 'high'
        elif risk_score >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _generate_recommendations(self, person_data: Dict[str, Any],
                                is_anomaly: bool, risk_level: str) -> List[str]:
        """إنشاء توصيات"""
        recommendations = []
        
        if is_anomaly:
            recommendations.append("تم اكتشاف سلوك غير طبيعي - يُنصح بالمراجعة")
        
        activities = person_data.get('activities', {})
        total_time = sum(activities.values()) or 1
        
        # توصيات بناءً على الأنشطة
        working_ratio = activities.get('working', 0) / total_time
        sleeping_ratio = activities.get('sleeping', 0) / total_time
        
        if working_ratio < 0.3:
            recommendations.append("مستوى العمل منخفض - قد يحتاج تحفيز")
        
        if sleeping_ratio > 0.4:
            recommendations.append("نوم مفرط - يُنصح بالتحقق من الحالة الصحية")
        
        if risk_level == 'high':
            recommendations.append("مستوى مخاطر عالي - يتطلب تدخل فوري")
        elif risk_level == 'medium':
            recommendations.append("مستوى مخاطر متوسط - يُنصح بالمتابعة")
        
        return recommendations
    
    def _update_person_profile(self, person_id: str, person_data: Dict[str, Any],
                             analysis: Dict[str, Any]):
        """تحديث الملف الشخصي للشخص"""
        if person_id not in self.person_profiles:
            self.person_profiles[person_id] = {
                'first_seen': datetime.now(),
                'total_sessions': 0,
                'total_working_time': 0,
                'total_idle_time': 0,
                'anomaly_count': 0,
                'risk_history': [],
                'pattern_history': []
            }
        
        profile = self.person_profiles[person_id]
        profile['last_seen'] = datetime.now()
        profile['total_sessions'] += 1
        
        # تحديث الأوقات
        activities = person_data.get('activities', {})
        profile['total_working_time'] += activities.get('working', 0)
        profile['total_idle_time'] += activities.get('idle', 0)
        
        # تحديث إحصائيات الشذوذ
        if analysis['anomaly_detected']:
            profile['anomaly_count'] += 1
        
        # تحديث تاريخ المخاطر
        profile['risk_history'].append({
            'timestamp': datetime.now(),
            'risk_level': analysis['risk_level']
        })
        
        # الاحتفاظ بآخر 50 سجل
        if len(profile['risk_history']) > 50:
            profile['risk_history'] = profile['risk_history'][-50:]
    
    def update_models(self, all_person_data: List[Dict[str, Any]]):
        """تحديث جميع النماذج"""
        try:
            # تحديث كاشف الشذوذ
            self.anomaly_detector.update_model(all_person_data)
            
            # إضافة البيانات لمتنبئ السلوك
            for person_data in all_person_data:
                person_id = person_data.get('person_id', 'unknown')
                if person_id != 'unknown':
                    self.behavior_predictor.add_behavior_data(
                        person_id,
                        datetime.now(),
                        person_data.get('current_activity', 'idle'),
                        person_data
                    )
            
            # تدريب متنبئ السلوك
            self.behavior_predictor.train_model()
            
            # حفظ النماذج
            self.save_models()
            
            logger.info("تم تحديث جميع نماذج الذكاء الاصطناعي")
            
        except Exception as e:
            logger.error(f"خطأ في تحديث النماذج: {e}")
    
    def save_models(self):
        """حفظ النماذج"""
        try:
            if ML_AVAILABLE:
                # حفظ كاشف الشذوذ
                if self.anomaly_detector.is_trained:
                    joblib.dump(
                        self.anomaly_detector.model,
                        self.models_dir / "anomaly_detector.pkl"
                    )
                    joblib.dump(
                        self.anomaly_detector.scaler,
                        self.models_dir / "anomaly_scaler.pkl"
                    )
                
                # حفظ متنبئ السلوك
                if self.behavior_predictor.is_trained:
                    joblib.dump(
                        self.behavior_predictor.model,
                        self.models_dir / "behavior_predictor.pkl"
                    )
            
            # حفظ الملفات الشخصية
            with open(self.models_dir / "person_profiles.json", 'w', encoding='utf-8') as f:
                # تحويل datetime إلى string للتسلسل
                profiles_serializable = {}
                for person_id, profile in self.person_profiles.items():
                    profiles_serializable[person_id] = {
                        k: v.isoformat() if isinstance(v, datetime) else v
                        for k, v in profile.items()
                    }
                json.dump(profiles_serializable, f, ensure_ascii=False, indent=2)
            
            logger.info("تم حفظ جميع النماذج")
            
        except Exception as e:
            logger.error(f"خطأ في حفظ النماذج: {e}")
    
    def load_models(self):
        """تحميل النماذج المحفوظة"""
        try:
            if ML_AVAILABLE:
                # تحميل كاشف الشذوذ
                anomaly_model_path = self.models_dir / "anomaly_detector.pkl"
                anomaly_scaler_path = self.models_dir / "anomaly_scaler.pkl"
                
                if anomaly_model_path.exists() and anomaly_scaler_path.exists():
                    self.anomaly_detector.model = joblib.load(anomaly_model_path)
                    self.anomaly_detector.scaler = joblib.load(anomaly_scaler_path)
                    self.anomaly_detector.is_trained = True
                    logger.info("تم تحميل كاشف الشذوذ")
                
                # تحميل متنبئ السلوك
                predictor_path = self.models_dir / "behavior_predictor.pkl"
                if predictor_path.exists():
                    self.behavior_predictor.model = joblib.load(predictor_path)
                    self.behavior_predictor.is_trained = True
                    logger.info("تم تحميل متنبئ السلوك")
            
            # تحميل الملفات الشخصية
            profiles_path = self.models_dir / "person_profiles.json"
            if profiles_path.exists():
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    
                    for person_id, profile in profiles_data.items():
                        # تحويل strings إلى datetime
                        if 'first_seen' in profile:
                            profile['first_seen'] = datetime.fromisoformat(profile['first_seen'])
                        if 'last_seen' in profile:
                            profile['last_seen'] = datetime.fromisoformat(profile['last_seen'])
                        
                        self.person_profiles[person_id] = profile
                
                logger.info(f"تم تحميل {len(self.person_profiles)} ملف شخصي")
            
        except Exception as e:
            logger.error(f"خطأ في تحميل النماذج: {e}")
    
    def get_system_insights(self) -> Dict[str, Any]:
        """الحصول على رؤى النظام"""
        insights = {
            'total_persons': len(self.person_profiles),
            'anomaly_detection_enabled': self.anomaly_detector.is_trained,
            'behavior_prediction_enabled': self.behavior_predictor.is_trained,
            'high_risk_persons': 0,
            'most_common_patterns': [],
            'system_health': 'good'
        }
        
        # إحصائيات المخاطر
        risk_counts = {'low': 0, 'medium': 0, 'high': 0}
        
        for profile in self.person_profiles.values():
            if profile.get('risk_history'):
                latest_risk = profile['risk_history'][-1]['risk_level']
                risk_counts[latest_risk] += 1
        
        insights['risk_distribution'] = risk_counts
        insights['high_risk_persons'] = risk_counts['high']
        
        # صحة النظام
        if not ML_AVAILABLE:
            insights['system_health'] = 'limited'
        elif not (self.anomaly_detector.is_trained and self.behavior_predictor.is_trained):
            insights['system_health'] = 'training'
        
        return insights
