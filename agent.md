# Agent Overview

## Project Concept
- FastAPI 기반 측정 데이터 관리 서버; `/measurement-results` 단일 POST로 파일/Raw/통계를 한 번에 저장
- MySQL 스키마를 정규화하여 노드/모듈/버전/디렉터리 메타 정보를 별도 테이블로 관리하고, Raw/Stat/Value 타입 테이블에 측정 데이터를 적재
- `file_hash = SHA256(parent_dir_0/1/2 + file_name)` 으로 중복 파일을 감지하여 기존 데이터를 삭제 후 갱신

## Core Components
- `app/api/routers/measurement_results.py`: 통합 인제스트 엔드포인트
  - natural key(metric name, value type, class name 등) 기반 lookup/생성
  - 기존 파일이 있으면 Raw/Stat/Class-count 제거 후 재삽입
- `app/models/`: SQLAlchemy ORM (measurement_files + helper tables + Raw/Stat/Value)
- `app/schemas/`: Pydantic 스키마; `class_counts` dict/list 허용, 예제 payload 제공
- `docs/db-schema.md`: ERD, `/measurement-results` 예시, Raw/Stat/파일 계층 SQL 예시
- `sql/*.sql`: 문서의 SQL 예제를 실행 가능한 파일로 분리

## Data Flow
1. `/measurement-results` 호출 → 파일 해시 계산 → 기존 파일 여부 판단
2. 노드/모듈/버전/디렉터리/metric/item/value/class를 natural key로 lookup/생성 후 FK 연결
3. Raw 측정값(`raw_measurement_records`)과 통계값(`stat_measurements`, `stat_measurement_values`), 클래스 카운트(`file_class_counts`) 저장
4. 전체 요청은 트랜잭션으로 처리되어 Atomic하게 반영

## Usage
- 실행: `uvicorn app.main:app --reload` (루트 `/`는 `/docs`로 redirect)
- Request/SQL 예시는 `docs/db-schema.md` & `sql/` 디렉터리 참고
