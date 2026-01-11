# CLAUDE.md

> **공통 가이드라인**: `../.ssot/CLAUDE-COMMON.md` 참조

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

syc-ai - (프로젝트 설명 추가 예정)

## Commands

```bash
# 프로젝트별 명령어 추가 예정
```

## Architecture

(아키텍처 설명 추가 예정)

## Configuration

(설정 방법 추가 예정)

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
