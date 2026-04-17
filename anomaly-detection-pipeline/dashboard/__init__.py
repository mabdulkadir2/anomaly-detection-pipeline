"""
Dashboard Module

This module provides web-based dashboards and APIs for monitoring
the anomaly detection pipeline.
"""

from .app import create_app
from .api import AnomalyAPI
from .streamlit_app import StreamlitDashboard

__all__ = [
    'create_app',
    'AnomalyAPI',
    'StreamlitDashboard'
]




