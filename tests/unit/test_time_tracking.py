from __future__ import annotations

from datetime import datetime, timedelta

from src.time_tracking import TimeTracker


def test_time_tracker_segments_and_summary():
    tt = TimeTracker(min_segment_duration=0.5)
    t0 = datetime.now()
    tt.start_activity("1", "EMP001", "working", t0, "cam1")
    tt.update_activity("1", "working", t0 + timedelta(seconds=1))
    tt.update_activity("1", "idle", t0 + timedelta(seconds=2))
    tt.end_tracking("1", t0 + timedelta(seconds=4))

    segs = tt.get_segments("1")
    assert len(segs) >= 1
    sm = tt.get_activity_summary("1")
    assert sm["total"] > 0
