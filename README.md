# Anomaly Detection Pipeline Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Components](#components)
7. [API Reference](#api-reference)
8. [Deployment](#deployment)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

## Overview

The Anomaly Detection Pipeline is a comprehensive real-time system for detecting anomalies in streaming data. It combines multiple machine learning algorithms with Apache Kafka for scalable stream processing and provides a real-time dashboard for monitoring and alerting.

### Key Features

- **Real-time Processing**: Stream data through Apache Kafka for low-latency processing
- **Multiple Algorithms**: Support for Isolation Forest, Local Outlier Factor, One-Class SVM, and statistical methods
- **Ensemble Detection**: Combine multiple algorithms for improved accuracy
- **Real-time Dashboard**: Web-based dashboard with WebSocket updates
- **Scalable Architecture**: Microservices-based design with Docker support
- **Comprehensive Monitoring**: Prometheus and Grafana integration
- **Model Management**: Automated training and deployment pipeline

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Kafka Cluster │    │  Stream Processor│
│                 │───▶│                 │───▶│                 │
│ • IoT Devices   │    │ • Zookeeper     │    │ • Anomaly       │
│ • APIs          │    │ • Kafka Broker  │    │   Detection     │
│ • Files         │    │ • Kafka UI      │    │ • Data          │
└─────────────────┘    └─────────────────┘    │   Transformation│
                                             └─────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dashboard     │◀───│   Results Topic │◀───│  Output Topic   │
│                 │    │                 │    │                 │
│ • Real-time UI  │    │ • Anomaly       │    │ • Processed     │
│ • WebSocket     │    │   Results       │    │   Data          │
│ • REST API      │    │ • Alerts        │    │ • Statistics    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │
        ▼
┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │   Model Training│
│                 │    │                 │
│ • Prometheus    │    │ • AutoML        │
│ • Grafana       │    │ • Hyperparameter│
│ • Alert Manager │    │   Tuning        │
└─────────────────┘    └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Apache Kafka (or use Docker)
- PostgreSQL (optional)
- Redis (optional)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd anomaly-detection-pipeline
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup infrastructure**
   ```bash
   cd infra
   docker-compose up -d
   ```

### Production Setup

1. **Build Docker images**
   ```bash
   docker-compose -f infra/docker-compose.yml build
   ```

2. **Deploy with Kubernetes**
   ```bash
   kubectl apply -f infra/kubernetes/
   ```

## Quick Start

### 1. Start Infrastructure

```bash
# Start Kafka, Redis, PostgreSQL, and monitoring
cd infra
docker-compose up -d
```

### 2. Run the Pipeline

```bash
# Start the complete pipeline
python scripts/run_pipeline.py

# Or start components individually
python ingestion/producers/synthetic_data.py
python processing/stream_processor.py
python dashboard/app.py
```

### 3. Access Services

- **Dashboard**: http://localhost:8000
- **Kafka UI**: http://localhost:8080
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Configuration

The pipeline is configured through `config/config.yaml`. Key configuration sections:

### Kafka Configuration

```yaml
kafka:
  bootstrap_servers:
    - "localhost:9092"
  input_topic: "raw-data"
  output_topic: "anomaly-results"
  group_id: "anomaly-detection-group"
```

### Anomaly Detection Configuration

```yaml
anomaly_detection:
  method: "ensemble"
  threshold: 0.8
  detectors:
    isolation_forest:
      contamination: 0.1
      n_estimators: 100
    statistical:
      method: "zscore"
      threshold: 3.0
```

### Dashboard Configuration

```yaml
dashboard:
  host: "0.0.0.0"
  port: 8000
  websocket_enabled: true
  real_time_updates: true
```

## Components

### 1. Data Ingestion (`ingestion/`)

Handles data ingestion from various sources:

- **Synthetic Data Producer**: Generates test data with embedded anomalies
- **File Producer**: Reads data from CSV/JSON files
- **API Connector**: Connects to external APIs
- **Database Connector**: Reads from databases

### 2. Stream Processing (`processing/`)

Real-time data processing and anomaly detection:

- **Stream Processor**: Main processing engine
- **Anomaly Detector**: Multiple detection algorithms
- **Data Transformer**: Feature engineering and normalization
- **Window Processor**: Time-based aggregations

### 3. Models (`models/`)

Machine learning model management:

- **Model Trainer**: Automated training pipeline
- **Model Evaluator**: Performance evaluation
- **Model Registry**: Version control for models
- **Model Deployment**: Production deployment

### 4. Dashboard (`dashboard/`)

Web-based monitoring interface:

- **FastAPI App**: REST API and WebSocket server
- **Real-time UI**: Live anomaly monitoring
- **Alert Management**: Notification system
- **Performance Metrics**: System health monitoring

### 5. Infrastructure (`infra/`)

Deployment and infrastructure:

- **Docker Compose**: Local development setup
- **Kubernetes**: Production deployment
- **Monitoring**: Prometheus and Grafana
- **Database**: PostgreSQL and Redis

## API Reference

### REST API Endpoints

#### Health Check
```http
GET /api/health
```

#### Statistics
```http
GET /api/statistics
```

#### Recent Anomalies
```http
GET /api/anomalies?limit=100
```

#### Anomalies by Source
```http
GET /api/anomalies/{source}?limit=50
```

#### Create Alert
```http
POST /api/alert
Content-Type: application/json

{
  "source": "sensor_01",
  "value": 85.5,
  "metric": "cpu_usage",
  "timestamp": "2024-01-01T12:00:00Z",
  "is_anomaly": true,
  "anomaly_score": 0.95,
  "anomaly_type": "spike"
}
```

### WebSocket API

Connect to `/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

## Deployment

### Docker Deployment

1. **Build images**
   ```bash
   docker-compose -f infra/docker-compose.yml build
   ```

2. **Deploy services**
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```

### Kubernetes Deployment

1. **Create namespace**
   ```bash
   kubectl create namespace anomaly-detection
   ```

2. **Apply configurations**
   ```bash
   kubectl apply -f infra/kubernetes/
   ```

3. **Check deployment**
   ```bash
   kubectl get pods -n anomaly-detection
   ```

### Production Considerations

- **Scaling**: Use horizontal pod autoscaling
- **Security**: Enable authentication and TLS
- **Backup**: Regular database backups
- **Monitoring**: Comprehensive alerting
- **Logging**: Centralized log management

## Monitoring

### Metrics

The pipeline exposes metrics for:

- **Processing Rate**: Messages per second
- **Anomaly Rate**: Percentage of anomalies detected
- **Latency**: Processing time per message
- **Error Rate**: Failed processing attempts
- **Model Performance**: Detection accuracy

### Alerts

Configure alerts for:

- **High Anomaly Rate**: Unusual spike in anomalies
- **Service Down**: Component failures
- **High Latency**: Processing delays
- **Low Accuracy**: Model performance degradation

### Grafana Dashboards

Pre-configured dashboards for:

- **Pipeline Overview**: System health and performance
- **Anomaly Analysis**: Detection patterns and trends
- **Model Performance**: Accuracy and drift monitoring
- **Infrastructure**: Resource utilization

## Troubleshooting

### Common Issues

1. **Kafka Connection Failed**
   ```bash
   # Check if Kafka is running
   docker ps | grep kafka
   
   # Check Kafka logs
   docker logs kafka
   ```

2. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats
   
   # Adjust memory limits in docker-compose.yml
   ```

3. **Model Performance Degradation**
   ```bash
   # Retrain models
   python models/trainer.py --retrain
   
   # Check model metrics
   curl http://localhost:8000/api/statistics
   ```

### Logs

Check logs for each component:

```bash
# Application logs
tail -f logs/anomaly_detection.log

# Docker logs
docker logs stream-processor
docker logs dashboard
docker logs data-producer
```

### Performance Tuning

1. **Kafka Tuning**
   - Increase partition count for parallel processing
   - Adjust batch size and linger time
   - Configure retention policies

2. **Model Tuning**
   - Adjust detection thresholds
   - Tune hyperparameters
   - Use ensemble methods

3. **Infrastructure Tuning**
   - Scale resources based on load
   - Optimize database queries
   - Configure caching strategies

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting guide
- Contact the development team
