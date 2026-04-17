"""
Model Trainer for Anomaly Detection

Handles training of various anomaly detection models with hyperparameter tuning
and model selection.
"""

import os
import json
import pickle
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix
import joblib

from processing.anomaly_detector import create_detector


class ModelTrainer:
    """Trainer for anomaly detection models."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model trainer.
        
        Args:
            config: Configuration dictionary for training
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.models_dir = config.get('models_dir', 'models/saved')
        self.experiments_dir = config.get('experiments_dir', 'models/experiments')
        
        # Create directories if they don't exist
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.experiments_dir, exist_ok=True)
        
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare data for training.
        
        Args:
            data: Input DataFrame with features and labels
            
        Returns:
            Tuple of (features, labels)
        """
        # Extract features and labels
        feature_columns = self.config.get('feature_columns', ['value'])
        label_column = self.config.get('label_column', 'is_anomaly')
        
        X = data[feature_columns].values
        y = data[label_column].values if label_column in data.columns else None
        
        return X, y
    
    def train_model(self, model_type: str, train_data: pd.DataFrame, 
                   validation_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Train a single model.
        
        Args:
            model_type: Type of model to train
            train_data: Training data
            validation_data: Optional validation data
            
        Returns:
            Training results dictionary
        """
        self.logger.info(f"Training {model_type} model...")
        
        # Prepare data
        X_train, y_train = self.prepare_data(train_data)
        
        # Create detector
        detector_config = self.config.get('detector_configs', {}).get(model_type, {})
        detector = create_detector(model_type, detector_config)
        
        # Train the model
        start_time = datetime.now()
        detector.fit(X_train)
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Evaluate on validation data if provided
        validation_metrics = None
        if validation_data is not None:
            validation_metrics = self.evaluate_model(detector, validation_data)
        
        # Save model
        model_path = self.save_model(detector, model_type)
        
        results = {
            'model_type': model_type,
            'model_path': model_path,
            'training_time': training_time,
            'validation_metrics': validation_metrics,
            'config': detector_config,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Training completed for {model_type} in {training_time:.2f}s")
        return results
    
    def train_multiple_models(self, train_data: pd.DataFrame, 
                            validation_data: Optional[pd.DataFrame] = None,
                            model_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Train multiple models and compare their performance.
        
        Args:
            train_data: Training data
            validation_data: Optional validation data
            model_types: List of model types to train
            
        Returns:
            Dictionary with training results for all models
        """
        if model_types is None:
            model_types = ['isolation_forest', 'statistical', 'ensemble']
        
        results = {}
        
        for model_type in model_types:
            try:
                result = self.train_model(model_type, train_data, validation_data)
                results[model_type] = result
            except Exception as e:
                self.logger.error(f"Failed to train {model_type}: {e}")
                results[model_type] = {'error': str(e)}
        
        return results
    
    def hyperparameter_tuning(self, model_type: str, train_data: pd.DataFrame,
                            param_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning using grid search.
        
        Args:
            model_type: Type of model to tune
            train_data: Training data
            param_grid: Parameter grid for tuning
            
        Returns:
            Tuning results
        """
        self.logger.info(f"Performing hyperparameter tuning for {model_type}...")
        
        X_train, y_train = self.prepare_data(train_data)
        
        # Create base detector
        detector_config = self.config.get('detector_configs', {}).get(model_type, {})
        detector = create_detector(model_type, detector_config)
        
        # Perform grid search
        cv = TimeSeriesSplit(n_splits=5)
        grid_search = GridSearchCV(
            detector,
            param_grid,
            cv=cv,
            scoring='f1',
            n_jobs=-1,
            verbose=1
        )
        
        grid_search.fit(X_train, y_train)
        
        # Get best model
        best_detector = grid_search.best_estimator_
        best_params = grid_search.best_params_
        best_score = grid_search.best_score_
        
        # Save best model
        model_path = self.save_model(best_detector, f"{model_type}_tuned")
        
        results = {
            'model_type': model_type,
            'best_params': best_params,
            'best_score': best_score,
            'model_path': model_path,
            'cv_results': grid_search.cv_results_,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Hyperparameter tuning completed. Best score: {best_score:.4f}")
        return results
    
    def evaluate_model(self, detector, test_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Evaluate a trained model on test data.
        
        Args:
            detector: Trained anomaly detector
            test_data: Test data
            
        Returns:
            Evaluation metrics
        """
        X_test, y_test = self.prepare_data(test_data)
        
        # Make predictions
        predictions = []
        scores = []
        
        for i, x in enumerate(X_test):
            result = detector.detect({'value': x[0]})
            predictions.append(result['is_anomaly'])
            scores.append(result['score'])
        
        predictions = np.array(predictions)
        scores = np.array(scores)
        
        # Calculate metrics
        if y_test is not None:
            # Classification metrics
            report = classification_report(y_test, predictions, output_dict=True)
            conf_matrix = confusion_matrix(y_test, predictions).tolist()
            
            metrics = {
                'precision': report['weighted avg']['precision'],
                'recall': report['weighted avg']['recall'],
                'f1_score': report['weighted avg']['f1-score'],
                'accuracy': report['accuracy'],
                'confusion_matrix': conf_matrix
            }
        else:
            metrics = {
                'anomaly_rate': np.mean(predictions),
                'avg_score': np.mean(scores),
                'score_std': np.std(scores)
            }
        
        return metrics
    
    def save_model(self, detector, model_name: str) -> str:
        """
        Save a trained model to disk.
        
        Args:
            detector: Trained detector to save
            model_name: Name for the model
            
        Returns:
            Path to saved model
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"{model_name}_{timestamp}.pkl"
        model_path = os.path.join(self.models_dir, model_filename)
        
        with open(model_path, 'wb') as f:
            pickle.dump(detector, f)
        
        self.logger.info(f"Model saved to {model_path}")
        return model_path
    
    def load_model(self, model_path: str):
        """
        Load a trained model from disk.
        
        Args:
            model_path: Path to the saved model
            
        Returns:
            Loaded detector
        """
        with open(model_path, 'rb') as f:
            detector = pickle.load(f)
        
        return detector
    
    def create_experiment_report(self, results: Dict[str, Any]) -> str:
        """
        Create a detailed experiment report.
        
        Args:
            results: Training results
            
        Returns:
            Path to the report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"experiment_report_{timestamp}.json"
        report_path = os.path.join(self.experiments_dir, report_filename)
        
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"Experiment report saved to {report_path}")
        return report_path


class AutoMLTrainer(ModelTrainer):
    """Automated machine learning trainer for anomaly detection."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.auto_ml_config = config.get('auto_ml', {})
    
    def auto_train(self, train_data: pd.DataFrame, 
                  validation_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Automatically train and select the best model.
        
        Args:
            train_data: Training data
            validation_data: Optional validation data
            
        Returns:
            Best model results
        """
        self.logger.info("Starting automated model training...")
        
        # Define model types to try
        model_types = self.auto_ml_config.get('model_types', [
            'isolation_forest', 'statistical', 'ensemble'
        ])
        
        # Train all models
        results = self.train_multiple_models(train_data, validation_data, model_types)
        
        # Select best model based on validation metrics
        best_model = None
        best_score = -1
        
        for model_type, result in results.items():
            if 'error' not in result and result.get('validation_metrics'):
                metrics = result['validation_metrics']
                score = metrics.get('f1_score', 0)
                
                if score > best_score:
                    best_score = score
                    best_model = model_type
        
        if best_model:
            self.logger.info(f"Best model: {best_model} with F1 score: {best_score:.4f}")
            results['best_model'] = best_model
            results['best_score'] = best_score
        
        return results


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Generate sample data
    np.random.seed(42)
    n_samples = 1000
    
    # Normal data
    normal_data = np.random.normal(50, 10, int(n_samples * 0.9))
    # Anomaly data
    anomaly_data = np.random.normal(100, 5, int(n_samples * 0.1))
    
    # Create DataFrame
    data = pd.DataFrame({
        'value': np.concatenate([normal_data, anomaly_data]),
        'is_anomaly': [False] * len(normal_data) + [True] * len(anomaly_data)
    })
    
    # Shuffle data
    data = data.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Split data
    train_size = int(0.7 * len(data))
    train_data = data[:train_size]
    test_data = data[train_size:]
    
    # Configuration
    config = {
        'models_dir': 'models/saved',
        'experiments_dir': 'models/experiments',
        'feature_columns': ['value'],
        'label_column': 'is_anomaly',
        'detector_configs': {
            'isolation_forest': {'contamination': 0.1},
            'statistical': {'method': 'zscore', 'threshold': 3.0},
            'ensemble': {
                'detectors': {
                    'isolation_forest': {'contamination': 0.1},
                    'statistical': {'method': 'zscore', 'threshold': 3.0}
                },
                'weights': {'isolation_forest': 0.6, 'statistical': 0.4},
                'threshold': 0.5
            }
        }
    }
    
    # Train models
    trainer = ModelTrainer(config)
    results = trainer.train_multiple_models(train_data, test_data)
    
    print("\nTraining Results:")
    for model_type, result in results.items():
        if 'error' not in result:
            print(f"{model_type}: {result['validation_metrics']}")
        else:
            print(f"{model_type}: Error - {result['error']}")




