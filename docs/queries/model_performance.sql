WITH base_table AS (
	SELECT
		trial_id,
		study_name,
		ROUND(MAX(CASE WHEN LOWER(key) LIKE 'accuracy' THEN value_json ELSE NULL END),5) AS accuracy,
		ROUND(MAX(CASE WHEN LOWER(key) LIKE 'f1_macro' THEN value_json ELSE NULL END),5) AS f1_macro,
		ROUND(MAX(CASE WHEN LOWER(key) LIKE 'f1_weighted' THEN value_json ELSE NULL END),5) AS f1_weighted,
		MAX(CASE WHEN LOWER(key) LIKE 'classification_report' THEN value_json ELSE NULL END) AS report,
		MAX(CASE WHEN LOWER(key) LIKE 'confusion_matrix' THEN value_json ELSE NULL END) AS confusion_matrix
	FROM 
		studies JOIN trials 
		USING(study_id) 
		JOIN trial_user_attributes 
		USING(trial_id)
	GROUP BY
		1,2
	ORDER BY 4 DESC
) SELECT 
	--study_name, 
	CASE 
		WHEN LOWER(study_name) LIKE '%knn%' THEN 'KNN'
		WHEN LOWER(study_name) LIKE '%BILSTM%' THEN 'BILSTM'
		WHEN LOWER(study_name) LIKE '%LSTM%' THEN 'LSTM'
		WHEN LOWER(study_name) LIKE '%logisticregression%new%' THEN 'Logistic Regression'
		WHEN LOWER(study_name) LIKE '%decisiontree%' THEN 'Decision Tree'
		WHEN LOWER(study_name) LIKE '%randomforest%' THEN 'Random Forest'
		WHEN LOWER(study_name) LIKE '%xgboost%' THEN 'XGBoost'
		ELSE study_name END AS model,
	CASE 
		WHEN LOWER(study_name) LIKE '%policy%raw%' THEN 'Raw'
		WHEN LOWER(study_name) LIKE '%policy%clean%' THEN 'Clean'
		WHEN LOWER(study_name) LIKE '%policy%presence%' THEN 'Presence'
		WHEN LOWER(study_name) LIKE '%policy%rolling%5%' THEN 'Rolling(5)'
		WHEN LOWER(study_name) LIKE '%policy%rolling%10%' THEN 'Rolling(10)'
		ELSE study_name END AS policy,
	accuracy, 
	MAX(f1_macro) AS f1_macro, 
	f1_weighted, 
	report,
	confusion_matrix
FROM base_table GROUP BY study_name ORDER BY 4 DESC;