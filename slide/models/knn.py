

import numpy as np
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.neighbors import KNeighborsClassifier
from sklearn.impute import SimpleImputer
import json
import pickle

logging = Logger()
logger = logging.get_logger()

class KNN(BaseModel):
    def __init__(self):
        super().__init__()
        self.imputer = None
    
    def train(self, data: ModelDataset) -> None:
        # Remove rows with missing target values
        train_mask = data.train_target.notna()

        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        
        # Impute missing values (KNN requires no missing values)
        self.imputer = SimpleImputer(strategy='median')
        train_data_imputed = self.imputer.fit_transform(train_data_clean)
        
        param_grid = {
            'n_neighbors': [3, 5, 7, 9, 11, 15],
            'weights': ['uniform', 'distance'],
            'metric': ['euclidean', 'manhattan', 'minkowski'],
            'p': [1, 2],  # Power parameter for Minkowski metric
            'algorithm': ['auto', 'ball_tree', 'kd_tree']
        }
        
        grid_search = GridSearchCV(
            estimator=KNeighborsClassifier(
                n_jobs=-1
            ),
            param_grid=param_grid,
            cv=3,  # 3-fold cross-validation
            scoring='accuracy',
            verbose=2,
            n_jobs=-1
        )
        grid_search.fit(train_data_imputed, train_target_clean)
        self.model = grid_search.best_estimator_
        logger.info(f"Best KNN parameters: {grid_search.best_params_}")
        
    
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