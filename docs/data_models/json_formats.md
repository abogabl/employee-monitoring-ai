# JSON Data Formats

## Camera Config
```json
{
  "id": "cam1",
  "name": "مدخل المكتب",
  "source": "rtsp://192.168.1.100/stream1",
  "device": "cuda:0",
  "imgsz": 640,
  "conf": 0.5,
  "enabled": true,
  "location": "entrance"
}
```

## Employee
```json
{
  "id": "EMP001",
  "name": "أحمد علي",
  "department": "IT",
  "position": "مطور",
  "email": "ahmed@company.com",
  "active": true
}
```

## Report Output (daily_summary)
```json
{
  "report_type": "daily_summary",
  "date": "2024-01-15",
  "generated_at": "2024-01-15T18:00:00",
  "employees": [
    {
      "employee_id": "EMP001",
      "name": "أحمد علي",
      "check_in": "09:05:00",
      "check_out": "17:30:00",
      "total_hours": 8.42,
      "activities": {
        "working": 6.5,
        "on_phone": 0.8,
        "idle": 1.12
      },
      "productivity_rate": 0.77
    }
  ]
}
```
