WITH
best_models AS (
	SELECT
		model,
		policy,
		accuracy,
		MAX(f1_macro),
		f1_weighted,
		report
	FROM summary
	GROUP BY model
),

-- explode JSON and extract per-lithology recall
lithology_recall AS (
  SELECT
    model,
    je.key AS lithology,
    CAST(json_extract(je.value, '$.recall') AS REAL) AS recall,
	CAST(json_extract(je.value, '$.support') AS INTEGER) AS support
  FROM best_models
  JOIN json_each(report) AS je
  WHERE je.key NOT IN ('accuracy', 'macro avg', 'weighted avg', 'micro avg')
)

-- pivot top 3 into columns (extend CASEs if you increase top_k beyond 3)
SELECT
  lithology,
  support,
  ROUND(MAX(CASE WHEN lower(model) like 'lstm' THEN recall END),4) AS LSTM,
  ROUND(MAX(CASE WHEN lower(model) like 'bilstm' THEN recall END),4) AS BILSTM,
  ROUND(MAX(CASE WHEN lower(model) like 'decision tree' THEN recall END),4) AS DT,
  ROUND(MAX(CASE WHEN lower(model) like 'knn' THEN recall END),4) AS KNN,
  ROUND(MAX(CASE WHEN lower(model) like 'logistic regression' THEN recall END),4) AS LR,
  ROUND(MAX(CASE WHEN lower(model) like 'random forest' THEN recall END),4) AS RF,
  ROUND(MAX(CASE WHEN lower(model) like 'xgboost' THEN recall END),4) AS XGB
FROM lithology_recall
GROUP BY lithology
ORDER BY support DESC;
