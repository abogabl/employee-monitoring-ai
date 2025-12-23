"""
لوحة مراقبة بسيطة باستخدام Flask.
- تعرض حالة كل كاميرا (تشغيل/إيقاف، FPS، frozen، أخطاء)
- أزرار تحكم لبدء/إيقاف كاميرات
- بث JSON لحالة جميع الكاميرات للتحديث الدوري عبر AJAX
"""
from __future__ import annotations

import threading
from typing import Any, Dict

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from .multi_camera_runner import MultiCameraRunner

HTML = """
<!doctype html>
<html lang="ar">
<head>
  <meta charset="utf-8">
  <title>لوحة الكاميرات</title>
  <style>
    body { font-family: sans-serif; direction: rtl; margin: 16px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    th { background: #f5f5f5; }
    .ok { color: green; }
    .bad { color: red; }
    .controls { margin: 12px 0; }
    button { padding: 6px 12px; }
  </style>
</head>
<body>
  <h2>لوحة مراقبة الكاميرات</h2>
  <div class="controls">
    <form method="post" action="{{ url_for('control_all') }}" style="display:inline">
      <input type="hidden" name="action" value="start" />
      <button>تشغيل الكل</button>
    </form>
    <form method="post" action="{{ url_for('control_all') }}" style="display:inline">
      <input type="hidden" name="action" value="stop" />
      <button>إيقاف الكل</button>
    </form>
  </div>
  <table id="tbl">
    <thead>
      <tr>
        <th>Camera ID</th>
        <th>Running</th>
        <th>OK</th>
        <th>Frozen</th>
        <th>FPS</th>
        <th>Errors</th>
        <th>Message</th>
        <th>Controls</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
<script>
async function refresh(){
  const r = await fetch("{{ url_for('status_json') }}");
  const data = await r.json();
  const tbody = document.querySelector('#tbl tbody');
  tbody.innerHTML = '';
  Object.values(data).forEach(st => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${st.camera_id}</td>
      <td class="${st.running? 'ok':'bad'}">${st.running}</td>
      <td class="${st.health.ok? 'ok':'bad'}">${st.health.ok}</td>
      <td class="${st.health.frozen? 'bad':'ok'}">${st.health.frozen}</td>
      <td>${st.health.fps ?? '-'}</td>
      <td>${st.health.errors}</td>
      <td>${st.health.message}</td>
      <td>
        <form method="post" action="${'${'}'{{ url_for('control') }}'${'}'}" style="display:inline">
          <input type="hidden" name="camera_id" value="${st.camera_id}" />
          <input type="hidden" name="action" value="restart" />
          <button>إعادة تشغيل</button>
        </form>
        <form method="post" action="${'${'}'{{ url_for('control') }}'${'}'}" style="display:inline">
          <input type="hidden" name="camera_id" value="${st.camera_id}" />
          <input type="hidden" name="action" value="stop" />
          <button>إيقاف</button>
        </form>
      </td>`;
    tbody.appendChild(tr);
  });
}
setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>
"""


def create_app(runner: MultiCameraRunner) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template_string(HTML)

    @app.route("/status.json")
    def status_json():
        return jsonify(runner.get_all_status())

    @app.route("/control", methods=["POST"])
    def control():
        camera_id = request.form.get("camera_id", "")
        action = request.form.get("action", "")
        if action == "restart":
            runner.restart_camera(camera_id)
        elif action == "stop":
            runner.stop_camera(camera_id)
        return redirect(url_for("index"))

    @app.route("/control_all", methods=["POST"])
    def control_all():
        action = request.form.get("action", "")
        if action == "stop":
            runner.stop_all_cameras()
        elif action == "start":
            runner.start_all_cameras()
        return redirect(url_for("index"))

    return app


def run_dashboard(runner: MultiCameraRunner, host: str = "127.0.0.1", port: int = 5000) -> threading.Thread:
    app = create_app(runner)
    th = threading.Thread(target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False), daemon=True)
    th.start()
    return th
