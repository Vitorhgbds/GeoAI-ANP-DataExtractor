

import numpy as np
import pandas as pd
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer
from torch.utils.data import TensorDataset, DataLoader
import json
import pickle
import torch
import torch.nn as nn
from torch.optim import Adam
import optuna
import gc

logging = Logger()
logger = logging.get_logger()

SEQUENCE_LENGTH = 10  # Use 10 consecutive depth readings
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
    def __init__(self, sequence_length=10, hidden_size=128, num_layers=2, dropout=0.3):
        super().__init__()
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.label_encoder = LabelEncoder()
        logger.info(f"Using device: {self.device}")

    def create_sequences(self, data, targets, sequence_length=10):
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

        hidden_size = trial.suggest_categorical("hidden_size", [128, 256])
        num_layers = trial.suggest_int("num_layers", 2, 3, step=1)
        dropout = trial.suggest_float("dropout", 0.0, 0.3, step=0.1)
        batch_size = trial.suggest_categorical("batch_size", [64, 128])

        # keep objective trials reasonably fast
        epochs = trial.suggest_categorical("epochs", [30, 50])
        
        num_classes = len(self.label_encoder_lstm.classes_)
        num_features = X_train.shape[2]
        
        # Convert to PyTorch tensors (keep on CPU, DataLoader will batch them)
        train_sequences_tensor = torch.FloatTensor(X_train)  # Don't move to GPU yet
        train_targets_tensor = torch.LongTensor(y_train)
        test_sequences_tensor = torch.FloatTensor(x_test)
        test_targets_tensor = torch.LongTensor(y_test)
        
        # Create DataLoaders (pin_memory helps CPU→GPU transfer)
        train_dataset = TensorDataset(train_sequences_tensor, train_targets_tensor)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)
        test_dataset = TensorDataset(test_sequences_tensor, test_targets_tensor)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)
        
        try:
            model = LSTMClassifier(
                num_features=num_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
                num_classes=num_classes,
                dropout=dropout
            ).to(DEVICE)
            
            criterion = nn.CrossEntropyLoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

            train_losses = []
            train_accs = []
            test_accs = []

            for epoch in range(epochs):
                # ---- Train ----
                model.train()
                train_loss = 0
                train_preds_epoch = []
                train_true_epoch = []
                
                for batch_x, batch_y in train_loader:
                    batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)  # Move only batch to GPU
                    optimizer.zero_grad()
                    logits = model(batch_x)
                    loss = criterion(logits, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()
                    
                    train_preds_epoch.append(logits.argmax(dim=1).detach().cpu().numpy())
                    train_true_epoch.append(batch_y.detach().cpu().numpy())
                
                train_loss /= len(train_loader)
                train_losses.append(train_loss)
                
                # Train accuracy (computed from batches)
                train_preds_all = np.concatenate(train_preds_epoch)
                train_true_all = np.concatenate(train_true_epoch)
                train_acc = accuracy_score(train_true_all, train_preds_all)
                train_accs.append(train_acc)
                
                # ---- Evaluate on Test ----
                model.eval()
                test_preds_epoch = []
                test_true_epoch = []
                
                with torch.no_grad():
                    for batch_x, batch_y in test_loader:
                        batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
                        logits = model(batch_x)
                        test_preds_epoch.append(logits.argmax(dim=1).detach().cpu().numpy())
                        test_true_epoch.append(batch_y.detach().cpu().numpy())
                
                test_preds_all = np.concatenate(test_preds_epoch)
                test_true_all = np.concatenate(test_true_epoch)
                test_acc = accuracy_score(test_true_all, test_preds_all)
                test_accs.append(test_acc)
                
                if (epoch + 1) % 5 == 0:
                    logger.info(f"Epoch {epoch+1}/{epochs} | Loss: {train_loss:.4f} | "
                        f"Train Acc: {train_acc:.4f} | Test Acc: {test_acc:.4f}")

            logger.info(f"\n{'='*60}")
            logger.info("LSTM Training Complete")
            logger.info(f"{'='*60}")
            logger.info(f"Final Train Accuracy: {train_acc:.4f}")
            logger.info(f"Final Test Accuracy: {test_acc:.4f}")
            logger.info(f"Overfitting Gap: {train_acc - test_acc:.4f}")

            # ============ Final Evaluation ============
            model.eval()
            test_preds_final = []
            with torch.no_grad():
                for batch_x, batch_y in test_loader:
                    batch_x = batch_x.to(DEVICE)
                    logits = model(batch_x)
                    test_preds_final.append(logits.argmax(dim=1).detach().cpu().numpy())
            
            test_preds_final = np.concatenate(test_preds_final)
            test_preds_decoded = self.label_encoder_lstm.inverse_transform(test_preds_final)
            test_targets_decoded = self.label_encoder_lstm.inverse_transform(test_true_all)
            
            
            test_accuracy = accuracy_score(test_true_all, test_preds_final)
            trial.set_user_attr("test_accuracy", float(test_accuracy))
            
            report = classification_report(test_targets_decoded, test_preds_decoded, output_dict=True)
            trial.set_user_attr("classification_report", report)
            
            return float(test_accuracy)
        finally:
            if self.device.type == "cuda":
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
            study_name="lstm_optimization",
            load_if_exists=True,
        )

        study.optimize(
            lambda trial: self.__objective(trial, train_sequences, train_targets_encoded, test_sequences, test_targets_encoded),
            n_trials=50,
            gc_after_trial=True
        )

        logger.info(f"Best hyperparameters: {study.best_params}")


    def evaluate(self, test_data):
        return super().evaluate(test_data)
    
    def predict(self, input_data):
        return super().predict(input_data)
    
    def save(self):
        pass