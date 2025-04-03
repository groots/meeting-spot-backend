import json
import logging
import os
from datetime import datetime
from typing import Dict, List


class MetricsCollector:
    def __init__(self) -> None:
        self.response_times: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.request_counts: Dict[str, int] = {}
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_thresholds = {
            "response_time": 2.0,  # seconds
            "error_rate": 0.1,  # 10% error rate
            "request_rate": 100,  # requests per minute
        }

        # Setup monitoring log file
        if not os.path.exists("logs"):
            os.mkdir("logs")
        self.monitor_logger = logging.getLogger("monitoring")
        self.monitor_logger.setLevel(logging.INFO)
        fh = logging.FileHandler("logs/monitoring.log")
        fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.monitor_logger.addHandler(fh)

    def record_request(self, endpoint: str, response_time: float, status_code: int):
        """Record metrics for a request."""
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []
            self.error_counts[endpoint] = 0
            self.request_counts[endpoint] = 0
            self.last_alert_time[endpoint] = datetime.utcnow()

        self.response_times[endpoint].append(response_time)
        self.request_counts[endpoint] += 1

        # Keep only last 1000 response times
        if len(self.response_times[endpoint]) > 1000:
            self.response_times[endpoint] = self.response_times[endpoint][-1000:]

        if status_code >= 400:
            self.error_counts[endpoint] += 1

        self._check_alerts(endpoint)

    def _check_alerts(self, endpoint: str) -> None:
        """Check if any metrics exceed thresholds and send alerts if needed."""
        current_time = datetime.utcnow()
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

        # Calculate request rate (requests per minute)
        time_diff = (current_time - self.last_alert_time[endpoint]).total_seconds()
        if time_diff > 0:  # Prevent division by zero
            requests_per_minute = (total_requests / time_diff) * 60
            if requests_per_minute > self.alert_thresholds["request_rate"]:
                self._send_alert(endpoint, "request_rate", requests_per_minute)

        # Reset counters after checking alerts
        self.request_counts[endpoint] = 0
        self.error_counts[endpoint] = 0
        self.last_alert_time[endpoint] = current_time

    def _send_alert(self, endpoint: str, metric: str, value: float) -> None:
        """Send an alert when a metric exceeds its threshold."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "metric": metric,
            "value": value,
            "threshold": self.alert_thresholds[metric],
        }

        # Log the alert
        self.monitor_logger.warning(f"ALERT: {json.dumps(alert)}")

        # TODO: Implement additional alert channels (email, Slack, etc.)
        # For now, we just log to file

    def get_metrics(self) -> dict:
        """Get current metrics for all endpoints."""
        metrics = {}
        for endpoint in self.response_times:
            metrics[endpoint] = {
                "avg_response_time": (
                    sum(self.response_times[endpoint]) / len(self.response_times[endpoint])
                    if self.response_times[endpoint]
                    else 0
                ),
                "total_requests": self.request_counts[endpoint],
                "error_count": self.error_counts[endpoint],
                "error_rate": (
                    self.error_counts[endpoint] / self.request_counts[endpoint]
                    if self.request_counts[endpoint] > 0
                    else 0
                ),
            }
        return metrics


# Create a global metrics collector instance
metrics_collector = MetricsCollector()
