# 도구 선택 규칙

세영화학 스마트팩토리에서 사용하는 핵심 도구들.

## 도구 점수표

| 분야 | 도구 | 점수 | 용도 |
|------|------|:----:|------|
| 생산 계획 | frePPLe | 8.55 | APS 스케줄링 |
| 배송 최적화 | PyVRP | 9.00 | VRP 솔버 |
| 배송 최적화 | OR-Tools | 8.95 | VRP 대안 |
| IoT | ThingsBoard | 8.60 | 데이터 수집 |
| PLC 통신 | opcua-asyncio | 8.15 | OPC-UA |
| 모니터링 | Libre/Grafana | 8.45 | 대시보드 |

## 도구 선택 규칙

### 생산 스케줄링
```
생산 계획 요청 → frePPLe
  └─ 실패 시 → Python 휴리스틱
```

### 배송 최적화
```
배송 경로 요청 → PyVRP (기본)
  └─ 특수 제약 시 → OR-Tools
```

### 데이터 수집
```
PLC 데이터 → opcua-asyncio
  └─ OPC-UA 미지원 시 → Modbus (pymodbus)
```

## 상세 가이드

| 도구 | 가이드 |
|------|--------|
| frePPLe | [frepple.md](frepple.md) |
| PyVRP | [pyvrp.md](pyvrp.md) |
| OR-Tools | [ortools.md](ortools.md) |
| opcua-asyncio | [opcua.md](opcua.md) |

---

## Next References

- [frePPLe 상세](frepple.md)
- [PyVRP 상세](pyvrp.md)
- [에이전트 목록](../agents/_index.md)
