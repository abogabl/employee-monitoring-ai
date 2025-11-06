from __future__ import annotations

import numpy as np
import pytest

# تخطّي الاختبارات إن لم تتوفر insightface
pytest.importorskip("insightface")

from src.face_recognition_system import FaceRecognitionSystem


def test_frs_init_and_empty_db():
    frs = FaceRecognitionSystem(model_name="buffalo_l", threshold=0.6)
    frs.encodings.clear()
    # لا توجد قاعدة -> التعرف يرجع None
    dummy = np.random.rand(512).astype(np.float32)
    emp, sim, name = frs.recognize_face(dummy)
    assert emp is None


def test_add_employee_and_recognize(tmp_path):
    frs = FaceRecognitionSystem(model_name="buffalo_l", threshold=0.0)
    # إنشاء تضمين صناعي مباشر (نتجنب قراءة صور لسرعة الاختبار)
    emb = np.ones((512,), dtype=np.float32)
    frs._add_embedding("EMPX", "Test User", emb)
    emp, sim, name = frs.recognize_face(emb)
    assert emp == "EMPX"
    assert sim > 0.9
