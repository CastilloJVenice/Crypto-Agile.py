import random
import csv
from metrics import measure_time, write_results_csv
from switching import estimate_latency_ms_for_suite, decide_suite
import classical
from pqc import KyberKEM, DilithiumSig
import time
from cryptography.hazmat.primitives import serialization

# Prepare test message
MESSAGE = b'Test message for authentication and key exchange'

# Test cases (Updated to stress test different Levels)
CLIENTS = [
    {'type': 'iot', 'security': 2},  # Should use Level 1 (Kyber512) if switched
    {'type': 'mobile', 'security': 3},  # Should use Level 3 (Kyber768) if switched
    {'type': 'desktop', 'security': 4},  # Should use Level 3 (Kyber768) if switched
    {'type': 'server', 'security': 5}  # Should use Level 5 (Kyber1024) if switched
]


# --- Classical test (Updated for Levels) ---
def run_classical_test(message: bytes, sec_level: int):
    # 1. Generate keys based on Security Level (P-256, P-384, or P-521)
    priv_a, pub_a = classical.generate_ecdh_keypair(sec_level)
    priv_b, pub_b = classical.generate_ecdh_keypair(sec_level)


    # 2. Measure Key Exchange
    t1 = measure_time(classical.derive_shared_key_ecdh, priv_a, pub_b)
    t2 = measure_time(classical.derive_shared_key_ecdh, priv_b, pub_a)

    # 3. Measure Signing
    sign_t = measure_time(classical.ec_sign, priv_a, message)
    sig = sign_t['result']
    verify_t = measure_time(classical.ec_verify, pub_a, message, sig)

    # 4. Serialize to measure size
    pk_bytes = classical.serialize_public_key(pub_a)
    sk_bytes = classical.serialize_private_key(priv_a)

    # Determine Curve Name for logging
    if sec_level <= 2:
        curve_name = "P-256"
    elif sec_level <= 4:
        curve_name = "P-384"
    else:
        curve_name = "P-521"

    sizes = {
        'pubkey_size': len(pk_bytes),
        'privkey_size': len(sk_bytes),
        'signature_size': len(sig)
    }

    cpu_time_ms = sign_t['time_ms'] + verify_t['time_ms'] + t1['time_ms'] + t2['time_ms']

    return {
        'algorithm': f"ECDH-{curve_name} + ECDSA",
        'sizes': sizes,
        'cpu_time_ms': cpu_time_ms,
    }


# --- PQC test (Updated for Levels) ---
def run_pqc_test(message: bytes, sec_level: int):
    kem_obj = KyberKEM(security_level=sec_level)
    sig_obj = DilithiumSig(security_level=sec_level)

    # --- START TIMER (Includes Generation) ---
    t_start = time.perf_counter()

    # 1. Generate Keypair (The heavy math part)
    pk, sk = kem_obj.generate_keypair()

    # 2. Encapsulate
    ciphertext, shared_secret = kem_obj.encapsulate(pk)

    # --- STOP TIMER ---
    t_end = time.perf_counter()
    real_cpu_time = (t_end - t_start) * 1000.0

    # 3. Sign & Verify (Dilithium)
    pk_sig, sk_sig = sig_obj.generate_keypair()
    signature = sig_obj.sign(message, sk_sig)
    verify_ok = sig_obj.verify(message, signature, pk_sig)

    sizes = {
        'kem_ciphertext': len(ciphertext),
        'signature_size': len(signature)
    }

    algo_name = f"{kem_obj.name} + {sig_obj.name}"

    return {
        'algorithm': algo_name,
        'signature_valid': verify_ok,
        'sizes': sizes,
        'cpu_time_ms': real_cpu_time,  # Captures the slow generation time
    }


# --- Main ---
def main():
    results = []
    print("Running Crypto-Agile MVP (Multi-Level Security Simulation)...")
    print("=" * 70)

    CURRENT_STATE = 'classical'

    for client in CLIENTS:
        client_type = client['type']
        sec_level = client['security']

        # --- FIX: Pass sec_level to the test functions ---
        cls = run_classical_test(MESSAGE, sec_level)
        pqc_res = run_pqc_test(MESSAGE, sec_level)

        # 1. Calculate Latency based on PQC packet size
        base_pqc_size = pqc_res['sizes']['signature_size'] + pqc_res['sizes']['kem_ciphertext']
        base_latency = estimate_latency_ms_for_suite('pqc', baseline_ms=5.0, size_bytes=base_pqc_size)

        # 2. Add Network Jitter
        network_jitter = random.uniform(0, 200.0)
        final_latency_pqc = base_latency + network_jitter

        print(f"\n[Client: {client_type.upper()} | Security Level: {sec_level}]")
        print(f"  --- Data Plane Metrics ---")
        print(f"  Classical ({cls['algorithm']}): Sig={cls['sizes']['signature_size']}B")
        print(
            f"  PQC       ({pqc_res['algorithm']}): Sig={pqc_res['sizes']['signature_size']}B | CT={pqc_res['sizes']['kem_ciphertext']}B")
        print(f"  Telemetry: Jitter={network_jitter:.1f}ms | Est. Latency={final_latency_pqc:.1f}ms")

        # 3. Decision Logic
        new_state, meta = decide_suite(
            current_state=CURRENT_STATE,
            security_req=sec_level,
            client_type=client_type,
            est_latency_pqc=final_latency_pqc
        )

        #Watchdog
        WATCHDOG_LIMIT_MS = 500.0
        # Check if the Controller wants PQC, but the Latency is actually dangerous
        if new_state == 'pqc' and final_latency_pqc > WATCHDOG_LIMIT_MS:
            print(f"\n!!! WATCHDOG TRIGGERED: Latency ({final_latency_pqc:.1f}ms) > 500ms. Forcing Fallback.")
            new_state = 'classical'
            meta['reason'] = "Watchdog Override"
            meta['sv_api'] = 0.0  # Optional: Zero out score to reflect failure

        CURRENT_STATE = new_state

        # Log exactly which algorithm was chosen
        chosen_algo = pqc_res['algorithm'] if new_state == 'pqc' else cls['algorithm']

        row = {
            'client': client_type,
            'security_req': sec_level,
            'jitter_ms': network_jitter,
            'final_latency': final_latency_pqc,
            'start_state': CURRENT_STATE,
            'new_state': new_state,
            'chosen_algorithm': chosen_algo,  # NEW COLUMN
            'sv_score': meta['sv_api'],
            'decision_reason': meta['reason'],
            'pqc_sig_size': pqc_res['sizes']['signature_size'],
            'cls_sig_size': cls['sizes']['signature_size']
        }

        print(f"  --- Control Plane Decision ---")
        print(f"  SV Score: {meta['sv_api']:.3f} -> {meta['reason']}")
        print(f"  ACTION:   Active Suite is now [{chosen_algo}]")

        results.append(row)

    write_results_csv(results)
    print("\n" + "=" * 70)
    print("Results saved to results.csv")


if __name__ == '__main__':
    main()