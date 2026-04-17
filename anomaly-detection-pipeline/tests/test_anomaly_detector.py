"""
Unit tests for anomaly detection algorithms.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

from processing.anomaly_detector import (
    IsolationForestDetector,
    LocalOutlierFactorDetector,
    StatisticalDetector,
    EnsembleDetector,
    create_detector
)


class TestIsolationForestDetector:
    """Test cases for Isolation Forest detector."""
    
    def setup_method(self):
        """Setup test data."""
        self.config = {'contamination': 0.1}
        self.detector = IsolationForestDetector(self.config)
        
        # Generate test data
        np.random.seed(42)
        self.normal_data = np.random.normal(50, 10, 100)
        self.anomaly_data = np.random.normal(100, 5, 20)
        self.test_data = np.concatenate([self.normal_data, self.anomaly_data])
    
    def test_initialization(self):
        """Test detector initialization."""
        assert self.detector.config == self.config
        assert not self.detector.is_fitted
    
    def test_fit(self):
        """Test model fitting."""
        self.detector.fit(self.normal_data)
        assert self.detector.is_fitted
        assert hasattr(self.detector, 'model')
        assert hasattr(self.detector, 'scaler')
    
    def test_detect_normal_data(self):
        """Test detection on normal data."""
        self.detector.fit(self.normal_data)
        
        # Test with normal data point
        result = self.detector.detect({'value': 50.0})
        
        assert isinstance(result, dict)
        assert 'is_anomaly' in result
        assert 'score' in result
        assert 'type' in result
        assert result['type'] == 'isolation_forest'
    
    def test_detect_anomaly_data(self):
        """Test detection on anomaly data."""
        self.detector.fit(self.normal_data)
        
        # Test with anomaly data point
        result = self.detector.detect({'value': 100.0})
        
        assert isinstance(result, dict)
        assert 'is_anomaly' in result
        assert 'score' in result
        assert 'type' in result
    
    def test_detect_unfitted_model(self):
        """Test detection without fitting."""
        result = self.detector.detect({'value': 50.0})
        
        assert result['is_anomaly'] is False
        assert result['score'] == 0.0
        assert result['type'] == 'unknown'


class TestStatisticalDetector:
    """Test cases for Statistical detector."""
    
    def setup_method(self):
        """Setup test data."""
        self.config = {'method': 'zscore', 'threshold': 3.0, 'window_size': 100}
        self.detector = StatisticalDetector(self.config)
        
        # Generate test data
        np.random.seed(42)
        self.normal_data = np.random.normal(50, 10, 100)
    
    def test_initialization(self):
        """Test detector initialization."""
        assert self.detector.method == 'zscore'
        assert self.detector.threshold == 3.0
        assert self.detector.window_size == 100
        assert len(self.detector.data_buffer) == 0
    
    def test_fit(self):
        """Test model fitting."""
        self.detector.fit(self.normal_data)
        assert self.detector.is_fitted
        assert len(self.detector.data_buffer) == len(self.normal_data)
    
    def test_zscore_detection(self):
        """Test z-score based detection."""
        self.detector.fit(self.normal_data)
        
        # Test normal value
        result = self.detector.detect({'value': 50.0})
        assert isinstance(result, dict)
        assert result['type'] == 'zscore'
        
        # Test anomaly value
        result = self.detector.detect({'value': 100.0})
        assert isinstance(result, dict)
    
    def test_iqr_detection(self):
        """Test IQR based detection."""
        self.detector.method = 'iqr'
        self.detector.fit(self.normal_data)
        
        result = self.detector.detect({'value': 50.0})
        assert result['type'] == 'iqr'
    
    def test_window_size_limit(self):
        """Test window size limiting."""
        self.detector.fit(self.normal_data)
        
        # Add more data than window size
        for i in range(150):
            self.detector.detect({'value': float(i)})
        
        assert len(self.detector.data_buffer) <= self.detector.window_size


class TestEnsembleDetector:
    """Test cases for Ensemble detector."""
    
    def setup_method(self):
        """Setup test data."""
        self.config = {
            'detectors': {
                'isolation_forest': {'contamination': 0.1},
                'statistical': {'method': 'zscore', 'threshold': 3.0}
            },
            'weights': {'isolation_forest': 0.6, 'statistical': 0.4},
            'threshold': 0.5
        }
        self.detector = EnsembleDetector(self.config)
        
        # Generate test data
        np.random.seed(42)
        self.normal_data = np.random.normal(50, 10, 100)
    
    def test_initialization(self):
        """Test detector initialization."""
        assert len(self.detector.detectors) == 2
        assert 'isolation_forest' in self.detector.detectors
        assert 'statistical' in self.detector.detectors
        assert self.detector.weights == self.config['weights']
    
    def test_fit(self):
        """Test ensemble fitting."""
        self.detector.fit(self.normal_data)
        assert self.detector.is_fitted
        
        # Check that all detectors are fitted
        for detector in self.detector.detectors.values():
            assert detector.is_fitted
    
    def test_detect(self):
        """Test ensemble detection."""
        self.detector.fit(self.normal_data)
        
        result = self.detector.detect({'value': 50.0})
        
        assert isinstance(result, dict)
        assert 'is_anomaly' in result
        assert 'score' in result
        assert 'type' in result
        assert result['type'] == 'ensemble'
        assert 'detector_results' in result
        
        # Check individual detector results
        detector_results = result['detector_results']
        assert 'isolation_forest' in detector_results
        assert 'statistical' in detector_results


class TestDetectorFactory:
    """Test cases for detector factory function."""
    
    def test_create_isolation_forest(self):
        """Test creating Isolation Forest detector."""
        config = {'contamination': 0.1}
        detector = create_detector('isolation_forest', config)
        
        assert isinstance(detector, IsolationForestDetector)
        assert detector.config == config
    
    def test_create_statistical(self):
        """Test creating Statistical detector."""
        config = {'method': 'zscore', 'threshold': 3.0}
        detector = create_detector('statistical', config)
        
        assert isinstance(detector, StatisticalDetector)
        assert detector.config == config
    
    def test_create_ensemble(self):
        """Test creating Ensemble detector."""
        config = {
            'detectors': {
                'isolation_forest': {'contamination': 0.1},
                'statistical': {'method': 'zscore', 'threshold': 3.0}
            }
        }
        detector = create_detector('ensemble', config)
        
        assert isinstance(detector, EnsembleDetector)
        assert detector.config == config
    
    def test_create_unknown_detector(self):
        """Test creating unknown detector type."""
        with pytest.raises(ValueError, match="Unknown detector type"):
            create_detector('unknown_type', {})


class TestDataPreparation:
    """Test cases for data preparation methods."""
    
    def setup_method(self):
        """Setup test data."""
        self.detector = IsolationForestDetector({})
    
    def test_prepare_dict_data(self):
        """Test preparing dictionary data."""
        data = {'value': 50.0}
        result = self.detector._prepare_data(data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1)
        assert result[0, 0] == 50.0
    
    def test_prepare_list_data(self):
        """Test preparing list data."""
        data = [50.0, 60.0, 70.0]
        result = self.detector._prepare_data(data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 1)
        assert result[0, 0] == 50.0
    
    def test_prepare_numpy_data(self):
        """Test preparing numpy array data."""
        data = np.array([50.0, 60.0, 70.0])
        result = self.detector._prepare_data(data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 1)
    
    def test_prepare_scalar_data(self):
        """Test preparing scalar data."""
        data = 50.0
        result = self.detector._prepare_data(data)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1)
        assert result[0, 0] == 50.0


if __name__ == "__main__":
    pytest.main([__file__])




