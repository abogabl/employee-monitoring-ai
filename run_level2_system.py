#!/usr/bin/env python3
"""
Level 2 Enhanced System Runner
سكريبت تشغيل النظام المحسن - المستوى الثاني

الميزات الجديدة:
- نظام كاميرات متعددة متزامن
- لوحة تحكم في الوقت الفعلي
- ذكاء اصطناعي متقدم للسلوك
- تحليلات وتنبؤات ذكية

الاستخدام:
python run_level2_system.py --mode dashboard    # لوحة التحكم فقط
python run_level2_system.py --mode cameras     # الكاميرات فقط  
python run_level2_system.py --mode full        # النظام الكامل
"""

import sys
import argparse
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any

# إضافة المجلد الجذر للمشروع
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.multi_camera_system import MultiCameraSystem
from src.advanced_behavior_ai import AdvancedBehaviorAI
from web_app.app import create_app
from web_app.real_time_dashboard import init_dashboard, start_update_broadcaster

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("level2_system")


class Level2System:
    """النظام المحسن - المستوى الثاني"""
    
    def __init__(self, args):
        self.args = args
        self.running = False
        
        # المكونات الرئيسية
        self.multi_camera_system = None
        self.behavior_ai = None
        self.web_app = None
        self.socketio = None
        
        # خيوط التشغيل
        self.camera_thread = None
        self.ai_thread = None
        self.web_thread = None
        
        logger.info("🚀 تهيئة النظام المحسن - المستوى الثاني")
    
    def initialize_components(self):
        """تهيئة جميع المكونات"""
        try:
            # تهيئة نظام الكاميرات المتعددة
            if self.args.mode in ['cameras', 'full']:
                logger.info("📹 تهيئة نظام الكاميرات المتعددة...")
                self.multi_camera_system = MultiCameraSystem()
                
                if not self.multi_camera_system.initialize_cameras():
                    logger.error("❌ فشل في تهيئة نظام الكاميرات")
                    return False
                
                logger.info("✅ تم تهيئة نظام الكاميرات بنجاح")
            
            # تهيئة الذكاء الاصطناعي المتقدم
            if self.args.enable_ai:
                logger.info("🧠 تهيئة الذكاء الاصطناعي المتقدم...")
                self.behavior_ai = AdvancedBehaviorAI()
                logger.info("✅ تم تهيئة الذكاء الاصطناعي بنجاح")
            
            # تهيئة تطبيق الويب ولوحة التحكم
            if self.args.mode in ['dashboard', 'full']:
                logger.info("🌐 تهيئة تطبيق الويب ولوحة التحكم...")
                
                try:
                    from flask_socketio import SocketIO
                    
                    # إنشاء تطبيق Flask
                    self.web_app = create_app()
                    
                    # إنشاء SocketIO
                    self.socketio = SocketIO(
                        self.web_app,
                        cors_allowed_origins="*",
                        async_mode='threading'
                    )
                    
                    # تهيئة لوحة التحكم
                    init_dashboard(self.web_app, self.socketio)
                    
                    logger.info("✅ تم تهيئة تطبيق الويب ولوحة التحكم بنجاح")
                    
                except ImportError:
                    logger.warning("⚠️ Flask-SocketIO غير متوفر. سيتم استخدام Flask العادي فقط.")
                    self.web_app = create_app()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة المكونات: {e}")
            return False
    
    def start_camera_system(self):
        """بدء نظام الكاميرات"""
        if not self.multi_camera_system:
            return
        
        def camera_worker():
            try:
                logger.info("🎬 بدء نظام الكاميرات المتعددة...")
                
                if self.multi_camera_system.start_all_cameras():
                    logger.info("✅ تم بدء جميع الكاميرات بنجاح")
                    
                    # حلقة المراقبة والتحديث
                    while self.running:
                        try:
                            # جمع البيانات من جميع الكاميرات
                            if self.behavior_ai:
                                self._update_ai_with_camera_data()
                            
                            time.sleep(5)  # تحديث كل 5 ثواني
                            
                        except Exception as e:
                            logger.error(f"خطأ في حلقة الكاميرات: {e}")
                            time.sleep(1)
                else:
                    logger.error("❌ فشل في بدء الكاميرات")
                    
            except Exception as e:
                logger.error(f"❌ خطأ في خيط الكاميرات: {e}")
            finally:
                if self.multi_camera_system:
                    self.multi_camera_system.stop_all_cameras()
        
        self.camera_thread = threading.Thread(target=camera_worker, name="CameraSystem")
        self.camera_thread.daemon = True
        self.camera_thread.start()
    
    def start_ai_system(self):
        """بدء نظام الذكاء الاصطناعي"""
        if not self.behavior_ai:
            return
        
        def ai_worker():
            try:
                logger.info("🧠 بدء نظام الذكاء الاصطناعي...")
                
                while self.running:
                    try:
                        # تحديث النماذج بشكل دوري
                        if self.multi_camera_system:
                            all_person_data = self._collect_all_person_data()
                            if len(all_person_data) >= 5:  # حد أدنى للتحديث
                                self.behavior_ai.update_models(all_person_data)
                                logger.info(f"تم تحديث نماذج الذكاء الاصطناعي بـ {len(all_person_data)} عينة")
                        
                        # انتظار قبل التحديث التالي
                        time.sleep(300)  # تحديث كل 5 دقائق
                        
                    except Exception as e:
                        logger.error(f"خطأ في نظام الذكاء الاصطناعي: {e}")
                        time.sleep(60)  # انتظار دقيقة في حالة الخطأ
                        
            except Exception as e:
                logger.error(f"❌ خطأ في خيط الذكاء الاصطناعي: {e}")
        
        self.ai_thread = threading.Thread(target=ai_worker, name="AISystem")
        self.ai_thread.daemon = True
        self.ai_thread.start()
    
    def start_web_system(self):
        """بدء نظام الويب"""
        if not self.web_app:
            return
        
        def web_worker():
            try:
                logger.info("🌐 بدء خادم الويب...")
                
                # بدء مذيع التحديثات إذا كان SocketIO متوفراً
                if self.socketio:
                    start_update_broadcaster()
                
                # تشغيل الخادم
                if self.socketio:
                    self.socketio.run(
                        self.web_app,
                        host=self.args.host,
                        port=self.args.port,
                        debug=self.args.debug,
                        use_reloader=False  # تجنب إعادة التحميل التلقائي
                    )
                else:
                    self.web_app.run(
                        host=self.args.host,
                        port=self.args.port,
                        debug=self.args.debug,
                        use_reloader=False
                    )
                    
            except Exception as e:
                logger.error(f"❌ خطأ في خادم الويب: {e}")
        
        self.web_thread = threading.Thread(target=web_worker, name="WebServer")
        self.web_thread.daemon = True
        self.web_thread.start()
    
    def _update_ai_with_camera_data(self):
        """تحديث الذكاء الاصطناعي ببيانات الكاميرات"""
        try:
            if not self.behavior_ai or not self.multi_camera_system:
                return
            
            # جمع بيانات جميع الأشخاص من جميع الكاميرات
            for camera_id, camera_info in self.multi_camera_system.cameras.items():
                processor = camera_info['processor']
                
                for track_id, person_data in processor.person_data.items():
                    # تحليل سلوك الشخص
                    analysis = self.behavior_ai.analyze_person_behavior(
                        f"{camera_id}_{track_id}", person_data
                    )
                    
                    # إضافة التحليل لبيانات الشخص
                    person_data['ai_analysis'] = analysis
                    
                    # طباعة التحليلات المهمة
                    if analysis['anomaly_detected']:
                        logger.warning(
                            f"⚠️ شذوذ مكتشف: {person_data.get('name', 'Unknown')} "
                            f"في الكاميرا {camera_id} (ثقة: {analysis['anomaly_confidence']:.2f})"
                        )
                    
                    if analysis['risk_level'] == 'high':
                        logger.warning(
                            f"🚨 مخاطر عالية: {person_data.get('name', 'Unknown')} "
                            f"في الكاميرا {camera_id}"
                        )
                        
        except Exception as e:
            logger.error(f"خطأ في تحديث الذكاء الاصطناعي: {e}")
    
    def _collect_all_person_data(self) -> List[Dict[str, Any]]:
        """جمع بيانات جميع الأشخاص"""
        all_data = []
        
        try:
            if not self.multi_camera_system:
                return all_data
            
            for camera_id, camera_info in self.multi_camera_system.cameras.items():
                processor = camera_info['processor']
                
                for track_id, person_data in processor.person_data.items():
                    # إضافة معرف فريد
                    person_data['person_id'] = f"{camera_id}_{track_id}"
                    person_data['camera_id'] = camera_id
                    all_data.append(person_data.copy())
                    
        except Exception as e:
            logger.error(f"خطأ في جمع بيانات الأشخاص: {e}")
        
        return all_data
    
    def run(self):
        """تشغيل النظام الكامل"""
        if not self.initialize_components():
            logger.error("❌ فشل في تهيئة النظام")
            return False
        
        self.running = True
        
        try:
            logger.info("🚀 بدء النظام المحسن - المستوى الثاني")
            
            # بدء المكونات المختلفة
            if self.args.mode in ['cameras', 'full']:
                self.start_camera_system()
            
            if self.args.enable_ai:
                self.start_ai_system()
            
            if self.args.mode in ['dashboard', 'full']:
                self.start_web_system()
            
            # طباعة معلومات النظام
            self._print_system_info()
            
            # انتظار إيقاف النظام
            if self.args.mode == 'full':
                # في الوضع الكامل، انتظار خيط الويب
                if self.web_thread:
                    self.web_thread.join()
            elif self.args.mode == 'cameras':
                # في وضع الكاميرات فقط، انتظار إدخال المستخدم
                try:
                    input("اضغط Enter لإيقاف النظام...\n")
                except KeyboardInterrupt:
                    pass
            elif self.args.mode == 'dashboard':
                # في وضع لوحة التحكم فقط، انتظار خيط الويب
                if self.web_thread:
                    self.web_thread.join()
            
        except KeyboardInterrupt:
            logger.info("تم استلام إشارة الإيقاف من المستخدم")
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل النظام: {e}")
            return False
        finally:
            self.stop()
        
        return True
    
    def _print_system_info(self):
        """طباعة معلومات النظام"""
        logger.info("=" * 60)
        logger.info("🎯 النظام المحسن - المستوى الثاني")
        logger.info("=" * 60)
        
        if self.args.mode in ['dashboard', 'full']:
            logger.info(f"🌐 لوحة التحكم: http://{self.args.host}:{self.args.port}/dashboard")
            logger.info(f"📊 واجهة الفيديو: http://{self.args.host}:{self.args.port}/test-video")
        
        if self.args.mode in ['cameras', 'full']:
            camera_count = len(self.multi_camera_system.cameras) if self.multi_camera_system else 0
            logger.info(f"📹 الكاميرات المتاحة: {camera_count}")
        
        if self.args.enable_ai:
            logger.info("🧠 الذكاء الاصطناعي المتقدم: مُفعل")
        
        logger.info(f"⚙️ الوضع: {self.args.mode}")
        logger.info("=" * 60)
    
    def stop(self):
        """إيقاف النظام"""
        logger.info("🛑 إيقاف النظام...")
        self.running = False
        
        # إيقاف الكاميرات
        if self.multi_camera_system:
            self.multi_camera_system.stop_all_cameras()
        
        # حفظ نماذج الذكاء الاصطناعي
        if self.behavior_ai:
            self.behavior_ai.save_models()
        
        logger.info("✅ تم إيقاف النظام بنجاح")


