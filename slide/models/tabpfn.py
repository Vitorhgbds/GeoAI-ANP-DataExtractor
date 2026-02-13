import numpy as np
from sklearn.calibration import LabelEncoder
from sklearn.discriminant_analysis import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
import pickle
import gc
from tabpfn import TabPFNClassifier
from tabpfn_extensions.many_class import ManyClassClassifier
import os

logging = Logger()
logger = logging.get_logger()

os.environ["TABPFN_DISABLE_TELEMETRY"] = "1"
logger.info("TABPFN telemetry disabled via environment variable.")

class TABPFN(BaseModel):
	def __init__(
		self,
		device: str = "cpu",
		n_jobs: int = 1,
		n_preprocessing_jobs: int = 1,
		n_estimators: int | None = None,
		alphabet_size: int = 8,
		subsample_size: int = 10_000,
		seed: int = 42,
		ignore_pretraining_limits: bool = False,
		fit_mode: str = "fit_preprocessors",
		*args, **kwargs):
		"""
		Initialize TABPFN model.

		Args:
			device: Device to run the model on ("cpu" or "cuda")
			n_estimators: Number of estimators in the ensemble
			seed: Random seed for reproducibility
		"""
		super().__init__()
		self.device = device
		self.n_estimators = n_estimators
		self.seed = seed
		self.model = None
		self.imputer = SimpleImputer(strategy="median")
		self.label_encoder = LabelEncoder()
		self.scaler = StandardScaler()
		self.n_jobs = n_jobs
		self.subsample_size = subsample_size
		self.n_preprocessing_jobs = n_preprocessing_jobs
		self.ignore_pretraining_limits = ignore_pretraining_limits
		self.alphabet_size = alphabet_size
		self.fit_mode = fit_mode
  
		logger.info(
			"Initialized TABPFN with "
			f"device={device}, n_estimators={n_estimators}, seed={seed}, alphabet_size={alphabet_size}, "
			f"ignore_pretraining_limits={ignore_pretraining_limits}, fit_mode={fit_mode}, "
			f"n_jobs={n_jobs}, n_preprocessing_jobs={n_preprocessing_jobs}"
		)

	def train(self, data: ModelDataset) -> None:
		"""
		Train TABPFN model on data.

		Args:
			data: ModelDataset with train/test features and targets
		"""
		logger.info("Training TABPFN model...")

		# Remove rows with missing target values
		train_mask = data.train_target.notna()
		train_data_clean = data.train[train_mask]
		train_target_clean = data.train_target[train_mask]
		test_mask = data.test_target.notna()
		test_data_clean = data.test[test_mask]
		test_target_clean = data.test_target[test_mask]
  
		# Impute missing values
		train_data_imputed = self.imputer.fit_transform(train_data_clean)
		test_data_imputed = self.imputer.transform(test_data_clean)
  		
		train_target_encoded = self.label_encoder.fit_transform(train_target_clean)
		test_target_encoded = self.label_encoder.transform(test_target_clean)
  
		train_data_scaled = self.scaler.fit_transform(train_data_imputed)
		test_data_scaled = self.scaler.transform(test_data_imputed)
  
		counts = np.bincount(train_target_encoded)
		beta = 0.9999
		effective_num = 1.0 - np.power(beta, counts)
		class_weights = (1.0 - beta) / np.maximum(effective_num, 1e-12)
		class_weights = class_weights / class_weights.mean()

		sample_weights = class_weights[train_target_encoded].astype(np.float64)
		p = sample_weights / sample_weights.sum()

		rng = np.random.default_rng(0)


		idx_per_estimator = [
			rng.choice(len(train_target_encoded), size=self.subsample_size, replace=True, p=p).astype(np.int32)
			for _ in range(self.n_estimators)
		]
  
		idx_per_estimator = idx_per_estimator[:self.n_estimators]
  
		logger.debug(f"Train data shape: {train_data_scaled.shape}")
		logger.debug(f"Train target shape: {train_target_encoded.shape}")

		# Train model
		tabpfn = TabPFNClassifier(
			device=self.device,
			n_preprocessing_jobs=self.n_preprocessing_jobs,
			ignore_pretraining_limits=self.ignore_pretraining_limits,
			n_estimators=self.n_estimators,
			fit_mode=self.fit_mode,
			inference_config={"SUBSAMPLE_SAMPLES": idx_per_estimator},
		)
  
		# Wrap it with ManyClassClassifier
		self.model = ManyClassClassifier(
			estimator=tabpfn,
			#row_weighting_config="train_entropy",  # How to weight samples when creating subproblems
			alphabet_size=self.alphabet_size,    # Size of subproblems (should be <= TabPFN's class limit)
			verbose=3,
			#codebook_config="legacy_rest",  # How to create subproblems (dense or sparse)
		)
  
		logger.debug("Starting model fitting...")

		self.model.fit(train_data_scaled, train_target_encoded)
		logger.debug("Model fitting complete.")
  
		logger.debug("Starting model evaluation on training data...")
		# Evaluate on training data
		train_preds = self.model.predict(train_data_scaled)
		train_acc = accuracy_score(train_target_encoded, train_preds)
		train_f1 = f1_score(train_target_encoded, train_preds, average="macro", zero_division=0)

		logger.info(f"Training Accuracy: {train_acc:.4f}")
		logger.info(f"Training F1 (macro): {train_f1:.4f}")

		test_preds = self.model.predict(test_data_scaled)
		test_acc = accuracy_score(test_target_encoded, test_preds)
		test_f1 = f1_score(test_target_encoded, test_preds, average="macro", zero_division=0)

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

		# Impute missing values
		data_imputed = self.imputer.transform(input_data)
		data_scaled = self.scaler.transform(data_imputed)

		# Make predictions
		predictions_encoded = self.model.predict(data_scaled)

		# Decode labels if needed
		predictions = self.label_encoder.inverse_transform(predictions_encoded)

		return predictions

	def evaluate(self, data: ModelDataset) -> dict:
		"""
		Evaluate model on test data.

		Args:
			data: ModelDataset with test features and targets

		Returns:
			Dictionary with evaluation metrics
		"""

		# Remove rows with missing target values
		test_mask = data.test_target.notna()
		test_data_clean = data.test[test_mask]
		test_target_clean = data.test_target[test_mask]

		# Impute missing values
		test_data_imputed = self.imputer.transform(test_data_clean)
		test_data_scaled = self.scaler.transform(test_data_imputed)

		logger.debug(f"Test data shape: {data.test.shape}")
		logger.debug(f"Test target shape: {data.test_target.shape}")

		# Make predictions
		predictions_encoded = self.model.predict(test_data_scaled)

		# Decode predictions for reporting
		predictions_decoded = self.label_encoder.inverse_transform(predictions_encoded)
		
		# Calculate metrics
		accuracy = accuracy_score(test_target_clean, predictions_decoded)
		f1_macro = f1_score(test_target_clean, predictions_decoded, average="macro", zero_division=0)
		f1_weighted = f1_score(test_target_clean, predictions_decoded, average="weighted", zero_division=0)
		report = classification_report(test_target_clean, predictions_decoded, output_dict=True)
		cm = confusion_matrix(test_target_clean, predictions_decoded)

		results = {
			"accuracy": float(accuracy),
			"f1_macro": float(f1_macro),
			"f1_weighted": float(f1_weighted),
			"classification_report": report,
			"confusion_matrix": cm.tolist()
		}

		logger.info(f"Test Accuracy: {accuracy:.4f}")
		logger.info(f"Test F1 (macro): {f1_macro:.4f}")
		logger.info(f"Test F1 (weighted): {f1_weighted:.4f}")

		return results

	def save(self, file_path: str = "tabpfn_model.pkl") -> None:
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
			"label_encoder": self.label_encoder,
			"scaler": self.scaler,
			"hyperparameters": {
				"device": self.device,
				"n_estimators": self.n_estimators,
				"seed": self.seed,
				"ignore_pretraining_limits": self.ignore_pretraining_limits,
				"fit_mode": self.fit_mode
			}
		}

		with open(file_path, "wb") as f:
			pickle.dump(model_data, f)

		logger.info(f"Model saved to {file_path}")

	def load(self, file_path: str = "tabpfn_model.pkl") -> None:
		"""
		Load a trained model from disk.

		Args:
			file_path: Path to the saved model
		"""
		with open(file_path, "rb") as f:
			model_data = pickle.load(f)

		# Restore model and preprocessors
		self.model = model_data["model"]
		self.imputer = model_data["imputer"]
		self.label_encoder = model_data["label_encoder"]
		self.scaler = model_data["scaler"]

		# Restore hyperparameters
		hparams = model_data["hyperparameters"]
		self.device = hparams["device"]
		self.n_estimators = hparams["n_estimators"]
		self.fit_mode = hparams.get("fit_mode", "fit_preprocessors")
		self.ignore_pretraining_limits = hparams.get("ignore_pretraining_limits", False)
		self.seed = hparams["seed"]

		logger.info(f"Model loaded from {file_path}")

		if self.device == "cuda":
			gc.collect()
