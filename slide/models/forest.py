

from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
import json
import pickle

logging = Logger()
logger = logging.get_logger()

class RandomForest(BaseModel):
    def __init__(self):
        super().__init__()
    
    def train(self, data: ModelDataset) -> None:
        # Remove rows with missing target values
        train_mask = data.train_target.notna()

        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        
        param_grid = {
            'n_estimators': [50, 100, 200, 300],           # Number of trees
            'max_depth': [15, 20, 25, None],           # Tree depth (None = unlimited)
            'min_samples_split': [10, 20, 50],         # Min samples to split a node
            'min_samples_leaf': [5, 10, 20],           # Min samples in leaf nodes
            'max_features': ['sqrt', 'log2', 0.5],     # Features considered for split
            'max_samples': [0.7, 0.8, None],           # Bootstrap sample size (None = use all)
            'class_weight': ['balanced', None]         # Handle class imbalance
        }
        
        grid_search = GridSearchCV(
            estimator=RandomForestClassifier(
                random_state=42,
                n_jobs=-1,
                bootstrap=True,      # Enable bootstrap sampling
                oob_score=True,      # Out-of-bag score for validation
                ),
            param_grid=param_grid,
            cv=3,
            scoring='accuracy',
            verbose=1,
            n_jobs=-1
        )
        grid_search.fit(train_data_clean, train_target_clean)
        self.model = grid_search.best_estimator_
        logger.info(f"Best Random Forest parameters: {grid_search.best_params_}")
        
    
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