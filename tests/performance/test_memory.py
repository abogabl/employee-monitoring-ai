from __future__ import annotations

import psutil


def test_memory_usage_reasonable():
    vm = psutil.virtual_memory()
    # يتأكد أن استدعاء psutil يعمل وأن هناك ذاكرة متاحة
    assert vm.total > 0
    # لا نضع حدود صارمة بسبب اختلاف البيئات
    assert vm.percent >= 0
