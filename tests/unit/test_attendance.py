from __future__ import annotations

from datetime import datetime, timedelta, date

from src.attendance_system import AttendanceSystem


def test_check_in_out_and_report(tmp_path, monkeypatch):
    db_path = tmp_path / "attendance.db"
    sys = AttendanceSystem(db_path=db_path)
    now = datetime.now()
    ok_in = sys.check_in("EMP001", "cam1", now, employee_name="Tester")
    assert ok_in is True
    # لا يسمح بدخول مزدوج
    assert sys.check_in("EMP001", "cam1", now) is False
    # خروج
    ok_out = sys.check_out("EMP001", "cam1", now + timedelta(hours=1))
    assert ok_out is True
    # تقرير يومي
    df = sys.generate_daily_report(now.date())
    assert not df.empty
    assert int(df.iloc[0]["duration_seconds"]) >= 3600
