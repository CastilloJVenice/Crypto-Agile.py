import random
import time
import sys
import os



# Import your modules
from metrics import measure_time, write_results_csv
from switching import estimate_latency_ms_for_suite, decide_suite
import classical
from pqc import KyberKEM, DilithiumSig
from cloud_service import CloudService

# ==========================================
# 1. GLOBAL VARIABLES & FUNCTIONS (EXPOSED)
# ==========================================
# These must be outside of main() for the Dashboard to import them
MESSAGE = b'Test message for authentication and key exchange'

# KEY LIFECYCLE MANAGER (Pre-Generated Keys)
KEY_POOL = {}


def pre_generate_keys():
    """Initializes keys so the dashboard/simulation starts faster."""
    print("\n[Key Lifecycle Manager] Status: INITIALIZING...")
    levels_needed = [2, 3, 5]
    for level in levels_needed:
        try:
            kem_temp = KyberKEM(security_level=level)
            pk, sk = kem_temp.generate_keypair()
            KEY_POOL[level] = {'pk': pk, 'sk': sk}
            print(f"   >>> Generated {kem_temp.name} Keys (Level {level}). [READY]")
        except Exception as e:
            print(f"   >>> Failed to generate level {level}: {e}")
    print("[Key Lifecycle Manager] Status: ONLINE.\n")


def run_classical_test(message: bytes, sec_level: int):
    """Executes ECDH and ECDSA benchmarks."""
    priv_a, pub_a = classical.generate_ecdh_keypair(sec_level)
    priv_b, pub_b = classical.generate_ecdh_keypair(sec_level)

    t1 = measure_time(classical.derive_shared_key_ecdh, priv_a, pub_b)
    t2 = measure_time(classical.derive_shared_key_ecdh, priv_b, pub_a)

    sign_t = measure_time(classical.ec_sign, priv_a, message)
    sig = sign_t['result']
    verify_t = measure_time(classical.ec_verify, pub_a, message, sig)

    pk_bytes = classical.serialize_public_key(pub_a)
    sk_bytes = classical.serialize_private_key(priv_a)

    curve_name = "P-256" if sec_level <= 2 else "P-384" if sec_level <= 4 else "P-521"

    sizes = {
        'pubkey_size': len(pk_bytes),
        'privkey_size': len(sk_bytes),
        'signature_size': len(sig)
    }

    cpu_time_ms = sign_t['time_ms'] + verify_t['time_ms'] + t1['time_ms'] + t2['time_ms']

    return {
        'algorithm': f"ECDH-{curve_name} + ECDSA",
        'sizes': sizes,
        'cpu_time_ms': cpu_time_ms
    }


def run_pqc_test(message: bytes, sec_level: int):
    """Executes Kyber and Dilithium benchmarks."""
    kem_obj = KyberKEM(security_level=sec_level)
    sig_obj = DilithiumSig(security_level=sec_level)

    # Use pre-generated keys if available
    pool_level = 3 if sec_level == 4 else sec_level
    if pool_level in KEY_POOL:
        pk = KEY_POOL[pool_level]['pk']
    else:
        pk, _ = kem_obj.generate_keypair()

    t_start = time.perf_counter()
    ciphertext, shared_secret = kem_obj.encapsulate(pk)
    t_end = time.perf_counter()

    real_cpu_time = (t_end - t_start) * 1000.0

    pk_sig, sk_sig = sig_obj.generate_keypair()
    signature = sig_obj.sign(message, sk_sig)
    verify_ok = sig_obj.verify(message, signature, pk_sig)

    sizes = {
        'kem_ciphertext': len(ciphertext),
        'signature_size': len(signature)
    }

    return {
        'algorithm': f"{kem_obj.name} + {sig_obj.name}",
        'signature_valid': verify_ok,
        'sizes': sizes,
        'cpu_time_ms': real_cpu_time
    }


# ==========================================
# 2. SIMULATION CONFIG
# ==========================================
CLIENTS = [
    {'type': 'iot', 'security': 2},
    {'type': 'mobile', 'security': 3},
    {'type': 'desktop', 'security': 3},
    {'type': 'server', 'security': 5}
]


# ==========================================
# 3. MAIN SIMULATION LOOP
# ==========================================
def main():
    pre_generate_keys()

    cloud_service = CloudService(
        service_name="API-Auth-Service",
        base_latency_ms=30,
        max_concurrent_requests=5
    )

    results = []
    CURRENT_STATE = 'classical'
    NUM_RUNS = 5

    print("Running Crypto-Agile MVP Simulation...")
    print("=" * 70)

    for client in CLIENTS:
        client_type = client['type']
        sec_level = client['security']

        print(f"\nProcessing Client: {client_type.upper()} (Level {sec_level})")
        print("-" * 40)

        for i in range(NUM_RUNS):
            cls = run_classical_test(MESSAGE, sec_level)
            pqc_res = run_pqc_test(MESSAGE, sec_level)

            # Performance Modeling
            base_pqc_size = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']
            base_latency = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=base_pqc_size)

            network_jitter = random.uniform(0, 1200.0)
            service_metrics = cloud_service.process_request()
            service_delay = service_metrics['service_delay_ms']

            final_latency_pqc = base_latency + network_jitter + service_delay + pqc_res['cpu_time_ms']

            # Decision Logic
            new_state, meta = decide_suite(
                current_state=CURRENT_STATE,
                security_req=sec_level,
                client_type=client_type,
                est_latency_pqc=final_latency_pqc
            )

            # Watchdog Guard
            if new_state == 'pqc' and final_latency_pqc > 500.0:
                new_state = 'classical'
                meta['reason'] = "Watchdog Override"
                meta['sv_api'] = 0.0

            CURRENT_STATE = new_state
            chosen_algo = pqc_res['algorithm'] if new_state == 'pqc' else cls['algorithm']

            print(f"   [Run {i + 1}] Score={meta['sv_api']:.2f} | Action={new_state.upper()}")

            results.append({
                'run_id': i + 1,
                'client': client_type,
                'security_req': sec_level,
                'jitter_ms': network_jitter,
                'final_latency_ms': final_latency_pqc,
                'new_state': new_state,
                'chosen_algorithm': chosen_algo,
                'sv_score': meta['sv_api'],
                'decision_reason': meta['reason']
            })

    write_results_csv(results, filename="results.csv")
    print("\nSimulation Complete. Results saved.")


if __name__ == "__main__":
    main()
