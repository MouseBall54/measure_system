SELECT
    mf.id            AS file_id,
    mf.file_name,
    mf.post_time,
    mi.class_name,
    mi.measure_item_key,
    mmt.name         AS metric_name,
    mmt.unit         AS metric_unit,
    rmr.measurable,
    rmr.x_index,
    rmr.y_index,
    rmr.x_0,
    rmr.y_0,
    rmr.x_1,
    rmr.y_1,
    rmr.value
FROM raw_measurement_records rmr
JOIN measurement_files mf      ON mf.id = rmr.file_id
JOIN measurement_items mi      ON mi.id = rmr.item_id
JOIN measurement_metric_types mmt ON mmt.id = mi.metric_type_id
ORDER BY mf.id, mi.id, rmr.y_index, rmr.x_index;
