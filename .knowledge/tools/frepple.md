# frePPLe 사용 가이드

오픈소스 APS (Advanced Planning & Scheduling) 도구.
TOC(제약이론) 기반 생산 스케줄링.

## 기본 정보

- **GitHub**: https://github.com/frePPLe/frepple
- **문서**: https://frepple.com/docs/
- **라이선스**: AGPL-3.0 (Community), Commercial (Enterprise)
- **점수**: 8.55/10

## 설치

```bash
# Docker 설치 (권장)
docker pull frepple/frepple:latest
docker run -d -p 8000:8000 frepple/frepple

# 또는 pip
pip install frepple
```

## 핵심 개념

| 개념 | 설명 |
|------|------|
| Resource | 기계, 작업자 등 생산 자원 |
| Operation | 공정 단계 |
| Buffer | 재고/WIP 버퍼 |
| Demand | 주문/수요 |

## REST API 사용

```python
import requests

# 수요 등록
response = requests.post(
    "http://localhost:8000/api/input/demand/",
    json={
        "name": "ORDER-001",
        "item": "PE-FILM-600",
        "quantity": 1000,
        "due": "2026-01-15"
    }
)

# 계획 실행
requests.post("http://localhost:8000/api/execute/")

# 결과 조회
schedule = requests.get(
    "http://localhost:8000/api/output/operationplan/"
).json()
```

## 세영화학 적용

### 자원 매핑
```python
RESOURCES = {
    "1호기": {"type": "machine", "width_range": [400, 600]},
    "2호기": {"type": "machine", "width_range": [600, 800]},
    "3호기": {"type": "machine", "width_range": [800, 1200]},
}
```

### 셋업 시간 모델링
```python
SETUP_MATRIX = {
    ("PE-CLEAR", "PE-COLOR"): 30,  # 30분
    ("PE-COLOR", "PE-CLEAR"): 45,  # 45분 (세척 필요)
}
```

---

## Next References

- [PyVRP 가이드](pyvrp.md)
- [생산 계획 에이전트](../../.claude/agents/production-planner.md)
