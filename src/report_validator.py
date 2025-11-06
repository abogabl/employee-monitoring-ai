"""
ReportValidator: التحقق من صحة تقارير CSV وإصلاح الأخطاء الشائعة.
- لا تداخل أوقات
- مجموع المقاطع = الوقت الكلي (اختياري إذا توفرت بيانات كلية)
- لا أزمنة سالبة
- التواريخ منطقية
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


class ReportValidator:
    """مدقق تقارير CSV للمقاطع الزمنية."""

    def __init__(self) -> None:
        self.errors: List[str] = []

    def _parse_dt(self, s: str) -> datetime:
        # يدعم ISO أو "YYYY-MM-DD HH:MM:SS"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

    def validate_csv(self, file_path: str | Path) -> Tuple[bool, List[str]]:
        p = Path(file_path)
        if not p.exists():
            return False, [f"ملف غير موجود: {p}"]
        self.errors.clear()
        rows = []
        with p.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        # تحقق من أزمنة سالبة وتواريخ منطقية
        for r in rows:
            try:
                st = self._parse_dt(r.get("start_time", ""))
                et = self._parse_dt(r.get("end_time", "")) if r.get("end_time") else None
                if et and et < st:
                    self.errors.append(f"نهاية قبل البداية في السطر: {r}")
                dur = float(r.get("duration_seconds", 0) or 0)
                if dur < 0:
                    self.errors.append(f"مدة سالبة في السطر: {r}")
            except Exception as e:
                self.errors.append(f"خطأ في parsing التاريخ/الوقت: {e} | السطر: {r}")
        # تحقق من التداخل لكل موظف
        from collections import defaultdict
        by_emp = defaultdict(list)
        for r in rows:
            eid = r.get("employee_id", "")
            try:
                st = self._parse_dt(r.get("start_time", ""))
                et = self._parse_dt(r.get("end_time", "")) if r.get("end_time") else None
            except Exception:
                continue
            by_emp[eid].append((st, et, r))
        for eid, lst in by_emp.items():
            lst.sort(key=lambda x: x[0])
            for i in range(1, len(lst)):
                a_st, a_et, a_r = lst[i - 1]
                b_st, b_et, b_r = lst[i]
                if a_et and b_st < a_et:
                    self.errors.append(f"تداخل زمني للموظف {eid}: {a_r} <-> {b_r}")
        return len(self.errors) == 0, list(self.errors)

    def fix_common_errors(self, file_path: str | Path) -> str:
        """محاولة إصلاح أخطاء شائعة مثل تنسيقات التاريخ أو مدة مفقودة عبر إعادة الحساب."""
        p = Path(file_path)
        rows = []
        with p.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
        # إعادة حساب المدة إن كانت مفقودة ولديك start/end
        for r in rows:
            st_s = r.get("start_time")
            et_s = r.get("end_time")
            if st_s and et_s:
                try:
                    st = self._parse_dt(st_s)
                    et = self._parse_dt(et_s)
                    r["duration_seconds"] = str(max(0, int((et - st).total_seconds())))
                except Exception:
                    pass
        out = p.with_name(p.stem + "_fixed" + p.suffix)
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return str(out)

    def generate_validation_report(self) -> str:
        if not self.errors:
            return "No errors found."
        return "\n".join(self.errors)
