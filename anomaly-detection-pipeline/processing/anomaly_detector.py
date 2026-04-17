"""
Anomaly Detection Module

Implements various anomaly detection algorithms for real-time stream processing.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
import logging

from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN


class AnomalyDetector(ABC):
    """Abstract base class for anomaly detection algorithms."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the anomaly detector.
        
        Args:
            config: Configuration dictionary for the detector
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.is_fitted = False
        
    @abstractmethod
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'AnomalyDetector':
        """Fit the anomaly detection model."""
        pass
    
    @abstractmethod
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies in the data."""
        pass
    
    def _prepare_data(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> np.ndarray:
        """Prepare data for anomaly detection."""
        if isinstance(data, dict):
            # Extract value from dictionary
            value = data.get('value', data.get('data', 0))
            return np.array([[value]])
        elif isinstance(data, (list, pd.Series)):
            return np.array(data).reshape(-1, 1)
        elif isinstance(data, np.ndarray):
            return data.reshape(-1, 1)
        else:
            return np.array([[data]])


class IsolationForestDetector(AnomalyDetector):
    """Isolation Forest anomaly detector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = IsolationForest(
            contamination=config.get('contamination', 0.1),
            random_state=config.get('random_state', 42),
            n_estimators=config.get('n_estimators', 100)
        )
        self.scaler = StandardScaler()
        
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'IsolationForestDetector':
        """Fit the Isolation Forest model."""
        X = self._prepare_data(data)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        return self
    
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies using Isolation Forest."""
        if not self.is_fitted:
            self.logger.warning("Model not fitted. Using default prediction.")
            return {'is_anomaly': False, 'score': 0.0, 'type': 'unknown'}
        
        X = self._prepare_data(data)
        X_scaled = self.scaler.transform(X)
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(X_scaled)
        # Get anomaly score (lower = more anomalous)
        score = self.model.score_samples(X_scaled)
        
        is_anomaly = prediction[0] == -1
        anomaly_score = 1 - score[0]  # Convert to 0-1 scale where 1 is most anomalous
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(anomaly_score),
            'type': 'isolation_forest'
        }


class LocalOutlierFactorDetector(AnomalyDetector):
    """Local Outlier Factor anomaly detector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = LocalOutlierFactor(
            contamination=config.get('contamination', 0.1),
            n_neighbors=config.get('n_neighbors', 20),
            novelty=True
        )
        self.scaler = StandardScaler()
        
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'LocalOutlierFactorDetector':
        """Fit the LOF model."""
        X = self._prepare_data(data)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        return self
    
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies using Local Outlier Factor."""
        if not self.is_fitted:
            self.logger.warning("Model not fitted. Using default prediction.")
            return {'is_anomaly': False, 'score': 0.0, 'type': 'unknown'}
        
        X = self._prepare_data(data)
        X_scaled = self.scaler.transform(X)
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(X_scaled)
        # Get decision function score
        score = self.model.decision_function(X_scaled)
        
        is_anomaly = prediction[0] == -1
        anomaly_score = 1 - score[0]  # Convert to 0-1 scale
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(anomaly_score),
            'type': 'local_outlier_factor'
        }


class OneClassSVMDetector(AnomalyDetector):
    """One-Class SVM anomaly detector."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = OneClassSVM(
            nu=config.get('nu', 0.1),
            kernel=config.get('kernel', 'rbf'),
            gamma=config.get('gamma', 'scale')
        )
        self.scaler = StandardScaler()
        
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'OneClassSVMDetector':
        """Fit the One-Class SVM model."""
        X = self._prepare_data(data)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        return self
    
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies using One-Class SVM."""
        if not self.is_fitted:
            self.logger.warning("Model not fitted. Using default prediction.")
            return {'is_anomaly': False, 'score': 0.0, 'type': 'unknown'}
        
        X = self._prepare_data(data)
        X_scaled = self.scaler.transform(X)
        
        # Predict anomaly (-1 for anomaly, 1 for normal)
        prediction = self.model.predict(X_scaled)
        # Get decision function score
        score = self.model.decision_function(X_scaled)
        
        is_anomaly = prediction[0] == -1
        anomaly_score = 1 - score[0]  # Convert to 0-1 scale
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(anomaly_score),
            'type': 'one_class_svm'
        }


class StatisticalDetector(AnomalyDetector):
    """Statistical-based anomaly detector using z-score and IQR methods."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.method = config.get('method', 'zscore')
        self.threshold = config.get('threshold', 3.0)
        self.window_size = config.get('window_size', 100)
        self.data_buffer = []
        
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'StatisticalDetector':
        """Initialize the statistical detector with historical data."""
        if isinstance(data, (list, pd.Series)):
            self.data_buffer = list(data)
        elif isinstance(data, np.ndarray):
            self.data_buffer = data.flatten().tolist()
        
        self.is_fitted = True
        return self
    
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies using statistical methods."""
        if not self.is_fitted or len(self.data_buffer) < 10:
            return {'is_anomaly': False, 'score': 0.0, 'type': 'statistical'}
        
        # Extract current value
        if isinstance(data, dict):
            current_value = data.get('value', 0)
        else:
            current_value = float(data)
        
        # Update buffer
        self.data_buffer.append(current_value)
        if len(self.data_buffer) > self.window_size:
            self.data_buffer.pop(0)
        
        # Calculate statistics
        if self.method == 'zscore':
            result = self._zscore_detection(current_value)
        elif self.method == 'iqr':
            result = self._iqr_detection(current_value)
        else:
            result = self._zscore_detection(current_value)
        
        return result
    
    def _zscore_detection(self, value: float) -> Dict[str, Any]:
        """Detect anomalies using z-score method."""
        mean_val = np.mean(self.data_buffer[:-1])  # Exclude current value
        std_val = np.std(self.data_buffer[:-1])
        
        if std_val == 0:
            return {'is_anomaly': False, 'score': 0.0, 'type': 'zscore'}
        
        z_score = abs((value - mean_val) / std_val)
        is_anomaly = z_score > self.threshold
        anomaly_score = min(z_score / self.threshold, 1.0)
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(anomaly_score),
            'type': 'zscore'
        }
    
    def _iqr_detection(self, value: float) -> Dict[str, Any]:
        """Detect anomalies using IQR method."""
        q1 = np.percentile(self.data_buffer[:-1], 25)
        q3 = np.percentile(self.data_buffer[:-1], 75)
        iqr = q3 - q1
        
        lower_bound = q1 - self.threshold * iqr
        upper_bound = q3 + self.threshold * iqr
        
        is_anomaly = value < lower_bound or value > upper_bound
        
        if is_anomaly:
            if value < lower_bound:
                distance = (lower_bound - value) / iqr
            else:
                distance = (value - upper_bound) / iqr
            anomaly_score = min(distance / self.threshold, 1.0)
        else:
            anomaly_score = 0.0
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(anomaly_score),
            'type': 'iqr'
        }


class EnsembleDetector(AnomalyDetector):
    """Ensemble anomaly detector combining multiple methods."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.detectors = {}
        self.weights = config.get('weights', {})
        
        # Initialize detectors
        detector_configs = config.get('detectors', {})
        
        if 'isolation_forest' in detector_configs:
            self.detectors['isolation_forest'] = IsolationForestDetector(
                detector_configs['isolation_forest']
            )
        
        if 'lof' in detector_configs:
            self.detectors['lof'] = LocalOutlierFactorDetector(
                detector_configs['lof']
            )
        
        if 'statistical' in detector_configs:
            self.detectors['statistical'] = StatisticalDetector(
                detector_configs['statistical']
            )
    
    def fit(self, data: Union[np.ndarray, List[float], pd.Series]) -> 'EnsembleDetector':
        """Fit all detectors."""
        for detector in self.detectors.values():
            detector.fit(data)
        self.is_fitted = True
        return self
    
    def detect(self, data: Union[np.ndarray, List[float], pd.Series, Dict[str, Any]]) -> Dict[str, Any]:
        """Detect anomalies using ensemble of detectors."""
        if not self.is_fitted:
            return {'is_anomaly': False, 'score': 0.0, 'type': 'ensemble'}
        
        results = {}
        weighted_score = 0.0
        total_weight = 0.0
        
        for name, detector in self.detectors.items():
            result = detector.detect(data)
            results[name] = result
            
            weight = self.weights.get(name, 1.0)
            weighted_score += result['score'] * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0.0
        
        # Determine if anomaly based on threshold
        threshold = self.config.get('threshold', 0.5)
        is_anomaly = final_score > threshold
        
        return {
            'is_anomaly': is_anomaly,
            'score': float(final_score),
            'type': 'ensemble',
            'detector_results': results
        }


