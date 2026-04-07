import time
import statistics
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import your modules (Ensure these files are in the same directory)
from switching import decide_suite
import classical
from pqc import KyberKEM, DilithiumSig

app = FastAPI(title="Crypto-Agile API Gateway (MVP)")

# --- GLOBAL STATE ---
# Start in Classical Mode (Safe default)
SYSTEM_STATE = "classical"


# --- COMPONENT: TELEMETRY AGGREGATOR ---
# This class implements the "Telemetry Aggregator" box from Figure 1.
# It collects real-time streams and processes them into usable data for the controller.
class TelemetryAggregator:
    def __init__(self, window_size=10, initial_seed=50.0):
        self.window_size = window_size
        # Seed history so the first request has a baseline to work with
        self.history = [initial_seed]

    def update(self, latency_ms: float):
        """Ingest new real-time stream data."""
        self.history.append(latency_ms)
        # Keep the window size fixed (e.g., last 10 requests)
        if len(self.history) > self.window_size:
            self.history.pop(0)

    def get_prediction(self) -> float:
        """Process data to return a prediction (Moving Average)."""
        if not self.history:
            return 50.0  # Fallback default
        return statistics.mean(self.history)


# Instantiate the component (Singleton pattern)
aggregator = TelemetryAggregator()


class AuthRequest(BaseModel):
    client_type: str  # 'iot', 'mobile', 'desktop', 'server'
    security_level: int  # 1 to 5


# --- HELPER: REAL-TIME BENCHMARKING ---
def execute_and_measure_pqc(security_level: int):
    """
    Runs the actual PQC Key Encapsulation and Signing processes
    and returns the execution time in milliseconds.
    """
    # Use perf_counter for high-precision benchmarking
    start_time = time.perf_counter()

    # 1. KEM Operations (Kyber)
    # Instantiate the class from your pqc.py
    kem = KyberKEM(security_level=security_level)
    pk, sk = kem.generate_keypair()
    ciphertext, shared_secret = kem.encapsulate(pk)
    # Decapsulate is part of the handshake, so we measure it too
    _ = kem.decapsulate(sk, ciphertext)

    # 2. Signature Operations (Dilithium)
    # Instantiate the class from your pqc.py
    sig_agent = DilithiumSig(security_level=security_level)
    pk_sig, sk_sig = sig_agent.generate_keypair()
    message = b"Test Authentication Payload"
    signature = sig_agent.sign(message, sk_sig)
    # Verification is the gateway's job
    _ = sig_agent.verify(message, signature, pk_sig)

    end_time = time.perf_counter()

    # Return duration in milliseconds
    return (end_time - start_time) * 1000


@app.post("/authenticate")
def authenticate_client(request: AuthRequest):
    """
    Main API Endpoint (Data Plane).
    Uses 'def' to run CPU-bound crypto tasks in a thread pool.
    """
    global SYSTEM_STATE

    # ---------------------------------------------------------
    # 1. TELEMETRY GATHERING (Real-Time Prediction)
    # ---------------------------------------------------------
    # Use the Telemetry Aggregator component to get the current estimate
    current_avg_pqc_latency = aggregator.get_prediction()

    # ---------------------------------------------------------
    # 2. CONTROL PLANE: DECISION MAKING
    # ---------------------------------------------------------
    # The Controller decides the suite based on the PREDICTED latency.
    # This aligns with the "Crypto-Agility Controller" in Figure 1.
    new_state, metadata = decide_suite(
        current_state=SYSTEM_STATE,
        security_req=request.security_level,
        client_type=request.client_type,
        est_latency_pqc=current_avg_pqc_latency
    )

    # ---------------------------------------------------------
    # 3. DATA PLANE: EXECUTION & MEASUREMENT
    # ---------------------------------------------------------
    measured_latency = 0.0

    # Run the Watchdog Check (Fail-Safe / Circuit Breaker)
    # Aligning with Topic 2: "Quantum-safe watchdog timer protocol"
    WATCHDOG_LIMIT_MS = 500.0
    if new_state == 'pqc' and current_avg_pqc_latency > WATCHDOG_LIMIT_MS:
        print(f"!!! WATCHDOG TRIGGERED: Latency {current_avg_pqc_latency:.2f}ms too high. Fallback.")
        new_state = 'classical'
        metadata['reason'] = "Watchdog Override"

    # EXECUTE THE ALGORITHMS
    if new_state == 'pqc':
        # --- PQC MODE ---
        # Run the heavy math and measure how long it ACTUALLY takes
        measured_latency = execute_and_measure_pqc(request.security_level)

        # UPDATE TELEMETRY: Feed this new fact back into the Aggregator
        aggregator.update(measured_latency)

    else:
        # --- CLASSICAL MODE ---
        # We simulate or measure classical. Classical is usually fast.
        start_c = time.perf_counter()

        # Using the low-level functions from your classical.py
        priv, pub = classical.generate_ecdh_keypair(request.security_level)
        # Simulate simple handshake
        _ = classical.derive_shared_key_ecdh(priv, pub)

        end_c = time.perf_counter()
        measured_latency = (end_c - start_c) * 1000

    # ---------------------------------------------------------
    # 4. STATE SYNC & RESPONSE
    # ---------------------------------------------------------
    SYSTEM_STATE = new_state

    return {
        "status": "success",
        "mode": SYSTEM_STATE.upper(),
        "sv_score": metadata['sv_api'],
        "decision_reason": metadata['reason'],
        "metrics": {
            "prediction_used_ms": round(current_avg_pqc_latency, 2),
            "actual_execution_ms": round(measured_latency, 2),
            "history_buffer_size": len(aggregator.history)
        },
        "message": f"Secure connection established using {SYSTEM_STATE.upper()}."
    }

# To run: uvicorn api:app --reload