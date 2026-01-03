

import numpy as np
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import json
import pickle
import xgboost as xgb
import optuna
import gc

logging = Logger()
logger = logging.get_logger()

class XGBoost(BaseModel):
    def __init__(self):
        super().__init__()

    def __objective(self, trial: optuna.Trial, X_train, y_train):
        logger.info(f"Starting trial {trial.number} for hyperparameter optimization.")

        params = {
            "max_depth": trial.suggest_categorical("max_depth", [6, 8, 10]),
            "learning_rate": trial.suggest_categorical("learning_rate", [0.05, 0.1, 0.2]),
            "n_estimators": trial.suggest_categorical("n_estimators", [100, 200, 300]),
            "subsample": trial.suggest_categorical("subsample", [0.7, 0.8, 0.9]),
            "colsample_bytree": trial.suggest_categorical("colsample_bytree", [0.7, 0.8, 0.9]),
        }

        model = xgb.XGBClassifier(
            **params,
            random_state=42,
            tree_method="hist",
            missing=np.nan,
            n_jobs=20,  # avoid nested parallelism / memory blowups
            eval_metric="mlogloss",
        )

        try:
            score = cross_val_score(
                model,
                X_train,
                y_train,
                cv=3,
                scoring="accuracy",
                n_jobs=1,
            ).mean()
        finally:
            del model
            gc.collect()
            return score

    def train(self, data: ModelDataset) -> None:
        train_mask = data.train_target.notna()
        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]

        storage = "sqlite:///optuna_studies.db"

        study = optuna.create_study(
            direction="maximize",
            storage=storage,
            study_name="xgboost_optimization",
            load_if_exists=True,
        )

        study.optimize(
            lambda trial: self.__objective(trial, train_data_clean, train_target_clean),
            n_trials=50,
            gc_after_trial=True,
            show_progress_bar=True,
        )

        logger.info(f"Best hyperparameters: {study.best_params}")

        
    
    def predict(self, input_data: list) -> list:
        pass
        #X = input_data.features
        #return self.model.predict(X).tolist()
    
    def evaluate(self, data: ModelDataset) -> dict:
        # Remove rows with missing target values
        test_mask = data.test_target.notna()

        test_data_clean = data.test[test_mask]
        test_target_clean = data.test_target[test_mask]
        
        accuracy = self.model.score(test_data_clean, test_target_clean)

        predictions = self.model.predict(test_data_clean)
        self.results = {
            "accuracy": accuracy,
            "classification_report": classification_report(test_target_clean, predictions),
            "confusion_matrix": confusion_matrix(test_target_clean, predictions),
            "feature_importances": self.model.feature_importances_.tolist()
        }
        logger.info(f"Evaluation results: {json.dumps(self.results, indent=4)}")
        return self.results
    
    def save(self, file_path: str) -> None:
        if self.model is not None:
            with open(file_path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved to {file_path}")
            
        if self.results is not None:
            results_path = file_path + "_results_xgboost.json"
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=4)
            logger.info(f"Results saved to {results_path}")