

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression as LogisticRegressionClassifier
from sklearn.metrics import accuracy_score
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix
import json
import pickle
import optuna
import gc

logging = Logger()
logger = logging.get_logger()

class LogisticRegression(BaseModel):
    def __init__(self):
        super().__init__()
        
    def __objective(self, trial: optuna.Trial, X_train, y_train, x_test, y_test):
        logger.info(f"Starting trial {trial.number} for hyperparameter optimization.")
        
        # Suggest hyperparameters
        params = {
            "max_iter": trial.suggest_categorical("max_iter", [100, 200, 300, 400, 500]),
            "C": trial.suggest_float("C", 0.01, 10.0, log=True)
            
        }
        
        try:
            # Create the model with suggested hyperparameters
            model = LogisticRegressionClassifier(
                **params,
                verbose=1,
                random_state=42,
                n_jobs=25
            )
            
            logger.info(f"Training the model")
            model.fit(X_train, y_train)
            
            logger.info("Calculating training vs test accuracy")
            # Make predictions
            train_predictions = model.predict(X_train)
            test_predictions = model.predict(x_test)

            # Calculate accuracies
            train_accuracy = accuracy_score(y_train, train_predictions)
            test_accuracy = accuracy_score(y_test, test_predictions)
        
            trial.set_user_attr("train_accuracy", float(train_accuracy))
            trial.set_user_attr("test_accuracy", float(test_accuracy))
            
            report = classification_report(y_test, test_predictions, output_dict=True)
            trial.set_user_attr("classification_report", report)
            # Evaluate the model using cross-validation
            return float(test_accuracy)
        finally:
            del model
            gc.collect()
    
    def train(self, data: ModelDataset) -> None:
        # Remove rows with missing target values
        train_mask = data.train_target.notna()
        
        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        
        test_mask = data.test_target.notna()
        test_data_clean = data.test[test_mask]
        test_target_clean = data.test_target[test_mask]
        
        # Impute missing values (KNN requires no missing values)
        self.imputer = SimpleImputer(strategy='median')
        train_data_imputed = self.imputer.fit_transform(train_data_clean)
        test_data_imputed = self.imputer.transform(test_data_clean)
        
        # Specify the SQLite database file
        storage = "sqlite:///optuna_studies.db"
    
        study = optuna.create_study(direction="maximize", storage=storage, study_name="LogisticRegressionOptimization", load_if_exists=True)
        study.optimize(lambda trial: self.__objective(trial, train_data_imputed, train_target_clean, test_data_imputed, test_target_clean), n_trials=20, gc_after_trial=True)
        
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
            "oob_score": self.model.oob_score_ if hasattr(self.model, 'oob_score_') else None,
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
            results_path = file_path + "_results_forest.json"
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=4)
            logger.info(f"Results saved to {results_path}")