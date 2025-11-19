WITH RECURSIVE directory_path AS (
    SELECT
        d.id,
        d.parent_id,
        d.name,
        CAST(d.name AS CHAR(1024)) AS full_path
    FROM measurement_directories d
    WHERE d.parent_id IS NULL
    UNION ALL
    SELECT
        child.id,
        child.parent_id,
        child.name,
        CONCAT(directory_path.full_path, '/', child.name) AS full_path
    FROM measurement_directories child
    JOIN directory_path ON directory_path.id = child.parent_id
)
SELECT
    mf.id AS file_id,
    mf.file_name,
    directory_path.full_path AS directory_path,
    mn.name AS node,
    mm.name AS module,
    mv.name AS version
FROM measurement_files mf
LEFT JOIN directory_path ON directory_path.id = mf.directory_id
LEFT JOIN measurement_nodes   mn ON mn.id = mf.node_id
LEFT JOIN measurement_modules mm ON mm.id = mf.module_id
LEFT JOIN measurement_versions mv ON mv.id = mf.version_id
ORDER BY directory_path.full_path, mf.file_name;
