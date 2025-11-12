"""
Real-Time Dashboard - Level 2 Enhancement
لوحة تحكم في الوقت الفعلي لنظام الكاميرات المتعددة

الميزات:
- مراقبة مباشرة لجميع الكاميرات
- إحصائيات في الوقت الفعلي
- إنذارات فورية
- واجهة تفاعلية
"""
from __future__ import annotations
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from flask import Blueprint, render_template, jsonify, request, Response
import cv2
import numpy as np

# استيراد اختياري لـ SocketIO
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logging.warning("Flask-SocketIO غير متوفر. سيتم استخدام التحديثات العادية فقط.")

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.multi_camera_system import MultiCameraSystem
from src.attendance_manager import AttendanceManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real_time_dashboard")

# إنشاء Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# متغيرات عامة
multi_camera_system = None
socketio = None


def init_dashboard(app, socket_io):
    """تهيئة لوحة التحكم"""
    global multi_camera_system, socketio
    
    socketio = socket_io
    
    # تسجيل Blueprint
    app.register_blueprint(dashboard_bp)
    
    # تهيئة نظام الكاميرات المتعددة
    multi_camera_system = MultiCameraSystem()
    
    # تسجيل أحداث SocketIO
    register_socketio_events()
    
    logger.info("تم تهيئة لوحة التحكم في الوقت الفعلي")


def register_socketio_events():
    """تسجيل أحداث SocketIO"""
    if not SOCKETIO_AVAILABLE or not socketio:
        logger.warning("SocketIO غير متوفر - تم تخطي تسجيل الأحداث")
        return
    
    @socketio.on('connect', namespace='/dashboard')
    def on_connect():
        logger.info(f"اتصال جديد بلوحة التحكم: {request.sid}")
        emit('status', {'message': 'متصل بلوحة التحكم'})
    
    @socketio.on('disconnect', namespace='/dashboard')
    def on_disconnect():
        logger.info(f"انقطاع الاتصال: {request.sid}")
    
    @socketio.on('join_camera', namespace='/dashboard')
    def on_join_camera(data):
        camera_id = data.get('camera_id')
        if camera_id:
            join_room(f"camera_{camera_id}")
            logger.info(f"انضمام إلى غرفة الكاميرا {camera_id}")
    
    @socketio.on('leave_camera', namespace='/dashboard')
    def on_leave_camera(data):
        camera_id = data.get('camera_id')
        if camera_id:
            leave_room(f"camera_{camera_id}")
            logger.info(f"مغادرة غرفة الكاميرا {camera_id}")
    
    @socketio.on('start_cameras', namespace='/dashboard')
    def on_start_cameras():
        if multi_camera_system:
            success = multi_camera_system.start_all_cameras()
            emit('camera_status', {
                'action': 'start',
                'success': success,
                'message': 'تم بدء الكاميرات' if success else 'فشل في بدء الكاميرات'
            })
    
    @socketio.on('stop_cameras', namespace='/dashboard')
    def on_stop_cameras():
        if multi_camera_system:
            multi_camera_system.stop_all_cameras()
            emit('camera_status', {
                'action': 'stop',
                'success': True,
                'message': 'تم إيقاف الكاميرات'
            })


@dashboard_bp.route('/')
def dashboard_home():
    """الصفحة الرئيسية للوحة التحكم"""
    return render_template('real_time_dashboard.html')


