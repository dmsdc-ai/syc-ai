# CLAUDE.md

> **공통 가이드라인**: `../.ssot/CLAUDE-COMMON.md` 참조

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**syc-ai** - 세영화학 스마트팩토리 프로젝트

세영화학 공장의 데이터 기반 운영 최적화 시스템 구축 프로젝트.
3형제가 각자의 전문성을 활용하여 진행.

### 최종 목표
> **세영화학의 스마트 팩토리화**
> - 데이터 기반 의사결정 체계 구축
> - 생산/배송/품질 최적화
> - 장기적으로 에너지 효율화

### 팀 구성
| 역할 | 담당 | 전문성 |
|------|------|--------|
| 시스템/임베디드 자문 | 덕영 | PLC/설비, 아키텍처 리뷰 (주말 참여) |
| 현장 CEO / 도메인 오너 | 준영 | 10년+ 현장 경험, Ground Truth |
| 총괄 아키텍트 / 최적화 | 기영 | DP/PMP 최적화, 빅데이터 분석 |

## Commands

```bash
# 생산 스케줄링 실행
python scripts/optimizers/production_scheduler.py

# 배송 경로 최적화
python scripts/optimizers/delivery_router.py

# PLC 데이터 수집 테스트
python scripts/connectors/opcua_client.py --test

# frePPLe 연동
python scripts/project/skills/frepple_wrapper.py
```

## Architecture

```
현장 (Shop Floor)
  PLC/센서 → OPC-UA (opcua-asyncio) → MQTT → ThingsBoard
           ↓
데이터 레이어
  InfluxDB (시계열) + PostgreSQL (마스터 데이터)
           ↓
애플리케이션 레이어
  생산계획: frePPLe (8.55점)
  모니터링: Libre/Grafana (8.45점)
  배송최적화: PyVRP (9.00점)
  분석: Python (Pandas, Scikit-learn)
           ↓
시각화/UI
  Grafana 대시보드 + 웹 UI
```

## Tech Stack

| 분야 | 도구 | 점수 |
|------|------|:----:|
| 생산 계획 | frePPLe | 8.55 |
| 배송 최적화 | PyVRP + OR-Tools | 9.00 |
| IoT 플랫폼 | ThingsBoard | 8.60 |
| PLC 통신 | opcua-asyncio | 8.15 |
| 모니터링 | Libre (Grafana) | 8.45 |
| DB | InfluxDB + PostgreSQL | - |

## Configuration

### 환경 변수
```bash
# .env 파일
INFLUXDB_URL=http://localhost:8086
POSTGRES_URL=postgresql://localhost:5432/syc
THINGSBOARD_URL=http://localhost:9090
FREPPLE_API_URL=http://localhost:8000/api
```

### PLC 연결 설정
```python
# scripts/connectors/config.py
PLC_CONFIG = {
    "protocol": "opc-ua",  # 또는 "modbus"
    "endpoint": "opc.tcp://192.168.1.100:4840",
    "polling_interval_ms": 1000
}
```

## 핵심 과제 우선순위

| 순위 | 과제 | 예상 효과 |
|:----:|------|----------|
| 🥇 | 생산 일정 최적화 | 납기 준수율 ↑, 셋업 손실 ↓ |
| 🥈 | 배송 스케줄링 | 배송비용 15~25% 절감 |
| 🥉 | 데이터 수집 기반 | 모든 분석의 전제조건 |
| 4 | 불량 원인 추적 | 불량률 감소 |
| 5 | 작업자 의존도 감소 | 품질 균일화 |
| 6 | 에너지 최적화 | kWh/ton 절감 |

## 도메인 용어

| 용어 | 설명 |
|------|------|
| 폭 | 필름 너비 (mm) |
| 롤 | 생산 단위 (1사이클 = 2롤) |
| 셋업 | 품목 전환 시 설정 변경 |
| 혼합생산 | 여러 품목 동시 생산 |
| 폭 활용률 | 다이 폭 대비 실제 사용률 |

## 생산 스케줄링 제약조건

```python
CONSTRAINTS = {
    "cycle_structure": "1사이클 = 2롤",
    "mixed_production": True,  # 혼합생산 우선
    "max_items_per_machine": 4,  # 기계별 조합 품목 수
    "setup_time_minutes": 30,  # 평균 셋업 시간
}
```

## Knowledge Base

프로젝트 지식 베이스는 `.knowledge/` 폴더에 있습니다.

```bash
# 진입점
cat .knowledge/_index.md
```

### 탐색 규칙

1. **한 번에 1개 파일만** 읽어 Context window 효율화
2. **100줄 이하** 모든 파일은 atomic size 유지
3. **Next References** 각 파일 하단의 링크로 탐색

### 빠른 참조

| 상황 | 경로 |
|-----|------|
| 에이전트 사용법 | `.knowledge/agents/_index.md` |
| 에러 해결 | `.knowledge/errors/_index.md` |
| 도구 선택 | `.knowledge/tools/_index.md` |
| 비용 확인 | `.knowledge/costs/_index.md` |
