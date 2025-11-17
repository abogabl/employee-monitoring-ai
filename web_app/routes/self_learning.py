"""
مسارات واجهة نظام التعلم الذاتي
Self-Learning System Routes
"""
from flask import Blueprint, jsonify, render_template, render_template_string, request
from pathlib import Path
from src.self_learning.database import SelfLearningDB
from src.self_learning.models import HumanCorrection
from src.self_learning.continuous_trainer import ContinuousTrainer
from src.self_learning.monitoring import SystemMonitor

# إنشاء Blueprint
self_learning_bp = Blueprint('self_learning', __name__, url_prefix='/self-learning')

# قاعدة البيانات
db = SelfLearningDB()
trainer = ContinuousTrainer(db=db)
monitor = SystemMonitor(db=db)


@self_learning_bp.route('/')
def dashboard():
    """لوحة معلومات التعلم الذاتي"""
    try:
        stats = db.get_stats()
        
        html = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام التعلم الذاتي</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
    <style>
        /* قائمة تنقل سريع */
        .quick-nav {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .quick-nav a {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .quick-nav a:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        
        .quick-nav a i {
            font-size: 1.2em;
        }
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-title {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-subtitle {
            font-size: 0.8em;
            color: #999;
            margin-top: 5px;
        }
        .success {
            color: #10b981;
        }
        .warning {
            color: #f59e0b;
        }
        .info {
            color: #3b82f6;
        }
        .section {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .section h2 {
            color: #333;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            margin-right: 10px;
        }
        .badge-success {
            background: #d1fae5;
            color: #065f46;
        }
        .badge-warning {
            background: #fef3c7;
            color: #92400e;
        }
        .badge-info {
            background: #dbeafe;
            color: #1e40af;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }
        .back-link {
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 10px 20px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }
        .back-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 7px 20px rgba(0,0,0,0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 نظام التعلم الذاتي</h1>
        
        <!-- قائمة تنقل سريع -->
        <div class="quick-nav">
            <a href="/self-learning">
                <i class="bi bi-house-fill"></i>
                الرئيسية
            </a>
            <a href="/self-learning/confirmation/queue">
                <i class="bi bi-check-circle"></i>
                قائمة التأكيد
            </a>
            <a href="/self-learning/monitoring">
                <i class="bi bi-heart-pulse"></i>
                المراقبة
            </a>
            <a href="/monitoring">
                <i class="bi bi-activity"></i>
                المراقبة الشاملة
            </a>
            <a href="/">
                <i class="bi bi-arrow-left-circle"></i>
                الرئيسية العامة
            </a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-title">📸 إجمالي الصور</div>
                <div class="stat-value">{{ stats.images.total }}</div>
                <div class="stat-subtitle">صورة تدريبية</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-title">✅ الصور المؤكدة</div>
                <div class="stat-value success">{{ stats.images.validated }}</div>
                <div class="stat-subtitle">{{ ((stats.images.validated / stats.images.total * 100) if stats.images.total > 0 else 0)|round(1) }}% من الإجمالي</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-title">⭐ متوسط الجودة</div>
                <div class="stat-value warning">{{ (stats.images.avg_quality * 100)|round(1) }}%</div>
                <div class="stat-subtitle">جودة الصور المجمعة</div>
            </div>
            
            <div class="stat-card">
                <div class="stat-title">🎯 متوسط الثقة</div>
                <div class="stat-value info">{{ (stats.images.avg_confidence * 100)|round(1) }}%</div>
                <div class="stat-subtitle">ثقة التعرف</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📋 قائمة التأكيد</h2>
            {% if stats.queue %}
                <p>
                    <span class="status-badge badge-warning">⏳ معلقة: {{ stats.queue.get('pending', 0) }}</span>
                    <span class="status-badge badge-success">✓ مؤكدة: {{ stats.queue.get('confirmed', 0) }}</span>
                    <span class="status-badge badge-info">✗ مرفوضة: {{ stats.queue.get('rejected', 0) }}</span>
                </p>
                {% if stats.queue.get('pending', 0) > 0 %}
                <p style="margin-top: 15px;">
                    <a href="/self-learning/confirmation/queue" style="display: inline-block; background: #667eea; color: white; padding: 12px 25px; border-radius: 25px; text-decoration: none; font-weight: bold; box-shadow: 0 5px 15px rgba(0,0,0,0.2); transition: all 0.3s ease;">
                        🔍 فتح قائمة التأكيد ←
                    </a>
                </p>
                {% endif %}
            {% else %}
                <p style="color: #999;">لا توجد حالات في قائمة التأكيد</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>🔧 التصحيحات البشرية</h2>
            <p style="font-size: 1.2em; color: #333;">
                إجمالي التصحيحات: <strong>{{ stats.corrections }}</strong>
            </p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {{ ((stats.corrections / (stats.images.total if stats.images.total > 0 else 1)) * 100)|round(0)|int }}%">
                    {{ ((stats.corrections / (stats.images.total if stats.images.total > 0 else 1)) * 100)|round(1) }}%
                </div>
            </div>
            <p style="color: #666; margin-top: 5px; font-size: 0.9em;">نسبة التصحيحات إلى الصور</p>
        </div>
        
        {% if stats.latest_performance %}
        <div class="section">
            <h2>📊 آخر أداء للنموذج</h2>
            <p><strong>الإصدار:</strong> {{ stats.latest_performance.model_version }}</p>
            <p><strong>الدقة:</strong> {{ (stats.latest_performance.accuracy * 100)|round(2) }}%</p>
            <p><strong>Precision:</strong> {{ (stats.latest_performance.precision * 100)|round(2) }}%</p>
            <p><strong>Recall:</strong> {{ (stats.latest_performance.recall * 100)|round(2) }}%</p>
            <p><strong>F1 Score:</strong> {{ (stats.latest_performance.f1_score * 100)|round(2) }}%</p>
        </div>
        {% else %}
        <div class="section">
            <h2>📊 أداء النموذج</h2>
            <p style="color: #999;">لم يتم تسجيل أي مؤشرات أداء بعد</p>
        </div>
        {% endif %}
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="back-link">← العودة للرئيسية</a>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(html, stats=stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/api/stats')
def api_stats():
    """API للحصول على الإحصائيات"""
    try:
        stats = db.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/confirmation/queue')
def confirmation_queue():
    """صفحة قائمة التأكيد"""
    try:
        # جلب الحالات المعلقة
        pending_items = db.get_pending_confirmations(limit=100)
        
        # إعداد البيانات للعرض
        items = []
        for queue_item in pending_items:
            # جلب بيانات الصورة
            training_img = db.get_training_image(queue_item.image_id)
            if not training_img:
                continue
            
            # مسار الصورة
            image_path = Path(training_img.image_path)
            if image_path.exists():
                # تحويل المسار لـ URL
                # training_data/raw/EMP001/... -> /static/training_data/raw/EMP001/...
                rel_path = image_path.relative_to(Path.cwd())
                image_url = f'/static/{rel_path.as_posix()}'
            else:
                image_url = '/static/placeholder.png'
            
            items.append({
                'id': queue_item.id,
                'image_id': queue_item.image_id,
                'employee_id': training_img.employee_id,
                'confidence': training_img.confidence,
                'quality_score': training_img.quality_score,
                'priority': queue_item.priority,
                'top_predictions': queue_item.top_predictions,
                'image_url': image_url,
            })
        
        # الإحصائيات
        stats = db.get_stats()
        queue_stats = stats.get('queue', {})
        
        context = {
            'items': items,
            'pending_count': queue_stats.get('pending', 0),
            'confirmed_count': queue_stats.get('confirmed', 0),
            'rejected_count': queue_stats.get('rejected', 0),
            'accuracy': round(stats['images'].get('avg_confidence', 0) * 100, 1),
        }
        
        return render_template('confirmation/queue.html', **context)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/api/confirm', methods=['POST'])
def api_confirm():
    """API لتأكيد أو رفض صورة"""
    try:
        data = request.get_json()
        queue_id = data.get('queue_id')
        action = data.get('action')  # confirm, reject, correct
        employee_id = data.get('employee_id')
        
        if not queue_id or not action:
            return jsonify({'success': False, 'error': 'بيانات ناقصة'}), 400
        
        # جلب حالة القائمة
        pending = db.get_pending_confirmations(limit=1000)
        queue_item = next((q for q in pending if q.id == queue_id), None)
        
        if not queue_item:
            return jsonify({'success': False, 'error': 'الحالة غير موجودة'}), 404
        
        # جلب الصورة
        training_img = db.get_training_image(queue_item.image_id)
        if not training_img:
            return jsonify({'success': False, 'error': 'الصورة غير موجودة'}), 404
        
        # معالجة الإجراء
        if action == 'confirm':
            # تأكيد التوقع الأول
            db.update_confirmation_status(queue_id, 'confirmed', 'web_user')
            db.mark_as_validated(queue_item.image_id)
            
        elif action == 'reject':
            # رفض الصورة
            db.update_confirmation_status(queue_id, 'rejected', 'web_user')
            
        elif action == 'correct':
            # تصحيح بشري
            if not employee_id:
                return jsonify({'success': False, 'error': 'معرف الموظف مطلوب'}), 400
            
            # حفظ التصحيح
            correction = HumanCorrection(
                image_id=queue_item.image_id,
                original_prediction=training_img.employee_id,
                corrected_to=employee_id,
                confidence=training_img.confidence,
                corrected_by='web_user',
                correction_reason='تصحيح يدوي من واجهة التأكيد'
            )
            db.insert_correction(correction)
            
            # تحديث حالة القائمة
            db.update_confirmation_status(queue_id, 'confirmed', 'web_user')
        
        else:
            return jsonify({'success': False, 'error': 'إجراء غير معروف'}), 400
        
        return jsonify({'success': True, 'message': 'تم التنفيذ بنجاح'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@self_learning_bp.route('/api/pending-count')
def api_pending_count():
    """API لعدد الحالات المعلقة"""
    try:
        count = db.get_pending_count()
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/monitoring')
def monitoring_dashboard():
    """لوحة المراقبة"""
    try:
        dashboard_data = monitor.get_monitoring_dashboard_data()
        
        html = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة المراقبة - نظام التعلم الذاتي</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .health-meter {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border-radius: 15px;
            color: white;
            margin: 20px 0;
        }
        .health-score {
            font-size: 4em;
            font-weight: bold;
            margin: 10px 0;
        }
        .health-status {
            font-size: 1.5em;
            opacity: 0.9;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .alerts-section {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .alert-item {
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-right: 5px solid;
        }
        .alert-critical { background: #fee2e2; border-color: #dc2626; }
        .alert-error { background: #fef3c7; border-color: #f59e0b; }
        .alert-warning { background: #fef9c3; border-color: #eab308; }
        .alert-info { background: #dbeafe; border-color: #3b82f6; }
        .alert-title { font-weight: bold; margin-bottom: 5px; }
        .back-link {
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 12px 25px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 لوحة مراقبة النظام</h1>
            <p style="color: #666;">مراقبة صحة وأداء نظام التعلم الذاتي</p>
        </div>
        
        <div class="health-meter">
            <div class="health-score">{{ dashboard_data.health_score }}%</div>
            <div class="health-status">{{ dashboard_data.health_status }}</div>
            <p style="margin-top: 15px; opacity: 0.8;">درجة صحة النظام</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ dashboard_data.total_alerts }}</div>
                <div>إجمالي التنبيهات</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #dc2626;">{{ dashboard_data.alerts_by_level.critical }}</div>
                <div>عاجل</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #f59e0b;">{{ dashboard_data.alerts_by_level.error }}</div>
                <div>أخطاء</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #eab308;">{{ dashboard_data.alerts_by_level.warning }}</div>
                <div>تحذيرات</div>
            </div>
        </div>
        
        <div class="alerts-section">
            <h2>🔔 التنبيهات النشطة</h2>
            {% if dashboard_data.alerts %}
                {% for alert in dashboard_data.alerts %}
                <div class="alert-item alert-{{ alert.level }}">
                    <div class="alert-title">{{ alert.title }}</div>
                    <div>{{ alert.message }}</div>
                    <small style="opacity: 0.7;">{{ alert.timestamp }}</small>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #999; padding: 20px; text-align: center;">
                    ✅ لا توجد تنبيهات - النظام يعمل بشكل ممتاز!
                </p>
            {% endif %}
        </div>
        
        <div style="text-align: center;">
            <a href="/self-learning" class="back-link">← العودة للرئيسية</a>
        </div>
    </div>
</body>
</html>
        """
        
        return render_template_string(html, dashboard_data=dashboard_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/api/train', methods=['POST'])
def api_train():
    """API لتشغيل التدريب"""
    try:
        force = request.json.get('force', False) if request.is_json else False
        
        performance = trainer.train(force=force)
        
        if performance:
            return jsonify({
                'success': True,
                'message': 'تم التدريب بنجاح',
                'performance': performance.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'لم يتم التدريب - لا حاجة له حالياً'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@self_learning_bp.route('/api/training-stats')
def api_training_stats():
    """API لإحصائيات التدريب"""
    try:
        stats = trainer.get_training_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@self_learning_bp.route('/api/monitoring/health')
def api_health():
    """API لدرجة صحة النظام"""
    try:
        health_score = monitor.get_health_score()
        return jsonify({'health_score': health_score})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