@dashboard_bp.route('/api/system/status')
def get_system_status():
    """الحصول على حالة النظام"""
    if not multi_camera_system:
        return jsonify({'error': 'النظام غير مهيأ'}), 500
    
    try:
        stats = multi_camera_system.get_system_statistics()
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"خطأ في الحصول على حالة النظام: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/cameras/list')
def get_cameras_list():
    """قائمة الكاميرات المتاحة"""
    if not multi_camera_system:
        return jsonify({'error': 'النظام غير مهيأ'}), 500
    
    try:
        cameras = []
        for camera_id, camera_info in multi_camera_system.cameras.items():
            config = camera_info['config']
            stats = camera_info['stats']
            
            cameras.append({
                'id': camera_id,
                'name': config['name'],
                'location': config['location'],
                'enabled': config.get('enabled', True),
                'frames_processed': stats['frames_processed'],
                'persons_detected': stats['persons_detected'],
                'is_active': time.time() - camera_info['last_frame_time'] < 5
            })
        
        return jsonify({
            'success': True,
            'cameras': cameras
        })
    except Exception as e:
        logger.error(f"خطأ في الحصول على قائمة الكاميرات: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/camera/<camera_id>/stream')
def camera_stream(camera_id):
    """بث مباشر للكاميرا"""
    def generate_frames():
        while True:
            if not multi_camera_system or not multi_camera_system.running:
                break
            
            frame_data = multi_camera_system.get_camera_frame(camera_id)
            if frame_data:
                frame, stats = frame_data
                
                # تحويل الإطار إلى JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.1)  # تجنب الحمل الزائد
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@dashboard_bp.route('/api/persons/active')
def get_active_persons():
    """الأشخاص النشطين حالياً"""
    if not multi_camera_system:
        return jsonify({'error': 'النظام غير مهيأ'}), 500
    
    try:
        active_persons = []
        
        for global_id in multi_camera_system.cross_tracker.global_persons.keys():
            person_summary = multi_camera_system.cross_tracker.get_person_summary(global_id)
            if person_summary and person_summary['active_cameras']:
                active_persons.append(person_summary)
        
        return jsonify({
            'success': True,
            'active_persons': active_persons,
            'total_count': len(active_persons)
        })
    except Exception as e:
        logger.error(f"خطأ في الحصول على الأشخاص النشطين: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/analytics/summary')
def get_analytics_summary():
    """ملخص التحليلات"""
    if not multi_camera_system:
        return jsonify({'error': 'النظام غير مهيأ'}), 500
    
    try:
        stats = multi_camera_system.get_system_statistics()
        
        # حساب إحصائيات إضافية
        total_working = 0
        total_sleeping = 0
        total_idle = 0
        
        for person in stats.get('cross_camera_persons', []):
            activities = person.get('activities', {})
            total_working += activities.get('working', 0)
            total_sleeping += activities.get('sleeping', 0)
            total_idle += activities.get('idle', 0)
        
        summary = {
            'system_uptime': stats['system']['uptime'],
            'total_cameras': stats['system']['total_cameras'],
            'active_cameras': stats['system']['active_cameras'],
            'total_persons': stats['system']['total_persons'],
            'known_persons': stats['system']['known_persons'],
            'activity_breakdown': {
                'working': total_working,
                'sleeping': total_sleeping,
                'idle': total_idle
            },
            'camera_health': []
        }
        
        # صحة الكاميرات
        for camera_id, camera_stats in stats.get('cameras', {}).items():
            summary['camera_health'].append({
                'id': camera_id,
                'name': camera_stats['name'],
                'is_active': camera_stats['is_active'],
                'frames_processed': camera_stats['frames_processed']
            })
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        logger.error(f"خطأ في الحصول على ملخص التحليلات: {e}")
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/api/alerts/recent')
def get_recent_alerts():
    """الإنذارات الحديثة"""
    # يمكن تطوير نظام إنذارات متقدم هنا
    alerts = [
        {
            'id': 1,
            'type': 'info',
            'message': 'تم بدء النظام بنجاح',
            'timestamp': datetime.now().isoformat(),
            'camera_id': None
        }
    ]
    
    return jsonify({
        'success': True,
        'alerts': alerts
    })


@dashboard_bp.route('/api/reports/generate', methods=['POST'])
def generate_report():
    """إنشاء تقرير"""
    if not multi_camera_system:
        return jsonify({'error': 'النظام غير مهيأ'}), 500
    
    try:
        report_path = multi_camera_system.save_system_report()
        return jsonify({
            'success': True,
            'report_path': report_path,
            'message': 'تم إنشاء التقرير بنجاح'
        })
    except Exception as e:
        logger.error(f"خطأ في إنشاء التقرير: {e}")
        return jsonify({'error': str(e)}), 500


# دالة لإرسال التحديثات المباشرة
def broadcast_system_updates():
    """إرسال تحديثات النظام للعملاء المتصلين"""
    if not multi_camera_system or not socketio or not SOCKETIO_AVAILABLE:
        return
    
    try:
        stats = multi_camera_system.get_system_statistics()
        
        # إرسال إحصائيات النظام
        socketio.emit('system_update', {
            'type': 'system_stats',
            'data': stats['system'],
            'timestamp': datetime.now().isoformat()
        }, namespace='/dashboard')
        
        # إرسال حالة الكاميرات
        socketio.emit('cameras_update', {
            'type': 'camera_stats',
            'data': stats['cameras'],
            'timestamp': datetime.now().isoformat()
        }, namespace='/dashboard')
        
        # إرسال الأشخاص النشطين
        active_persons = [p for p in stats.get('cross_camera_persons', []) 
                         if p and p.get('active_cameras')]
        
        socketio.emit('persons_update', {
            'type': 'active_persons',
            'data': active_persons,
            'timestamp': datetime.now().isoformat()
        }, namespace='/dashboard')
        
    except Exception as e:
        logger.error(f"خطأ في إرسال التحديثات: {e}")


# يمكن استدعاء هذه الدالة من خيط منفصل للتحديثات المستمرة
def start_update_broadcaster():
    """بدء مذيع التحديثات"""
    import threading
    import time
    
    def update_loop():
        while True:
            if multi_camera_system and multi_camera_system.running:
                broadcast_system_updates()
            time.sleep(2)  # تحديث كل ثانيتين
    
    update_thread = threading.Thread(target=update_loop, daemon=True)
    update_thread.start()
    logger.info("تم بدء مذيع التحديثات المباشرة")
