# switching.py

# --- BINARY SWITCHING CONFIGURATION ---
# High Watermark (0.6): If Score >= 0.6, Switch to PQC (Secure)
# Low Watermark (0.4): If Score <= 0.4, Switch to Classical (Legacy)
THRESHOLD_HIGH = 0.6
THRESHOLD_LOW = 0.4


# --- HELPER FUNCTIONS ---

def estimate_latency_ms_for_suite(suite_name: str, baseline_ms: float = 5.0, size_bytes: int = 0):
    """
    Estimates latency based on packet size.
    Reference: Derived from Cloudflare's sizing benchmarks
    """
    # Heuristic: larger packets = higher latency penalty
    # We assume a fast internal network (divisor 2000.0)
    network_penalty = size_bytes / 2000.0
    return baseline_ms + network_penalty


def calculate_quantum_risk(security_level: int):
    # Mosca's Inequality Simulation:
    # If security_req is 5 (Top Secret), we force risk to 1.0
    return security_level / 5.0


def calculate_resource_penalty(client_type: str):
    penalties = {
        'iot': 0.9,  # High penalty for IoT (weak CPU)
        'mobile': 0.5,  # Medium penalty
        'desktop': 0.1,  # Low penalty
        'server': 0.0
    }
    return penalties.get(client_type, 0.5)


def calculate_latency_penalty(est_latency_ms: float, max_allowed_ms: float = 500.0):
    # Derived from [76] Cloudflare (Network constraints)
    # Returns 0.0 (No penalty) to 1.0 (Max penalty)
    if est_latency_ms >= max_allowed_ms:
        return 1.0
    return est_latency_ms / max_allowed_ms


# --- CORE LOGIC ---

def decide_suite(current_state: str, security_req: int, client_type: str, est_latency_pqc: float):

    # 1. Calculate Inputs (Normalized 0.0 to 1.0)
    R_quant = calculate_quantum_risk(security_req)  # Risk
    P_cost = calculate_resource_penalty(client_type)  # Resource Cost
    P_lat = calculate_latency_penalty(est_latency_pqc)  # Latency Cost

    # 2. Calculate SV_API Score
    # Formula: SV = base_score + (Weight_Risk * Risk) - (Weight_Cost * Cost) - (Weight_Lat * Latency)


    # Weights (Configurable by Policy Engine)
    W_R = 1.0  # Security priority
    W_C = 0.4  # Cost priority
    W_L = 0.4  # Latency priority

    base_score = 0.5
    sv_api = base_score + (W_R * R_quant) - (W_C * P_cost) - (W_L * P_lat)

    # Clamp score between 0 and 1
    sv_api = max(0.0, min(1.0, sv_api))

    # 3. State Machine Logic (Hysteresis)
    new_state = current_state  # Default: Stay in current state
    reason = "Stable State"

    if current_state == 'classical':
        # Only switch UP if we cross the High Watermark
        if sv_api >= THRESHOLD_HIGH:
            new_state = 'pqc'
            reason = f"Score {sv_api:.2f} >= {THRESHOLD_HIGH} (Security Critical - Upgrade)"
        else:
            reason = f"Score {sv_api:.2f} < {THRESHOLD_HIGH} (Stay Legacy)"

    elif current_state == 'pqc':
        # Only switch DOWN if we drop below Low Watermark
        if sv_api <= THRESHOLD_LOW:
            new_state = 'classical'
            reason = f"Score {sv_api:.2f} <= {THRESHOLD_LOW} (Performance Drop - Downgrade)"
        else:
            reason = f"Score {sv_api:.2f} > {THRESHOLD_LOW} (Maintain Security)"

    return new_state, {
        'sv_api': sv_api,
        'risk': R_quant,
        'reason': reason
    }