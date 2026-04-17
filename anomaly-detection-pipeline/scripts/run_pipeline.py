#!/usr/bin/env python3
"""
Main Pipeline Runner

This script orchestrates the entire anomaly detection pipeline,
starting all components in the correct order.
"""

import os
import sys
import time
import logging
import argparse
import subprocess
import signal
from typing import List, Dict, Any
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ingestion.producers.synthetic_data import SyntheticDataProducer
from processing.stream_processor import StreamProcessor
from dashboard.app import AnomalyDashboard, DashboardConfig


class PipelineRunner:
    """Main pipeline orchestrator."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the pipeline runner.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        self.processes: List[subprocess.Popen] = []
        
        # Load configuration
        self.config = self.load_config()
        
        # Setup logging
        self.setup_logging()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_config.get('file', 'logs/pipeline.log')),
                logging.StreamHandler() if log_config.get('console_output', True) else logging.NullHandler()
            ]
        )
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        self.logger.info("Checking dependencies...")
        
        # Check if Kafka is running
        try:
            from kafka import KafkaProducer
            producer = KafkaProducer(
                bootstrap_servers=self.config['kafka']['bootstrap_servers'],
                request_timeout_ms=5000
            )
            producer.close()
            self.logger.info("✓ Kafka connection successful")
        except Exception as e:
            self.logger.error(f"✗ Kafka connection failed: {e}")
            return False
        
        # Check if required directories exist
        required_dirs = ['logs', 'models/saved', 'data']
        for dir_path in required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("✓ All dependencies available")
        return True
    
    def start_data_producer(self) -> subprocess.Popen:
        """Start the data producer."""
        self.logger.info("Starting data producer...")
        
        kafka_config = self.config['kafka']
        producer_config = self.config['ingestion']['producers'][0]  # Use first producer
        
        cmd = [
            sys.executable, "-m", "ingestion.producers.synthetic_data",
            "--bootstrap-servers", ",".join(kafka_config['bootstrap_servers']),
            "--topic", kafka_config['input_topic'],
            "--source", producer_config['source'],
            "--interval", str(producer_config['interval']),
            "--max-messages", str(producer_config['max_messages'])
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        self.processes.append(process)
        self.logger.info(f"Data producer started with PID: {process.pid}")
        return process
    
    def start_stream_processor(self) -> subprocess.Popen:
        """Start the stream processor."""
        self.logger.info("Starting stream processor...")
        
        cmd = [
            sys.executable, "-m", "processing.stream_processor",
            "--config", self.config_path
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        self.processes.append(process)
        self.logger.info(f"Stream processor started with PID: {process.pid}")
        return process
    
    def start_dashboard(self) -> subprocess.Popen:
        """Start the dashboard."""
        self.logger.info("Starting dashboard...")
        
        dashboard_config = self.config['dashboard']
        kafka_config = self.config['kafka']
        
        cmd = [
            sys.executable, "-m", "dashboard.app",
            "--host", dashboard_config['host'],
            "--port", str(dashboard_config['port']),
            "--kafka-servers", ",".join(kafka_config['bootstrap_servers']),
            "--input-topic", kafka_config['input_topic'],
            "--output-topic", kafka_config['output_topic']
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        self.processes.append(process)
        self.logger.info(f"Dashboard started with PID: {process.pid}")
        return process
    
    def start_monitoring(self) -> List[subprocess.Popen]:
        """Start monitoring services (Prometheus, Grafana)."""
        self.logger.info("Starting monitoring services...")
        
        monitoring_processes = []
        
        # Start Prometheus if enabled
        if self.config.get('monitoring', {}).get('prometheus', {}).get('enabled', False):
            prometheus_config = self.config['monitoring']['prometheus']
            cmd = [
                "prometheus",
                "--config.file=infra/prometheus.yml",
                f"--web.listen-address=:{prometheus_config['port']}"
            ]
            
            try:
                process = subprocess.Popen(cmd)
                monitoring_processes.append(process)
                self.logger.info(f"Prometheus started with PID: {process.pid}")
            except FileNotFoundError:
                self.logger.warning("Prometheus not found, skipping...")
        
        # Start Grafana if enabled
        if self.config.get('monitoring', {}).get('grafana', {}).get('enabled', False):
            grafana_config = self.config['monitoring']['grafana']
            cmd = [
                "grafana-server",
                f"--http-port={grafana_config['port']}",
                "--config=infra/grafana.ini"
            ]
            
            try:
                process = subprocess.Popen(cmd)
                monitoring_processes.append(process)
                self.logger.info(f"Grafana started with PID: {process.pid}")
            except FileNotFoundError:
                self.logger.warning("Grafana not found, skipping...")
        
        self.processes.extend(monitoring_processes)
        return monitoring_processes
    
    def run_pipeline(self, start_monitoring: bool = True):
        """Run the complete pipeline."""
        self.logger.info("Starting Anomaly Detection Pipeline...")
        
        # Check dependencies
        if not self.check_dependencies():
            self.logger.error("Dependency check failed. Exiting.")
            return
        
        try:
            # Start components in order
            self.logger.info("Starting pipeline components...")
            
            # Start monitoring first (if enabled)
            if start_monitoring:
                self.start_monitoring()
                time.sleep(5)  # Give monitoring services time to start
            
            # Start data producer
            producer_process = self.start_data_producer()
            time.sleep(2)
            
            # Start stream processor
            processor_process = self.start_stream_processor()
            time.sleep(2)
            
            # Start dashboard
            dashboard_process = self.start_dashboard()
            time.sleep(2)
            
            self.logger.info("Pipeline started successfully!")
            self.logger.info("Dashboard available at: http://localhost:8000")
            self.logger.info("Kafka UI available at: http://localhost:8080")
            if start_monitoring:
                self.logger.info("Prometheus available at: http://localhost:9090")
                self.logger.info("Grafana available at: http://localhost:3000")
            
            # Monitor processes
            self.monitor_processes()
            
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal. Shutting down...")
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
        finally:
            self.shutdown()
    
    def monitor_processes(self):
        """Monitor running processes."""
        self.logger.info("Monitoring pipeline processes...")
        
        try:
            while True:
                # Check if any process has died
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:
                        self.logger.warning(f"Process {i} (PID: {process.pid}) has stopped")
                        # Restart the process if needed
                        # self.restart_process(i)
                
                time.sleep(10)  # Check every 10 seconds
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped")
    
    def shutdown(self):
        """Shutdown all processes gracefully."""
        self.logger.info("Shutting down pipeline...")
        
        for process in self.processes:
            try:
                if process.poll() is None:  # Process is still running
                    self.logger.info(f"Terminating process {process.pid}")
                    process.terminate()
                    process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.logger.warning(f"Force killing process {process.pid}")
                process.kill()
            except Exception as e:
                self.logger.error(f"Error shutting down process {process.pid}: {e}")
        
        self.logger.info("Pipeline shutdown complete")


def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\nReceived interrupt signal. Shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Anomaly Detection Pipeline Runner")
    parser.add_argument(
        "--config", 
        default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--no-monitoring",
        action="store_true",
        help="Skip starting monitoring services"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check dependencies and exit"
    )
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run pipeline
    runner = PipelineRunner(args.config)
    
    if args.check_only:
        if runner.check_dependencies():
            print("✓ All dependencies available")
            sys.exit(0)
        else:
            print("✗ Dependency check failed")
            sys.exit(1)
    
    runner.run_pipeline(start_monitoring=not args.no_monitoring)


if __name__ == "__main__":
    main()




