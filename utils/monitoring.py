"""Module for monitoring application performance and health.

This module provides functionality for tracking API endpoints, response times,
and error rates to help identify performance issues and potential problems.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import current_app

# Configure logger
logger = logging.getLogger(__name__)


class APIMonitor:
    """Monitor API endpoints for performance and errors.

    This class tracks various metrics for API endpoints including:
    - Request counts
    - Error counts
    - Response times
    - Error rates
    """

    def __init__(self) -> None:
        """Initialize the API monitor with default values."""
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, List[float]] = defaultdict(list)
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "response_time": 1.0,  # 1 second
        }
        self.last_alert_time: Dict[str, datetime] = defaultdict(lambda: datetime.min)

    def track_request(self, endpoint: str, response_time: float, is_error: bool = False) -> None:
        """Track a request to an API endpoint.

        Args:
            endpoint: The API endpoint that was called.
            response_time: The time taken to process the request in seconds.
            is_error: Whether the request resulted in an error.
        """
        self.request_counts[endpoint] += 1
        if is_error:
            self.error_counts[endpoint] += 1
        self.response_times[endpoint].append(response_time)

        # Check for alerts
        self._check_alerts(endpoint)

    def _check_alerts(self, endpoint: str) -> None:
        """Check if any alerts should be triggered for the given endpoint.

        Args:
            endpoint: The API endpoint to check for alerts.
        """
        now = datetime.now()
        if (now - self.last_alert_time[endpoint]).total_seconds() < 300:  # 5 minutes cooldown
            return

        total_requests = self.request_counts[endpoint]
        total_errors = self.error_counts[endpoint]

        # Calculate average response time
        if self.response_times[endpoint]:
            avg_response_time = sum(self.response_times[endpoint]) / len(self.response_times[endpoint])
            if avg_response_time > self.alert_thresholds["response_time"]:
                self._send_alert(endpoint, "response_time", avg_response_time)

        # Calculate error rate
        if total_requests > 0:
            error_rate = total_errors / total_requests
            if error_rate > self.alert_thresholds["error_rate"]:
                self._send_alert(endpoint, "error_rate", error_rate)

    def _send_alert(self, endpoint: str, alert_type: str, value: float) -> None:
        """Send an alert for the given endpoint and alert type.

        Args:
            endpoint: The API endpoint that triggered the alert.
            alert_type: The type of alert (e.g., "response_time", "error_rate").
            value: The value that triggered the alert.
        """
        self.last_alert_time[endpoint] = datetime.now()
        message = f"Alert: {alert_type} threshold exceeded for {endpoint}. " f"Value: {value:.2f}"
        logger.warning(message)
        # TODO: Send alert to monitoring service (e.g., Sentry, Datadog)


# Global instance of the API monitor
api_monitor = APIMonitor()
