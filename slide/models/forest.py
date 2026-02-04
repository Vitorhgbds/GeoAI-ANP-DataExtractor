from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
import json
import pickle
import gc

logging = Logger()
logger = logging.get_logger()


class RandomForest(BaseModel):
    def __init__(
        self,
        n_estimators: int | None = None,
        min_samples_split: int | None = None,
        min_samples_leaf: int | None = None,
        max_features: str | None = None,
        max_samples: float | None = None,
        bootstrap: bool = True,
        random_state: int = 42,
        n_jobs: int = -1,
        *args, **kwargs):
        """
        Initialize Random Forest model with fixed parameters.
        
        Args:
            n_estimators: Number of trees in the forest
            min_samples_split: Minimum samples required to split a node
            min_samples_leaf: Minimum samples required at a leaf node
            max_features: Number of features to consider at each split ('sqrt', 'log2', or float)
            max_samples: Fraction of samples to use for training each tree
            bootstrap: Whether bootstrap samples are used when building trees
            random_state: Random seed for reproducibility
            n_jobs: Number of CPU cores to use (-1 = all cores)
        """
        super().__init__()
        self.n_estimators = n_estimators
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.max_samples = max_samples
        self.bootstrap = bootstrap
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.model = None
        self.imputer = None
        self.label_encoder_mapping = None
        logger.info(
            f"Initialized RandomForest with n_estimators={n_estimators}, "
            f"min_samples_split={min_samples_split}, max_features={max_features}"
        )

    def train(self, data: ModelDataset) -> None:
        """
        Train Random Forest model on data.
        
        Args:
            data: ModelDataset with train/test features and targets
        """
        logger.info("Training Random Forest model...")
        
        # Remove rows with missing target values
        train_mask = data.train_target.notna()
        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        
        # Impute missing values
        self.imputer = SimpleImputer(strategy='median')
        train_data_imputed = self.imputer.fit_transform(train_data_clean)
        
        # Create label encoding for non-numeric targets
        if train_target_clean.dtype == 'object':
            unique_labels = sorted(train_target_clean.unique())
            self.label_encoder_mapping = {label: idx for idx, label in enumerate(unique_labels)}
            train_target_encoded = train_target_clean.map(self.label_encoder_mapping)
        else:
            train_target_encoded = train_target_clean
        
        logger.debug(f"Train data shape: {train_data_imputed.shape}")
        logger.debug(f"Train target shape: {train_target_encoded.shape}")
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            max_features=self.max_features,
            max_samples=self.max_samples,
            bootstrap=self.bootstrap,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            verbose=1
        )
        
        self.model.fit(train_data_imputed, train_target_encoded)
        
        # Evaluate on training data
        train_preds = self.model.predict(train_data_imputed)
        train_acc = accuracy_score(train_target_encoded, train_preds)
        train_f1 = f1_score(train_target_encoded, train_preds, average='macro', zero_division=0)
        
        logger.info(f"Training Accuracy: {train_acc:.4f}")
        logger.info(f"Training F1 (macro): {train_f1:.4f}")
        
        # Evaluate on test data if available
        test_mask = data.test_target.notna()
        if test_mask.sum() > 0:
            test_data_clean = data.test[test_mask]
            test_target_clean = data.test_target[test_mask]
            
            test_data_imputed = self.imputer.transform(test_data_clean)
            
            if self.label_encoder_mapping:
                test_target_encoded = test_target_clean.map(self.label_encoder_mapping)
            else:
                test_target_encoded = test_target_clean
            
            test_preds = self.model.predict(test_data_imputed)
            test_acc = accuracy_score(test_target_encoded, test_preds)
            test_f1 = f1_score(test_target_encoded, test_preds, average='macro', zero_division=0)
            
            logger.info(f"Test Accuracy: {test_acc:.4f}")
            logger.info(f"Test F1 (macro): {test_f1:.4f}")
        
        logger.info("Training complete!")

    def predict(self, input_data) -> list:
        """
        Predict labels for input data.
        
        Args:
            input_data: DataFrame with same features as training data
            
        Returns:
            List of predicted labels
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        if self.imputer is None:
            raise ValueError("Imputer not fitted. Call train() first or load a trained model.")
        
        # Impute missing values
        data_imputed = self.imputer.transform(input_data)
        
        # Make predictions
        predictions_encoded = self.model.predict(data_imputed)
        
        # Decode labels if needed
        if self.label_encoder_mapping:
            reverse_mapping = {v: k for k, v in self.label_encoder_mapping.items()}
            predictions = [reverse_mapping[pred] for pred in predictions_encoded]
        else:
            predictions = predictions_encoded.tolist()
        
        return predictions

    def evaluate(self, data: ModelDataset) -> dict:
        """
        Evaluate model on test data.
        
        Args:
            data: ModelDataset with test features and targets
            
        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        if self.imputer is None:
            raise ValueError("Imputer not fitted. Call train() first or load a trained model.")
        
        # Remove rows with missing target values
        test_mask = data.test_target.notna()
        test_data_clean = data.test[test_mask]
        test_target_clean = data.test_target[test_mask]
        
        # Impute missing values
        test_data_imputed = self.imputer.transform(test_data_clean)
        
        # Encode targets if needed
        if self.label_encoder_mapping:
            test_target_encoded = test_target_clean.map(self.label_encoder_mapping)
        else:
            test_target_encoded = test_target_clean
        
        logger.debug(f"Test data shape: {data.test.shape}")
        logger.debug(f"Test target shape: {data.test_target.shape}")
        
        # Make predictions
        predictions_encoded = self.model.predict(test_data_imputed)
        
        # Decode predictions for reporting
        if self.label_encoder_mapping:
            reverse_mapping = {v: k for k, v in self.label_encoder_mapping.items()}
            predictions_decoded = [reverse_mapping[pred] for pred in predictions_encoded]
            targets_decoded = [reverse_mapping[target] for target in test_target_encoded]
        else:
            predictions_decoded = predictions_encoded
            targets_decoded = test_target_encoded
        
        # Calculate metrics
        accuracy = accuracy_score(test_target_encoded, predictions_encoded)
        f1_macro = f1_score(test_target_encoded, predictions_encoded, average='macro', zero_division=0)
        f1_weighted = f1_score(test_target_encoded, predictions_encoded, average='weighted', zero_division=0)
        report = classification_report(targets_decoded, predictions_decoded, output_dict=True)
        cm = confusion_matrix(targets_decoded, predictions_decoded)
        
        # Get feature importances
        feature_importances = self.model.feature_importances_.tolist()
        oob_score = self.model.oob_score_ if hasattr(self.model, 'oob_score_') else None
        
        results = {
            "accuracy": float(accuracy),
            "f1_macro": float(f1_macro),
            "f1_weighted": float(f1_weighted),
            "oob_score": float(oob_score) if oob_score is not None else None,
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "feature_importances": feature_importances
        }
        
        logger.info(f"Test Accuracy: {accuracy:.4f}")
        logger.info(f"Test F1 (macro): {f1_macro:.4f}")
        logger.info(f"Test F1 (weighted): {f1_weighted:.4f}")
        if oob_score is not None:
            logger.info(f"OOB Score: {oob_score:.4f}")
        logger.info(f"Classification Report:\n{classification_report(targets_decoded, predictions_decoded)}")
        logger.debug(f"Feature Importances: {feature_importances}")
        return results

    def save(self, file_path: str = "random_forest_model.pkl") -> None:
        """
        Save trained model, imputer, and label encoder to disk.
        
        Args:
            file_path: Path where to save the model
        """
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        
        model_data = {
            "model": self.model,
            "imputer": self.imputer,
            "label_encoder_mapping": self.label_encoder_mapping,
            "hyperparameters": {
                "n_estimators": self.n_estimators,
                "min_samples_split": self.min_samples_split,
                "min_samples_leaf": self.min_samples_leaf,
                "max_features": self.max_features,
                "max_samples": self.max_samples,
                "random_state": self.random_state,
                "n_jobs": self.n_jobs
            }
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {file_path}")

    def load(self, file_path: str = "random_forest_model.pkl") -> None:
        """
        Load a trained model from disk.
        
        Args:
            file_path: Path to the saved model
        """
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # Restore model and preprocessors
        self.model = model_data["model"]
        self.imputer = model_data["imputer"]
        self.label_encoder_mapping = model_data["label_encoder_mapping"]
        
        # Restore hyperparameters
        hparams = model_data["hyperparameters"]
        self.n_estimators = hparams["n_estimators"]
        self.min_samples_split = hparams["min_samples_split"]
        self.min_samples_leaf = hparams["min_samples_leaf"]
        self.max_features = hparams["max_features"]
        self.max_samples = hparams["max_samples"]
        self.random_state = hparams["random_state"]
        self.n_jobs = hparams["n_jobs"]
        
        logger.info(f"Model loaded from {file_path}")