"""
FastAPI Application for Anomaly Detection Dashboard

Provides REST API endpoints and real-time dashboard for monitoring
anomaly detection pipeline.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError


class AnomalyData(BaseModel):
    """Pydantic model for anomaly data."""
    source: str
    value: float
    metric: str
    timestamp: str
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: Optional[str] = None


class DashboardConfig(BaseModel):
    """Configuration for the dashboard."""
    kafka_bootstrap_servers: List[str]
    input_topic: str
    output_topic: str
    port: int = 8000
    host: str = "0.0.0.0"


class AnomalyDashboard:
    """Main dashboard application."""
    
    def __init__(self, config: DashboardConfig):
        """
        Initialize the dashboard.
        
        Args:
            config: Dashboard configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Anomaly Detection Dashboard",
            description="Real-time monitoring dashboard for anomaly detection pipeline",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Kafka components
        self.consumer = None
        self.producer = None
        
        # WebSocket connections
        self.active_connections: List[WebSocket] = []
        
        # Data storage
        self.recent_anomalies: List[Dict[str, Any]] = []
        self.statistics: Dict[str, Any] = {
            'total_processed': 0,
            'total_anomalies': 0,
            'anomaly_rate': 0.0,
            'last_update': None
        }
        
        # Setup routes
        self.setup_routes()
        
    def setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with dashboard HTML."""
            return HTMLResponse(self.get_dashboard_html())
        
        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "kafka_connected": self.consumer is not None
            }
        
        @self.app.get("/api/statistics")
        async def get_statistics():
            """Get current statistics."""
            return self.statistics
        
        @self.app.get("/api/anomalies")
        async def get_recent_anomalies(limit: int = 100):
            """Get recent anomalies."""
            return self.recent_anomalies[-limit:]
        
        @self.app.get("/api/anomalies/{source}")
        async def get_anomalies_by_source(source: str, limit: int = 50):
            """Get anomalies for a specific source."""
            source_anomalies = [
                anomaly for anomaly in self.recent_anomalies
                if anomaly.get('source') == source
            ]
            return source_anomalies[-limit:]
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await self.handle_websocket(websocket)
        
        @self.app.post("/api/alert")
        async def create_alert(anomaly_data: AnomalyData):
            """Create a new alert."""
            try:
                await self.process_anomaly(anomaly_data.dict())
                return {"status": "success", "message": "Alert created"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def get_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Anomaly Detection Dashboard</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                .header { text-align: center; margin-bottom: 30px; }
                .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
                .stat-card { background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 2em; font-weight: bold; color: #333; }
                .stat-label { color: #666; margin-top: 5px; }
                .charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
                .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .anomaly-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .anomaly-item { border-bottom: 1px solid #eee; padding: 10px 0; }
                .anomaly-item:last-child { border-bottom: none; }
                .status-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }
                .status-active { background: #4CAF50; }
                .status-inactive { background: #f44336; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Anomaly Detection Dashboard</h1>
                    <p>Real-time monitoring of anomaly detection pipeline</p>
                    <div>
                        <span class="status-indicator" id="kafka-status"></span>
                        <span id="kafka-status-text">Connecting to Kafka...</span>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value" id="total-processed">0</div>
                        <div class="stat-label">Total Processed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="total-anomalies">0</div>
                        <div class="stat-label">Total Anomalies</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="anomaly-rate">0%</div>
                        <div class="stat-label">Anomaly Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="last-update">-</div>
                        <div class="stat-label">Last Update</div>
                    </div>
                </div>
                
                <div class="charts-grid">
                    <div class="chart-container">
                        <h3>Anomaly Trend</h3>
                        <canvas id="anomalyChart" width="400" height="200"></canvas>
                    </div>
                    <div class="chart-container">
                        <h3>Anomaly Distribution by Source</h3>
                        <div id="sourceChart"></div>
                    </div>
                </div>
                
                <div class="anomaly-list">
                    <h3>Recent Anomalies</h3>
                    <div id="anomaly-list"></div>
                </div>
            </div>
            
            <script>
                // WebSocket connection
                const ws = new WebSocket('ws://localhost:8000/ws');
                
                ws.onopen = function() {
                    console.log('WebSocket connected');
                    updateKafkaStatus(true);
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                };
                
                ws.onclose = function() {
                    console.log('WebSocket disconnected');
                    updateKafkaStatus(false);
                };
                
                function updateKafkaStatus(connected) {
                    const statusEl = document.getElementById('kafka-status');
                    const textEl = document.getElementById('kafka-status-text');
                    
                    if (connected) {
                        statusEl.className = 'status-indicator status-active';
                        textEl.textContent = 'Connected to Kafka';
                    } else {
                        statusEl.className = 'status-indicator status-inactive';
                        textEl.textContent = 'Disconnected from Kafka';
                    }
                }
                
                function updateDashboard(data) {
                    // Update statistics
                    document.getElementById('total-processed').textContent = data.statistics.total_processed;
                    document.getElementById('total-anomalies').textContent = data.statistics.total_anomalies;
                    document.getElementById('anomaly-rate').textContent = data.statistics.anomaly_rate.toFixed(2) + '%';
                    document.getElementById('last-update').textContent = new Date(data.statistics.last_update).toLocaleTimeString();
                    
                    // Update anomaly list
                    updateAnomalyList(data.recent_anomalies);
                }
                
                function updateAnomalyList(anomalies) {
                    const listEl = document.getElementById('anomaly-list');
                    listEl.innerHTML = '';
                    
                    anomalies.slice(-10).reverse().forEach(anomaly => {
                        const item = document.createElement('div');
                        item.className = 'anomaly-item';
                        item.innerHTML = `
                            <strong>${anomaly.source}</strong> - ${anomaly.metric}: ${anomaly.value}
                            <br><small>Score: ${anomaly.anomaly_score.toFixed(3)} | ${new Date(anomaly.timestamp).toLocaleString()}</small>
                        `;
                        listEl.appendChild(item);
                    });
                }
                
                // Initialize charts
                const anomalyCtx = document.getElementById('anomalyChart').getContext('2d');
                const anomalyChart = new Chart(anomalyCtx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: 'Anomaly Rate',
                            data: [],
                            borderColor: 'rgb(255, 99, 132)',
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100
                            }
                        }
                    }
                });
            </script>
        </body>
        </html>
        """
    
    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            while True:
                # Send initial data
                await websocket.send_text(json.dumps({
                    'type': 'update',
                    'statistics': self.statistics,
                    'recent_anomalies': self.recent_anomalies[-10:]
                }))
                
                # Keep connection alive
                await asyncio.sleep(1)
                
        except WebSocketDisconnect:
            self.active_connections.remove(websocket)
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all WebSocket connections."""
        message = json.dumps(data)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)
    
    async def process_anomaly(self, anomaly_data: Dict[str, Any]):
        """Process incoming anomaly data."""
        # Update statistics
        self.statistics['total_processed'] += 1
        if anomaly_data.get('is_anomaly'):
            self.statistics['total_anomalies'] += 1
            self.recent_anomalies.append(anomaly_data)
            
            # Keep only recent anomalies
            if len(self.recent_anomalies) > 1000:
                self.recent_anomalies = self.recent_anomalies[-1000:]
        
        # Update anomaly rate
        if self.statistics['total_processed'] > 0:
            self.statistics['anomaly_rate'] = (
                self.statistics['total_anomalies'] / self.statistics['total_processed']
            ) * 100
        
        self.statistics['last_update'] = datetime.now().isoformat()
        
        # Broadcast update
        await self.broadcast_update({
            'type': 'update',
            'statistics': self.statistics,
            'recent_anomalies': self.recent_anomalies[-10:]
        })
    
    def start_kafka_consumer(self):
        """Start Kafka consumer for real-time data."""
        try:
            self.consumer = KafkaConsumer(
                self.config.output_topic,
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                group_id='dashboard-consumer',
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            self.logger.info(f"Kafka consumer started for topic: {self.config.output_topic}")
            
            # Start consuming in background
            asyncio.create_task(self.consume_messages())
            
        except Exception as e:
            self.logger.error(f"Failed to start Kafka consumer: {e}")
    
    async def consume_messages(self):
        """Consume messages from Kafka."""
        for message in self.consumer:
            try:
                data = message.value
                await self.process_anomaly(data)
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
    
    def run(self):
        """Run the dashboard server."""
        # Start Kafka consumer
        self.start_kafka_consumer()
        
        # Run FastAPI server
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )


def create_app(config: DashboardConfig) -> FastAPI:
    """Create and configure the FastAPI application."""
    dashboard = AnomalyDashboard(config)
    return dashboard.app


if __name__ == "__main__":
    # Example configuration
    config = DashboardConfig(
        kafka_bootstrap_servers=['localhost:9092'],
        input_topic='raw-data',
        output_topic='anomaly-results',
        port=8000,
        host='0.0.0.0'
    )
    
    # Create and run dashboard
    dashboard = AnomalyDashboard(config)
    dashboard.run()




