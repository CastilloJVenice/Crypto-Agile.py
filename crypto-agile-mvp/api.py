import threading
import time
import statistics
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

from switching import decide_suite
from cal import CryptoAbstractionLayer

app = FastAPI(title="Crypto-Agile API Gateway (Refactored MVP)")


# --- DATA MODELS ---
class AuthRequest(BaseModel):
    client_type: str  # 'iot', 'mobile', 'desktop', 'server'
    security_level: int  # 1 to 5


# --- TELEMETRY AGGREGATOR COMPONENT ---
class TelemetryAggregator:
    def __init__(self, window_size=10, initial_seed=50.0):
        self.window_size = window_size
        self.history = [initial_seed]

    def update(self, latency_ms: float):
        """Ingest new real-time stream data."""
        self.history.append(latency_ms)
        if len(self.history) > self.window_size:
            self.history.pop(0)

    def get_prediction(self) -> float:
        """Process data to return a prediction (Moving Average)."""
        if not self.history:
            return 50.0  # Fallback default
        return statistics.mean(self.history)


# --- KEY LIFECYCLE MANAGER (Asynchronous Key Pooling) ---
# Thread-safe local storage buffer for pre-generated crypto elements
KEY_POOL = {
    2: {"kem": [], "sig": []},  # Level 1-2 (Kyber512 / Dilithium2)
    3: {"kem": [], "sig": []},  # Level 3-4 (Kyber768 / Dilithium3)
    5: {"kem": [], "sig": []}  # Level 5   (Kyber1024 / Dilithium5)
}
POOL_MAX_SIZE = 10


def background_key_generator():
    """Background engine tracking pool sizes to buffer key sets natively."""
    from pqc import KyberKEM, DilithiumSig
    while True:
        for level in [2, 3, 5]:
            # Maintain KEM keys
            if len(KEY_POOL[level]["kem"]) < POOL_MAX_SIZE:
                try:
                    kem = KyberKEM(security_level=level)
                    pair = kem.generate_keypair()
                    KEY_POOL[level]["kem"].append(pair)
                except Exception:
                    pass

            # Maintain Digital Signature keys
            if len(KEY_POOL[level]["sig"]) < POOL_MAX_SIZE:
                try:
                    sig = DilithiumSig(security_level=level)
                    pair = sig.generate_keypair()
                    KEY_POOL[level]["sig"].append(pair)
                except Exception:
                    pass
        time.sleep(0.5)



bg_worker = threading.Thread(target=background_key_generator, daemon=True)
bg_worker.start()

# --- SYSTEM INITIALIZATION ---
aggregator = TelemetryAggregator()
cal_layer = CryptoAbstractionLayer(key_pool_reference=KEY_POOL)
SYSTEM_STATE = "classical"  # Safe architectural standard startup state


# --- BACKGROUND TASK HANDLING ---
def async_telemetry_update(latency: float):
    """Safely updates moving state information off the main response route."""
    aggregator.update(latency)


# --- CORE API GATEWAY ROUTE ---
@app.post("/authenticate")
def authenticate_client(request: AuthRequest, background_tasks: BackgroundTasks):
    global SYSTEM_STATE

    # 1. Telemetry Gathering & Control Plane Decision Engine Assessment
    current_avg_pqc_latency = aggregator.get_prediction()

    new_state, metadata = decide_suite(
        current_state=SYSTEM_STATE,
        security_req=request.security_level,
        client_type=request.client_type,
        est_latency_pqc=current_avg_pqc_latency
    )

    # 2. Data Plane Cryptographic Execution managed cleanly via the CAL Engine
    payload = b"Test Authentication Payload"
    measured_latency, algorithm_used = cal_layer.execute(
        payload=payload,
        state_mode=new_state,
        security_level=request.security_level
    )

    # System State Synchronizer Check
    SYSTEM_STATE = new_state

    # 3. Decouple Telemetry Processing asynchronously to minimize client transit overhead
    background_tasks.add_task(async_telemetry_update, measured_latency)

    return {
        "status": "success",
        "mode": SYSTEM_STATE.upper(),
        "algorithm": algorithm_used,
        "sv_score": metadata['sv_api'],
        "decision_reason": metadata['reason'],
        "metrics": {
            "prediction_used_ms": round(current_avg_pqc_latency, 2),
            "actual_execution_ms": round(measured_latency, 2),
            "history_buffer_size": len(aggregator.history)
        },
        "message": f"Secure connection established using {SYSTEM_STATE.upper()}."
    }

# To run manually via CLI:
# uvicorn api:app --reload
