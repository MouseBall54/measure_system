# Database Schema Overview

이 문서는 FastAPI 백엔드가 사용하는 MySQL 테이블 구조를 시각/텍스트로 정리합니다. raw 측정 데이터와 통계 측정 데이터가 `measurement_files`와 `measurement_items`를 중심으로 어떻게 연결되는지 한눈에 볼 수 있습니다.

## Entity Relationship Diagram

```mermaid
erDiagram
    MEASUREMENT_FILES ||--o{ RAW_MEASUREMENT_RECORDS : "file_id"
    MEASUREMENT_FILES ||--o{ STAT_MEASUREMENTS : "file_id"
    MEASUREMENT_FILES ||--o{ FILE_CLASS_COUNTS : "file_id"

    MEASUREMENT_METRIC_TYPES ||--o{ MEASUREMENT_ITEMS : "metric_type_id"
    MEASUREMENT_ITEMS ||--o{ RAW_MEASUREMENT_RECORDS : "item_id"
    MEASUREMENT_ITEMS ||--o{ STAT_MEASUREMENTS : "item_id"

    STAT_MEASUREMENTS ||--|{ STAT_MEASUREMENT_VALUES : "stat_measurement_id"
    STAT_VALUE_TYPES ||--o{ STAT_MEASUREMENT_VALUES : "value_type_id"

    CLASSES ||--o{ FILE_CLASS_COUNTS : "class_id"

    MEASUREMENT_FILES {
        BIGINT id PK
        DATETIME post_time
        DATE post_date
        TEXT file_path
        VARCHAR parent_dir_0
        VARCHAR parent_dir_1
        VARCHAR parent_dir_2
        VARCHAR file_name
        CHAR file_hash
        INT processing_ms
        ENUM status
        TIMESTAMP created_at
    }

    MEASUREMENT_METRIC_TYPES {
        BIGINT id PK
        VARCHAR name
        VARCHAR unit
        TINYINT is_active
    }

    MEASUREMENT_ITEMS {
        BIGINT id PK
        VARCHAR class_name
        VARCHAR measure_item_key
        BIGINT metric_type_id FK
        TINYINT is_active
    }

    RAW_MEASUREMENT_RECORDS {
        BIGINT id PK
        BIGINT file_id FK
        BIGINT item_id FK
        TINYINT measurable
        INT x_index
        INT y_index
        DOUBLE x_0
        DOUBLE y_0
        DOUBLE x_1
        DOUBLE y_1
        DOUBLE value
    }

    STAT_MEASUREMENTS {
        BIGINT id PK
        BIGINT file_id FK
        BIGINT item_id FK
        JSON extra_json
    }

    STAT_VALUE_TYPES {
        BIGINT id PK
        VARCHAR name
        TINYINT is_active
    }

    STAT_MEASUREMENT_VALUES {
        BIGINT stat_measurement_id PK FK
        BIGINT value_type_id PK FK
        DOUBLE value
    }

    CLASSES {
        BIGINT id PK
        VARCHAR name
        TINYINT is_active
    }

    FILE_CLASS_COUNTS {
        BIGINT file_id PK FK
        BIGINT class_id PK FK
        INT cnt
    }
```

## Table Summaries

### measurement_files
- 한 번의 측정/인퍼런스 파일 메타데이터 (`post_time`, `file_path`, 디렉터리/파일명 정보, 해시, 처리시간, 상태 등).
- Raw/통계/클래스 정보는 모두 이 테이블의 `id`(= `file_id`)를 FK로 참조합니다.

### measurement_metric_types
- `CD`, `LER` 등 측정 물리량과 단위를 정의합니다.
- 하나의 metric 은 여러 `measurement_items`를 가질 수 있습니다.

### measurement_items
- `class_name` + `measure_item_key` + `metric_type` 조합으로 측정 포인트를 식별합니다.
- Raw 샘플(`raw_measurement_records`)과 통계 헤더(`stat_measurements`)가 모두 `item_id`를 참조합니다.

### raw_measurement_records
- 실제 측정 샘플 데이터를 저장합니다.
- 주요 컬럼: `measurable`(True/False), `x_index`/`y_index`(격자 위치), `x_0`~`y_1`(좌표), `value`.
- `(file_id, item_id, x_index, y_index)`로 유니크 보장.

### stat_measurements & stat_measurement_values
- Raw 값에서 집계된 결과 세트(`stat_measurements`)와 각 통계 지표(`stat_measurement_values`).
- 예: `mean`, `stdev`, `p95` 등은 `stat_value_types`에서 정의.

### classes & file_class_counts
- Object detection/분류 결과에 사용할 수 있는 보조 테이블. 특정 파일이 어떤 클래스에 얼마나 매핑됐는지 `file_class_counts`에 저장합니다.

## 데이터 흐름 요약
1. 새로운 측정 파일을 수신하면 `measurement_files`에 메타데이터를 넣습니다.
2. 해당 작업에서 수집된 샘플을 `measurement_items`(class + item key)와 매칭해 `raw_measurement_records`에 저장합니다.
3. Raw 데이터를 요약한 통계는 `stat_measurements`에 헤더를 만들고, 각 통계 지표를 `stat_measurement_values`에 기록합니다.

이 구조로 Raw/통계 데이터를 분리해 저장하되, `measurement_files.id`와 `measurement_items.id`를 통해 일관된 조인을 유지할 수 있습니다.
