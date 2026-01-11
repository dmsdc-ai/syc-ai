# PyVRP 사용 가이드

State-of-the-art VRP (Vehicle Routing Problem) 솔버.
Python 네이티브, 논문 검증된 알고리즘.

## 기본 정보

- **GitHub**: https://github.com/PyVRP/PyVRP
- **문서**: https://pyvrp.readthedocs.io/
- **라이선스**: MIT
- **점수**: 9.00/10

## 설치

```bash
pip install pyvrp
```

## 기본 사용법

```python
from pyvrp import Model
from pyvrp.stop import MaxIterations

# 모델 생성
m = Model()

# 창고 (공장)
depot = m.add_depot(x=0, y=0)

# 배송지 추가
clients = [
    m.add_client(x=10, y=20, demand=5),
    m.add_client(x=30, y=40, demand=3),
    m.add_client(x=50, y=10, demand=7),
]

# 차량 추가
m.add_vehicle_type(capacity=15, num_available=3)

# 거리 계산 (유클리드)
locations = [depot] + clients
for frm in locations:
    for to in locations:
        distance = ((frm.x - to.x)**2 + (frm.y - to.y)**2)**0.5
        m.add_edge(frm, to, distance=int(distance))

# 최적화 실행
result = m.solve(stop=MaxIterations(1000))
print(result.best)
```

## 세영화학 적용

### 비용 함수 커스터마이징
```python
def calculate_cost(route):
    """
    총 비용 = 인건비 + 연료비 + 감가상각
    """
    distance_km = route.distance / 1000
    time_hours = route.duration / 3600

    labor_cost = time_hours * 15000  # 시급 15,000원
    fuel_cost = distance_km * 200    # km당 200원
    depreciation = 50000 if route.used else 0  # 차량 사용 시 5만원

    return labor_cost + fuel_cost + depreciation
```

### 시간 윈도우 제약
```python
# 오전 배송 제약
m.add_client(
    x=10, y=20,
    demand=5,
    tw_early=8*60,   # 08:00
    tw_late=12*60    # 12:00
)
```

## OR-Tools 대비 장점

| 항목 | PyVRP | OR-Tools |
|------|-------|----------|
| 속도 | 빠름 | 보통 |
| Python 친화성 | 높음 | 중간 |
| 최신 알고리즘 | O | X |
| 커뮤니티 | 작음 | 큼 |

---

## Next References

- [OR-Tools 가이드](ortools.md)
- [배송 최적화 에이전트](../../.claude/agents/delivery-optimizer.md)
