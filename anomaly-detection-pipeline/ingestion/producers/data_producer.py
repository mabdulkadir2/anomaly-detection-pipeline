"""
Data Producer for Anomaly Detection Pipeline

Handles data ingestion from various sources and publishes to Kafka topics.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd

from kafka import KafkaProducer
from kafka.errors import KafkaError


class DataProducer(ABC):
    """Abstract base class for data producers."""
    
    def __init__(self, kafka_config: Dict[str, Any]):
        """
        Initialize the data producer.
        
        Args:
            kafka_config: Kafka configuration dictionary
        """
        self.kafka_config = kafka_config
        self.producer = None
        self.logger = logging.getLogger(__name__)
        
    @abstractmethod
    def generate_data(self) -> Dict[str, Any]:
        """Generate data to be published."""
        pass
    
    def connect_kafka(self):
        """Establish connection to Kafka cluster."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_config['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                **self.kafka_config.get('producer_config', {})
            )
            self.logger.info("Successfully connected to Kafka")
        except Exception as e:
            self.logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def publish_data(self, topic: str, data: Dict[str, Any], key: Optional[str] = None):
        """
        Publish data to Kafka topic.
        
        Args:
            topic: Kafka topic name
            data: Data to publish
            key: Optional message key
        """
        if not self.producer:
            self.connect_kafka()
            
        try:
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
                
            future = self.producer.send(topic, value=data, key=key)
            record_metadata = future.get(timeout=10)
            
            self.logger.debug(
                f"Data published to {topic} "
                f"[partition: {record_metadata.partition}, "
                f"offset: {record_metadata.offset}]"
            )
            
        except KafkaError as e:
            self.logger.error(f"Failed to publish data to {topic}: {e}")
            raise
    
    def close(self):
        """Close the Kafka producer connection."""
        if self.producer:
            self.producer.close()
            self.logger.info("Kafka producer connection closed")


class KafkaProducer(DataProducer):
    """Kafka-specific data producer implementation."""
    
    def __init__(self, kafka_config: Dict[str, Any], data_source: str):
        """
        Initialize Kafka producer.
        
        Args:
            kafka_config: Kafka configuration
            data_source: Source identifier for the data
        """
        super().__init__(kafka_config)
        self.data_source = data_source
        
    def generate_data(self) -> Dict[str, Any]:
        """Generate sample data for testing."""
        return {
            'source': self.data_source,
            'value': 100.0,
            'metric': 'cpu_usage',
            'timestamp': datetime.now().isoformat()
        }
    
    def run(self, topic: str, interval: float = 1.0, max_messages: Optional[int] = None):
        """
        Run the producer continuously.
        
        Args:
            topic: Kafka topic to publish to
            interval: Time interval between messages (seconds)
            max_messages: Maximum number of messages to send (None for infinite)
        """
        self.logger.info(f"Starting producer for topic: {topic}")
        
        message_count = 0
        try:
            while max_messages is None or message_count < max_messages:
                data = self.generate_data()
                self.publish_data(topic, data, key=self.data_source)
                message_count += 1
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Producer stopped by user")
        finally:
            self.close()
            self.logger.info(f"Producer finished. Sent {message_count} messages")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    kafka_config = {
        'bootstrap_servers': ['localhost:9092'],
        'producer_config': {
            'acks': 'all',
            'retries': 3
        }
    }
    
    producer = KafkaProducer(kafka_config, "sensor_01")
    producer.run("raw-data", interval=0.5, max_messages=100)

