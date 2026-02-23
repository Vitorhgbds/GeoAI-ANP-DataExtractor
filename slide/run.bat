


REM ----------------- Raw Data -----------------

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/decision-tree.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/forest.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/logistic-regression.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/xgboost.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/lstm.yaml --db-name optuna_studies_size.db



REM ----------------- Clean Data -----------------

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/decision-tree.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/forest.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/logistic-regression.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/xgboost.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/lstm.yaml --db-name optuna_studies_size.db



REM ----------------- Presence Data -----------------

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/decision-tree.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/forest.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/logistic-regression.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/xgboost.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/lstm.yaml --db-name optuna_studies_size.db


REM ----------------- Rolling 5 Data -----------------
python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/decision-tree.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/forest.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/logistic-regression.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/xgboost.yaml --db-name optuna_studies_size.db


REM ----------------- Rolling 10 Data -----------------
python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/decision-tree.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/forest.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/logistic-regression.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/xgboost.yaml --db-name optuna_studies_size.db



REM ----------------- Problematic BILSTM models -----------------
python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/bilstm.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/bilstm.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/bilstm.yaml --db-name optuna_studies_size.db


REM ----------------- Problematic KNN models -----------------

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/knn.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/knn.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/knn.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/knn.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/knn.yaml --db-name optuna_studies_size.db