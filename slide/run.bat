

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/forest.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/logistic-regression.yaml --db-name REM optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/xgboost.yaml --db-name optuna_studies_size.db


REM ----------------- Rolling 10 Data -----------------
REM mkdir -p logs/rolling-10
REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/decision-tree.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/forest.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/logistic-regression.yaml --db-name REM optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/xgboost.yaml --db-name optuna_studies_size.db



REM ----------------- Problematic BILSTM models -----------------
python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/lstm.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/bilstm.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/bilstm.yaml --db-name optuna_studies_size.db

python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/bilstm.yaml --db-name optuna_studies_size.db


REM ----------------- Problematic KNN models -----------------

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/raw/knn.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/clean/knn.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/presence/knn.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-5/knn.yaml --db-name optuna_studies_size.db

REM python .\run.py --log-level DEBUG --model-config models/configs/final-models/rolling-10/knn.yaml --db-name optuna_studies_size.db