# Python Data Models

هذه نماذج بيانات مرجعية (dataclasses) توضح البُنى المنطقية للكائنات في النظام.

> ملاحظة: هذه النماذج مرجعية للتوثيق والتنميط، وقد تختلف الحقول الفعلية المخزّنة بحسب طبقة التخزين/الـ APIs.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Tuple

@dataclass
class Employee:
    id: str
    name: str
    department: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[datetime] = None
    active: bool = True

@dataclass
class AttendanceLog:
    employee_id: str
    camera_id: str
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    status: str = 'checked_in'  # 'checked_in' | 'checked_out' | 'on_break'
    date: Optional[datetime] = None
    duration_seconds: Optional[int] = None

@dataclass
class ActivitySegment:
    employee_id: str
    camera_id: str
    activity: str  # 'working' | 'on_phone' | 'idle' | 'meeting' | 'away'
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    confidence: float

@dataclass
class Detection:
    box: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float
    class_id: int
    track_id: Optional[int] = None

@dataclass
class FaceRecognitionResult:
    employee_id: Optional[str]
    similarity: float
    name: Optional[str] = None
    is_known: bool = False
```
