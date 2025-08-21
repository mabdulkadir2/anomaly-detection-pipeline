## Real-Time Anomaly Detection Pipeline

A comprehensive real-time anomaly detection system built with Python and Apache Kafka for streaming data processing and machine learning-based anomaly detection.

### Goals
- Kafka producers/consumers and streaming basics
- Implement anomaly detection (from simple thresholds to ML)
- Build a small real-time dashboard
- Containerize and optionally scale with Spark/Kubernetes

### Tech Stack
- Python 3.10+
- Apache Kafka (via Docker)
- FastAPI (API + optional WebSocket)
- Spark Structured Streaming, Redis, PostgreSQL, Prometheus/Grafana

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Data      │    │  Kafka      │    │  Processing │    │  Dashboard  │
│  Sources    │───▶│  Cluster    │───▶│   Engine    │───▶│    & API    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐    ┌─────────────┐
                    │   Models    │    │  Monitoring │
                    │  Training   │    │   & Alerts  │
                    └─────────────┘    └─────────────┘
```

### Project Structure
```
anomaly-detection-pipeline/
├── ingestion/           # Data ingestion components
├── processing/          # Stream processing logic
├── models/             # ML models and training
├── dashboard/          # Web dashboard and API
├── infra/              # Infrastructure and deployment
├── config/             # Configuration files
├── tests/              # Test suites
├── docs/               # Documentation
└── scripts/            # Utility scripts
```
