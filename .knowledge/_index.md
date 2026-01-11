# Knowledge Base - 세영화학 스마트팩토리

이 프로젝트의 지식 베이스입니다.
단계적 탐색 기법(Hierarchical Navigation Pattern)을 따릅니다.

## 규칙

1. **한 번에 1개 파일만** 읽어 Context window 효율화
2. **100줄 이하** 모든 파일은 atomic size 유지
3. **Next References** 각 파일 하단의 링크로 탐색

## 카테고리

### 🏭 공장 도메인
| 카테고리 | 설명 | 경로 |
|---------|------|------|
| machines | 설비별 최적 설정값, 스펙 | [machines/_index.md](machines/_index.md) |
| products | 제품별 생산 조건 | [products/_index.md](products/_index.md) |
| errors | 설비 에러 패턴 및 해결책 | [errors/_index.md](errors/_index.md) |
| costs | 원료/에너지 비용 정보 | [costs/_index.md](costs/_index.md) |

### 🤖 시스템
| 카테고리 | 설명 | 경로 |
|---------|------|------|
| agents | 에이전트 사용법 | [agents/_index.md](agents/_index.md) |
| tools | 도구 선택 규칙 (frePPLe, PyVRP 등) | [tools/_index.md](tools/_index.md) |
| prompts | 프롬프트 템플릿 | [prompts/_index.md](prompts/_index.md) |

## 빠른 참조

| 상황 | 경로 |
|------|------|
| 압출기 설정값 확인 | `machines/extruder.md` |
| 권취기 설정값 확인 | `machines/winder.md` |
| 제품 생산 조건 | `products/{product-code}.md` |
| 설비 에러 해결 | `errors/{machine-type}/` |
| 생산 스케줄링 도구 | `tools/frepple.md` |
| 배송 최적화 도구 | `tools/pyvrp.md` |

## 자동 캡처

개발 중 발생하는 이벤트는 자동으로 캡처됩니다:
- **설비 에러** → `errors/{machine}/`
- **최적 설정값** → `machines/` (성공 조건 기록)
- **비용 데이터** → `costs/daily/` (에너지, 원료)

---

## Next References

- [설비 정보](machines/_index.md)
- [제품별 조건](products/_index.md)
- [에러 해결](errors/_index.md)
- [도구 가이드](tools/_index.md)
