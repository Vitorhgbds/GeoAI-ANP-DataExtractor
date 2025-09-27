SELECT load_extension('regex0.dll');

WITH AGPWells AS (
    SELECT DISTINCT 
        replace(
            regex_replace(
                '([A-Za-z]*|^0[0-9])0+([A-Za-z0-9])',
                a.well,'$1$2'),
            " ", "") AS well
    FROM AGPLithology a
    WHERE a.well IS NOT NULL
),
LogsWells AS (
    SELECT 
        replace(well,"-","") AS well,
        url,
        path,
        name,
        errors,
        headers,
        basin,
        status
    FROM logs
)
SELECT 
    url,
    path,
    name,
    errors,
    headers,
    basin,
    status,
    well
FROM LogsWells 
    INNER JOIN AGPWells 
    USING(well)
WHERE LOWER(name) LIKE "%.dlis" 
    or LOWER(name) LIKE "%.lis" 
    or LOWER(name) LIKE "%.las";
    