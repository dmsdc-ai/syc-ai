# 제품별 생산 조건

제품 코드별 생산 조건 및 최적 설정값.

## 제품 분류

| 분류 | 설명 | 예시 |
|------|------|------|
| PE 필름 | 폴리에틸렌 필름 | 일반, 산업용 |
| 특수 필름 | 특수 용도 | 방습, 정전기 방지 |

## 제품 조건 템플릿

각 제품 파일은 다음 구조를 따름:

```yaml
product_code: "XXX-001"
name: "제품명"
width_mm: 600
thickness_um: 50
machine_compatible: ["1호기", "2호기"]
optimal_settings:
  zone1_temp: 180
  zone2_temp: 200
  line_speed: 30
quality_criteria:
  max_thickness_variation: 5%
  max_defect_rate: 0.5%
```

## 폭 그룹

| 그룹 | 폭 범위 | 호환 기계 |
|------|---------|----------|
| A | 400-600mm | 1호기, 2호기 |
| B | 600-800mm | 2호기, 3호기 |
| C | 800-1200mm | 3호기 |

## 혼합 생산 규칙

- 동일 폭 그룹 내 혼합 가능
- 최대 4개 품목까지 동시 생산
- 색상 전환 시 순서 고려 (밝은색 → 어두운색)

---

## Next References

- [설비 호환성](../machines/_index.md)
- [생산 스케줄링 도구](../tools/frepple.md)
