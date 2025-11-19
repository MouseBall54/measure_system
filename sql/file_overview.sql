WITH raw_stats AS (
    SELECT
        rmr.file_id,
        COUNT(*)          AS raw_points,
        AVG(rmr.value)    AS raw_value_avg
    FROM raw_measurement_records rmr
    GROUP BY rmr.file_id
),
stat_totals AS (
    SELECT
        sm.file_id,
        COUNT(DISTINCT sm.id) AS stat_sets
    FROM stat_measurements sm
    GROUP BY sm.file_id
)
SELECT
    mf.id             AS file_id,
    mf.file_name,
    mf.post_time,
    mn.name           AS node,
    mm.name           AS module,
    mv.name           AS version,
    COALESCE(raw_stats.raw_points, 0) AS raw_points,
    COALESCE(raw_stats.raw_value_avg, 0) AS raw_value_avg,
    COALESCE(stat_totals.stat_sets, 0) AS stat_sets
FROM measurement_files mf
LEFT JOIN measurement_nodes   mn ON mn.id = mf.node_id
LEFT JOIN measurement_modules mm ON mm.id = mf.module_id
LEFT JOIN measurement_versions mv ON mv.id = mf.version_id
LEFT JOIN raw_stats        ON raw_stats.file_id = mf.id
LEFT JOIN stat_totals      ON stat_totals.file_id = mf.id
ORDER BY mf.post_time DESC;
