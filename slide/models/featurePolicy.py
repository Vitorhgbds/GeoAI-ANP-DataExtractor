



from pathlib import Path
import sqlite3
from typing import Tuple
from slide.logger import Logger
from slide.models import ModelDataset, FeatureProcessingPolicy
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split


logger = Logger().get_logger()

class DefaultFeatures(FeatureProcessingPolicy):
    
    def __init__(self, apply_rolling_stats: bool = True, window: int = 5, *args, **kwargs) -> None:
        self.apply_rolling_stats = apply_rolling_stats
        self.window = window
        super().__init__(*args, **kwargs)
    
    def _add_sequential_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, list[str]]:
        """Add lagged features to capture sequential dependencies"""
        features = self.features.copy()
        features.remove("depth")  # Exclude 'depth' from sequential features
        new_features = []
        
        df = df.sort_values(['well', 'depth'])  # Ensure sorted by well and depth
        for f in features:
            df[f'{f}_rolling_mean'] = df.groupby('well')[f].transform(
                lambda x: x.rolling(window=self.window, min_periods=1).mean()
            )
            df[f'{f}_rolling_std'] = df.groupby('well')[f].transform(
                lambda x: x.rolling(window=self.window, min_periods=1).std()
            )
            new_features.extend([f'{f}_rolling_mean', f'{f}_rolling_std'])
        
        return df, new_features
    
    
    def fetch(self) -> ModelDataset:
        database_path = Path(__file__).parent.parent / "database" / "features.db"
        
        logger.info(f"Fetching features from database at {database_path}")
        conn = sqlite3.connect(database_path)
        
        logger.debug("Connected to the database successfully.")
        logger.debug("Executing SQL query to fetch features.")
        logger.debug(f"SQL Query: \n{self.sql_features}")
        df_features = pd.read_sql_query(self.sql_features, conn)
        
        logger.debug(f"Fetched {len(df_features)} rows from the database.")
        logger.debug(f"Total wells fetched: {len(df_features['well'].unique())}")
        features_columns = [
                'depth',
                'GR', 
                'SP', 
                'DT', 
                'CALI', 
                'ILD', 
                'RHOB', 
                'NPHI', 
                'MSFL',
                'DRHO', 
                'SFLU']
        valid_rocks = [
            'FOLHELHO', 'ARENITO', 'SILTITO', 'CALCILUTITO', 'AREIA', 'CALCARENITO',
            'ARGILA', 'CALCARIO', 'CONGLOMERADO', 'ARGILITO', 'ANIDRITA', 'MARGA',
            'GRANITO', 'BASALTO', 'DOLOMITO'
        ]

        all_features = self.features.copy()
        
        if self.apply_presence:
            logger.info("Applying presence indicators to features.")
            df_features, new_features = self.build_presence(df_features)
            all_features.extend(new_features)
            logger.info("Done.")
        
        if self.apply_rolling_stats:
            logger.info("Applying rolling statistics to features.")
            df_features, new_features = self._add_sequential_features(df_features)
            all_features.extend(new_features)
            logger.info("Done.")
        
        logger.debug("Completed data cleaning and preprocessing steps.")
        logger.debug(f"Dataframe shape after cleaning: {df_features.shape}")
        logger.debug(f"Dataframe sample after cleaning: {df_features.head()}")
        logger.debug(f"Total features used: {len(all_features)}")
        logger.debug(f"Features: {all_features}")
        self.features = all_features
        
        return self.split_train_test(df_features)
    

