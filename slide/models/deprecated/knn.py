

from sklearn.metrics import accuracy_score
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.neighbors import KNeighborsClassifier
from sklearn.impute import SimpleImputer
import json
import pickle
import optuna
import gc

logging = Logger()
logger = logging.get_logger()

class KNN(BaseModel):
    def __init__(self):
        super().__init__()
        self.imputer = None

    def __objective(self, trial: optuna.Trial, X_train, y_train, x_test, y_test):
        logger.info(f"Starting trial {trial.number} for hyperparameter optimization.")
        
        # Suggest hyperparameters
        params = {
        "n_neighbors": trial.suggest_int("n_neighbors", 3, 15, step=2),
        "weights": trial.suggest_categorical("weights", ["uniform", "distance"]),
        "p": trial.suggest_int("p", 1, 2),  # Only relevant for Minkowski metric
        "algorithm": trial.suggest_categorical("algorithm", ["auto", "ball_tree", "kd_tree"])
        }
        # Create the model with suggested hyperparameters
        model = KNeighborsClassifier(
            **params,
            metric="minkowski",
            n_jobs=25
        )
        try:
            logger.info(f"Starting training KNN with params: {params}")
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
        test_mask = data.test_target.notna()

        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        test_data_clean = data.test[test_mask]
        test_target_clean = data.test_target[test_mask]
        
        # Impute missing values (KNN requires no missing values)
        self.imputer = SimpleImputer(strategy='median')
        train_data_imputed = self.imputer.fit_transform(train_data_clean)
        test_data_imputed = self.imputer.transform(test_data_clean)
        
        # Specify the SQLite database file
        storage = "sqlite:///optuna_studies.db"
        
        # Create or load an Optuna study
        study = optuna.create_study(direction="maximize", storage=storage, study_name="knn_optimization", load_if_exists=True)
        study.optimize(lambda trial: self.__objective(trial, train_data_imputed, train_target_clean, test_data_imputed, test_target_clean), n_trials=50, gc_after_trial=True)
        
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
        
        # Impute missing values using the fitted imputer
        test_data_imputed = self.imputer.transform(test_data_clean)
        
        accuracy = self.model.score(test_data_imputed, test_target_clean)

        predictions = self.model.predict(test_data_imputed)
        self.results = {
            "accuracy": accuracy,
            "classification_report": classification_report(test_target_clean, predictions),
            "confusion_matrix": confusion_matrix(test_target_clean, predictions)
        }
        logger.info(f"Evaluation results: {json.dumps(self.results, indent=4)}")
        return self.results
    
    def save(self, file_path: str) -> None:
        if self.model is not None and self.imputer is not None:
            # Save both model and imputer
            model_data = {
                'model': self.model,
                'imputer': self.imputer
            }
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"Model and imputer saved to {file_path}")
            
        if self.results is not None:
            results_path = file_path + "_results_knn.json"
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=4)
            logger.info(f"Results saved to {results_path}")