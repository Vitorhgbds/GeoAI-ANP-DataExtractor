

import numpy as np
import pandas as pd
from slide.logger import Logger
from slide.models import BaseModel, ModelDataset
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder
import json
import pickle
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import Adam

logging = Logger()
logger = logging.get_logger()

class WellLogDataset(Dataset):
    """Custom Dataset for sequential well log data"""
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.LongTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

class LSTMModel(nn.Module):
    """LSTM model for rock type classification"""
    def __init__(self, input_size, hidden_size, num_layers, num_classes, dropout=0.3):
        super(LSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Linear(hidden_size, num_classes)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        # x shape: (batch, sequence_length, input_size)
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use the last hidden state
        out = self.dropout(h_n[-1])
        out = self.fc(out)
        return out

class LSTM(BaseModel):
    def __init__(self, sequence_length=10, hidden_size=128, num_layers=2, dropout=0.3):
        super().__init__()
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.label_encoder = LabelEncoder()
        logger.info(f"Using device: {self.device}")
    
    def _create_sequences(self, df, features_columns, target_column):
        """Create sequences for LSTM from well log data"""
        sequences = []
        targets = []
        wells = []
        
        # Get unique wells
        unique_wells = df['well'].unique() if 'well' in df.columns else [0]
        
        for well in unique_wells:
            if 'well' in df.columns:
                well_data = df[df['well'] == well].sort_values('depth')
            else:
                well_data = df.sort_values('depth')
            
            # Get features and target
            features = well_data[features_columns].fillna(0).values
            labels = well_data[target_column].values
            
            # Create sequences
            for i in range(len(well_data) - self.sequence_length):
                seq = features[i:i+self.sequence_length]
                target = labels[i+self.sequence_length]
                
                # Only include if target is valid
                if pd.notna(target):
                    sequences.append(seq)
                    targets.append(target)
                    wells.append(well)
        
        return np.array(sequences), np.array(targets), np.array(wells)
    
    def train(self, data: ModelDataset, epochs=50, batch_size=32, learning_rate=0.001) -> None:
        logger.info("Preparing sequential data for LSTM training...")
        
        # Get feature columns (exclude well, depth, target)
        feature_columns = [col for col in data.train.columns if col not in ['well', 'depth', 'rock']]
        
        # Create sequences
        train_sequences, train_targets, _ = self._create_sequences(
            pd.concat([data.train, data.train_target], axis=1),
            feature_columns,
            'rock'
        )
        
        logger.info(f"Created {len(train_sequences)} training sequences")
        logger.info(f"Sequence shape: {train_sequences.shape}")
        
        # Encode labels
        train_targets_encoded = self.label_encoder.fit_transform(train_targets)
        num_classes = len(self.label_encoder.classes_)
        logger.info(f"Number of classes: {num_classes}")
        logger.info(f"Classes: {self.label_encoder.classes_}")
        
        # Create dataset and dataloader
        train_dataset = WellLogDataset(train_sequences, train_targets_encoded)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        # Initialize model
        input_size = train_sequences.shape[2]
        self.model = LSTMModel(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            num_classes=num_classes,
            dropout=self.dropout
        ).to(self.device)
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = Adam(self.model.parameters(), lr=learning_rate)
        
        # Training loop
        logger.info("Starting LSTM training...")
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            correct = 0
            total = 0
            
            for sequences, targets in train_loader:
                sequences = sequences.to(self.device)
                targets = targets.to(self.device)
                
                # Forward pass
                outputs = self.model(sequences)
                loss = criterion(outputs, targets)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                # Statistics
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += targets.size(0)
                correct += (predicted == targets).sum().item()
            
            epoch_loss = total_loss / len(train_loader)
            epoch_acc = 100 * correct / total
            
            if (epoch + 1) % 5 == 0:
                logger.info(f'Epoch [{epoch+1}/{epochs}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.2f}%')
        
        logger.info("LSTM training completed!")
        self.input_size = input_size
        self.num_classes = num_classes
        self.feature_columns = feature_columns
        
    
    def predict(self, input_data: list) -> list:
        """Predict on new sequences"""
        self.model.eval()
        with torch.no_grad():
            sequences = torch.FloatTensor(input_data).to(self.device)
            outputs = self.model(sequences)
            _, predicted = torch.max(outputs, 1)
            return self.label_encoder.inverse_transform(predicted.cpu().numpy()).tolist()
    
    def evaluate(self, data: ModelDataset) -> dict:
        logger.info("Evaluating LSTM model...")
        
        # Create sequences for test data
        test_sequences, test_targets, _ = self._create_sequences(
            pd.concat([data.test, data.test_target], axis=1),
            self.feature_columns,
            'rock'
        )
        
        logger.info(f"Created {len(test_sequences)} test sequences")
        
        # Encode labels
        test_targets_encoded = self.label_encoder.transform(test_targets)
        
        # Create dataset and dataloader
        test_dataset = WellLogDataset(test_sequences, test_targets_encoded)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
        
        # Evaluate
        self.model.eval()
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for sequences, targets in test_loader:
                sequences = sequences.to(self.device)
                outputs = self.model(sequences)
                _, predicted = torch.max(outputs.data, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_targets.extend(targets.numpy())
        
        # Decode predictions
        predictions_decoded = self.label_encoder.inverse_transform(all_predictions)
        targets_decoded = self.label_encoder.inverse_transform(all_targets)
        
        # Calculate metrics
        accuracy = accuracy_score(targets_decoded, predictions_decoded)
        
        self.results = {
            "accuracy": float(accuracy),
            "classification_report": classification_report(targets_decoded, predictions_decoded),
            "confusion_matrix": confusion_matrix(targets_decoded, predictions_decoded).tolist()
        }
        
        logger.info(f"Test Accuracy: {accuracy:.4f}")
        logger.info(f"\n{self.results['classification_report']}")
        
        return self.results
    
    def save(self, file_path: str) -> None:
        if self.model is not None:
            # Save model state and configuration
            model_data = {
                'model_state_dict': self.model.state_dict(),
                'label_encoder': self.label_encoder,
                'sequence_length': self.sequence_length,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout,
                'input_size': self.input_size,
                'num_classes': self.num_classes,
                'feature_columns': self.feature_columns
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info(f"LSTM model saved to {file_path}")
            
        if self.results is not None:
            results_path = file_path + "_results_lstm.json"
            with open(results_path, 'w') as f:
                json.dump(self.results, f, indent=4)
            logger.info(f"Results saved to {results_path}")
    
    def load(self, file_path: str) -> None:
        """Load a saved LSTM model"""
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.label_encoder = model_data['label_encoder']
        self.sequence_length = model_data['sequence_length']
        self.hidden_size = model_data['hidden_size']
        self.num_layers = model_data['num_layers']
        self.dropout = model_data['dropout']
        self.input_size = model_data['input_size']
        self.num_classes = model_data['num_classes']
        self.feature_columns = model_data['feature_columns']
        
        # Recreate model
        self.model = LSTMModel(
            input_size=self.input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            num_classes=self.num_classes,
            dropout=self.dropout
        ).to(self.device)
        
        self.model.load_state_dict(model_data['model_state_dict'])
        logger.info(f"LSTM model loaded from {file_path}")