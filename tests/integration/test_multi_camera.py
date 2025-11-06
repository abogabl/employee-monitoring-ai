from __future__ import annotations

from pathlib import Path

from src.multi_camera_runner import MultiCameraRunner


def test_config_load_and_validate(tmp_path):
    # إنشاء ملف إعدادات بسيط
    cfg = tmp_path / "cameras_config.json"
    cfg.write_text(
        """
        {"global_settings": {"output_dir": "results/"},
         "cameras": [
           {"id": "cam1", "source": "0", "device": "cpu", "enabled": true}
         ]}
        """,
        encoding="utf-8",
    )
    runner = MultiCameraRunner(cfg)
    data = runner.load_config()
    ok, errs = runner.validate_config()
    assert ok, f"Config invalid: {errs}"
