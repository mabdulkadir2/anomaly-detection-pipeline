"""
Synthetic Data Producer

Generates synthetic time series data with embedded anomalies for testing
the anomaly detection pipeline.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random

from .data_producer import DataProducer


class SyntheticDataProducer(DataProducer):
    """Generates synthetic time series data with anomalies."""
    
    def __init__(self, kafka_config: Dict[str, Any], data_source: str):
        """
        Initialize synthetic data producer.
        
        Args:
            kafka_config: Kafka configuration
            data_source: Source identifier
        """
        super().__init__(kafka_config)
        self.data_source = data_source
        self.current_time = datetime.now()
        self.anomaly_probability = 0.05  # 5% chance of anomaly
        self.base_value = 50.0
        self.noise_std = 5.0
        
    def generate_normal_data(self) -> float:
        """Generate normal data point with some noise."""
        # Add some trend and seasonality
        time_factor = (self.current_time.hour - 12) / 12  # -1 to 1 over 24 hours
        trend = 10 * np.sin(2 * np.pi * time_factor)
        noise = np.random.normal(0, self.noise_std)
        
        return self.base_value + trend + noise
    
    def generate_anomaly(self, normal_value: float) -> float:
        """Generate an anomalous data point."""
        anomaly_types = ['spike', 'drop', 'drift']
        anomaly_type = random.choice(anomaly_types)
        
        if anomaly_type == 'spike':
            return normal_value + np.random.uniform(20, 50)
        elif anomaly_type == 'drop':
            return normal_value - np.random.uniform(20, 50)
        else:  # drift
            return normal_value + np.random.uniform(-30, 30)
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate a single data point with potential anomaly."""
        # Update time
        self.current_time += timedelta(seconds=1)
        
        # Generate base value
        normal_value = self.generate_normal_data()
        
        # Check for anomaly
        is_anomaly = random.random() < self.anomaly_probability
        value = self.generate_anomaly(normal_value) if is_anomaly else normal_value
        
        return {
            'source': self.data_source,
            'value': round(value, 2),
            'metric': 'cpu_usage',
            'timestamp': self.current_time.isoformat(),
            'is_anomaly': is_anomaly,
            'normal_value': round(normal_value, 2) if is_anomaly else None
        }
    
    def generate_batch(self, num_points: int) -> List[Dict[str, Any]]:
        """Generate a batch of data points."""
        data_points = []
        for _ in range(num_points):
            data_points.append(self.generate_data())
        return data_points
    
    def run(self, topic: str, interval: float = 1.0, max_messages: Optional[int] = None):
        """Run the synthetic data producer."""
        self.logger.info(f"Starting synthetic data producer for topic: {topic}")
        
        message_count = 0
        anomaly_count = 0
        
        try:
            while max_messages is None or message_count < max_messages:
                data = self.generate_data()
                
                if data['is_anomaly']:
                    anomaly_count += 1
                    self.logger.info(f"Generated anomaly: {data['value']} (normal: {data['normal_value']})")
                
                self.publish_data(topic, data, key=self.data_source)
                message_count += 1
                
                if message_count % 100 == 0:
                    anomaly_rate = (anomaly_count / message_count) * 100
                    self.logger.info(f"Sent {message_count} messages, {anomaly_rate:.1f}% anomalies")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Synthetic data producer stopped by user")
        finally:
            self.close()
            final_anomaly_rate = (anomaly_count / message_count) * 100 if message_count > 0 else 0
            self.logger.info(f"Producer finished. Sent {message_count} messages, {final_anomaly_rate:.1f}% anomalies")


class MultiSourceSyntheticProducer:
    """Produces synthetic data from multiple sources simultaneously."""
    
    def __init__(self, kafka_config: Dict[str, Any], sources: List[str]):
        """
        Initialize multi-source producer.
        
        Args:
            kafka_config: Kafka configuration
            sources: List of source identifiers
        """
        self.kafka_config = kafka_config
        self.sources = sources
        self.producers = {}
        
        for source in sources:
            self.producers[source] = SyntheticDataProducer(kafka_config, source)
    
    def run(self, topic: str, interval: float = 1.0, max_messages: Optional[int] = None):
        """Run all producers simultaneously."""
        import threading
        import time
        
        threads = []
        
        for source, producer in self.producers.items():
            thread = threading.Thread(
                target=producer.run,
                args=(topic, interval, max_messages),
                name=f"producer-{source}"
            )
            threads.append(thread)
            thread.start()
        
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            print("Stopping all producers...")


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    kafka_config = {
        'bootstrap_servers': ['localhost:9092'],
        'producer_config': {
            'acks': 'all',
            'retries': 3
        }
    }
    
    # Single source
    producer = SyntheticDataProducer(kafka_config, "sensor_01")
    producer.run("raw-data", interval=0.5, max_messages=100)
    
    # Multiple sources
    # sources = ["sensor_01", "sensor_02", "sensor_03"]
    # multi_producer = MultiSourceSyntheticProducer(kafka_config, sources)
    # multi_producer.run("raw-data", interval=1.0, max_messages=50)

