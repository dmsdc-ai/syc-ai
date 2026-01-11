---
name: frepple-scheduler
description: |
  frePPLe 오픈소스 APS를 활용한 생산 스케줄링 스킬.
  주문 데이터를 입력받아 최적 생산 일정을 생성합니다.
  "생산 스케줄 생성", "frePPLe 실행" 요청 시 사용.
---

## 기능

1. 주문 데이터 → frePPLe 포맷 변환
2. frePPLe API 호출
3. 결과 파싱 및 저장

## 사용법

```bash
# 스케줄 생성
python scripts/project/skills/frepple_wrapper.py \
  --orders data/orders.csv \
  --output outputs/schedules/

# 테스트 모드
python scripts/project/skills/frepple_wrapper.py --test
```

## 입력 포맷

```csv
order_id,product_code,quantity,due_date
ORD-001,PE-FILM-600,1000,2026-01-15
ORD-002,PE-FILM-800,500,2026-01-16
```

## 출력 포맷

```json
{
  "schedule_date": "2026-01-11",
  "assignments": [
    {
      "machine": "1호기",
      "orders": ["ORD-001"],
      "start_time": "08:00",
      "end_time": "16:00"
    }
  ]
}
```

## 의존성

- frePPLe (Docker or pip)
- requests
- pandas

## 설정

```python
# config.py
FREPPLE_CONFIG = {
    "api_url": "http://localhost:8000/api",
    "username": "admin",
    "password": "admin"
}
```
