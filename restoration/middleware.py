import threading
from django.utils import timezone


_last_alert_run = None
_lock = threading.Lock()
ALERT_INTERVAL_SECONDS = 300


class AlertAutoCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._maybe_run_alerts()
        return self.get_response(request)

    def _maybe_run_alerts(self):
        global _last_alert_run
        now = timezone.now()
        if _last_alert_run is not None:
            elapsed = (now - _last_alert_run).total_seconds()
            if elapsed < ALERT_INTERVAL_SECONDS:
                return
        if _lock.acquire(blocking=False):
            try:
                if _last_alert_run is not None:
                    elapsed = (timezone.now() - _last_alert_run).total_seconds()
                    if elapsed < ALERT_INTERVAL_SECONDS:
                        return
                from restoration.alerts import run_all_alerts
                run_all_alerts()
                _last_alert_run = timezone.now()
            finally:
                _lock.release()
