import argparse
import os
import optuna
import yaml
from pathlib import Path
from slide.models import BaseModel, ModelDataset
from slide.models.featurePolicy import DefaultFeatures
from slide.models.forest import RandomForest
from slide.models.xgboost import XGBoost
from slide.models.knn import KNN
from slide.models.lstm import LSTM
from slide.models.tree import DecisionTree
from slide.models.logistic import LogisticRegression
from slide.models.bilstm import BILSTM

from slide.logger import Logger


logging = Logger()
logger = logging.get_logger()

model_classes_map: dict[str, BaseModel] = {
    "XGBoost": XGBoost,
    "RandomForest": RandomForest,
    "KNN": KNN,
    "DecisionTree": DecisionTree,
    "LogisticRegression": LogisticRegression,
    "LSTM": LSTM,
    "BILSTM": BILSTM
}
    
def load_config(config_path: str) -> dict:
    """
    Load YAML configuration file.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Dictionary with configuration
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_model_params(trial: optuna.Trial, params: dict) -> dict:
    model_params = {}
    for param_name, param_values in params.items():
        if isinstance(param_values, dict):
            min_val = param_values.get("low")
            if isinstance(min_val, int):
                v = trial.suggest_int(param_name, **param_values)
            elif isinstance(min_val, float):
                v = trial.suggest_float(param_name, **param_values)
        elif isinstance(param_values, list) and isinstance(param_values[0], (int, float, str, bool)):
            v = trial.suggest_categorical(param_name, param_values)
        else:
            v = param_values  # Use as is if not a list
        model_params[param_name] = v
    return model_params

def objective(trial: optuna.Trial, data: ModelDataset, model_type: str, params: dict) -> float:
    logger.info(f"Starting trial {trial.number}")
    model_params = load_model_params(trial, params)
    logger.debug(f"Model parameters for trial {trial.number}: {model_params}")
    model: BaseModel = model_classes_map[model_type](**model_params)
    
    # Train the model
    model.train(data)
    
    # Evaluate the model
    results = model.evaluate(data)
    
    trial.set_user_attr("f1_macro", results["f1_macro"])
    trial.set_user_attr("accuracy", results["accuracy"])
    trial.set_user_attr("f1_weighted", results["f1_weighted"])
    trial.set_user_attr("confusion_matrix", results["confusion_matrix"])
    trial.set_user_attr("classification_report", results["classification_report"])
    
    best_value = 0
    try:
        best_value = trial.study.best_value
    except Exception:
        pass
    
    if results["f1_macro"] > best_value:
        logger.info(f"New best F1 (macro): {results['f1_macro']:.4f} with params: {model_params}")
        os.makedirs("models/checkpoints", exist_ok=True)
        model.save(f"models/checkpoints/{trial.study.study_name}.pkl")
    # Return the metric to optimize (e.g., accuracy)
    return results["f1_macro"]


def main():
    parser = argparse.ArgumentParser(
        description="GeoAI ANP Data Extractor - Train and evaluate lithology classification models"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        dest="log_level",
        help="Set the logging level"
    )
    parser.add_argument(
        "--model-config",
        type=str,
        required=True,
        dest="model_config",
        help="Path to model configuration YAML file"
    )
    
    parser.add_argument(
        "--policy-config",
        type=str,
        required=True,
        dest="policy_config",
        help="Path to feature processing policy configuration YAML file"
    )
    
    args = parser.parse_args()
    
    args_dict = vars(args).copy()
    logging.set_level(args_dict.pop("log_level"))
    
    # Validate config files exist
    model_config_path = Path(args.model_config)
    policy_config_path = Path(args.policy_config)
    
    if not model_config_path.exists():
        raise FileNotFoundError(f"Model config file not found: {model_config_path}")
    
    if not policy_config_path.exists():
        raise FileNotFoundError(f"Policy config file not found: {policy_config_path}")
    
    # Load configurations
    model_config = load_config(args.model_config)
    policy_config = load_config(args.policy_config)
    logger.info("Model Config:", model_config)
    logger.info("Policy Config:", policy_config)
    
    
    data_policy = DefaultFeatures(**policy_config["policy"])
    data = data_policy.fetch()
    
    
    # Specify the SQLite database file
    storage = "sqlite:///optuna_studies_latest.db"
    study_name = f"{model_config['model_type'].lower()}_{str(args.policy_config).split('/')[-1].split('.')[0]}"
    
    # Create or load an Optuna study
    study = optuna.create_study(direction="maximize", storage=storage, study_name=study_name, load_if_exists=True)
    study.optimize(lambda trial: objective(trial, data=data, **model_config), n_trials=15, gc_after_trial=True)
    logger.info(f"Best trial: {study.best_trial.params}")
    logger.info(f"Best parameters: {study.best_trial.params}")

if __name__ == "__main__":
    main()