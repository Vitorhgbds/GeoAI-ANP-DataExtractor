WITH trial_metrics AS (
  SELECT
    t.trial_id,
    s.study_name,
    MAX(CASE WHEN LOWER(ua.key) = 'f1_macro' THEN CAST(ua.value_json AS REAL) END) AS f1_macro,
    MAX(CASE WHEN LOWER(ua.key) = 'classification_report' THEN ua.value_json END) AS report
  FROM studies s
  JOIN trials t USING (study_id)
  JOIN trial_user_attributes ua USING (trial_id)
  WHERE t.state = 'COMPLETE'
  GROUP BY t.trial_id, s.study_name
),
best_per_study AS (
  SELECT *
  FROM (
    SELECT
      tm.*,
      ROW_NUMBER() OVER (PARTITION BY tm.study_name ORDER BY tm.f1_macro DESC) AS rn
    FROM trial_metrics tm
    WHERE tm.f1_macro IS NOT NULL AND tm.report IS NOT NULL
  )
  WHERE rn = 1
)
SELECT
  study_name,
  trial_id,
  ROUND(f1_macro, 6) AS f1_macro
FROM best_per_study
ORDER BY f1_macro DESC;
