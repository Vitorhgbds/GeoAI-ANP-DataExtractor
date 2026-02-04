from typing import Tuple
import numpy as np
import pandas as pd
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler
import pickle
import torch
import torch.nn as nn
import gc

logging = Logger()
logger = logging.get_logger()

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True


class LSTMClassifier(nn.Module):
    def __init__(
        self, 
        num_features: int, 
        hidden_size: int, 
        num_layers: int, 
        num_classes: int, 
        dropout: float):
        super(LSTMClassifier, self).__init__()
        self.lstm = nn.LSTM(
            input_size=num_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
    
    def forward(self, x):
        lstm_out, (hidden, cell) = self.lstm(x)
        forward_hidden = hidden[-2, :, :]
        backward_hidden = hidden[-1, :, :]
        combined_hidden = torch.cat((forward_hidden, backward_hidden), dim=1)
        out = self.fc(combined_hidden)
        return out


class BILSTM(BaseModel):
    def __init__(
        self, 
        sequence_length: int = 11, 
        hidden_size: int = 128, 
        num_layers: int = 2, 
        dropout: float = 0.3,
        batch_size: int = 128,
        epochs: int = 50,
        learning_rate: float = 1e-3,
        patience: int = 10,
        num_workers: int = 4):
        
        super().__init__()
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.patience = patience
        self.num_workers = num_workers
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.label_encoder = LabelEncoder()
        self.model = None
        self.imputer = None
        logger.info(f"Using device: {self.device}")

    def create_sequences(self, data, targets):
        """
        Create sequences from well log data using centered windows.
        """
        sequences = []
        target_labels = []
        
        half = self.sequence_length // 2
        for idx in range(half, len(data) - (self.sequence_length - half)):
            sequences.append(data[idx - half:idx + (self.sequence_length - half)])
            target_labels.append(targets.iloc[idx])
        
        return np.array(sequences), np.array(target_labels)

    def __process_train_test(
        self, 
        data: ModelDataset) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        
        # Remove rows with missing target values
        train_mask = data.train_target.notna()
        train_data_clean = data.train[train_mask]
        train_target_clean = data.train_target[train_mask]
        
        test_mask = data.test_target.notna()
        test_data_clean = data.test[test_mask]
        test_target_clean = data.test_target[test_mask]
        
        # Impute missing values
        self.imputer = SimpleImputer(strategy='median')
        train_data_imputed = self.imputer.fit_transform(train_data_clean)
        test_data_imputed = self.imputer.transform(test_data_clean)
        
        # Create sequences
        train_sequences, train_targets_seq = self.create_sequences(
            train_data_imputed, 
            train_target_clean
        )
        test_sequences, test_targets_seq = self.create_sequences(
            test_data_imputed, 
            test_target_clean
        )
        
        logger.debug(f"Train sequences shape: {train_sequences.shape}")
        logger.debug(f"Test sequences shape: {test_sequences.shape}")
        
        # Encode targets
        self.label_encoder = LabelEncoder()
        train_targets_encoded = self.label_encoder.fit_transform(train_targets_seq)
        test_targets_encoded = self.label_encoder.transform(test_targets_seq)
        
        return train_sequences, train_targets_encoded, test_sequences, test_targets_encoded

    def train(self, data: ModelDataset) -> None:
        logger.info("Preparing sequential data for BiLSTM training...")
        logger.debug(f"CUDA available: {torch.cuda.is_available()}")
        logger.debug(f"Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
        logger.debug(f"CUDA version: {torch.version.cuda}")
        
        # Process data
        X_train, y_train, X_test, y_test = self.__process_train_test(data)
        
        num_classes = len(self.label_encoder.classes_)
        num_features = X_train.shape[2]
        
        logger.debug(f"Num classes: {num_classes}, Num features: {num_features}")
        
        # Convert to tensors
        train_X = torch.as_tensor(X_train, dtype=torch.float32)
        train_y = torch.as_tensor(y_train, dtype=torch.long)
        test_X = torch.as_tensor(X_test, dtype=torch.float32)
        test_y = torch.as_tensor(y_test, dtype=torch.long)
        
        # Class weights for imbalanced data
        y_train_np = np.asarray(y_train)
        counts = np.bincount(y_train_np)
        beta = 0.9999
        effective_num = 1.0 - np.power(beta, counts)
        class_weights = (1.0 - beta) / np.maximum(effective_num, 1e-12)
        class_weights = class_weights / class_weights.mean()
        sample_weights = class_weights[y_train_np]
        
        sampler = WeightedRandomSampler(
            weights=torch.as_tensor(sample_weights, dtype=torch.double),
            num_samples=len(sample_weights),
            replacement=True
        )
        
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32, device=self.device)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        
        # Create data loaders
        train_ds = TensorDataset(train_X, train_y)
        test_ds = TensorDataset(test_X, test_y)
        
        train_loader = DataLoader(
            train_ds,
            batch_size=self.batch_size,
            sampler=sampler,
            num_workers=self.num_workers,
            pin_memory=True,
            persistent_workers=(self.num_workers > 0),
            prefetch_factor=2
        )
        test_loader = DataLoader(
            test_ds,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
            persistent_workers=(self.num_workers > 0),
            prefetch_factor=2
        )
        
        # Initialize model
        self.model = LSTMClassifier(
            num_features=num_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            num_classes=num_classes,
            dropout=self.dropout
        ).to(self.device)
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        
        # Mixed precision training
        use_amp = (self.device.type == "cuda")
        scaler = torch.amp.GradScaler(enabled=use_amp)
        
        best_f1 = -1.0
        best_state = None
        no_improve = 0
        
        logger.info(f"Training with: hidden_size={self.hidden_size}, num_layers={self.num_layers}, "
                   f"dropout={self.dropout}, batch_size={self.batch_size}")
        
        try:
            for epoch in range(self.epochs):
                # Training phase
                self.model.train()
                total_loss = 0.0
                correct = 0
                total = 0
                
                for batch_x, batch_y in train_loader:
                    batch_x = batch_x.to(self.device, non_blocking=True)
                    batch_y = batch_y.to(self.device, non_blocking=True)
                    
                    optimizer.zero_grad(set_to_none=True)
                    
                    with torch.amp.autocast(device_type=self.device.type, dtype=torch.float16, enabled=use_amp):
                        logits = self.model(batch_x)
                        loss = criterion(logits, batch_y)
                    
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                    
                    total_loss += loss.item()
                    preds = logits.argmax(dim=1)
                    correct += (preds == batch_y).sum().item()
                    total += batch_y.numel()
                
                train_loss = total_loss / max(1, len(train_loader))
                train_acc = correct / max(1, total)
                
                # Validation phase
                self.model.eval()
                preds_all = []
                true_all = []
                
                with torch.no_grad():
                    for batch_x, batch_y in test_loader:
                        batch_x = batch_x.to(self.device, non_blocking=True)
                        logits = self.model(batch_x)
                        preds_all.append(logits.argmax(dim=1).cpu())
                        true_all.append(batch_y.cpu())
                
                preds_all = torch.cat(preds_all).numpy()
                true_all = torch.cat(true_all).numpy()
                
                val_acc = accuracy_score(true_all, preds_all)
                val_f1 = f1_score(true_all, preds_all, average="macro", zero_division=0)
                
                # Early stopping
                if val_f1 > best_f1:
                    best_f1 = val_f1
                    no_improve = 0
                    best_state = {k: v.detach().cpu().clone() for k, v in self.model.state_dict().items()}
                    logger.debug(f"New best F1: {best_f1:.4f}")
                else:
                    no_improve += 1
                
                if (epoch + 1) % 5 == 0:
                    logger.info(
                        f"Epoch {epoch+1}/{self.epochs} | Loss: {train_loss:.4f} | "
                        f"Train Acc: {train_acc:.4f} | Val Acc: {val_acc:.4f} | "
                        f"Val F1: {val_f1:.4f} | No Improve: {no_improve}/{self.patience}"
                    )
                
                if no_improve >= self.patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
            
            # Restore best model
            if best_state is not None:
                self.model.load_state_dict(best_state, strict=True)
                logger.info(f"Training complete. Best Val F1: {best_f1:.4f}")
            
        finally:
            if self.device.type == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

    def predict(self, input_data: pd.DataFrame) -> np.ndarray:
        """
        Predict rock types for input data.
        
        Args:
            input_data: DataFrame with same features as training data
            
        Returns:
            Array of predicted rock type labels
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        if self.imputer is None:
            raise ValueError("Imputer not fitted. Call train() first or load a trained model.")
        
        # Create dummy targets (won't be used but needed for create_sequences)
        dummy_targets = pd.Series([self.label_encoder.classes_[0]] * len(input_data))
        
        # Impute missing values
        data_imputed = self.imputer.transform(input_data)
        
        # Create sequences
        sequences, _ = self.create_sequences(data_imputed, dummy_targets, self.sequence_length)
        
        # Convert to tensor
        sequences_tensor = torch.as_tensor(sequences, dtype=torch.float32)
        
        # Create data loader
        dataset = TensorDataset(sequences_tensor)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=False)
        
        # Predict
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for (batch_x,) in loader:
                batch_x = batch_x.to(self.device)
                logits = self.model(batch_x)
                preds = logits.argmax(dim=1).cpu().numpy()
                predictions.append(preds)
        
        predictions = np.concatenate(predictions)
        
        # Decode labels
        predicted_labels = self.label_encoder.inverse_transform(predictions)
        
        return predicted_labels

    def evaluate(self, test_data: ModelDataset) -> dict:
        """
        Evaluate model on test data.
        
        Args:
            test_data: ModelDataset with test features and targets
            
        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load a trained model.")
        
        # Process test data
        test_mask = test_data.test_target.notna()
        test_data_clean = test_data.test[test_mask]
        test_target_clean = test_data.test_target[test_mask]
        
        # Impute and create sequences
        test_data_imputed = self.imputer.transform(test_data_clean)
        test_sequences, test_targets_seq = self.create_sequences(
            test_data_imputed, 
            test_target_clean, 
            self.sequence_length
        )
        
        # Encode targets
        test_targets_encoded = self.label_encoder.transform(test_targets_seq)
        
        # Convert to tensors
        test_X = torch.as_tensor(test_sequences, dtype=torch.float32)
        test_y = torch.as_tensor(test_targets_encoded, dtype=torch.long)
        
        test_ds = TensorDataset(test_X, test_y)
        test_loader = DataLoader(test_ds, batch_size=self.batch_size, shuffle=False)
        
        # Evaluate
        self.model.eval()
        preds_all = []
        true_all = []
        
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x = batch_x.to(self.device)
                logits = self.model(batch_x)
                preds_all.append(logits.argmax(dim=1).cpu().numpy())
                true_all.append(batch_y.cpu().numpy())
        
        preds_all = np.concatenate(preds_all)
        true_all = np.concatenate(true_all)
        
        # Decode labels
        test_preds_decoded = self.label_encoder.inverse_transform(preds_all)
        test_targets_decoded = self.label_encoder.inverse_transform(true_all)
        
        # Calculate metrics
        accuracy = accuracy_score(test_targets_decoded, test_preds_decoded)
        f1_macro = f1_score(test_targets_decoded, test_preds_decoded, average="macro", zero_division=0)
        f1_weighted = f1_score(test_targets_decoded, test_preds_decoded, average="weighted", zero_division=0)
        report = classification_report(test_targets_decoded, test_preds_decoded, output_dict=True)
        cm = confusion_matrix(test_targets_decoded, test_preds_decoded)
        
        logger.info(f"Test Accuracy: {accuracy:.4f}")
        logger.info(f"Test F1 (macro): {f1_macro:.4f}")
        logger.info(f"Test F1 (weighted): {f1_weighted:.4f}")
        
        return {
            "accuracy": float(accuracy),
            "f1_macro": float(f1_macro),
            "f1_weighted": float(f1_weighted),
            "classification_report": report,
            "confusion_matrix": cm.tolist()
        }

    def save(self, file_path: str = "bilstm_model.pkl") -> None:
        """
        Save the trained model to disk.
        
        Args:
            file_path: Path where to save the model
        """
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        
        model_data = {
            "model_state_dict": self.model.state_dict(),
            "label_encoder": self.label_encoder,
            "imputer": self.imputer,
            "hyperparameters": {
                "sequence_length": self.sequence_length,
                "hidden_size": self.hidden_size,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
                "batch_size": self.batch_size,
                "learning_rate": self.learning_rate,
            },
            "num_features": self.model.lstm.input_size,
            "num_classes": self.model.fc[-1].out_features
        }
        
        with open(file_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {file_path}")
    
    def load(self, file_path: str = "bilstm_model.pkl") -> None:
        """
        Load a trained model from disk.
        
        Args:
            file_path: Path to the saved model
        """
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        # Restore hyperparameters
        hparams = model_data["hyperparameters"]
        self.sequence_length = hparams["sequence_length"]
        self.hidden_size = hparams["hidden_size"]
        self.num_layers = hparams["num_layers"]
        self.dropout = hparams["dropout"]
        self.batch_size = hparams["batch_size"]
        self.learning_rate = hparams["learning_rate"]
        
        # Restore label encoder and imputer
        self.label_encoder = model_data["label_encoder"]
        self.imputer = model_data["imputer"]
        
        # Reconstruct model
        self.model = LSTMClassifier(
            num_features=model_data["num_features"],
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            num_classes=model_data["num_classes"],
            dropout=self.dropout
        ).to(self.device)
        
        self.model.load_state_dict(model_data["model_state_dict"])
        self.model.eval()
        
        logger.info(f"Model loaded from {file_path}")