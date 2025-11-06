# Entity Relationships (ER)

هذا المستند يوضح العلاقات بين كيانات النظام.

## العلاقات اللفظية
- employees (1) → (N) attendance_logs
- employees (1) → (N) activity_segments
- employees (1) → (N) face_encodings
- cameras (1) → (N) attendance_logs
- cameras (1) → (N) activity_segments
- alerts مستقل لكنها قد تُسند إلى user_id/employee_id مستقبلاً
- audit_logs يسجل كل عمليات الوصول/التعديل (مرتبط بمنفذين وليس بالضرورة موظفين)

## ER Diagram (Mermaid)
```mermaid
erDiagram
  EMPLOYEES ||--o{ ATTENDANCE_LOGS : has
  EMPLOYEES ||--o{ ACTIVITY_SEGMENTS : has
  EMPLOYEES ||--o{ FACE_ENCODINGS : has
  CAMERAS ||--o{ ATTENDANCE_LOGS : records
  CAMERAS ||--o{ ACTIVITY_SEGMENTS : records

  EMPLOYEES {
    TEXT id PK
    TEXT name
    TEXT department
    TEXT position
    TEXT email
    TEXT phone
    DATE hire_date
    BOOLEAN active
  }
  CAMERAS {
    TEXT id PK
    TEXT name
    TEXT source
    TEXT location
    TEXT device
    TEXT status
    DATETIME last_frame_time
    REAL fps
  }
  ATTENDANCE_LOGS {
    INTEGER id PK
    TEXT employee_id FK
    TEXT camera_id
    DATETIME check_in_time
    DATETIME check_out_time
    TEXT status
    DATE date
    INTEGER duration_seconds
  }
  ACTIVITY_SEGMENTS {
    INTEGER id PK
    TEXT employee_id FK
    TEXT camera_id
    TEXT activity
    DATETIME start_time
    DATETIME end_time
    INTEGER duration_seconds
    REAL confidence
  }
  FACE_ENCODINGS {
    INTEGER id PK
    TEXT employee_id FK
    BLOB encoding
    TEXT image_path
  }
  ALERTS {
    INTEGER id PK
    TEXT alert_type
    TEXT priority
    TEXT message
    TEXT details
    BOOLEAN acknowledged
  }
  AUDIT_LOGS {
    INTEGER id PK
    TEXT user_id
    TEXT action
    TEXT resource
    TEXT details
    TEXT ip_address
  }
```

## القيود والقواعد
- ATTENDANCE_LOGS.employee_id يجب أن يوجد في EMPLOYEES.id
- ACTIVITY_SEGMENTS.employee_id يجب أن يوجد في EMPLOYEES.id
- FACE_ENCODINGS.employee_id يجب أن يوجد في EMPLOYEES.id
- يفضّل فرض `PRAGMA foreign_keys=ON` في SQLite.
- استخدم معاملات لسلامة الكتابة عند إدخال بيانات متعددة الجداول.