class DeprecatedDefaultFeatures(FeatureProcessingPolicy):
    
    def __init__(self, apply_rolling_stats: bool = True, window: int = 5, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.apply_rolling_stats = apply_rolling_stats
        self.window = window
    
    def fetch(self) -> ModelDataset:
        database_path = Path(__file__).parent.parent / "database" / "features.db"
        
        logger.info(f"Fetching features from database at {database_path}")
        conn = sqlite3.connect(database_path)
        
        logger.debug("Connected to the database successfully.")
        logger.debug("Executing SQL query to fetch features.")
        logger.debug(f"SQL Query: \n{self.sql_features}")
        df_features = pd.read_sql_query(self.sql_features, conn)
        
        logger.debug(f"Fetched {len(df_features)} rows from the database.")
        logger.debug(f"Total wells fetched: {len(df_features['well'].unique())}")
        
        if self.apply_presence:
            logger.info("Applying presence indicators to features.")
            df_features = self.build_presence(df_features)
            logger.info("Done.")
        
        if self.apply_rolling_stats:
            logger.info("Applying rolling statistics to features.")
            df_features = self._add_rolling_statistics(df_features, features_columns, window=self.window)
            logger.info("Done.")
        target_column = 'rock'
        features_columns = [
                'depth',
                'GR', 
                'SP', 
                'DT', 
                'CALI', 
                'ILD', 
                'RHOB', 
                'NPHI', 
                'MSFL',
                'DRHO', 
                'SFLU']
        valid_rocks = [
            'FOLHELHO', 'ARENITO', 'SILTITO', 'CALCILUTITO', 'AREIA', 'CALCARENITO',
            'ARGILA', 'CALCARIO', 'CONGLOMERADO', 'ARGILITO', 'ANIDRITA', 'MARGA',
            'GRANITO', 'BASALTO', 'DOLOMITO'
        ]

        for col in features_columns:
            if col == "GR":
                df_features[col] = np.where((df_features[col] >= 0) & (df_features[col] <= 200), df_features[col], np.nan)
            elif col == "SP":
                df_features[col] = np.where((df_features[col] >= -100) & (df_features[col] <= 100), df_features[col], np.nan)
            elif col == "DT":
                df_features[col] = np.where((df_features[col] >= 40) & (df_features[col] <= 140), df_features[col], np.nan)
            elif col == "CALI":
                df_features[col] = np.where((df_features[col] >= 6) & (df_features[col] <= 16), df_features[col], np.nan)
            elif col == "ILD":
                df_features[col] = np.where((df_features[col] >= 0.2) & (df_features[col] <= 2000), df_features[col], np.nan)
            elif col == "RHOB":
                df_features[col] = np.where((df_features[col] >= 1.95) & (df_features[col] <= 2.95), df_features[col], np.nan)
            elif col == "NPHI":
                df_features[col] = np.where((df_features[col] >= 0) & (df_features[col] <= 45), df_features[col], np.nan)
            elif col == "MSFL":
                df_features[col] = np.where((df_features[col] >= 0.2) & (df_features[col] <= 2000), df_features[col], np.nan)
            elif col == "DRHO":
                df_features[col] = np.where((df_features[col] >= -0.1) & (df_features[col] <= 0.3), df_features[col], np.nan)
            elif col == "SFLU":
                df_features[col] = np.where((df_features[col] >= 0.2) & (df_features[col] <= 2000), df_features[col], np.nan)

        # Filter rows based on valid rock types
        df_features["rock"] = np.where(df_features['rock'].isin(valid_rocks), df_features["rock"], np.nan)

        # Add boolean columns indicating null values for each numeric column
        for col in features_columns:
            df_features[f'{col}_is_null'] = df_features[col].isnull().astype(int)

        logger.debug("Completed data cleaning and preprocessing steps.")
        logger.debug(f"Dataframe shape after cleaning: {df_features.shape}")
        logger.debug(f"Dataframe sample after cleaning: {df_features.head()}")
        # Get unique wells
        unique_wells = df_features['well'].unique()

        # Split wells into train and test (80-20 split)
        train_wells, test_wells = train_test_split(unique_wells, test_size=0.2, random_state=42)

        # Create train and test datasets based on well splits
        train_data = df_features[df_features['well'].isin(train_wells)]
        test_data = df_features[df_features['well'].isin(test_wells)]

        train_target = train_data[target_column]
        test_target = test_data[target_column]
        
        feature_cols = features_columns + [f'{col}_is_null' for col in features_columns]
        train_data = train_data[feature_cols]
        test_data = test_data[feature_cols]
        
        logger.debug(f"Num of features: {len(feature_cols)}")
                
        return ModelDataset(train=train_data, train_target=train_target, test=test_data, test_target=test_target)