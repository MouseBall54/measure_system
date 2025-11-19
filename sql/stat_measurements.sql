SELECT
    mf.id             AS file_id,
    mf.file_name,
    mi.class_name,
    mi.measure_item_key,
    mmt.name          AS metric_name,
    mmt.unit          AS metric_unit,
    svt.name          AS stat_value_type,
    smv.value
FROM stat_measurements sm
JOIN measurement_files mf      ON mf.id = sm.file_id
JOIN measurement_items mi      ON mi.id = sm.item_id
JOIN measurement_metric_types mmt ON mmt.id = mi.metric_type_id
JOIN stat_measurement_values smv ON smv.stat_measurement_id = sm.id
JOIN stat_value_types svt    ON svt.id = smv.value_type_id
ORDER BY mf.id, mi.id, svt.name;
