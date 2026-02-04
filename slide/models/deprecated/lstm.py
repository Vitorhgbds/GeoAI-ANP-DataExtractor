

import numpy as np
import pandas as pd
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler
import json
import pickle
import torch
import torch.nn as nn
from torch.optim import Adam
import optuna
import gc

logging = Logger()
logger = logging.get_logger()

SEQUENCE_LENGTH = 10  # Use 11 consecutive depth readings
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============ Define LSTM Model ============
class LSTMClassifier(nn.Module):
    def __init__(self, num_features, hidden_size=128, num_layers=2, num_classes=15, dropout=0.3):
        super(LSTMClassifier, self).__init__()
        self.lstm = nn.LSTM(
            input_size=num_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
    
    def forward(self, x):
        # x shape: (batch_size, sequence_length, num_features)
        lstm_out, (hidden, cell) = self.lstm(x)
        # Use last hidden state
        out = self.fc(hidden[-1])  # (batch_size, num_classes)
        return out

class LSTM(BaseModel):
    def __init__(self, sequence_length=11, hidden_size=128, num_layers=2, dropout=0.3):
        super().__init__()
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.label_encoder = LabelEncoder()
        logger.info(f"Using device: {self.device}")

    def create_sequences(self, data, targets, sequence_length=11):
        """
        Create sequences from well log data.
        Each sequence = sequence_length consecutive readings.
        Target = the rock type at the end of each sequence.
        """
        sequences = []
        target_labels = []
        
        for idx in range(len(data) - sequence_length):
            sequences.append(data[idx:idx + sequence_length])
            target_labels.append(targets.iloc[idx + sequence_length])
        
        return np.array(sequences), np.array(target_labels)

    def __objective(self, trial: optuna.Trial, X_train, y_train, x_test, y_test):
        logger.info(f"Starting trial {trial.number} for hyperparameter optimization.")
        hidden_size = trial.suggest_categorical("hidden_size", [32, 64, 128, 256])
        num_layers  = trial.suggest_int("num_layers", 1, 4)
        dropout     = trial.suggest_float("dropout", 0.0, 0.3, step=0.1)
        batch_size  = trial.suggest_categorical("batch_size", [64, 128, 256])
        
        

        epochs = 64
        eval_every =  1                 # <-- big speed win
        num_workers = 8                # tune: 2/4/8 depending on CPU
        patience = 7

        num_classes  = len(self.label_encoder_lstm.classes_)
        num_features = X_train.shape[2]

        # ----- Cache tensors across trials (avoid re-creating huge tensors every Optuna trial) -----
        # Only do this if X_train/x_test are the same for all trials (they are in your flow).
        if not hasattr(self, "_cached_bilstm_tensors"):
            train_X = torch.as_tensor(X_train, dtype=torch.float32)  # CPU
            train_y = torch.as_tensor(y_train, dtype=torch.long)     # CPU
            test_X  = torch.as_tensor(x_test,  dtype=torch.float32)  # CPU
            test_y  = torch.as_tensor(y_test,  dtype=torch.long)     # CPU
            self._cached_bilstm_tensors = (train_X, train_y, test_X, test_y)
        else:
            train_X, train_y, test_X, test_y = self._cached_bilstm_tensors

        # ----- Class weights (fast + avoids WeightedRandomSampler) -----
        y_train_np = np.asarray(y_train)
        counts = np.bincount(y_train_np)

        beta = 0.9999
        effective_num = 1.0 - np.power(beta, counts)
        class_weights = (1.0 - beta) / np.maximum(effective_num, 1e-12)

        # normalize (optional but nice)
        class_weights = class_weights / class_weights.mean()

        sample_weights = class_weights[y_train_np]

        sampler = WeightedRandomSampler(
            weights=torch.as_tensor(sample_weights, dtype=torch.double),
            num_samples=len(sample_weights),
            replacement=True
        )

        weight_tensor = torch.tensor(class_weights, dtype=torch.float32, device=DEVICE)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)

        train_ds = TensorDataset(train_X, train_y)
        test_ds  = TensorDataset(test_X, test_y)

        train_loader = DataLoader(
            train_ds,
            batch_size=batch_size,
            sampler=sampler,                     # <-- much faster than WeightedRandomSampler
            num_workers=num_workers,
            pin_memory=True,
            persistent_workers=(num_workers > 0),
            prefetch_factor=2
        )
        test_loader = DataLoader(
            test_ds,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True,
            persistent_workers=(num_workers > 0),
            prefetch_factor=2
        )

        model = LSTMClassifier(
            num_features=num_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_classes=num_classes,
            dropout=dropout
        ).to(DEVICE)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

        # AMP (mixed precision)
        use_amp = (DEVICE.type == "cuda")
        scaler = torch.amp.GradScaler(enabled=use_amp)

        best_f1 = -1.0
        best_state = None
        no_improve = 0

        logger.info(f"Trial {trial.number} hyperparameters: hidden_size={hidden_size}, num_layers={num_layers}, dropout={dropout}, batch_size={batch_size}")
        try:
            for epoch in range(epochs):
                # ---- Train ----
                model.train()
                total_loss = 0.0
                correct = 0
                total = 0

                for batch_x, batch_y in train_loader:
                    batch_x = batch_x.to(DEVICE, non_blocking=True)
                    batch_y = batch_y.to(DEVICE, non_blocking=True)

                    optimizer.zero_grad(set_to_none=True)

                    with torch.amp.autocast(device_type=DEVICE.type, dtype=torch.float16, enabled=use_amp):
                        logits = model(batch_x)
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

                # ---- Validate (only every eval_every epochs) ----
                if (epoch % eval_every) != (eval_every - 1) and epoch != (epochs - 1):
                    continue

                model.eval()
                # Collect on CPU *once per eval*, not per batch
                preds_all = []
                true_all  = []

                with torch.no_grad():
                    for batch_x, batch_y in test_loader:
                        batch_x = batch_x.to(DEVICE, non_blocking=True)
                        logits = model(batch_x)
                        preds_all.append(logits.argmax(dim=1).cpu())
                        true_all.append(batch_y.cpu())

                preds_all = torch.cat(preds_all).numpy()
                true_all  = torch.cat(true_all).numpy()

                # If you want it even faster: compute ONLY accuracy during Optuna,
                # and compute F1 only for the best trial after optimization.
                val_acc = accuracy_score(true_all, preds_all)
                val_f1  = f1_score(true_all, preds_all, average="macro", zero_division=0)

                # Early stopping
                if val_f1 > best_f1:
                    best_f1 = val_f1
                    no_improve = 0
                    # Proper deep copy of weights (avoid state_dict().copy() shallow copy)
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                else:
                    no_improve += 1

                logger.info(
                    f"Epoch {epoch+1}/{epochs} | loss {train_loss:.4f} | train_acc {train_acc:.4f} | "
                    f"val_acc {val_acc:.4f} | val_f1m {val_f1:.4f} | no_improve {no_improve}/{patience}"
                )

                if no_improve >= patience:
                    break

            if best_state is not None:
                model.load_state_dict(best_state, strict=True)
                
            model.eval()
            # Collect on CPU *once per eval*, not per batch
            preds_all = []
            true_all  = []

            with torch.no_grad():
                for batch_x, batch_y in test_loader:
                    batch_x = batch_x.to(DEVICE, non_blocking=True)
                    logits = model(batch_x)
                    preds_all.append(logits.argmax(dim=1).cpu())
                    true_all.append(batch_y.cpu())

            preds_all = torch.cat(preds_all).numpy()
            true_all  = torch.cat(true_all).numpy()

            # If you want it even faster: compute ONLY accuracy during Optuna,
            # and compute F1 only for the best trial after optimization.
            val_acc = accuracy_score(true_all, preds_all)
            val_f1  = f1_score(true_all, preds_all, average="macro", zero_division=0)
                
            test_preds_decoded = self.label_encoder_lstm.inverse_transform(preds_all)
            test_targets_decoded = self.label_encoder_lstm.inverse_transform(true_all)
            
            trial.set_user_attr("train_accuracy", float(train_acc))
            trial.set_user_attr("test_accuracy", float(val_acc))

            report = classification_report(test_targets_decoded, test_preds_decoded, output_dict=True)
            trial.set_user_attr("classification_report", report)

            cm = confusion_matrix(test_targets_decoded, test_preds_decoded)
            trial.set_user_attr("confusion_matrix", cm.tolist())    # Optuna objective: return something cheap+stable
            # (accuracy is cheaper than macro-F1 to compute)
            return float(val_acc)

        finally:
            if DEVICE.type == "cuda":
                torch.cuda.empty_cache()
            gc.collect()

    def train(self, data: ModelDataset) -> None:
        logger.info("Preparing sequential data for LSTM training...")
        
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
        
        # Create sequences
        train_sequences, train_targets_seq = self.create_sequences(
            train_data_imputed, 
            train_target_clean, 
            SEQUENCE_LENGTH
        )
        test_sequences, test_targets_seq = self.create_sequences(
            test_data_imputed, 
            test_target_clean, 
            SEQUENCE_LENGTH
        )
        
        logger.debug(f"Train sequences shape: {train_sequences.shape}")
        logger.debug(f"Test sequences shape: {test_sequences.shape}")
        logger.debug(f"Train targets shape: {train_targets_seq.shape}")

        # Encode targets
        self.label_encoder_lstm = LabelEncoder()
        train_targets_encoded = self.label_encoder_lstm.fit_transform(train_targets_seq)
        test_targets_encoded = self.label_encoder_lstm.transform(test_targets_seq)
        
        num_classes = len(self.label_encoder_lstm.classes_)
        num_features = train_sequences.shape[2]

        logger.debug(f"Num classes: {num_classes}, Num features: {num_features}")

        storage = "sqlite:///optuna_studies.db"
        study = optuna.create_study(
            direction="maximize",
            storage=storage,
            study_name="lstm_default",
            load_if_exists=True,
        )

        study.optimize(
            lambda trial: self.__objective(trial, train_sequences, train_targets_encoded, test_sequences, test_targets_encoded),
            n_trials=15,
            gc_after_trial=True
        )

        logger.info(f"Best hyperparameters: {study.best_params}")


    def evaluate(self, test_data):
        return super().evaluate(test_data)
    
    def predict(self, input_data):
        return super().predict(input_data)
    
    def save(self):
        pass