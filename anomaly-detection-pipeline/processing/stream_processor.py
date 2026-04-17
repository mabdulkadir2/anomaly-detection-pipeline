"""
Stream Processor for Anomaly Detection

Handles real-time processing of data streams using Kafka and Spark Streaming.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from .anomaly_detector import AnomalyDetector
from .data_transformer import DataTransformer


class StreamProcessor:
    """Main stream processor for anomaly detection pipeline."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the stream processor.
        
        Args:
            config: Configuration dictionary containing Kafka and processing settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.spark = None
        self.consumer = None
        self.anomaly_detector = AnomalyDetector(config.get('anomaly_detection', {}))
        self.data_transformer = DataTransformer(config.get('transformation', {}))
        
        # Processing state
        self.is_running = False
        self.processed_count = 0
        self.anomaly_count = 0
        
    def initialize_spark(self):
        """Initialize Spark session for stream processing."""
        try:
            self.spark = SparkSession.builder \
                .appName("AnomalyDetectionPipeline") \
                .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoint") \
                .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
                .getOrCreate()
            
            self.logger.info("Spark session initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Spark: {e}")
            raise
    
    def initialize_kafka_consumer(self):
        """Initialize Kafka consumer for reading data streams."""
        try:
            kafka_config = self.config['kafka']
            
            self.consumer = KafkaConsumer(
                kafka_config['input_topic'],
                bootstrap_servers=kafka_config['bootstrap_servers'],
                group_id=kafka_config.get('group_id', 'anomaly-detection-group'),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                **kafka_config.get('consumer_config', {})
            )
            
            self.logger.info(f"Kafka consumer initialized for topic: {kafka_config['input_topic']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single message through the pipeline.
        
        Args:
            message: Input message from Kafka
            
        Returns:
            Processed result with anomaly detection results
        """
        try:
            # Transform data
            transformed_data = self.data_transformer.transform(message)
            
            # Detect anomalies
            anomaly_result = self.anomaly_detector.detect(transformed_data)
            
            # Add metadata
            result = {
                'original_data': message,
                'transformed_data': transformed_data,
                'anomaly_detected': anomaly_result['is_anomaly'],
                'anomaly_score': anomaly_result['score'],
                'anomaly_type': anomaly_result.get('type'),
                'processing_timestamp': datetime.now().isoformat(),
                'source': message.get('source'),
                'metric': message.get('metric')
            }
            
            self.processed_count += 1
            
            if anomaly_result['is_anomaly']:
                self.anomaly_count += 1
                self.logger.warning(f"Anomaly detected: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return None
    
    def process_stream(self):
        """Process the Kafka stream continuously."""
        self.logger.info("Starting stream processing...")
        self.is_running = True
        
        try:
            for message in self.consumer:
                if not self.is_running:
                    break
                
                # Extract message value
                data = message.value
                
                # Process the message
                result = self.process_message(data)
                
                if result:
                    # Publish result to output topic
                    self.publish_result(result)
                
                # Log progress
                if self.processed_count % 100 == 0:
                    anomaly_rate = (self.anomaly_count / self.processed_count) * 100
                    self.logger.info(
                        f"Processed {self.processed_count} messages, "
                        f"{self.anomaly_count} anomalies ({anomaly_rate:.1f}%)"
                    )
                
        except KeyboardInterrupt:
            self.logger.info("Stream processing stopped by user")
        except Exception as e:
            self.logger.error(f"Error in stream processing: {e}")
        finally:
            self.stop()
    
    def publish_result(self, result: Dict[str, Any]):
        """Publish processing result to output Kafka topic."""
        try:
            # This would typically use a Kafka producer
            # For now, just log the result
            if result['anomaly_detected']:
                self.logger.info(f"Anomaly result: {result}")
                
        except Exception as e:
            self.logger.error(f"Error publishing result: {e}")
    
    def process_batch(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of messages.
        
        Args:
            messages: List of messages to process
            
        Returns:
            List of processing results
        """
        results = []
        
        for message in messages:
            result = self.process_message(message)
            if result:
                results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': (self.anomaly_count / self.processed_count * 100) if self.processed_count > 0 else 0,
            'is_running': self.is_running
        }
    
    def stop(self):
        """Stop the stream processor."""
        self.is_running = False
        
        if self.consumer:
            self.consumer.close()
            self.logger.info("Kafka consumer closed")
        
        if self.spark:
            self.spark.stop()
            self.logger.info("Spark session stopped")
        
        self.logger.info("Stream processor stopped")


class SparkStreamProcessor(StreamProcessor):
    """Spark Streaming-based processor for high-throughput processing."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.initialize_spark()
    
    def create_streaming_query(self):
        """Create a Spark Structured Streaming query."""
        kafka_config = self.config['kafka']
        
        # Read from Kafka
        df = self.spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", ",".join(kafka_config['bootstrap_servers'])) \
            .option("subscribe", kafka_config['input_topic']) \
            .option("startingOffsets", "latest") \
            .load()
        
        # Parse JSON
        schema = StructType([
            StructField("source", StringType(), True),
            StructField("value", DoubleType(), True),
            StructField("metric", StringType(), True),
            StructField("timestamp", StringType(), True)
        ])
        
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")
        
        # Apply transformations and anomaly detection
        processed_df = self.apply_processing_pipeline(parsed_df)
        
        return processed_df
    
    def apply_processing_pipeline(self, df):
        """Apply the processing pipeline to the DataFrame."""
        # Add processing timestamp
        df = df.withColumn("processing_timestamp", current_timestamp())
        
        # Apply windowing for time-based analysis
        window_spec = window("processing_timestamp", "1 minute")
        
        # Calculate statistics over window
        df = df.withWatermark("processing_timestamp", "30 seconds") \
            .groupBy(window_spec, "source", "metric") \
            .agg(
                avg("value").alias("avg_value"),
                stddev("value").alias("std_value"),
                count("value").alias("count")
            )
        
        return df
    
    def start_streaming(self):
        """Start Spark Structured Streaming."""
        query_df = self.create_streaming_query()
        
        # Write to console for debugging
        query = query_df.writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .start()
        
        self.logger.info("Spark streaming query started")
        
        try:
            query.awaitTermination()
        except KeyboardInterrupt:
            query.stop()
            self.logger.info("Spark streaming stopped")


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'kafka': {
            'bootstrap_servers': ['localhost:9092'],
            'input_topic': 'raw-data',
            'output_topic': 'anomaly-results',
            'group_id': 'anomaly-detection-group'
        },
        'anomaly_detection': {
            'method': 'isolation_forest',
            'threshold': 0.8
        },
        'transformation': {
            'normalize': True,
            'window_size': 100
        }
    }
    
    processor = StreamProcessor(config)
    processor.initialize_kafka_consumer()
    processor.process_stream()

