# Database Schema

هذه الوثيقة توضح الجداول الأساسية، الحقول، الأنواع، القيود، والفهارس المقترحة للنظام.

## Table: employees
```sql
CREATE TABLE employees (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    position TEXT,
    email TEXT,
    phone TEXT,
    hire_date DATE,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_employees_active ON employees(active);
CREATE INDEX idx_employees_department ON employees(department);
```

- القيود: `id` مفتاح أساسي، `name` مطلوب، `active` منطقية.
- ملاحظات: يمكن إضافة قيد صيغة للبريد، وفهرس للحقول الأكثر استعلاماً.

## Table: attendance_logs
```sql
CREATE TABLE attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    check_in_time DATETIME NOT NULL,
    check_out_time DATETIME,
    status TEXT CHECK(status IN ('checked_in', 'checked_out', 'on_break')),
    date DATE NOT NULL,
    duration_seconds INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE INDEX idx_attendance_employee ON attendance_logs(employee_id);
CREATE INDEX idx_attendance_date ON attendance_logs(date);
CREATE INDEX idx_attendance_status ON attendance_logs(status);
```

- القيود: `employee_id` مطلوب ومُشار إليه من employees، حالة `status` ضمن مجموعة محددة.
- ملاحظات: احرص على تناسق `check_out_time > check_in_time` عبر تحقق طبقي/تطبيق.

## Table: activity_segments
```sql
CREATE TABLE activity_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    camera_id TEXT NOT NULL,
    activity TEXT CHECK(activity IN ('working', 'on_phone', 'idle', 'meeting', 'away')),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    duration_seconds INTEGER NOT NULL,
    confidence REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE INDEX idx_segments_employee ON activity_segments(employee_id);
CREATE INDEX idx_segments_time ON activity_segments(start_time, end_time);
CREATE INDEX idx_segments_activity ON activity_segments(activity);
```

- القيود: `activity` ضمن مجموعة محددة، `duration_seconds >= 0` (تحقق تطبيق).

## Table: face_encodings
```sql
CREATE TABLE face_encodings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    encoding BLOB NOT NULL,
    image_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE INDEX idx_encodings_employee ON face_encodings(employee_id);
```

- ملاحظات: يفضّل تشفير BLOB عند التخزين (انظر SecurityManager).

## Table: cameras
```sql
CREATE TABLE cameras (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    location TEXT,
    device TEXT DEFAULT 'cpu',
    status TEXT DEFAULT 'inactive',
    last_frame_time DATETIME,
    fps REAL,
    error_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

- ملاحظات: يمكن إضافة فهرس على `status`.

## Table: alerts
```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    priority TEXT CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    message TEXT NOT NULL,
    details TEXT,
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_by TEXT,
    acknowledged_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_priority ON alerts(priority);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
```

- ملاحظات: يمكن ربطها بجدول مستخدمين عند إضافة نظام مستخدمين كامل.

## Table: audit_logs
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    details TEXT,
    ip_address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_time ON audit_logs(created_at);
```

## ملاحظات عامة
- استخدم معاملات (transactions) لكل عمليات الكتابة الحساسة.
- فعِّل `PRAGMA foreign_keys = ON` لضمان صحة المفاتيح الأجنبية.
- نفّذ مهام VACUUM/OPTIMIZE دورياً (انظر MaintenanceManager).
