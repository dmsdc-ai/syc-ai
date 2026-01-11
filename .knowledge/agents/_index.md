# Agents - 세영화학 스마트팩토리

프로젝트에서 사용하는 에이전트 목록입니다.

## 에이전트 목록

| 에이전트 | 역할 | 우선순위 | 상세 |
|---------|------|:--------:|------|
| production-planner | 생산 스케줄링 | 🥇 | [상세](../../.claude/agents/production-planner.md) |
| delivery-optimizer | 배송 경로 최적화 | 🥈 | [상세](../../.claude/agents/delivery-optimizer.md) |
| quality-monitor | 품질 모니터링 | 4순위 | (예정) |
| energy-analyzer | 에너지 분석 | 6순위 | (예정) |

## 에이전트 아키텍처

```
SupervisorAgent (스마트팩토리 총괄)
└── Clusters
    ├── ProductionCluster [PARALLEL]
    │   ├── production-planner    # 생산 일정 최적화
    │   └── quality-monitor       # 품질 모니터링
    ├── LogisticsCluster [SELECTIVE]
    │   └── delivery-optimizer    # 배송 경로 최적화
    └── AnalyticsCluster [OPTIONAL]
        └── energy-analyzer       # 에너지 효율 분석
```

## 실행 전략

| 전략 | 설명 | 적용 |
|------|------|------|
| PARALLEL | 동시 실행 | 다중 기계 모니터링 |
| SELECTIVE | 1개만 선택 | 최적 라인 선택 |
| SEQUENTIAL | 순차 실행 | 공정 순서 처리 |
| OPTIONAL | 조건부 실행 | 불량 발생 시 분석 |

## 트리거 조건

| 에이전트 | 트리거 키워드 |
|---------|---------------|
| production-planner | "생산 계획", "스케줄 최적화" |
| delivery-optimizer | "배송 계획", "배차 최적화" |
| quality-monitor | "품질 분석", "불량 추적" |
| energy-analyzer | "에너지 분석", "kWh 최적화" |

---

Parent: [_index.md](../_index.md)

## Next References

- [생산 스케줄러](../../.claude/agents/production-planner.md)
- [배송 최적화](../../.claude/agents/delivery-optimizer.md)
- [도구 목록](../tools/_index.md)
