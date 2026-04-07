import time
import random
import threading

class CloudService:
    def __init__(self, service_name, base_latency_ms, max_concurrent_requests):
        """
        Simulated Cloud Service

        :param service_name: Logical name of the service (e.g., AuthService)
        :param base_latency_ms: Base processing delay in milliseconds
        :param max_concurrent_requests: Capacity before queueing occurs
        """
        self.service_name = service_name
        self.base_latency_ms = base_latency_ms
        self.max_concurrent_requests = max_concurrent_requests
        self.active_requests = 0
        self.lock = threading.Lock()

    def process_request(self):
        """
        Simulates cloud-side request handling before cryptographic operations.
        Returns the service-side delay applied.
        """
        with self.lock:
            self.active_requests += 1
            current_load = self.active_requests

        try:
            # Load factor increases delay when service is saturated
            load_factor = max(0, current_load - self.max_concurrent_requests)

            # Simulated queueing delay (cloud congestion)
            queue_delay_ms = load_factor * random.uniform(5, 20)

            # Total service delay
            total_delay_ms = self.base_latency_ms + queue_delay_ms

            time.sleep(total_delay_ms / 1000.0)

            return {
                "service_name": self.service_name,
                "service_delay_ms": total_delay_ms,
                "queue_delay_ms": queue_delay_ms,
                "active_requests": current_load
            }

        finally:
            with self.lock:
                self.active_requests -= 1