# Factory function to create detectors
def create_detector(detector_type: str, config: Dict[str, Any]) -> AnomalyDetector:
    """Create an anomaly detector based on type."""
    if detector_type == 'isolation_forest':
        return IsolationForestDetector(config)
    elif detector_type == 'lof':
        return LocalOutlierFactorDetector(config)
    elif detector_type == 'one_class_svm':
        return OneClassSVMDetector(config)
    elif detector_type == 'statistical':
        return StatisticalDetector(config)
    elif detector_type == 'ensemble':
        return EnsembleDetector(config)
    else:
        raise ValueError(f"Unknown detector type: {detector_type}")


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Generate sample data
    np.random.seed(42)
    normal_data = np.random.normal(50, 10, 1000)
    anomaly_data = np.random.normal(100, 5, 50)  # Anomalies
    test_data = np.concatenate([normal_data, anomaly_data])
    
    # Test different detectors
    configs = {
        'isolation_forest': {'contamination': 0.05},
        'statistical': {'method': 'zscore', 'threshold': 3.0},
        'ensemble': {
            'detectors': {
                'isolation_forest': {'contamination': 0.05},
                'statistical': {'method': 'zscore', 'threshold': 3.0}
            },
            'weights': {'isolation_forest': 0.6, 'statistical': 0.4},
            'threshold': 0.5
        }
    }
    
    for detector_type, config in configs.items():
        print(f"\nTesting {detector_type} detector:")
        detector = create_detector(detector_type, config)
        detector.fit(normal_data[:500])  # Fit on normal data
        
        # Test on some data points
        for i in range(5):
            test_point = test_data[i]
            result = detector.detect({'value': test_point})
            print(f"Value: {test_point:.2f}, Anomaly: {result['is_anomaly']}, Score: {result['score']:.3f}")