def parse_arguments():
    """تحليل معاملات سطر الأوامر"""
    parser = argparse.ArgumentParser(
        description="النظام المحسن للمراقبة الذكية - المستوى الثاني",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة الاستخدام:
  python run_level2_system.py --mode full                    # النظام الكامل
  python run_level2_system.py --mode dashboard               # لوحة التحكم فقط
  python run_level2_system.py --mode cameras --enable-ai     # الكاميرات مع الذكاء الاصطناعي
  python run_level2_system.py --mode full --host 0.0.0.0    # إتاحة على الشبكة
        """
    )
    
    # الوضع الرئيسي
    parser.add_argument(
        "--mode", 
        choices=['dashboard', 'cameras', 'full'],
        default='full',
        help="وضع التشغيل (افتراضي: full)"
    )
    
    # إعدادات الخادم
    parser.add_argument(
        "--host", 
        default="127.0.0.1",
        help="عنوان الخادم (افتراضي: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="منفذ الخادم (افتراضي: 8080)"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true",
        help="تفعيل وضع التصحيح"
    )
    
    # الذكاء الاصطناعي
    parser.add_argument(
        "--enable-ai", 
        action="store_true",
        help="تفعيل الذكاء الاصطناعي المتقدم"
    )
    
    parser.add_argument(
        "--no-ai", 
        action="store_true",
        help="تعطيل الذكاء الاصطناعي"
    )
    
    args = parser.parse_args()
    
    # معالجة تضارب خيارات الذكاء الاصطناعي
    if args.no_ai:
        args.enable_ai = False
    elif args.mode == 'full':
        args.enable_ai = True  # تفعيل تلقائي في الوضع الكامل
    
    return args


def main():
    """الدالة الرئيسية"""
    try:
        args = parse_arguments()
        
        # إنشاء وتشغيل النظام
        system = Level2System(args)
        success = system.run()
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"❌ خطأ في النظام: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
