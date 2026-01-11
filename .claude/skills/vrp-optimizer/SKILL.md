---
name: vrp-optimizer
description: |
  PyVRP + OR-Tools를 활용한 배송 경로 최적화 스킬.
  출하 목록을 입력받아 최적 배송 경로를 계산합니다.
  "배송 경로 최적화", "배차 계획" 요청 시 사용.
---

## 기능

1. 출하 목록 로드
2. 거리 매트릭스 계산
3. VRP 최적화 실행
4. 경로 시각화 및 저장

## 사용법

```bash
# 경로 최적화
python scripts/project/skills/vrp_wrapper.py \
  --shipments data/shipments.csv \
  --output outputs/routes/

# 시각화 포함
python scripts/project/skills/vrp_wrapper.py \
  --shipments data/shipments.csv \
  --visualize
```

## 입력 포맷

```csv
shipment_id,customer,address,weight_kg,pallets,time_window
SHP-001,A사,서울시 강남구,500,2,AM
SHP-002,B사,경기도 성남시,300,1,ANY
```

## 출력 포맷

```json
{
  "route_date": "2026-01-11",
  "vehicles": [
    {
      "vehicle_id": "5톤_1",
      "route": ["공장", "A사", "C사", "공장"],
      "distance_km": 45.2,
      "estimated_cost": 156000
    }
  ],
  "total_cost": 423000,
  "savings_vs_baseline": "18%"
}
```

## 의존성

- pyvrp
- ortools (fallback)
- folium (시각화)
- pandas

## 설정

```python
# config.py
VRP_CONFIG = {
    "solver": "pyvrp",  # or "ortools"
    "max_iterations": 10000,
    "time_limit_seconds": 60,
    "vehicle_types": [
        {"name": "5톤", "capacity_kg": 5000, "cost_per_km": 200},
        {"name": "11톤", "capacity_kg": 11000, "cost_per_km": 350}
    ]
}
```
