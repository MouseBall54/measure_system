-- =========================================
-- 공통 설정
-- =========================================
SET NAMES utf8mb4;
SET time_zone = '+09:00';

-- 필요 시
-- SET FOREIGN_KEY_CHECKS = 0;

-- =========================================
-- 1) 기존 테이블 삭제 (역순)
-- =========================================
DROP TABLE IF EXISTS file_class_counts;
DROP TABLE IF EXISTS stat_measurement_values;
DROP TABLE IF EXISTS stat_measurements;
DROP TABLE IF EXISTS raw_measurement_records;
DROP TABLE IF EXISTS measurement_items;
DROP TABLE IF EXISTS stat_value_types;
DROP TABLE IF EXISTS measurement_metric_types;
DROP TABLE IF EXISTS measurement_files;
DROP TABLE IF EXISTS classes;

-- =========================================
-- =========================================
-- 2) 측정 파일(인퍼런스 단위)
--   - parent_dir_0: 바로 상위 폴더
--   - parent_dir_1: 그 상위 폴더
--   - parent_dir_2: 최상위 그룹 폴더
-- =========================================
CREATE TABLE measurement_files (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  post_time      DATETIME(6) NOT NULL,                 -- UTC 권장
  post_date      DATE AS (DATE(post_time)) STORED,     -- 생성열

  file_path      TEXT NOT NULL,                        -- 절대 경로
  parent_dir_0   VARCHAR(255) NOT NULL,                -- 예: "img"
  parent_dir_1   VARCHAR(255) NULL,                    -- 예: "wafer123"
  parent_dir_2   VARCHAR(255) NULL,                    -- 예: "2025-11-12" or "LINE_A"

  file_name      VARCHAR(255) NOT NULL,                -- basename

  file_hash      CHAR(64) NULL,                        -- 내용 기반 SHA-256
  processing_ms  INT NULL,
  status         ENUM('OK','FAIL') NOT NULL DEFAULT 'OK',
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uk_measurement_files_hash (file_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- =========================================
-- 3-A) 측정 항목(물리량) 정의
--   - 예: ("CD","nm"), ("LER","a.u.")
-- =========================================
CREATE TABLE measurement_metric_types (
  id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(64) NOT NULL,          -- "CD","LER","THICKNESS"...
  unit      VARCHAR(32) NULL,              -- "nm","a.u."
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_metric_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- =========================================
-- 3-B) 측정 위치/포지션 정의
--   - class_name + measure_item_key 조합으로 구분
-- =========================================
CREATE TABLE measurement_items (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  class_name      VARCHAR(64) NOT NULL,
  measure_item_key VARCHAR(64) NOT NULL,
  metric_type_id  BIGINT NOT NULL,
  is_active       TINYINT(1) NOT NULL DEFAULT 1,

  CONSTRAINT fk_items_metric_type
    FOREIGN KEY (metric_type_id) REFERENCES measurement_metric_types(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_item_class_key (class_name, measure_item_key, metric_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- =========================================
-- 3-C) Raw 측정 데이터 (파일 × 포지션 × 샘플)
-- =========================================
CREATE TABLE raw_measurement_records (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  file_id        BIGINT NOT NULL,
  item_id        BIGINT NOT NULL,
  measurable     TINYINT(1) NOT NULL DEFAULT 1,
  x_index        INT NOT NULL,
  y_index        INT NOT NULL,
  x_0            DOUBLE NOT NULL,
  y_0            DOUBLE NOT NULL,
  x_1            DOUBLE NOT NULL,
  y_1            DOUBLE NOT NULL,
  value          DOUBLE NOT NULL,

  CONSTRAINT fk_raw_file
    FOREIGN KEY (file_id) REFERENCES measurement_files(id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_raw_item
    FOREIGN KEY (item_id) REFERENCES measurement_items(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_raw_file_item_xy (file_id, item_id, x_index, y_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- 3-D) 통계 측정 헤더 (파일 × 포지션)
-- =========================================
CREATE TABLE stat_measurements (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  file_id        BIGINT NOT NULL,
  item_id        BIGINT NOT NULL,

  CONSTRAINT fk_stat_file
    FOREIGN KEY (file_id) REFERENCES measurement_files(id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_stat_item
    FOREIGN KEY (item_id) REFERENCES measurement_items(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  UNIQUE KEY uk_stat_file_item (file_id, item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- =========================================
-- 3-E) 통계 값 타입 (AVG, STD, ...)
-- =========================================
CREATE TABLE stat_value_types (
  id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(32) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_stat_value_type_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- =========================================
-- 3-F) 통계 측정 값
--   - (stat_measurement_id × value_type_id) → value
-- =========================================
CREATE TABLE stat_measurement_values (
  stat_measurement_id BIGINT NOT NULL,
  value_type_id       BIGINT NOT NULL,
  value               DOUBLE NOT NULL,

  CONSTRAINT fk_stat_values_header
    FOREIGN KEY (stat_measurement_id) REFERENCES stat_measurements(id)
    ON DELETE CASCADE ON UPDATE CASCADE,

  CONSTRAINT fk_stat_values_type
    FOREIGN KEY (value_type_id) REFERENCES stat_value_types(id)
    ON DELETE RESTRICT ON UPDATE CASCADE,

  PRIMARY KEY (stat_measurement_id, value_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- 4) Object Detection 클래스 마스터
--   - 예: "P1","P2","P3"
-- =========================================
CREATE TABLE classes (
  id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  name      VARCHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uk_classes_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =========================================
-- 5) 파일별 클래스 카운트
--   - 예: file_id=10, "P1" → 500
-- =========================================
CREATE TABLE file_class_counts (
  file_id   BIGINT NOT NULL,
  class_id  BIGINT NOT NULL,
  cnt       INT    NOT NULL,

  PRIMARY KEY (file_id, class_id),

  CONSTRAINT fk_fcc_file  FOREIGN KEY (file_id) REFERENCES measurement_files(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_fcc_class FOREIGN KEY (class_id) REFERENCES classes(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 필요 시
-- SET FOREIGN_KEY_CHECKS = 1;
