"""
إدارة قاعدة بيانات الموظفين بصيغة JSON.
توفر إضافة/تحديث/حذف/جلب/سرد الموظفين مع حفظ/قراءة الملف.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


class EmployeeDatabase:
    """مدير بسيط لبيانات الموظفين باستخدام ملف JSON."""

    def __init__(self, json_path: Path | str = "employees_database/employees.json") -> None:
        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """تحميل البيانات من الملف إن وجد، وإلا تهيئة قاعدة فارغة."""
        if self.json_path.exists():
            try:
                self.data = json.loads(self.json_path.read_text(encoding="utf-8"))
                if not isinstance(self.data, dict):
                    logger.warning("صيغة JSON غير متوقعة، سيتم إعادة التهيئة.")
                    self.data = {}
            except Exception as e:
                logger.error("تعذر قراءة ملف الموظفين: %s", e)
                self.data = {}
        else:
            self.data = {}

    def save(self) -> None:
        """حفظ قاعدة البيانات إلى ملف JSON."""
        try:
            self.json_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.exception("تعذر حفظ ملف الموظفين: %s", e)

    def add_employee(self, emp_id: str, name: str, **kwargs: Any) -> None:
        """إضافة موظف جديد أو تحديثه إذا كان موجوداً."""
        self.data[emp_id] = {
            "name": name,
            **kwargs,
        }
        logger.info("تمت إضافة/تحديث الموظف %s - %s", emp_id, name)

    def get_employee(self, emp_id: str) -> Optional[Dict[str, Any]]:
        """جلب بيانات موظف عبر المعرف."""
        return self.data.get(emp_id)

    def update_employee(self, emp_id: str, **kwargs: Any) -> bool:
        """تحديث بيانات موظف موجود. يرجع True إذا تم التحديث."""
        if emp_id not in self.data:
            logger.warning("لا يوجد موظف بالمعرف: %s", emp_id)
            return False
        self.data[emp_id].update(kwargs)
        logger.info("تم تحديث بيانات الموظف %s", emp_id)
        return True

    def delete_employee(self, emp_id: str) -> bool:
        """حذف موظف. يرجع True إذا تم الحذف."""
        if emp_id in self.data:
            del self.data[emp_id]
            logger.info("تم حذف الموظف %s", emp_id)
            return True
        logger.warning("فشل حذف الموظف (غير موجود): %s", emp_id)
        return False

    def list_all_employees(self) -> List[Dict[str, Any]]:
        """سرد جميع الموظفين كقائمة قواميس مع تضمين emp_id داخل كل عنصر."""
        return [
            {"emp_id": emp_id, **info}
            for emp_id, info in self.data.items()
        ]
