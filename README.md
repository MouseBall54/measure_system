# Measure System API

FastAPI + MySQL 기반 계측 데이터 관리 서버입니다. `sql/create_db.sql`에 정의된 스키마를 ORM 으로 구성하고, 파일/Raw 측정/통계 측정 엔드포인트 예제를 제공합니다.

## 요구 사항

- Python 3.11+
- MySQL 8.0 이상 (또는 호환 Aurora)
- 가상환경 권장: `python -m venv .venv && source .venv/bin/activate`

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env  # 연결 정보 수정
```

## 실행

```bash
uvicorn app.main:app --reload
```

기본 주소 `http://127.0.0.1:8000`에서 동작하며, `/docs`로 OpenAPI 문서를 확인할 수 있습니다.

## 기본 엔드포인트

- `POST /measurement-results`: 파일 + Raw + 통계 데이터를 한 번에 저장하는 트랜잭션 엔드포인트

## 주요 구성

- `app/core/config.py`: Pydantic Settings 기반 환경설정
- `app/core/db.py`: SQLAlchemy Async 엔진과 세션 의존성
- `app/models/`: SQL 스키마와 동일한 ORM 모델 패키지
- `app/api/routers/`: 도메인별 라우터(`measurement_results`, `health`)
- `app/main.py`: FastAPI 인스턴스 및 lifespan 훅에서 테이블 자동 생성
- `docs/db-schema.md`: 전체 DB 스키마/ER 다이어그램 개요

## 데이터베이스

초기 테이블은 앱 시작 시 자동 생성됩니다. 운영 단계에서는 Alembic 등을 이용해 마이그레이션을 관리하세요.

필요 시 `sql/create_db.sql`을 직접 실행하거나, 도메인 요구에 맞게 테이블을 수정한 뒤 ORM 모델을 업데이트하면 됩니다. 현재 스키마는 측정 결과를 Raw(`raw_measurement_records`)와 통계(`stat_measurements`, `stat_measurement_values`) 두 축으로 관리하고, 파일 메타(`measurement_nodes/modules/versions/directories`)를 정규화하여 노드·모듈·버전·디렉터리 정보를 재사용합니다. 또한 `file_name + parent_dir_0/1/2` 조합으로 자동 생성한 `file_hash`를 기반으로 중복 업로드 시 기존 파일 레코드를 갱신합니다.

## 테스트

```bash
pytest
```

`tests/test_routers.py`는 FastAPI 라우터 구조와 태그 구성을 검증합니다.
